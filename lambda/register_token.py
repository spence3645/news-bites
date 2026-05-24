"""
Lambda handler for POST /register-token

Stores an APNs device token in the existing DynamoDB Stories table
under the sentinel partition key "_tokens".

Environment variables required:
    DYNAMODB_TABLE  — DynamoDB table name (default: "Stories")
    AWS region is inherited from the Lambda execution environment.
"""

import json
import os
from datetime import datetime, timezone

import boto3

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "Stories"))


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, "invalid JSON body")

    token = (body.get("token") or "").strip()
    if not token:
        return _response(400, "missing token")

    _table.put_item(Item={
        "date": "_tokens",
        "storyId": token,
        "registeredAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    return _response(200, "ok")


def _response(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message}),
    }
