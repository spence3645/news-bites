"""
Google News top stories scraper.

Fetches the main Google News RSS feed (all outlets) and returns
articles with source names extracted from the feed metadata.
"""

import hashlib
import json
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

FEEDS = [
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/HEALTH?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OneBiteNewsBot/1.0; +https://onebitenews.app)",
    "Accept-Language": "en-US,en;q=0.9",
}

BLOCKED_TITLE_START = ("live updates:", "live:", "live blog:", "live coverage:")
BLOCKED_TITLE_CONTAINS = ("live results",)


def _is_article(title: str) -> bool:
    t = title.lower()
    if any(t.startswith(b) for b in BLOCKED_TITLE_START):
        return False
    if any(b in t for b in BLOCKED_TITLE_CONTAINS):
        return False
    return True


def _resolve_url(google_url: str) -> str:
    """Follow Google News redirect to get the real article URL."""
    try:
        resp = requests.get(google_url, headers=HEADERS, timeout=10, allow_redirects=True)
        return resp.url
    except Exception:
        return google_url


def _fetch_article(url: str) -> dict:
    """Fetch teaser and full text from an article page."""
    result = {"teaser": "", "fullText": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        tag = soup.find("meta", property="og:description")
        if tag and tag.get("content"):
            result["teaser"] = tag["content"].strip()

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if data.get("@type") == "NewsArticle" and data.get("articleBody"):
                    result["fullText"] = data["articleBody"].strip()
                    return result
            except Exception:
                continue

        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 80
        ]
        result["fullText"] = " ".join(paragraphs)

    except Exception as e:
        print(f"    Warning: could not fetch article — {e}")

    return result


def _content_hash(title: str, text: str) -> str:
    return hashlib.md5(f"{title}{text}".encode()).hexdigest()


def _fetch_feed(url: str) -> list[dict]:
    """Fetch and parse a single Google News RSS feed."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: could not fetch feed {url} — {e}")
        return []

    root = ET.fromstring(resp.text)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        google_url = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source_name = source_el.text.strip() if source_el is not None and source_el.text else "Unknown"

        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()

        if not title or not google_url:
            continue
        if not _is_article(title):
            continue

        items.append({
            "title": title,
            "google_url": google_url,
            "publishedAt": pub_date,
            "source": source_name,
        })

    return items


def scrape(limit: int | None = None, delay: float = 0.75) -> list[dict]:
    print(f"[Google News] Fetching {len(FEEDS)} feeds...")

    seen_urls = set()
    items = []
    for feed_url in FEEDS:
        feed_items = _fetch_feed(feed_url)
        for item in feed_items:
            if item["google_url"] not in seen_urls:
                seen_urls.add(item["google_url"])
                items.append(item)

    print(f"[Google News] Found {len(items)} unique articles across all feeds")

    if limit is not None:
        items = items[:limit]

    results = []
    total = len(items)
    for i, item in enumerate(items):
        print(f"[Google News] ({i + 1}/{total}) [{item['source']}] {item['title'][:60]}")

        real_url = _resolve_url(item["google_url"])
        fetched = _fetch_article(real_url)

        results.append({
            "url": real_url,
            "title": item["title"],
            "teaser": fetched["teaser"],
            "fullText": fetched["fullText"],
            "source": item["source"],
            "publishedAt": item["publishedAt"],
            "contentHash": _content_hash(item["title"], fetched["fullText"]),
        })

        if delay and i < total - 1:
            time.sleep(delay)

    print(f"[Google News] Done — {len(results)} articles scraped")
    return results
