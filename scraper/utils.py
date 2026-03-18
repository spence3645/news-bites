from datetime import datetime
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")


def get_today() -> str:
    """Return today's date in US Eastern time (handles EST/EDT automatically)."""
    return datetime.now(_ET).strftime("%Y-%m-%d")
