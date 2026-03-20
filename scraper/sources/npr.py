import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from utils import get_today
from email.utils import parsedate_to_datetime

import requests

SOURCE_NAME = "NPR"

RSS_FEEDS = [
    "https://feeds.npr.org/1001/rss.xml",   # News
    "https://feeds.npr.org/1004/rss.xml",   # World
    "https://feeds.npr.org/1014/rss.xml",   # Politics
    "https://feeds.npr.org/1006/rss.xml",   # Business
    "https://feeds.npr.org/1019/rss.xml",   # Technology
    "https://feeds.npr.org/1128/rss.xml",   # Health
    "https://feeds.npr.org/1007/rss.xml",   # Science
    "https://feeds.npr.org/1008/rss.xml",   # Arts & Culture
    "https://feeds.npr.org/1055/rss.xml",   # Sports
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_today(pub_date: str, today: str) -> bool:
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d") == today
    except Exception:
        return True


def _is_article(title: str) -> bool:
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
        title = (item.findtext("title") or "").strip()
        loc = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        teaser = (item.findtext("description") or "").strip()

        if not title or not loc or loc in seen_urls:
            continue
        if not _is_article(title):
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
            "source": SOURCE_NAME,
            "contentHash": _content_hash(article["title"], article["teaser"]),
        })

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
