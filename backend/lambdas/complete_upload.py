"""
Lambda Function: Complete Upload
Purpose: Marks file upload as complete and updates DynamoDB metadata
"""

import json
import logging
import os
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
FILES_TABLE = os.environ.get("FILES_TABLE", "campus-cloud-files")
S3_BUCKET = os.environ.get("S3_BUCKET", "campus-cloud-files-bucket")


def lambda_handler(event, context):
    """
    Main Lambda handler for completing file upload

    This function is called after the client successfully uploads a file to S3
    using a presigned URL. It verifies the upload and updates the file status.
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract user info from authorizer context
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        user_email = event["requestContext"]["authorizer"]["claims"]["email"]

        # Extract file ID from path parameters
        path_params = event.get("pathParameters", {})
        file_id = path_params.get("fileId")

        if not file_id:
            return create_response(
                400, {"error": "Bad Request", "message": "File ID is required"}
            )

        # Parse request body
        body = json.loads(event["body"])
        upload_success = body.get("uploadSuccess", False)
        s3_key = body.get("s3Key")
        checksum = body.get("checksum")

        if not upload_success:
            logger.warning(f"Upload marked as failed for file {file_id}")
            return handle_failed_upload(user_id, file_id)

        if not s3_key:
            return create_response(
                400, {"error": "Bad Request", "message": "S3 key is required"}
            )

        # Get file metadata from DynamoDB
        table = dynamodb.Table(FILES_TABLE)

        try:
            response = table.get_item(Key={"userId": user_id, "fileId": file_id})
        except ClientError as e:
            logger.error(f"DynamoDB error: {str(e)}")
            return create_response(
                500,
                {
                    "error": "Database Error",
                    "message": "Failed to retrieve file metadata",
                },
            )

        if "Item" not in response:
            return create_response(
                404, {"error": "Not Found", "message": "File not found"}
            )

        file_item = response["Item"]

        # Verify file belongs to user
        if file_item["userId"] != user_id:
            return create_response(
                403, {"error": "Forbidden", "message": "File does not belong to user"}
            )

        # Check if already completed
        if file_item.get("status") == "active":
            logger.info(f"File {file_id} already marked as complete")
            return create_response(
                200,
                {
                    "success": True,
                    "message": "File already completed",
                    "file": format_file_response(file_item, user_email),
                },
            )

        # Verify file exists in S3
        try:
            s3_response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            actual_file_size = s3_response["ContentLength"]
            s3_etag = s3_response.get("ETag", "").strip('"')

            logger.info(f"S3 file verified: {s3_key}, size: {actual_file_size}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.error(f"File not found in S3: {s3_key}")
                return create_response(
                    404,
                    {
                        "error": "Not Found",
                        "message": "File not found in S3. Upload may have failed.",
                    },
                )
            else:
                logger.error(f"S3 error: {str(e)}")
                return create_response(
                    500, {"error": "S3 Error", "message": "Failed to verify file in S3"}
                )

        # Update file status in DynamoDB
        timestamp = datetime.utcnow().isoformat() + "Z"

        update_expression = "SET #status = :status, lastModified = :timestamp"
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {
            ":status": "active",
            ":timestamp": timestamp,
        }

        # Add actual file size if different
        if actual_file_size != file_item.get("fileSize", 0):
            update_expression += ", fileSize = :fileSize"
            expression_attribute_values[":fileSize"] = actual_file_size

        # Add checksum if provided
        if checksum:
            update_expression += ", checksum = :checksum"
            expression_attribute_values[":checksum"] = checksum
        elif s3_etag:
            update_expression += ", checksum = :checksum"
            expression_attribute_values[":checksum"] = s3_etag

        # Add virus scan status
        update_expression += ", virusScanStatus = :virusScanStatus"
        expression_attribute_values[":virusScanStatus"] = "pending"

        try:
            table.update_item(
                Key={"userId": user_id, "fileId": file_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression="attribute_exists(fileId)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return create_response(
                    404, {"error": "Not Found", "message": "File not found"}
                )
            else:
                logger.error(f"DynamoDB update error: {str(e)}")
                return create_response(
                    500,
                    {
                        "error": "Database Error",
                        "message": "Failed to update file status",
                    },
                )

        # Get updated item
        response = table.get_item(Key={"userId": user_id, "fileId": file_id})
        updated_file = response["Item"]

        logger.info(f"Upload completed successfully for file {file_id}")

        return create_response(
            200,
            {
                "success": True,
                "message": "Upload completed successfully",
                "file": format_file_response(updated_file, user_email),
            },
        )

    except json.JSONDecodeError:
        return create_response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        return create_response(
            400,
            {"error": "Bad Request", "message": f"Missing required field: {str(e)}"},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_failed_upload(user_id, file_id):
    """
    Handle failed upload by marking file as failed in DynamoDB
    """
    try:
        table = dynamodb.Table(FILES_TABLE)
        timestamp = datetime.utcnow().isoformat() + "Z"

        table.update_item(
            Key={"userId": user_id, "fileId": file_id},
            UpdateExpression="SET #status = :status, lastModified = :timestamp",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "failed",
                ":timestamp": timestamp,
            },
        )

        logger.info(f"Marked file {file_id} as failed")

        return create_response(
            200,
            {
                "success": False,
                "message": "Upload marked as failed",
                "fileId": file_id,
            },
        )

    except Exception as e:
        logger.error(f"Error handling failed upload: {str(e)}")
        return create_response(
            500,
            {
                "error": "Internal Server Error",
                "message": "Failed to update upload status",
            },
        )


def format_file_response(file_item, user_email):
    """
    Format file item for API response
    """
    return {
        "fileId": file_item["fileId"],
        "filename": file_item["filename"],
        "fileSize": int(file_item["fileSize"]),
        "contentType": file_item["contentType"],
        "uploadedAt": file_item["uploadedAt"],
        "lastModified": file_item.get("lastModified", file_item["uploadedAt"]),
        "status": file_item["status"],
        "s3Key": file_item["s3Key"],
        "owner": {
            "userId": file_item["userId"],
            "email": user_email,
        },
        "description": file_item.get("description", ""),
        "tags": file_item.get("tags", []),
        "metadata": file_item.get("metadata", {}),
        "downloadCount": int(file_item.get("downloadCount", 0)),
        "checksum": file_item.get("checksum"),
        "virusScanStatus": file_item.get("virusScanStatus", "pending"),
    }


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
