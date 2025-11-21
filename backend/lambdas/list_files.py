"""
Lambda Function: List Files
Purpose: Retrieves list of files owned by or shared with the authenticated user
"""

import json
import logging
import os
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

# Environment variables
FILES_TABLE = os.environ.get("FILES_TABLE", "campus-cloud-files")
SHARES_TABLE = os.environ.get("SHARES_TABLE", "campus-cloud-shares")
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def lambda_handler(event, context):
    """
    Main Lambda handler for listing files

    Supports filtering, sorting, and pagination
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Extract user info from authorizer context
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        user_email = event["requestContext"]["authorizer"]["claims"]["email"]

        # Parse query parameters
        query_params = event.get("queryStringParameters") or {}

        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        limit = min(limit, MAX_LIMIT)  # Enforce max limit

        next_token = query_params.get("nextToken")
        filter_type = query_params.get("filter", "all")  # all, owned, shared
        sort_by = query_params.get("sortBy", "uploadedAt")
        sort_order = query_params.get("sortOrder", "desc")

        # Validate filter type
        if filter_type not in ["all", "owned", "shared"]:
            return create_response(
                400,
                {
                    "error": "Bad Request",
                    "message": "Invalid filter type. Must be 'all', 'owned', or 'shared'",
                },
            )

        # Get files based on filter
        if filter_type == "owned":
            files = get_owned_files(user_id, limit, next_token, sort_order)
        elif filter_type == "shared":
            files = get_shared_files(user_id, limit, next_token)
        else:  # all
            owned_files = get_owned_files(user_id, limit, next_token, sort_order)
            shared_files = get_shared_files(user_id, limit, next_token)

            # Combine and sort
            all_files = owned_files["files"] + shared_files["files"]
            all_files = sort_files(all_files, sort_by, sort_order)

            files = {
                "files": all_files[:limit],
                "total": owned_files["total"] + shared_files["total"],
                "nextToken": None,  # Simplified for combined view
            }

        # Format response
        formatted_files = [format_file_item(f, user_id) for f in files["files"]]

        response_body = {
            "files": formatted_files,
            "total": files["total"],
            "nextToken": files.get("nextToken"),
            "filter": filter_type,
            "limit": limit,
        }

        logger.info(f"Retrieved {len(formatted_files)} files for user {user_id}")

        return create_response(200, response_body)

    except ValueError as e:
        return create_response(
            400, {"error": "Bad Request", "message": f"Invalid parameter: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        return create_response(
            500, {"error": "Internal Server Error", "message": str(e)}
        )


def get_owned_files(user_id, limit, next_token, sort_order):
    """
    Get files owned by the user
    """
    try:
        table = dynamodb.Table(FILES_TABLE)

        # Build query parameters
        query_params = {
            "KeyConditionExpression": Key("userId").eq(user_id),
            "FilterExpression": Attr("status").eq("active"),
            "Limit": limit,
            "ScanIndexForward": (sort_order == "asc"),
        }

        # Add pagination token if provided
        if next_token:
            try:
                query_params["ExclusiveStartKey"] = json.loads(next_token)
            except json.JSONDecodeError:
                logger.warning(f"Invalid next token: {next_token}")

        # Execute query
        response = table.query(**query_params)

        files = response.get("Items", [])

        # Get share counts for each file
        for file in files:
            file["sharedWithCount"] = get_share_count(file["fileId"])

        # Prepare next token
        last_key = response.get("LastEvaluatedKey")
        new_next_token = json.dumps(last_key) if last_key else None

        return {"files": files, "total": len(files), "nextToken": new_next_token}

    except ClientError as e:
        logger.error(f"DynamoDB error getting owned files: {str(e)}")
        return {"files": [], "total": 0, "nextToken": None}


def get_shared_files(user_id, limit, next_token):
    """
    Get files shared with the user
    """
    try:
        shares_table = dynamodb.Table(SHARES_TABLE)
        files_table = dynamodb.Table(FILES_TABLE)

        # Query shares using GSI
        query_params = {
            "IndexName": "SharedWithUserIndex",
            "KeyConditionExpression": Key("sharedWithUserId").eq(user_id),
            "FilterExpression": Attr("status").eq("active"),
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
        files = []
        for share in shares:
            # Check if share has expired
            if "expiresAt" in share:
                expiry = datetime.fromisoformat(
                    share["expiresAt"].replace("Z", "+00:00")
                )
                if datetime.utcnow().replace(tzinfo=expiry.tzinfo) > expiry:
                    continue

            # Get file metadata using GSI
            try:
                file_response = files_table.query(
                    IndexName="FileIdIndex",
                    KeyConditionExpression=Key("fileId").eq(share["fileId"]),
                )

                if file_response["Items"]:
                    file = file_response["Items"][0]
                    file["sharedBy"] = {
                        "userId": share["ownerId"],
                        "email": share.get("sharedWithEmail", ""),
                    }
                    file["sharedAt"] = share["sharedAt"]
                    file["sharePermissions"] = share["permissions"]
                    file["isShared"] = True
                    files.append(file)
            except ClientError as e:
                logger.error(f"Error getting file {share['fileId']}: {str(e)}")
                continue

        last_key = response.get("LastEvaluatedKey")
        new_next_token = json.dumps(last_key) if last_key else None

        return {"files": files, "total": len(files), "nextToken": new_next_token}

    except ClientError as e:
        logger.error(f"DynamoDB error getting shared files: {str(e)}")
        return {"files": [], "total": 0, "nextToken": None}


def get_share_count(file_id):
    """
    Get count of how many users a file is shared with
    """
    try:
        shares_table = dynamodb.Table(SHARES_TABLE)

        response = shares_table.query(
            KeyConditionExpression=Key("fileId").eq(file_id),
            FilterExpression=Attr("status").eq("active"),
            Select="COUNT",
        )

        return response.get("Count", 0)

    except Exception as e:
        logger.error(f"Error getting share count: {str(e)}")
        return 0


def sort_files(files, sort_by, sort_order):
    """
    Sort files by specified field
    """
    valid_sort_fields = ["uploadedAt", "filename", "fileSize", "lastModified"]

    if sort_by not in valid_sort_fields:
        sort_by = "uploadedAt"

    reverse = sort_order == "desc"

    try:
        return sorted(files, key=lambda x: x.get(sort_by, ""), reverse=reverse)
    except Exception as e:
        logger.error(f"Error sorting files: {str(e)}")
        return files


def format_file_item(file_item, current_user_id):
    """
    Format file item for API response
    """
    formatted = {
        "fileId": file_item["fileId"],
        "filename": file_item["filename"],
        "fileSize": int(file_item["fileSize"]),
        "contentType": file_item["contentType"],
        "uploadedAt": file_item["uploadedAt"],
        "lastModified": file_item.get("lastModified", file_item["uploadedAt"]),
        "status": file_item["status"],
        "owner": {
            "userId": file_item["userId"],
            "email": file_item.get("ownerEmail", ""),
        },
        "isOwner": file_item["userId"] == current_user_id,
        "description": file_item.get("description", ""),
        "tags": file_item.get("tags", []),
        "downloadCount": int(file_item.get("downloadCount", 0)),
        "virusScanStatus": file_item.get("virusScanStatus", "pending"),
    }

    # Add share-specific fields if this is a shared file
    if file_item.get("isShared"):
        formatted["sharedBy"] = file_item.get("sharedBy", {})
        formatted["sharedAt"] = file_item.get("sharedAt")
        formatted["sharePermissions"] = file_item.get("sharePermissions", "read")
    else:
        # For owned files, add share count
        formatted["sharedWithCount"] = int(file_item.get("sharedWithCount", 0))

    return formatted


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
