import hashlib
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from utils import get_today

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "ABC News"
SITEMAP_URL = "https://abcnews.com/xmlLatestStories"

CATEGORY_MAP = [
    ("/Politics/", "Politics"),
    ("/International/", "World"),
    ("/US/", "US News"),
    ("/Business/", "Business"),
    ("/Health/", "Health"),
    ("/Technology/", "Tech"),
    ("/Entertainment/", "Culture"),
    ("/Sports/", "Sports"),
    ("/GMA/", "News"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}


def _is_article(url: str, title: str = "") -> bool:
    blocked_url = ("/GMA/Shop/", "/video/", "/Video/", "/gma/video/", "/live/", "/live-updates/", "/live-blog/")
    if any(b in url for b in blocked_url):
        return False
    blocked_title = ("live updates:", "live:", "live blog:", "live coverage:")
    if any(title.lower().startswith(b) for b in blocked_title):
        return False
    return True


def _category_from_url(url: str) -> str:
    for prefix, category in CATEGORY_MAP:
        if prefix.lower() in url.lower():
            return category
    return "News"


def _content_hash(title: str, text: str) -> str:
    return hashlib.md5(f"{title}{text}".encode()).hexdigest()


def _fetch_sitemap(today: str) -> list[dict]:
    resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    articles = []

    for url_el in root.findall("sm:url", NS):
        loc = url_el.findtext("sm:loc", "", NS).strip()
        lastmod = url_el.findtext("sm:lastmod", "", NS).strip()
        title = url_el.findtext("news:news/news:title", "", NS).strip()
        pub_date = url_el.findtext("news:news/news:publication_date", "", NS).strip()

        if not loc or not title:
            continue
        if "#" in loc:
            continue
        if not _is_article(loc, title):
            continue

        date_to_check = pub_date or lastmod
        if date_to_check and not date_to_check.startswith(today):
            continue

        if not loc.startswith("http"):
            loc = f"https://{loc}"

        articles.append(
            {
                "url": loc,
                "title": title,
                "publishedAt": pub_date or lastmod,
                "category": _category_from_url(loc),
            }
        )

    return articles


def _fetch_article(url: str) -> dict:
    """Fetch teaser (og:description) and fullText (body paragraphs) from an article page."""
    result = {"teaser": "", "fullText": "", "imageUrl": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Teaser from og:description
        tag = soup.find("meta", property="og:description")
        if tag and tag.get("content"):
            result["teaser"] = tag["content"].strip()

        img_tag = soup.find("meta", property="og:image")
        if img_tag and img_tag.get("content"):
            result["imageUrl"] = img_tag["content"].strip()

        # Full text: try JSON-LD articleBody first
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if data.get("@type") == "NewsArticle" and data.get("articleBody"):
                    result["fullText"] = data["articleBody"].strip()
                    return result
            except Exception:
                continue

        # Fallback: collect substantial <p> tags (avoids nav/footer noise)
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
    today = get_today()
    print(f"[{SOURCE_NAME}] Fetching sitemap (today: {today})...")
    articles = _fetch_sitemap(today)
    print(f"[{SOURCE_NAME}] Found {len(articles)} articles in sitemap")

    if limit is not None:
        articles = articles[:limit]

    results = []
    total = len(articles)

    for i, article in enumerate(articles):
        print(f"[{SOURCE_NAME}] ({i + 1}/{total}) {article['title'][:70]}")

        fetched = _fetch_article(article["url"])
        article["teaser"] = fetched["teaser"]
        article["fullText"] = fetched["fullText"]
        article["imageUrl"] = fetched.get("imageUrl", "")
        article["source"] = SOURCE_NAME
        article["contentHash"] = _content_hash(article["title"], fetched["fullText"])
        results.append(article)

        if delay and i < total - 1:
            time.sleep(delay)

    print(f"[{SOURCE_NAME}] Done — {len(results)} articles scraped")
    return results
