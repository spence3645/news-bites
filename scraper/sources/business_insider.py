import hashlib
import html
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from utils import get_today

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "Business Insider"

RSS_FEEDS = [
    "https://feeds.businessinsider.com/custom/all",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OneBiteNewsBot/1.0; +https://onebitenews.app)",
    "Accept-Language": "en-US,en;q=0.9",
}

_ATOM_NS = "http://www.w3.org/2005/Atom"


def _is_today(pub_date: str, today: str) -> bool:
    # Atom dates: 2026-03-16T15:22:25Z
    try:
        return pub_date[:10] == today
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

    articles = []
    seen_urls = set()

    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        loc = ""
        for link in entry.findall(f"{{{_ATOM_NS}}}link"):
            if link.get("rel") in (None, "alternate"):
                loc = (link.get("href") or "").strip()
                break
        title = html.unescape((entry.findtext(f"{{{_ATOM_NS}}}title") or "").strip())
        teaser = html.unescape((entry.findtext(f"{{{_ATOM_NS}}}summary") or "").strip())
        pub_date = (entry.findtext(f"{{{_ATOM_NS}}}published") or entry.findtext(f"{{{_ATOM_NS}}}updated") or "").strip()

        if not loc or not title or loc in seen_urls:
            continue
        if not _is_article(loc, title):
            continue

        seen_urls.add(loc)
        articles.append({"url": loc, "title": title, "teaser": teaser, "publishedAt": pub_date})

    return articles


def _fetch_article(url: str) -> dict:
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

    def _fetch(article):
        fetched = _fetch_article(article["url"])
        return {
            **article,
            "teaser": fetched["teaser"] or article.get("teaser", ""),
            "fullText": fetched["fullText"],
            "imageUrl": fetched.get("imageUrl", ""),
            "source": SOURCE_NAME,
            "contentHash": _content_hash(article["title"], fetched["fullText"]),
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
