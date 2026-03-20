"""
Shared scraper utilities and factory for standard RSS sources.
"""
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup
from utils import get_today

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_today(pub_date: str, today: str) -> bool:
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d") == today
    except Exception:
        return True


def _is_article(url: str, title: str = "") -> bool:
    blocked_url = ("/video/", "/live-updates/", "/live/", "/liveblog/", "/gallery/")
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


def fetch_feed(url: str) -> list[dict]:
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


def fetch_article(url: str) -> dict:
    result = {"teaser": "", "fullText": "", "imageUrl": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code in (401, 403):
            return result
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        tag = soup.find("meta", property="og:description")
        if tag and tag.get("content"):
            result["teaser"] = tag["content"].strip()

        img_tag = soup.find("meta", property="og:image")
        if img_tag and img_tag.get("content"):
            result["imageUrl"] = img_tag["content"].strip()

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


def make_scraper(source_name: str, rss_feeds: list[str], delay: float = 0.75):
    """Return a scrape() function for a standard RSS source."""

    def scrape(limit: int | None = None, delay: float = delay, today: str | None = None) -> list[dict]:
        print(f"[{source_name}] Fetching RSS feeds...")

        seen_urls = set()
        all_articles = []
        for feed_url in rss_feeds:
            for article in fetch_feed(feed_url):
                if article["url"] not in seen_urls:
                    seen_urls.add(article["url"])
                    all_articles.append(article)

        print(f"[{source_name}] Found {len(all_articles)} articles across {len(rss_feeds)} feeds")

        _today = today or get_today()
        all_articles = [a for a in all_articles if _is_today(a.get("publishedAt", ""), _today)]
        print(f"[{source_name}] {len(all_articles)} articles published today")

        if limit is not None:
            all_articles = all_articles[:limit]

        results = []
        total = len(all_articles)
        for i, article in enumerate(all_articles):
            print(f"[{source_name}] ({i + 1}/{total}) {article['title'][:70]}")
            fetched = fetch_article(article["url"])
            results.append({
                **article,
                "teaser": fetched["teaser"] or article.get("teaser", ""),
                "fullText": fetched["fullText"],
                "imageUrl": fetched.get("imageUrl", ""),
                "source": source_name,
                "contentHash": _content_hash(article["title"], fetched["fullText"]),
            })
            if delay and i < total - 1:
                time.sleep(delay)

        print(f"[{source_name}] Done — {len(results)} articles scraped")
        return results

    scrape.__name__ = f"scrape_{source_name.lower().replace(' ', '_')}"
    return scrape
