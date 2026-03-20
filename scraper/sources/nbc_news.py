import hashlib
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from utils import get_today

import requests
from bs4 import BeautifulSoup

SOURCE_NAME = "NBC News"
SITEMAP_URL = "https://www.nbcnews.com/sitemap/nbcnews/sitemap-news"

# Ordered most-specific first so the first match wins
CATEGORY_MAP = [
    ("/news/us-news/", "US News"),
    ("/news/world/", "World"),
    ("/news/science/", "Science"),
    ("/news/health/", "Health"),
    ("/politics/", "Politics"),
    ("/world/", "World"),
    ("/business/", "Business"),
    ("/health/", "Health"),
    ("/science/", "Science"),
    ("/sports/", "Sports"),
    ("/culture/", "Culture"),
    ("/entertainment/", "Culture"),
    ("/tech/", "Tech"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsBitesBot/1.0; +https://newsbites.app)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# XML namespaces used by the NBC News sitemap
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}


def _is_article(url: str, title: str = "") -> bool:
    # Skip video pages, NBC Select shopping content, and live blogs
    blocked_url = ("/video/", "/select/", "/slideshow/", "/live-blog/", "/live-updates/", "/live/")
    if any(b in url for b in blocked_url):
        return False
    # Skip live update articles by title
    blocked_title_start = ("live updates:", "live:", "live blog:", "live coverage:")
    if any(title.lower().startswith(b) for b in blocked_title_start):
        return False
    blocked_title_contains = ("live results",)
    if any(b in title.lower() for b in blocked_title_contains):
        return False
    return True


def _category_from_url(url: str) -> str:
    path = url.replace("https://www.nbcnews.com", "")
    for prefix, category in CATEGORY_MAP:
        if path.startswith(prefix):
            return category
    return "News"


def _content_hash(title: str, summary: str) -> str:
    return hashlib.md5(f"{title}{summary}".encode()).hexdigest()


def _fetch_sitemap(today: str) -> list[dict]:
    """Fetch the news sitemap and return a list of bare article dicts."""
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

        # Skip live-blog anchor links (they contain #rcrd)
        if "#" in loc:
            continue
        if not _is_article(loc, title):
            continue

        date_to_check = pub_date or lastmod
        if date_to_check and not date_to_check.startswith(today):
            continue

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
    """
    Fetch an article page and return:
      - teaser:   og:description (NBC's own short description)
      - fullText: full article body from the JSON-LD NewsArticle block
    """
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
                    break
            except Exception:
                continue

    except Exception as e:
        print(f"    Warning: could not fetch article — {e}")

    return result


def scrape(limit: int | None = None) -> list[dict]:
    """
    Scrape NBC News articles from the news sitemap.

    Args:
        limit:  Max number of articles to process. None = all.

    Returns:
        List of article dicts with keys:
            url, title, teaser, fullText, category, source, publishedAt, contentHash
    """
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
