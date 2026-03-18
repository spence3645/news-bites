"""
News Bites — Vectorization

Loads a summaries JSON, generates an embedding for each article,
and writes the results to a vectors JSON for testing.

Usage:
    python vectorize.py                        # process output/YYYY-MM-DD-summaries.json
    python vectorize.py --in summaries.json    # custom input
    python vectorize.py --out vectors.json     # custom output
"""

import argparse
import json
import os
from datetime import datetime, timezone

from embed import embed


def parse_args():
    parser = argparse.ArgumentParser(description="Vectorization pipeline")
    parser.add_argument("--in", dest="input", default=None, help="Input summaries JSON")
    parser.add_argument("--out", dest="output", default=None, help="Output vectors JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    input_path = args.input or f"output/{date_str}-summaries.json"
    output_path = args.output or f"output/{date_str}-vectors.json"

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        print("Run pipeline.py first to generate summaries.")
        return

    with open(input_path) as f:
        articles = json.load(f)

    print(f"Loaded {len(articles)} articles — generating embeddings...")

    results = []
    for i, article in enumerate(articles):
        print(f"({i + 1}/{len(articles)}) {article['title'][:70]}")

        # Embed title + summary together for best semantic representation
        text = f"{article['title']}. {article['summary']}"
        vector = embed(text)

        results.append(
            {
                "url": article["url"],
                "title": article["title"],
                "summary": article["summary"],
                "category": article["category"],
                "source": article["source"],
                "publishedAt": article["publishedAt"],
                "contentHash": article["contentHash"],
                "embedding": {
                    "model": "all-MiniLM-L6-v2",
                    "dimensions": len(vector),
                    "vector": vector,
                },
            }
        )

    os.makedirs("output", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} vectors to {output_path}")
    print(f"Dimensions per vector: {len(results[0]['embedding']['vector']) if results else 0}")


if __name__ == "__main__":
    main()
