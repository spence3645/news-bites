import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from utils import get_today
from email.utils import parsedate_to_datetime

import requests

SOURCE_NAME = "Washington Post"

RSS_FEEDS = [
    "https://feeds.washingtonpost.com/rss/national",
    "https://feeds.washingtonpost.com/rss/world",
    "https://feeds.washingtonpost.com/rss/politics",
    "https://feeds.washingtonpost.com/rss/business",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OneBiteNewsBot/1.0; +https://onebitenews.app)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_today(pub_date: str, today: str) -> bool:
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d") == today
    except Exception:
        return True


def _is_article(url: str, title: str = "") -> bool:
    blocked_url = ("/video/", "/live-updates/", "/live/", "/liveblog/")
    if any(b in url for b in blocked_url):
        return False
    blocked_title_start = ("live updates:", "live:", "live blog:", "live coverage:")
    blocked_title_contains = ("live results",)
    t = title.lower()
    if any(t.startswith(b) for b in blocked_title_start):
        return False
    if any(b in t for b in blocked_title_contains):
        return False
    return True


def _content_hash(title: str, text: str) -> str:
    return hashlib.md5(f"{title}{text}".encode()).hexdigest()


def _fetch_feed(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: could not fetch feed {url} — {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"  Warning: could not parse feed {url} — {e}")
        return []
    channel = root.find("channel")
    if channel is None:
        return []

    articles = []
    seen_urls = set()

    for item in channel.findall("item"):
        loc = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        teaser = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()

        if not loc or not title or loc in seen_urls:
            continue
        if not _is_article(loc, title):
            continue

        seen_urls.add(loc)
        articles.append({"url": loc, "title": title, "teaser": teaser, "publishedAt": pub_date})

    return articles


def scrape(limit: int | None = None) -> list[dict]:
    print(f"[{SOURCE_NAME}] Fetching RSS feeds...")

    seen_urls = set()
    all_articles = []
    for feed_url in RSS_FEEDS:
        for article in _fetch_feed(feed_url):
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)

    print(f"[{SOURCE_NAME}] Found {len(all_articles)} articles across {len(RSS_FEEDS)} feeds")

    today = get_today()
    all_articles = [a for a in all_articles if _is_today(a.get("publishedAt", ""), today)]
    print(f"[{SOURCE_NAME}] {len(all_articles)} articles published today")

    if limit is not None:
        all_articles = all_articles[:limit]

    results = []
    for article in all_articles:
        results.append({
            **article,
            "fullText": "",
            "imageUrl": "",
            "source": SOURCE_NAME,
            "contentHash": _content_hash(article["title"], article.get("teaser", "")),
        })

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
