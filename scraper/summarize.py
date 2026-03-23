import json
import os
import threading
import time

import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class _RateLimiter:
    """Serializes API calls to at most `rate_per_minute` requests per minute."""

    def __init__(self, rate_per_minute: int):
        self._lock = threading.Lock()
        self._interval = 60.0 / rate_per_minute
        self._next_allowed = time.monotonic()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
            self._next_allowed = time.monotonic() + self._interval


# 50 req/min — full Haiku allowance
_rate_limiter = _RateLimiter(50)


def _call_with_backoff(fn):
    """Call fn(), retrying on 429 with exponential backoff."""
    delay = 10
    for attempt in range(5):
        try:
            return fn()
        except anthropic.RateLimitError:
            if attempt == 4:
                raise
            print(f"  Rate limit hit — retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2


CATEGORIES = ["World", "Politics", "Business", "Tech", "Science", "Sports", "Entertainment", "Gaming", "Music", "Climate"]

SYSTEM_PROMPT = (
    "You are a news summarization assistant. "
    "Write clear, factual, neutral summaries. "
    "Never editorialize or add information not present in the articles."
)


def enrich(titles: list[str], texts: list[str]) -> dict:
    """Single API call that returns title, summary, and category for a cluster."""
    combined_titles = "\n".join(f"- {t}" for t in titles)
    combined_texts = "\n\n---\n\n".join(t[:800] for t in texts if t.strip())
    cats = ", ".join(CATEGORIES)

    _rate_limiter.acquire()
    message = _call_with_backoff(lambda: _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "The following are headlines and articles covering the same news story from different sources.\n\n"
                    f"Headlines:\n{combined_titles}\n\n"
                    f"Articles:\n{combined_texts}\n\n"
                    f"Return a JSON object with exactly these three fields:\n"
                    f"- \"title\": a single short headline under 10 words, no punctuation at the end\n"
                    f"- \"summary\": a 3-4 sentence summary using short, direct sentences. Avoid em dashes, en dashes, and semicolons. Neutral tone.\n"
                    f"- \"category\": exactly one of: {cats}\n\n"
                    "Return only the JSON object, nothing else."
                ),
            }
        ],
    ))

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
        merged_title = str(data.get("title", titles[0]))
        merged_summary = str(data.get("summary", ""))
        category = data.get("category") if data.get("category") in CATEGORIES else "World"
        if not merged_summary:
            print(f"  Warning: empty summary for cluster: {merged_title[:60]}")
        return {
            "mergedTitle": merged_title,
            "mergedSummary": merged_summary,
            "category": category,
        }
    except Exception:
        print(f"  Warning: failed to parse enrich response: {raw[:100]}")
        return None
