"""
Lambda Function: Generate Presigned URL
Purpose: Creates S3 presigned URLs for file uploads and downloads
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
FILES_TABLE = os.environ.get("FILES_TABLE", "campus-cloud-files")
S3_BUCKET = os.environ.get("S3_BUCKET", "campus-cloud-files-bucket")
UPLOAD_URL_EXPIRATION = int(os.environ.get("UPLOAD_URL_EXPIRATION", "300"))  # 5 minutes
DOWNLOAD_URL_EXPIRATION = int(
    os.environ.get("DOWNLOAD_URL_EXPIRATION", "900")
)  # 15 minutes
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "104857600"))  # 100MB

# Allowed file types (MIME types)
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/zip",
    "application/x-zip-compressed",
    "video/mp4",
    "video/mpeg",
]


def lambda_handler(event, context):
    """
    Main Lambda handler for presigned URL generation

    Supports both upload and download presigned URL generation
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract user info from authorizer context
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        user_email = event["requestContext"]["authorizer"]["claims"]["email"]

        # Determine request type (upload or download)
        http_method = event["httpMethod"]
        path = event["path"]

        if http_method == "POST" and "/upload-url" in path:
            return handle_upload_url(event, user_id, user_email)
        elif http_method == "POST" and "/download-url" in path:
            return handle_download_url(event, user_id, user_email)
        else:
            return create_response(400, {"error": "Invalid request"})

    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        return create_response(
            400,
            {"error": "Bad Request", "message": f"Missing required field: {str(e)}"},
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_upload_url(event, user_id, user_email):
    """
    Generate presigned URL for file upload
    """
    try:
        # Parse request body
        body = json.loads(event["body"])
        filename = body["filename"]
        content_type = body["contentType"]
        file_size = body["fileSize"]
        metadata = body.get("metadata", {})

        # Validate inputs
        validation_error = validate_upload_request(filename, content_type, file_size)
        if validation_error:
            return create_response(400, validation_error)

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Create S3 key
        s3_key = f"users/{user_id}/files/{file_id}"

        # Generate presigned POST URL
        presigned_post = s3_client.generate_presigned_post(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Fields={
                "Content-Type": content_type,
                "x-amz-meta-original-filename": filename,
                "x-amz-meta-user-id": user_id,
                "x-amz-meta-file-id": file_id,
            },
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, file_size + 1000],  # Allow small overhead
                {"x-amz-meta-original-filename": filename},
                {"x-amz-meta-user-id": user_id},
                {"x-amz-meta-file-id": file_id},
            ],
            ExpiresIn=UPLOAD_URL_EXPIRATION,
        )

        # Store pending upload in DynamoDB
        table = dynamodb.Table(FILES_TABLE)
        timestamp = datetime.utcnow().isoformat() + "Z"

        table.put_item(
            Item={
                "userId": user_id,
                "fileId": file_id,
                "filename": filename,
                "fileSize": file_size,
                "contentType": content_type,
                "s3Key": s3_key,
                "s3Bucket": S3_BUCKET,
                "status": "pending",
                "uploadedAt": timestamp,
                "lastModified": timestamp,
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "metadata": metadata,
                "downloadCount": 0,
                "isPublic": False,
            }
        )

        logger.info(f"Generated upload URL for file {file_id}")

        return create_response(
            200,
            {
                "fileId": file_id,
                "uploadUrl": presigned_post["url"],
                "uploadFields": presigned_post["fields"],
                "expiresIn": UPLOAD_URL_EXPIRATION,
                "uploadMethod": "POST",
                "s3Key": s3_key,
            },
        )

    except json.JSONDecodeError:
        return create_response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )
    except KeyError as e:
        return create_response(
            400,
            {"error": "Bad Request", "message": f"Missing required field: {str(e)}"},
        )


def handle_download_url(event, user_id, user_email):
    """
    Generate presigned URL for file download
    """
    try:
        # Extract file ID from path
        path_params = event.get("pathParameters", {})
        file_id = path_params.get("fileId")

        if not file_id:
            return create_response(
                400, {"error": "Bad Request", "message": "File ID is required"}
            )

        # Get file metadata from DynamoDB
        table = dynamodb.Table(FILES_TABLE)

        # First, try to get the file by fileId using GSI
        response = table.query(
            IndexName="FileIdIndex",
            KeyConditionExpression="fileId = :fid",
            ExpressionAttributeValues={":fid": file_id},
        )

        if not response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "File not found"}
            )

        file_item = response["Items"][0]

        # Check if user has access (owner or shared)
        has_access = False

        if file_item["userId"] == user_id:
            has_access = True
        else:
            # Check if file is shared with user
            has_access = check_file_share_access(file_id, user_id)

        if not has_access:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "You do not have access to this file",
                },
            )

        # Check file status
        if file_item["status"] != "active":
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": f"File is not available (status: {file_item['status']})",
                },
            )

        # Generate presigned GET URL
        s3_key = file_item["s3Key"]
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": s3_key,
                "ResponseContentDisposition": f'attachment; filename="{file_item["filename"]}"',
                "ResponseContentType": file_item["contentType"],
            },
            ExpiresIn=DOWNLOAD_URL_EXPIRATION,
        )

        # Update download count
        table.update_item(
            Key={"userId": file_item["userId"], "fileId": file_id},
            UpdateExpression="SET downloadCount = downloadCount + :inc",
            ExpressionAttributeValues={":inc": 1},
        )

        logger.info(f"Generated download URL for file {file_id}")

        return create_response(
            200,
            {
                "downloadUrl": download_url,
                "filename": file_item["filename"],
                "contentType": file_item["contentType"],
                "fileSize": int(file_item["fileSize"]),
                "expiresIn": DOWNLOAD_URL_EXPIRATION,
            },
        )

    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def validate_upload_request(filename, content_type, file_size):
    """
    Validate upload request parameters
    """
    # Check filename
    if not filename or len(filename) > 255:
        return {
            "error": "Bad Request",
            "message": "Filename must be between 1 and 255 characters",
        }

    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        return {
            "error": "Bad Request",
            "message": f"Content type {content_type} is not allowed",
            "allowedTypes": ALLOWED_CONTENT_TYPES,
        }

    # Check file size
    if file_size <= 0:
        return {"error": "Bad Request", "message": "File size must be greater than 0"}

    if file_size > MAX_FILE_SIZE:
        return {
            "error": "Payload Too Large",
            "message": f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes ({MAX_FILE_SIZE / 1024 / 1024}MB)",
            "maxSize": MAX_FILE_SIZE,
        }

    return None


def check_file_share_access(file_id, user_id):
    """
    Check if file is shared with user
    """
    try:
        shares_table = dynamodb.Table(
            os.environ.get("SHARES_TABLE", "campus-cloud-shares")
        )

        response = shares_table.query(
            KeyConditionExpression="fileId = :fid AND sharedWithUserId = :uid",
            ExpressionAttributeValues={":fid": file_id, ":uid": user_id},
        )

        if response["Items"]:
            share = response["Items"][0]

            # Check if share is active
            if share["status"] != "active":
                return False

            # Check if share has expired
            if "expiresAt" in share:
                expiry = datetime.fromisoformat(
                    share["expiresAt"].replace("Z", "+00:00")
                )
                if datetime.utcnow().replace(tzinfo=expiry.tzinfo) > expiry:
                    return False

            return True

        return False

    except Exception as e:
        logger.error(f"Error checking share access: {str(e)}")
        return False


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
