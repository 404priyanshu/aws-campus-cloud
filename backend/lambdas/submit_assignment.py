"""
Lambda Function: Submit Assignment
Purpose: Handles student assignment submissions and instructor grading
"""

import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

# Environment variables
FILES_TABLE = os.environ.get("FILES_TABLE", "campus-cloud-files")
ASSIGNMENTS_TABLE = os.environ.get("ASSIGNMENTS_TABLE", "campus-cloud-assignments")
SUBMISSIONS_TABLE = os.environ.get("SUBMISSIONS_TABLE", "campus-cloud-submissions")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "false").lower() == "true"


def lambda_handler(event, context):
    """
    Main Lambda handler for assignment submission operations

    Supports:
    - POST /assignments/{assignmentId}/submit - Submit assignment
    - GET /assignments/{assignmentId}/submissions - List submissions (instructor)
    - PUT /assignments/{assignmentId}/submissions/{submissionId}/grade - Grade submission
    - GET /assignments/{assignmentId}/submissions/me - Get my submissions
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract user info from authorizer context
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        user_email = event["requestContext"]["authorizer"]["claims"]["email"]
        user_name = event["requestContext"]["authorizer"]["claims"].get(
            "name", user_email
        )
        user_role = event["requestContext"]["authorizer"]["claims"].get(
            "cognito:groups", "student"
        )

        # Determine operation
        http_method = event["httpMethod"]
        path = event["path"]

        if http_method == "POST" and path.endswith("/submit"):
            return handle_submit_assignment(event, user_id, user_email, user_name)
        elif http_method == "GET" and "/submissions" in path and path.endswith("/me"):
            return handle_get_my_submissions(event, user_id)
        elif http_method == "GET" and "/submissions" in path:
            return handle_list_submissions(event, user_id, user_role)
        elif http_method == "PUT" and "/grade" in path:
            return handle_grade_submission(event, user_id, user_role, user_name)
        else:
            return create_response(400, {"error": "Invalid request"})

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_submit_assignment(event, user_id, user_email, user_name):
    """
    Submit a file for an assignment
    """
    try:
        # Extract assignment ID from path
        path_params = event.get("pathParameters", {})
        assignment_id = path_params.get("assignmentId")

        if not assignment_id:
            return create_response(
                400, {"error": "Bad Request", "message": "Assignment ID is required"}
            )

        # Parse request body
        body = json.loads(event["body"])
        file_id = body.get("fileId")
        comments = body.get("comments", "")

        if not file_id:
            return create_response(
                400, {"error": "Bad Request", "message": "File ID is required"}
            )

        # Get assignment details
        assignments_table = dynamodb.Table(ASSIGNMENTS_TABLE)

        assignment_response = assignments_table.query(
            IndexName="AssignmentIdIndex",
            KeyConditionExpression=Key("assignmentId").eq(assignment_id),
        )

        if not assignment_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "Assignment not found"}
            )

        assignment = assignment_response["Items"][0]

        # Check assignment status
        if assignment["status"] != "active":
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": f"Assignment is not active (status: {assignment['status']})",
                },
            )

        # Check deadline
        due_date = datetime.fromisoformat(assignment["dueDate"].replace("Z", "+00:00"))
        now = datetime.utcnow().replace(tzinfo=due_date.tzinfo)
        is_late = now > due_date

        # Verify file ownership and status
        files_table = dynamodb.Table(FILES_TABLE)

        file_response = files_table.get_item(Key={"userId": user_id, "fileId": file_id})

        if "Item" not in file_response:
            return create_response(
                404,
                {
                    "error": "Not Found",
                    "message": "File not found or you don't have access",
                },
            )

        file_item = file_response["Item"]

        if file_item["status"] != "active":
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "File is not active and cannot be submitted",
                },
            )

        # Validate file type
        if (
            "allowedFileTypes" in assignment
            and file_item["contentType"] not in assignment["allowedFileTypes"]
        ):
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": f"File type {file_item['contentType']} is not allowed for this assignment",
                    "allowedTypes": assignment["allowedFileTypes"],
                },
            )

        # Validate file size
        if (
            "maxFileSize" in assignment
            and file_item["fileSize"] > assignment["maxFileSize"]
        ):
            return create_response(
                400,
                {
                    "error": "Payload Too Large",
                    "message": f"File size exceeds maximum allowed size",
                    "maxSize": assignment["maxFileSize"],
                },
            )

        # Check submission count
        submissions_table = dynamodb.Table(SUBMISSIONS_TABLE)

        existing_submissions = submissions_table.query(
            KeyConditionExpression=Key("assignmentId").eq(assignment_id),
            FilterExpression=Attr("studentId").eq(user_id),
        )

        submission_count = len(existing_submissions.get("Items", []))
        max_submissions = assignment.get("maxSubmissions", 1)

        if submission_count >= max_submissions:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": f"Maximum submission limit reached ({max_submissions})",
                },
            )

        # Create submission record
        submission_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        submission_number = submission_count + 1

        submission_item = {
            "submissionId": submission_id,
            "assignmentId": assignment_id,
            "studentId": user_id,
            "studentEmail": user_email,
            "studentName": user_name,
            "fileId": file_id,
            "filename": file_item["filename"],
            "fileSize": file_item["fileSize"],
            "submittedAt": timestamp,
            "submissionNumber": submission_number,
            "status": "submitted",
            "isLate": is_late,
            "dueDate": assignment["dueDate"],
        }

        if comments:
            submission_item["comments"] = comments[:1000]  # Limit length

        # Save submission
        submissions_table.put_item(Item=submission_item)

        # Update assignment submission count
        assignments_table.update_item(
            Key={"courseId": assignment["courseId"], "assignmentId": assignment_id},
            UpdateExpression="SET submissionCount = submissionCount + :inc",
            ExpressionAttributeValues={":inc": 1},
        )

        # Send notification to instructor if enabled
        if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
            send_submission_notification(
                assignment["instructorEmail"], user_name, assignment["title"], is_late
            )

        logger.info(
            f"Assignment {assignment_id} submitted by {user_id}: submission {submission_id}"
        )

        return create_response(
            201,
            {
                "submissionId": submission_id,
                "assignmentId": assignment_id,
                "fileId": file_id,
                "filename": file_item["filename"],
                "student": {
                    "userId": user_id,
                    "email": user_email,
                    "name": user_name,
                },
                "submittedAt": timestamp,
                "submissionNumber": submission_number,
                "status": "submitted",
                "isLate": is_late,
                "comments": comments,
            },
        )

    except json.JSONDecodeError:
        return create_response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )
    except Exception as e:
        logger.error(f"Error submitting assignment: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_list_submissions(event, user_id, user_role):
    """
    List all submissions for an assignment (instructor only)
    """
    try:
        # Check if user is instructor
        if "instructor" not in user_role.lower() and "admin" not in user_role.lower():
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "Only instructors can view all submissions",
                },
            )

        # Extract assignment ID from path
        path_params = event.get("pathParameters", {})
        assignment_id = path_params.get("assignmentId")

        if not assignment_id:
            return create_response(
                400, {"error": "Bad Request", "message": "Assignment ID is required"}
            )

        # Parse query parameters
        query_params = event.get("queryStringParameters") or {}
        status_filter = query_params.get("status")
        limit = int(query_params.get("limit", 50))
        limit = min(limit, 100)
        next_token = query_params.get("nextToken")

        # Get assignment details
        assignments_table = dynamodb.Table(ASSIGNMENTS_TABLE)

        assignment_response = assignments_table.query(
            IndexName="AssignmentIdIndex",
            KeyConditionExpression=Key("assignmentId").eq(assignment_id),
        )

        if not assignment_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "Assignment not found"}
            )

        assignment = assignment_response["Items"][0]

        # Verify instructor owns this assignment
        if assignment["instructorId"] != user_id:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "You can only view submissions for your own assignments",
                },
            )

        # Query submissions
        submissions_table = dynamodb.Table(SUBMISSIONS_TABLE)

        query_kwargs = {
            "KeyConditionExpression": Key("assignmentId").eq(assignment_id),
            "Limit": limit,
        }

        if status_filter:
            query_kwargs["FilterExpression"] = Attr("status").eq(status_filter)

        if next_token:
            try:
                query_kwargs["ExclusiveStartKey"] = json.loads(next_token)
            except json.JSONDecodeError:
                logger.warning(f"Invalid next token: {next_token}")

        response = submissions_table.query(**query_kwargs)
        submissions = response.get("Items", [])

        # Calculate statistics
        all_submissions = submissions_table.query(
            KeyConditionExpression=Key("assignmentId").eq(assignment_id)
        ).get("Items", [])

        statistics = {
            "totalSubmissions": len(all_submissions),
            "onTime": len([s for s in all_submissions if not s.get("isLate", False)]),
            "late": len([s for s in all_submissions if s.get("isLate", False)]),
            "graded": len([s for s in all_submissions if s.get("status") == "graded"]),
            "pending": len(
                [s for s in all_submissions if s.get("status") == "submitted"]
            ),
        }

        # Format submissions
        formatted_submissions = [format_submission(s) for s in submissions]

        last_key = response.get("LastEvaluatedKey")
        new_next_token = json.dumps(last_key) if last_key else None

        return create_response(
            200,
            {
                "assignmentId": assignment_id,
                "assignmentTitle": assignment["title"],
                "submissions": formatted_submissions,
                "total": len(formatted_submissions),
                "statistics": statistics,
                "nextToken": new_next_token,
            },
        )

    except Exception as e:
        logger.error(f"Error listing submissions: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_get_my_submissions(event, user_id):
    """
    Get current user's submissions for an assignment
    """
    try:
        # Extract assignment ID from path
        path_params = event.get("pathParameters", {})
        assignment_id = path_params.get("assignmentId")

        if not assignment_id:
            return create_response(
                400, {"error": "Bad Request", "message": "Assignment ID is required"}
            )

        # Query user's submissions
        submissions_table = dynamodb.Table(SUBMISSIONS_TABLE)

        response = submissions_table.query(
            KeyConditionExpression=Key("assignmentId").eq(assignment_id),
            FilterExpression=Attr("studentId").eq(user_id),
        )

        submissions = response.get("Items", [])
        formatted_submissions = [format_submission(s) for s in submissions]

        return create_response(
            200,
            {
                "assignmentId": assignment_id,
                "submissions": formatted_submissions,
                "total": len(formatted_submissions),
            },
        )

    except Exception as e:
        logger.error(f"Error getting submissions: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_grade_submission(event, user_id, user_role, user_name):
    """
    Grade a student submission (instructor only)
    """
    try:
        # Check if user is instructor
        if "instructor" not in user_role.lower() and "admin" not in user_role.lower():
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "Only instructors can grade submissions",
                },
            )

        # Extract IDs from path
        path_params = event.get("pathParameters", {})
        assignment_id = path_params.get("assignmentId")
        submission_id = path_params.get("submissionId")

        if not assignment_id or not submission_id:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "Assignment ID and Submission ID are required",
                },
            )

        # Parse request body
        body = json.loads(event["body"])
        grade = body.get("grade")
        max_grade = body.get("maxGrade", 100)
        feedback = body.get("feedback", "")
        feedback_file_id = body.get("feedbackFileId")

        if grade is None:
            return create_response(
                400, {"error": "Bad Request", "message": "Grade is required"}
            )

        # Verify assignment ownership
        assignments_table = dynamodb.Table(ASSIGNMENTS_TABLE)

        assignment_response = assignments_table.query(
            IndexName="AssignmentIdIndex",
            KeyConditionExpression=Key("assignmentId").eq(assignment_id),
        )

        if not assignment_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "Assignment not found"}
            )

        assignment = assignment_response["Items"][0]

        if assignment["instructorId"] != user_id:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "You can only grade submissions for your own assignments",
                },
            )

        # Get submission
        submissions_table = dynamodb.Table(SUBMISSIONS_TABLE)

        submission_response = submissions_table.query(
            IndexName="SubmissionIdIndex",
            KeyConditionExpression=Key("submissionId").eq(submission_id),
        )

        if not submission_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "Submission not found"}
            )

        submission = submission_response["Items"][0]

        # Verify submission belongs to assignment
        if submission["assignmentId"] != assignment_id:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "Submission does not belong to this assignment",
                },
            )

        # Update submission with grade
        timestamp = datetime.utcnow().isoformat() + "Z"

        update_expression = "SET grade = :grade, maxGrade = :maxGrade, feedback = :feedback, gradedAt = :timestamp, gradedBy = :grader, gradedByName = :graderName, #status = :status"

        expression_values = {
            ":grade": Decimal(str(grade)),
            ":maxGrade": Decimal(str(max_grade)),
            ":feedback": feedback[:2000],  # Limit feedback length
            ":timestamp": timestamp,
            ":grader": user_id,
            ":graderName": user_name,
            ":status": "graded",
        }

        if feedback_file_id:
            update_expression += ", feedbackFileId = :feedbackFileId"
            expression_values[":feedbackFileId"] = feedback_file_id

        submissions_table.update_item(
            Key={
                "assignmentId": assignment_id,
                "studentId#submissionNumber": f"{submission['studentId']}#{submission['submissionNumber']}",
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=expression_values,
        )

        # Send notification to student if enabled
        if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
            send_grade_notification(
                submission["studentEmail"], assignment["title"], grade, max_grade
            )

        logger.info(f"Graded submission {submission_id}: {grade}/{max_grade}")

        return create_response(
            200,
            {
                "success": True,
                "submission": {
                    "submissionId": submission_id,
                    "grade": float(grade),
                    "maxGrade": float(max_grade),
                    "feedback": feedback,
                    "gradedAt": timestamp,
                    "gradedBy": {
                        "userId": user_id,
                        "name": user_name,
                    },
                    "status": "graded",
                },
            },
        )

    except json.JSONDecodeError:
        return create_response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )
    except Exception as e:
        logger.error(f"Error grading submission: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def format_submission(submission):
    """
    Format submission for API response
    """
    formatted = {
        "submissionId": submission["submissionId"],
        "student": {
            "userId": submission["studentId"],
            "email": submission["studentEmail"],
            "name": submission["studentName"],
        },
        "fileId": submission["fileId"],
        "filename": submission["filename"],
        "fileSize": int(submission["fileSize"]),
        "submittedAt": submission["submittedAt"],
        "submissionNumber": int(submission["submissionNumber"]),
        "status": submission["status"],
        "isLate": submission.get("isLate", False),
    }

    if "comments" in submission:
        formatted["comments"] = submission["comments"]

    if "grade" in submission:
        formatted["grade"] = float(submission["grade"])
        formatted["maxGrade"] = float(submission.get("maxGrade", 100))

    if "feedback" in submission:
        formatted["feedback"] = submission["feedback"]

    if "feedbackFileId" in submission:
        formatted["feedbackFileId"] = submission["feedbackFileId"]

    if "gradedAt" in submission:
        formatted["gradedAt"] = submission["gradedAt"]
        formatted["gradedBy"] = {
            "userId": submission.get("gradedBy"),
            "name": submission.get("gradedByName"),
        }

    return formatted


def send_submission_notification(
    instructor_email, student_name, assignment_title, is_late
):
    """
    Notify instructor of new submission
    """
    try:
        subject = f"New Assignment Submission: {assignment_title}"

        body = f"""
        {student_name} has submitted {assignment_title}.

        Status: {"Late submission" if is_late else "On time"}

        Log in to Campus Cloud to review and grade the submission.
        """

        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=body,
            MessageAttributes={
                "email": {"DataType": "String", "StringValue": instructor_email}
            },
        )

        logger.info(f"Sent submission notification to {instructor_email}")
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")


def send_grade_notification(student_email, assignment_title, grade, max_grade):
    """
    Notify student when submission is graded
    """
    try:
        subject = f"Your submission for {assignment_title} has been graded"

        body = f"""
        Your submission for {assignment_title} has been graded.

        Grade: {grade}/{max_grade}

        Log in to Campus Cloud to view detailed feedback.
        """

        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=body,
            MessageAttributes={
                "email": {"DataType": "String", "StringValue": student_email}
            },
        )

        logger.info(f"Sent grade notification to {student_email}")
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")


def create_response(status_code, body):
    """
    Create HTTP response with CORS headers
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=decimal_default),
    }


def decimal_default(obj):
    """
    JSON serializer for Decimal objects
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
