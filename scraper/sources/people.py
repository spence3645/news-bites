import hashlib
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from utils import get_today

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "People"

SITEMAP_URL = "https://people.com/sitemap_1.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_article(url: str) -> bool:
    # Skip tag/category pages, galleries, etc.
    blocked = ("/tag/", "/category/", "/gallery/", "/video/", "/news/photos/")
    return not any(b in url for b in blocked)


def _content_hash(title: str, text: str) -> str:
    return hashlib.md5(f"{title}{text}".encode()).hexdigest()


def _fetch_today_urls(today: str) -> list[str]:
    try:
        resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: could not fetch sitemap — {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"  Warning: could not parse sitemap — {e}")
        return []

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    urls = []
    for url in root.findall(f"{{{ns}}}url"):
        loc = (url.findtext(f"{{{ns}}}loc") or "").strip()
        lastmod = (url.findtext(f"{{{ns}}}lastmod") or "")[:10]
        if lastmod == today and loc and _is_article(loc):
            urls.append(loc)
    return urls


def _fetch_article(url: str) -> dict:
    result = {"title": "", "teaser": "", "fullText": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code in (401, 403):
            return result
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        tag = soup.find("meta", property="og:title")
        if tag and tag.get("content"):
            result["title"] = tag["content"].strip()

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


def scrape(limit: int | None = None, delay: float = 0.75) -> list[dict]:
    print(f"[{SOURCE_NAME}] Fetching sitemap...")

    today = get_today()
    urls = _fetch_today_urls(today)
    print(f"[{SOURCE_NAME}] {len(urls)} articles published today")

    if limit is not None:
        urls = urls[:limit]

    results = []
    total = len(urls)
    for i, url in enumerate(urls):
        fetched = _fetch_article(url)
        if not fetched["title"]:
            continue

        print(f"[{SOURCE_NAME}] ({i + 1}/{total}) {fetched['title'][:70]}")
        results.append({
            "url": url,
            "title": fetched["title"],
            "teaser": fetched["teaser"],
            "fullText": fetched["fullText"],
            "publishedAt": today,
            "source": SOURCE_NAME,
            "contentHash": _content_hash(fetched["title"], fetched["fullText"]),
        })

        if delay and i < total - 1:
            time.sleep(delay)

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
