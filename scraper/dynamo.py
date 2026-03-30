"""
Writes clustered stories to DynamoDB Stories table.
"""

import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = "Stories"

_dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)
_table = _dynamodb.Table(TABLE_NAME)


def _delete_stale(keep_ids: set):
    """Delete any items in the table whose storyId is not in keep_ids."""
    scan = _table.scan(ProjectionExpression="#d, storyId", ExpressionAttributeNames={"#d": "date"})
    deleted = 0

    while True:
        with _table.batch_writer() as batch:
            for item in scan["Items"]:
                if item["storyId"] not in keep_ids:
                    batch.delete_item(Key={"date": item["date"], "storyId": item["storyId"]})
                    deleted += 1
        if "LastEvaluatedKey" not in scan:
            break
        scan = _table.scan(
            ProjectionExpression="#d, storyId",
            ExpressionAttributeNames={"#d": "date"},
            ExclusiveStartKey=scan["LastEvaluatedKey"],
        )

    print(f"  Removed {deleted} stale items")


def fetch_today(date_str: str) -> list[dict]:
    """Return all stories already written for date_str."""
    result = _table.query(
        KeyConditionExpression=Key("date").eq(date_str)
    )
    return result.get("Items", [])


def write_stories(clusters: list[dict], date_str: str):
    """Write today's clusters, then remove any stale items from previous runs."""
    print(f"\nWriting {len(clusters)} stories to DynamoDB ({TABLE_NAME})...")

    # Step 1: write new data — if this fails, old data is untouched
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _table.batch_writer() as batch:
        for cluster in clusters:
            batch.put_item(Item={
                "date": date_str,
                "storyId": cluster["storyId"],
                "mergedTitle": cluster["mergedTitle"],
                "mergedSummary": cluster["mergedSummary"],
                "category": cluster["category"],
                "sourceCount": cluster["sourceCount"],
                "updatedAt": updated_at,
                "mostRecentUpdate": cluster.get("mostRecentUpdate", ""),
                "articles": cluster["articles"],
            })

    print(f"  Wrote {len(clusters)} stories")

    # Step 2: only clean up stale items if we wrote a meaningful batch
    # (skip if this run produced nothing, to avoid wiping good data)
    if not clusters:
        print("  Skipping stale cleanup — no stories written this run")
        return

    new_ids = {c["storyId"] for c in clusters}
    _delete_stale(new_ids)


if __name__ == "__main__":
    _delete_stale(keep_ids=set())
