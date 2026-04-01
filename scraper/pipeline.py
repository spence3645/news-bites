"""
One Bite News — Summarization Pipeline

Loads a scraped articles JSON, sends each article to Claude Haiku for
summarization, and writes the results to a separate JSON file.

Usage:
    python pipeline.py                          # process output/YYYY-MM-DD.json, limit 1
    python pipeline.py --limit 5               # process first 5 articles
    python pipeline.py --in output/raw.json    # custom input file
    python pipeline.py --out summaries.json    # custom output file
"""

import argparse
import json
import os
from datetime import datetime, timezone

from summarize import summarize


def parse_args():
    parser = argparse.ArgumentParser(description="Summarization pipeline")
    parser.add_argument("--in", dest="input", default=None, help="Input JSON file (default: output/YYYY-MM-DD.json)")
    parser.add_argument("--out", dest="output", default=None, help="Output JSON file (default: output/YYYY-MM-DD-summaries.json)")
    parser.add_argument("--limit", type=int, default=1, help="Number of articles to summarize (default: 1)")
    return parser.parse_args()


def main():
    args = parse_args()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    input_path = args.input or f"output/{date_str}.json"
    output_path = args.output or f"output/{date_str}-summaries.json"

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        print("Run main.py first to scrape articles.")
        return

    with open(input_path) as f:
        articles = json.load(f)

    batch = articles[: args.limit]
    print(f"Loaded {len(articles)} articles — summarizing {len(batch)}")

    results = []
    for i, article in enumerate(batch):
        print(f"({i + 1}/{len(batch)}) {article['title'][:70]}")

        if not article.get("fullText"):
            print("  Skipping — no fullText")
            continue

        summary = summarize(article["title"], article["fullText"])
        print(f"  → {summary[:100]}...")

        results.append(
            {
                "url": article["url"],
                "title": article["title"],
                "summary": summary,
                "teaser": article.get("teaser", ""),
                "category": article["category"],
                "source": article["source"],
                "publishedAt": article["publishedAt"],
                "contentHash": article["contentHash"],
            }
        )

    os.makedirs("output", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} summaries to {output_path}")


if __name__ == "__main__":
    main()
