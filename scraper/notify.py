"""
notify.py — Send dynamic push notifications with Haiku-generated summary.

Reads top 3 story titles from DynamoDB, summarizes them into 1 sentence via
Claude Haiku, then sends a push notification to all registered devices via APNs.

Usage:
    python notify.py                  # send to all registered devices
    python notify.py --dry-run        # print notification body, skip APNs send
"""

import argparse
import os
import time

import anthropic
import boto3
import httpx
import jwt
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

APNS_KEY_ID    = os.environ["APNS_KEY_ID"]
APNS_TEAM_ID   = os.environ["APNS_TEAM_ID"]
APNS_BUNDLE_ID = os.environ["APNS_BUNDLE_ID"]
APNS_KEY       = os.environ["APNS_KEY"]  # full .p8 file contents
APNS_SANDBOX   = os.environ.get("APNS_SANDBOX", "false").lower() == "true"
APNS_HOST      = "api.sandbox.push.apple.com" if APNS_SANDBOX else "api.push.apple.com"

TABLE_NAME = "Stories"
_dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)
_table = _dynamodb.Table(TABLE_NAME)
_anthropic = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def get_top_titles(date_str: str) -> list[str]:
    """Return the top 3 story titles for date_str, sorted by sourceCount."""
    result = _table.query(KeyConditionExpression=Key("date").eq(date_str))
    stories = result.get("Items", [])
    stories.sort(key=lambda s: int(s.get("sourceCount", 0)), reverse=True)
    return [s["mergedTitle"] for s in stories[:3]]


def summarize_titles(titles: list[str]) -> str:
    """Call Claude Haiku to distill 3 headlines into 1 notification sentence."""
    bullets = "\n".join(f"- {t}" for t in titles)
    msg = _anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=80,
        messages=[{
            "role": "user",
            "content": (
                "Summarize these 3 news headlines into exactly 1 short, engaging sentence "
                "suitable for a push notification. No list format. Neutral tone.\n\n"
                f"{bullets}"
            ),
        }],
    )
    return msg.content[0].text.strip()


def get_tokens() -> list[str]:
    """Return all registered APNs device tokens from the Stories table."""
    result = _table.query(KeyConditionExpression=Key("date").eq("_tokens"))
    return [item["storyId"] for item in result.get("Items", [])]


def _make_jwt() -> str:
    return jwt.encode(
        {"iss": APNS_TEAM_ID, "iat": int(time.time())},
        APNS_KEY,
        algorithm="ES256",
        headers={"kid": APNS_KEY_ID},
    )


def send_push(tokens: list[str], body: str):
    """Send a push notification to each device token via APNs."""
    auth_token = _make_jwt()
    env_label = "sandbox" if APNS_SANDBOX else "production"
    print(f"Sending via APNs ({env_label})...")

    with httpx.Client(http2=True) as client:
        for token in tokens:
            resp = client.post(
                f"https://{APNS_HOST}/3/device/{token}",
                headers={
                    "authorization": f"bearer {auth_token}",
                    "apns-topic": APNS_BUNDLE_ID,
                    "apns-push-type": "alert",
                    "apns-priority": "10",
                },
                json={"aps": {"alert": {"title": "One Bite News", "body": body}}},
            )
            status = "ok" if resp.status_code == 200 else f"error {resp.status_code}: {resp.text}"
            print(f"  [{token[:20]}...] {status}")


def parse_args():
    parser = argparse.ArgumentParser(description="Send dynamic push notifications")
    parser.add_argument("--dry-run", action="store_true", help="Print notification body without sending")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    titles = get_top_titles(date_str)
    if not titles:
        print("No stories found for today — skipping")
        exit(0)

    print("Top titles:")
    for t in titles:
        print(f"  • {t}")

    body = summarize_titles(titles)
    print(f"\nNotification body: {body}")

    if args.dry_run:
        print("\n[dry-run] Skipping APNs send")
        exit(0)

    tokens = get_tokens()
    if not tokens:
        print("No registered device tokens — skipping")
        exit(0)

    print(f"\nSending to {len(tokens)} device(s)...")
    send_push(tokens, body)
    print("Done")
