"""
One Bite News — Scraper
Usage:
    python main.py                        # scrape all sources, save to output/articles.json
    python main.py --limit 10             # cap at 10 articles per source
    python main.py --source nbc           # only run NBC News
    python main.py --out my_file.json     # custom output path
"""

import argparse
import json
import os
from datetime import datetime, timezone

from sources.registry import REGISTRY

# Custom sources (non-standard parsers — sitemap, Atom, dc:date, etc.)
from sources.abc_news import scrape as scrape_abc
from sources.ap_news import scrape as scrape_ap
from sources.axios import scrape as scrape_axios
from sources.bbc_news import scrape as scrape_bbc
from sources.business_insider import scrape as scrape_business_insider
from sources.cnn import scrape as scrape_cnn
from sources.deutsche_welle import scrape as scrape_dw
from sources.fox_news import scrape as scrape_fox
from sources.nbc_news import scrape as scrape_nbc
from sources.npr import scrape as scrape_npr
from sources.reuters import scrape as scrape_reuters
from sources.the_hill import scrape as scrape_hill
from sources.the_verge import scrape as scrape_verge
from sources.tmz import scrape as scrape_tmz
from sources.washington_post import scrape as scrape_wapo

SOURCES = {
    **REGISTRY,
    # General / US News
    "nbc": scrape_nbc,
    "abc": scrape_abc,
    "cnn": scrape_cnn,
    "fox": scrape_fox,
    "ap": scrape_ap,
    "npr": scrape_npr,
    "axios": scrape_axios,
    # World News
    "bbc": scrape_bbc,
    "dw": scrape_dw,
    # Politics
    "wapo": scrape_wapo,
    "hill": scrape_hill,
    # Business
    "businessinsider": scrape_business_insider,
    # Tech
    "verge": scrape_verge,
    # Entertainment
    "tmz": scrape_tmz,
    # Other
    "reuters": scrape_reuters,
}


def parse_args():
    parser = argparse.ArgumentParser(description="One Bite News scraper")
    parser.add_argument("--limit", type=int, default=None, help="Max articles per source")
    parser.add_argument("--source", choices=list(SOURCES.keys()), help="Run a single source")
    parser.add_argument("--out", type=str, default=None, help="Output file path (default: output/YYYY-MM-DD.json)")
    return parser.parse_args()


def main():
    args = parse_args()

    sources_to_run = (
        {args.source: SOURCES[args.source]} if args.source else SOURCES
    )

    all_articles = []
    for _, scrape_fn in sources_to_run.items():
        articles = scrape_fn(limit=args.limit)
        all_articles.extend(articles)

    print(f"\nTotal articles scraped: {len(all_articles)}")

    # Determine output path
    if args.out:
        out_path = args.out
    else:
        os.makedirs("output", exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = f"output/{date_str}.json"

    with open(out_path, "w") as f:
        json.dump(all_articles, f, indent=2)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
