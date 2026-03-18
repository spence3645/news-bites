"""
Adds mergedSummary to an existing clusters JSON file.

Usage:
    python merge_clusters.py output/2026-03-09_clusters.json
"""

import json
import sys

from summarize import merge


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "output/2026-03-09_clusters.json"

    with open(path) as f:
        clusters = json.load(f)

    total = len(clusters)
    for i, cluster in enumerate(clusters):
        summaries = [a["summary"] for a in cluster["articles"] if a.get("summary")]

        if len(summaries) > 1:
            print(f"({i + 1}/{total}) Merging {len(summaries)} summaries — {cluster['articles'][0]['title'][:60]}")
            cluster["mergedSummary"] = merge(summaries)
        else:
            cluster["mergedSummary"] = summaries[0] if summaries else ""
            print(f"({i + 1}/{total}) Single source, skipping — {cluster['articles'][0]['title'][:60]}")

    with open(path, "w") as f:
        json.dump(clusters, f, indent=2)

    print(f"\nDone — saved to {path}")


if __name__ == "__main__":
    main()
