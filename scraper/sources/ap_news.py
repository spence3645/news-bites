import hashlib
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from utils import get_today

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "AP News"
SITEMAP_URL = "https://apnews.com/news-sitemap-content.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)",
    "Accept-Language": "en-US,en;q=0.9",
}

NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}


def _is_article(url: str, title: str) -> bool:
    blocked_url = ("/video/", "/live-updates/", "/live/")
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


def _fetch_sitemap(today: str) -> list[dict]:
    try:
        resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: could not fetch sitemap — {e}")
        return []

    root = ET.fromstring(resp.text)
    articles = []

    for url_el in root.findall("sm:url", NS):
        loc = url_el.findtext("sm:loc", "", NS).strip()
        title = url_el.findtext("news:news/news:title", "", NS).strip()
        pub_date = url_el.findtext("news:news/news:publication_date", "", NS).strip()
        language = url_el.findtext("news:news/news:publication/news:language", "", NS).strip()

        if not loc or not title:
            continue
        if language and language != "eng":
            continue
        if not _is_article(loc, title):
            continue
        if pub_date and not pub_date.startswith(today):
            continue

        articles.append({"url": loc, "title": title, "publishedAt": pub_date})

    return articles


def _fetch_article(url: str) -> dict:
    result = {"teaser": "", "fullText": "", "imageUrl": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
    today = get_today()
    print(f"[{SOURCE_NAME}] Fetching sitemap (today: {today})...")
    articles = _fetch_sitemap(today)
    print(f"[{SOURCE_NAME}] Found {len(articles)} articles published today")

    if limit is not None:
        articles = articles[:limit]

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

    results = [None] * len(articles)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch, article): i for i, article in enumerate(articles)}
        for future in as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                print(f"    Warning: failed to fetch article — {e}")
    results = [r for r in results if r is not None]

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
