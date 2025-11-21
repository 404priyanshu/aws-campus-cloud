"""
Lambda Function: Share File
Purpose: Shares a file with other users and manages file sharing permissions
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

# Environment variables
FILES_TABLE = os.environ.get("FILES_TABLE", "campus-cloud-files")
SHARES_TABLE = os.environ.get("SHARES_TABLE", "campus-cloud-shares")
USERS_TABLE = os.environ.get("USERS_TABLE", "campus-cloud-users")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "false").lower() == "true"


def lambda_handler(event, context):
    """
    Main Lambda handler for file sharing operations

    Supports:
    - POST /files/{fileId}/share - Share file with users
    - GET /files/{fileId}/shares - List file shares
    - DELETE /files/{fileId}/shares/{shareId} - Revoke share
    - GET /shared-with-me - List files shared with user
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract user info from authorizer context
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        user_email = event["requestContext"]["authorizer"]["claims"]["email"]
        user_name = event["requestContext"]["authorizer"]["claims"].get(
            "name", user_email
        )

        # Determine operation based on HTTP method and path
        http_method = event["httpMethod"]
        path = event["path"]

        if http_method == "POST" and "/share" in path:
            return handle_share_file(event, user_id, user_email, user_name)
        elif http_method == "GET" and "/shares" in path:
            return handle_list_shares(event, user_id)
        elif http_method == "DELETE" and "/shares/" in path:
            return handle_revoke_share(event, user_id)
        elif http_method == "GET" and "shared-with-me" in path:
            return handle_shared_with_me(event, user_id)
        else:
            return create_response(400, {"error": "Invalid request"})

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_share_file(event, user_id, user_email, user_name):
    """
    Share a file with one or more users
    """
    try:
        # Extract file ID from path parameters
        path_params = event.get("pathParameters", {})
        file_id = path_params.get("fileId")

        if not file_id:
            return create_response(
                400, {"error": "Bad Request", "message": "File ID is required"}
            )

        # Parse request body
        body = json.loads(event["body"])
        recipients = body.get("recipients", [])
        message = body.get("message", "")
        expires_at = body.get("expiresAt")

        if not recipients or len(recipients) == 0:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "At least one recipient is required",
                },
            )

        if len(recipients) > 50:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "Cannot share with more than 50 users at once",
                },
            )

        # Verify file ownership
        files_table = dynamodb.Table(FILES_TABLE)

        try:
            file_response = files_table.query(
                IndexName="FileIdIndex",
                KeyConditionExpression=Key("fileId").eq(file_id),
            )

            if not file_response["Items"]:
                return create_response(
                    404, {"error": "Not Found", "message": "File not found"}
                )

            file_item = file_response["Items"][0]

            # Check ownership
            if file_item["userId"] != user_id:
                return create_response(
                    403,
                    {
                        "error": "Forbidden",
                        "message": "You can only share files you own",
                    },
                )

            # Check file status
            if file_item["status"] != "active":
                return create_response(
                    400,
                    {"error": "Bad Request", "message": "Cannot share inactive file"},
                )

        except ClientError as e:
            logger.error(f"Error retrieving file: {str(e)}")
            return create_response(
                500, {"error": "Database Error", "message": "Failed to retrieve file"}
            )

        # Process each recipient
        shares_table = dynamodb.Table(SHARES_TABLE)
        successful_shares = []
        failed_shares = []

        for recipient in recipients:
            recipient_email = recipient.get("email")
            permissions = recipient.get("permissions", "read")

            if not recipient_email:
                failed_shares.append({"error": "Missing email"})
                continue

            # Validate email format (basic check)
            if "@" not in recipient_email or "." not in recipient_email:
                failed_shares.append(
                    {"email": recipient_email, "error": "Invalid email format"}
                )
                continue

            # Prevent sharing with self
            if recipient_email.lower() == user_email.lower():
                failed_shares.append(
                    {"email": recipient_email, "error": "Cannot share with yourself"}
                )
                continue

            # Look up recipient user
            recipient_user = get_user_by_email(recipient_email)

            if not recipient_user:
                # For now, we'll allow sharing with emails not in the system
                # They'll need to sign up to access
                recipient_user_id = f"pending-{uuid.uuid4()}"
                logger.info(f"Sharing with non-registered user: {recipient_email}")
            else:
                recipient_user_id = recipient_user["userId"]

            # Check if already shared
            existing_share = check_existing_share(file_id, recipient_user_id)

            if existing_share and existing_share["status"] == "active":
                failed_shares.append(
                    {
                        "email": recipient_email,
                        "error": "File already shared with this user",
                    }
                )
                continue

            # Create share record
            share_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"

            share_item = {
                "shareId": share_id,
                "fileId": file_id,
                "ownerId": user_id,
                "sharedWithUserId": recipient_user_id,
                "sharedWithEmail": recipient_email,
                "permissions": permissions,
                "sharedAt": timestamp,
                "status": "active",
                "accessCount": 0,
            }

            # Add optional fields
            if message:
                share_item["message"] = message[:500]  # Limit message length

            if expires_at:
                share_item["expiresAt"] = expires_at
                # Calculate TTL for auto-deletion (Unix timestamp)
                try:
                    expiry_dt = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                    share_item["ttl"] = int(expiry_dt.timestamp())
                except Exception as e:
                    logger.warning(
                        f"Invalid expiry date: {expires_at}, error: {str(e)}"
                    )

            try:
                shares_table.put_item(Item=share_item)

                successful_shares.append(
                    {
                        "shareId": share_id,
                        "email": recipient_email,
                        "sharedAt": timestamp,
                        "expiresAt": expires_at,
                        "status": "active",
                    }
                )

                # Send notification if enabled
                if ENABLE_NOTIFICATIONS and SNS_TOPIC_ARN:
                    send_share_notification(
                        recipient_email, user_name, file_item["filename"], message
                    )

            except ClientError as e:
                logger.error(f"Error creating share for {recipient_email}: {str(e)}")
                failed_shares.append(
                    {"email": recipient_email, "error": "Failed to create share"}
                )

        logger.info(
            f"Shared file {file_id}: {len(successful_shares)} successful, {len(failed_shares)} failed"
        )

        return create_response(
            200,
            {
                "success": True,
                "shared": successful_shares,
                "failed": failed_shares,
                "totalShared": len(successful_shares),
                "totalFailed": len(failed_shares),
            },
        )

    except json.JSONDecodeError:
        return create_response(
            400, {"error": "Bad Request", "message": "Invalid JSON in request body"}
        )
    except Exception as e:
        logger.error(f"Error sharing file: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_list_shares(event, user_id):
    """
    List all shares for a specific file
    """
    try:
        # Extract file ID from path parameters
        path_params = event.get("pathParameters", {})
        file_id = path_params.get("fileId")

        if not file_id:
            return create_response(
                400, {"error": "Bad Request", "message": "File ID is required"}
            )

        # Verify file ownership
        files_table = dynamodb.Table(FILES_TABLE)

        file_response = files_table.query(
            IndexName="FileIdIndex", KeyConditionExpression=Key("fileId").eq(file_id)
        )

        if not file_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "File not found"}
            )

        file_item = file_response["Items"][0]

        if file_item["userId"] != user_id:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "You can only view shares for files you own",
                },
            )

        # Get all shares for this file
        shares_table = dynamodb.Table(SHARES_TABLE)

        response = shares_table.query(KeyConditionExpression=Key("fileId").eq(file_id))

        shares = response.get("Items", [])

        # Filter active shares and add user details
        active_shares = []
        for share in shares:
            if share["status"] != "active":
                continue

            # Check if expired
            if "expiresAt" in share:
                expiry = datetime.fromisoformat(
                    share["expiresAt"].replace("Z", "+00:00")
                )
                if datetime.utcnow().replace(tzinfo=expiry.tzinfo) > expiry:
                    continue

            formatted_share = {
                "shareId": share["shareId"],
                "sharedWith": {
                    "userId": share["sharedWithUserId"],
                    "email": share["sharedWithEmail"],
                },
                "sharedAt": share["sharedAt"],
                "permissions": share["permissions"],
                "status": share["status"],
                "accessCount": int(share.get("accessCount", 0)),
            }

            if "expiresAt" in share:
                formatted_share["expiresAt"] = share["expiresAt"]

            if "lastAccessedAt" in share:
                formatted_share["lastAccessedAt"] = share["lastAccessedAt"]

            active_shares.append(formatted_share)

        return create_response(
            200,
            {
                "fileId": file_id,
                "filename": file_item["filename"],
                "shares": active_shares,
                "total": len(active_shares),
            },
        )

    except Exception as e:
        logger.error(f"Error listing shares: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_revoke_share(event, user_id):
    """
    Revoke a file share
    """
    try:
        # Extract IDs from path parameters
        path_params = event.get("pathParameters", {})
        file_id = path_params.get("fileId")
        share_id = path_params.get("shareId")

        if not file_id or not share_id:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "File ID and Share ID are required",
                },
            )

        # Verify file ownership
        files_table = dynamodb.Table(FILES_TABLE)

        file_response = files_table.query(
            IndexName="FileIdIndex", KeyConditionExpression=Key("fileId").eq(file_id)
        )

        if not file_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "File not found"}
            )

        file_item = file_response["Items"][0]

        if file_item["userId"] != user_id:
            return create_response(
                403,
                {
                    "error": "Forbidden",
                    "message": "You can only revoke shares for files you own",
                },
            )

        # Find and revoke the share
        shares_table = dynamodb.Table(SHARES_TABLE)

        # Query share by shareId using GSI
        share_response = shares_table.query(
            IndexName="ShareIdIndex", KeyConditionExpression=Key("shareId").eq(share_id)
        )

        if not share_response["Items"]:
            return create_response(
                404, {"error": "Not Found", "message": "Share not found"}
            )

        share = share_response["Items"][0]

        # Verify share belongs to this file
        if share["fileId"] != file_id:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "Share does not belong to this file",
                },
            )

        # Update share status to revoked
        shares_table.update_item(
            Key={"fileId": file_id, "sharedWithUserId": share["sharedWithUserId"]},
            UpdateExpression="SET #status = :status, revokedAt = :timestamp",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "revoked",
                ":timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

        logger.info(f"Revoked share {share_id} for file {file_id}")

        return create_response(
            200,
            {"success": True, "message": "Share access revoked", "shareId": share_id},
        )

    except Exception as e:
        logger.error(f"Error revoking share: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def handle_shared_with_me(event, user_id):
    """
    List all files shared with the authenticated user
    """
    try:
        # Parse query parameters
        query_params = event.get("queryStringParameters") or {}
        limit = int(query_params.get("limit", 20))
        limit = min(limit, 100)  # Max 100
        next_token = query_params.get("nextToken")

        shares_table = dynamodb.Table(SHARES_TABLE)
        files_table = dynamodb.Table(FILES_TABLE)

        # Query shares using GSI
        query_params = {
            "IndexName": "SharedWithUserIndex",
            "KeyConditionExpression": Key("sharedWithUserId").eq(user_id),
            "Limit": limit,
        }

        if next_token:
            try:
                query_params["ExclusiveStartKey"] = json.loads(next_token)
            except json.JSONDecodeError:
                logger.warning(f"Invalid next token: {next_token}")

        response = shares_table.query(**query_params)
        shares = response.get("Items", [])

        # Get file details for each share
        shared_files = []
        for share in shares:
            # Skip inactive or expired shares
            if share["status"] != "active":
                continue

            if "expiresAt" in share:
                expiry = datetime.fromisoformat(
                    share["expiresAt"].replace("Z", "+00:00")
                )
                if datetime.utcnow().replace(tzinfo=expiry.tzinfo) > expiry:
                    continue

            # Get file metadata
            try:
                file_response = files_table.query(
                    IndexName="FileIdIndex",
                    KeyConditionExpression=Key("fileId").eq(share["fileId"]),
                )

                if file_response["Items"]:
                    file_item = file_response["Items"][0]

                    shared_file = {
                        "fileId": file_item["fileId"],
                        "filename": file_item["filename"],
                        "fileSize": int(file_item["fileSize"]),
                        "contentType": file_item["contentType"],
                        "sharedBy": {
                            "userId": share["ownerId"],
                            "email": share.get("ownerEmail", ""),
                        },
                        "sharedAt": share["sharedAt"],
                        "permissions": share["permissions"],
                    }

                    if "expiresAt" in share:
                        shared_file["expiresAt"] = share["expiresAt"]

                    if "message" in share:
                        shared_file["message"] = share["message"]

                    shared_files.append(shared_file)
            except ClientError as e:
                logger.error(f"Error getting file {share['fileId']}: {str(e)}")
                continue

        last_key = response.get("LastEvaluatedKey")
        new_next_token = json.dumps(last_key) if last_key else None

        return create_response(
            200,
            {
                "files": shared_files,
                "total": len(shared_files),
                "nextToken": new_next_token,
            },
        )

    except Exception as e:
        logger.error(f"Error getting shared files: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def get_user_by_email(email):
    """
    Look up user by email address
    """
    try:
        users_table = dynamodb.Table(USERS_TABLE)

        response = users_table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(email.lower()),
        )

        if response["Items"]:
            return response["Items"][0]

        return None
    except Exception as e:
        logger.error(f"Error looking up user by email: {str(e)}")
        return None


def check_existing_share(file_id, user_id):
    """
    Check if file is already shared with user
    """
    try:
        shares_table = dynamodb.Table(SHARES_TABLE)

        response = shares_table.query(
            KeyConditionExpression=Key("fileId").eq(file_id)
            & Key("sharedWithUserId").eq(user_id)
        )

        if response["Items"]:
            return response["Items"][0]

        return None
    except Exception as e:
        logger.error(f"Error checking existing share: {str(e)}")
        return None


def send_share_notification(recipient_email, sharer_name, filename, message):
    """
    Send email notification when file is shared
    """
    try:
        subject = f"{sharer_name} shared a file with you"

        body = f"""
        {sharer_name} has shared a file with you on Campus Cloud.

        File: {filename}

        {f"Message: {message}" if message else ""}

        Log in to Campus Cloud to access the file.
        """

        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=body,
            MessageAttributes={
                "email": {"DataType": "String", "StringValue": recipient_email}
            },
        )

        logger.info(f"Sent share notification to {recipient_email}")
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
