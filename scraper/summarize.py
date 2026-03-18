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


# 25 req/min keeps token usage (~2k tokens avg) under the 50k tokens/min limit
_rate_limiter = _RateLimiter(25)


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

SYSTEM_PROMPT = (
    "You are a news summarization assistant. "
    "Write clear, factual, neutral summaries. "
    "Never editorialize or add information not present in the article."
)

CATEGORIES = ["World", "Politics", "Business", "Tech", "Science", "Sports", "Entertainment", "Gaming", "Music", "Climate"]


def summarize(title: str, full_text: str) -> str:
    """Send an article to Claude Haiku and return a 3-4 sentence summary."""
    _rate_limiter.acquire()
    message = _call_with_backoff(lambda: _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Summarize this news article in 3-4 sentences. "
                    f"Be concise and stick to the key facts of the article, nothing more.\n\n"
                    f"Title: {title}\n\n"
                    f"Article:\n{full_text}"
                ),
            }
        ],
    ))
    return message.content[0].text.strip()


def generate_title(titles: list[str]) -> str:
    """Combine multiple source headlines into one short unified title."""
    combined = "\n".join(f"- {t}" for t in titles)
    _rate_limiter.acquire()
    message = _call_with_backoff(lambda: _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        system="You are a headline writer. Write concise, factual news headlines.",
        messages=[
            {
                "role": "user",
                "content": (
                    "The following are headlines for the same story from different news sources. "
                    "Write a single short headline (under 10 words) that captures the story. "
                    "Return only the headline, no punctuation at the end.\n\n"
                    f"{combined}"
                ),
            }
        ],
    ))
    return message.content[0].text.strip()


def generate_category(titles: list[str]) -> str:
    """Pick the best matching category from the fixed list based on article titles."""
    combined = "\n".join(f"- {t}" for t in titles)
    cats = ", ".join(CATEGORIES)
    _rate_limiter.acquire()
    message = _call_with_backoff(lambda: _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
        system="You are a news categorization assistant.",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Categorize this news story into exactly one of these categories: {cats}.\n\n"
                    f"Headlines:\n{combined}\n\n"
                    "Return only the category name, nothing else."
                ),
            }
        ],
    ))
    result = message.content[0].text.strip()
    return result if result in CATEGORIES else "World"


def merge(texts: list[str]) -> str:
    """Combine article text/teasers from multiple sources into one 4-5 sentence summary."""
    # Truncate each source text to avoid hitting token limits
    combined = "\n\n---\n\n".join(t[:2000] for t in texts if t.strip())
    _rate_limiter.acquire()
    message = _call_with_backoff(lambda: _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "The following are articles covering the same news story from different sources. "
                    "Write a single, unified 3-4 sentence summary that captures the key facts. "
                    "Use short, direct sentences. Avoid em dashes, en dashes, and semicolons — use periods instead. "
                    "Remove redundancy and write in a clear, neutral tone. "
                    "Return only the summary, no headings or labels.\n\n"
                    f"{combined}"
                ),
            }
        ],
    ))
    return message.content[0].text.strip()
