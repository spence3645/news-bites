import hashlib
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from utils import get_today
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "BBC News"

RSS_FEEDS = [
    ("Top Stories", "https://feeds.bbci.co.uk/news/rss.xml"),
    ("World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("US & Canada", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("Politics", "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Health", "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ("Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("Tech", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _is_today(pub_date: str, today: str) -> bool:
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d") == today
    except Exception:
        return True


def _is_article(url: str, title: str = "") -> bool:
    if "/articles/" not in url:
        return False
    blocked_title = ("live updates:", "live:", "live blog:", "live coverage:")
    if any(title.lower().startswith(b) for b in blocked_title):
        return False
    return True


def _content_hash(title: str, text: str) -> str:
    return hashlib.md5(f"{title}{text}".encode()).hexdigest()


def _fetch_feed(category: str, url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    Warning: could not fetch {category} feed — {e}")
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
        articles.append(
            {
                "url": loc,
                "title": title,
                "teaser": teaser,
                "fullText": "",
                "publishedAt": pub_date,
                "category": category,
                "source": SOURCE_NAME,
                "contentHash": "",
            }
        )

    return articles


def _fetch_full_text(url: str) -> str:
    """Fetch full article body from a BBC article page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try JSON-LD articleBody first
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if data.get("@type") == "NewsArticle" and data.get("articleBody"):
                    return data["articleBody"].strip()
            except Exception:
                continue

        # Fallback: BBC article text lives in <p> tags inside the article body
        # Filter by length to skip nav, captions, and footer noise
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 80
        ]
        return " ".join(paragraphs)

    except Exception as e:
        print(f"    Warning: could not fetch full text — {e}")
    return ""


def scrape(limit: int | None = None) -> list[dict]:
    print(f"[{SOURCE_NAME}] Fetching RSS feeds...")

    seen_urls = set()
    all_articles = []

    for category, url in RSS_FEEDS:
        articles = _fetch_feed(category, url)
        for article in articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)

    print(f"[{SOURCE_NAME}] Found {len(all_articles)} articles across {len(RSS_FEEDS)} feeds")

    today = get_today()
    all_articles = [a for a in all_articles if _is_today(a.get("publishedAt", ""), today)]
    print(f"[{SOURCE_NAME}] {len(all_articles)} articles published today")

    if limit is not None:
        all_articles = all_articles[:limit]

    def _fetch(article):
        full_text = _fetch_full_text(article["url"])
        return {
            **article,
            "fullText": full_text,
            "contentHash": _content_hash(article["title"], full_text),
        }

    results = [None] * len(all_articles)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch, article): i for i, article in enumerate(all_articles)}
        for future in as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                print(f"    Warning: failed to fetch article — {e}")
    results = [r for r in results if r is not None]

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
