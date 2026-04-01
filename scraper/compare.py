"""
One Bite News — Cross-Source Story Comparison

Orchestrates the full pipeline per source, saves intermediate files, then
finds articles covering the same story across different outlets.

Output structure:
    output/
    ├── nbc/
    │   ├── YYYY-MM-DD_articles.json
    │   └── YYYY-MM-DD_vectors.json
    ├── abc/
    │   └── ...
    ├── bbc/
    │   └── ...
    └── YYYY-MM-DD_clusters.json

Usage:
    python compare.py                    # run full pipeline, all sources
    python compare.py --limit 30         # cap at 30 articles per source
    python compare.py --threshold 0.80   # adjust similarity threshold (default 0.80)
    python compare.py --no-summarize     # skip AI summarization (uses teaser instead)
"""

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from itertools import combinations

import numpy as np

from dynamo import fetch_today, write_stories
from embed import embed, embed_batch
from main import SOURCES
from summarize import enrich
from utils import get_today


def parse_args():
    parser = argparse.ArgumentParser(description="Cross-source story comparison")
    parser.add_argument("--limit", type=int, default=None, help="Articles per source (default: all)")
    parser.add_argument("--threshold", type=float, default=0.72, help="Similarity threshold 0-1 (default: 0.72)")
    parser.add_argument("--from-cache", action="store_true", help="Load saved articles from output/, skip scraping and summarization")
    parser.add_argument("--date", type=str, default=None, help="Override date for cache lookup and DynamoDB writes (YYYY-MM-DD)")
    parser.add_argument("--check", action="store_true", help="Show similarity stats for each cluster without enriching")
    parser.add_argument("--dropped", action="store_true", help="Show cross-source pairs below threshold to evaluate cutoff")
    return parser.parse_args()


def save(data: list, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {len(data)} records → {path}")


def cosine_similarity(a, b) -> float:
    return float(np.dot(a, b))


def run_source(name: str, scrape_fn, date_str: str, limit: int) -> list[dict]:
    folder = f"output/{name}"

    # ── Step 1: Scrape ──────────────────────────────────────────
    articles = scrape_fn(limit=limit)

    # Save scraped articles
    save(articles, f"{folder}/{date_str}_articles.json")

    # ── Step 2: Vectorize on title + teaser ──────────────────────
    print(f"[{name.upper()}] Embedding {len(articles)} articles...")
    texts = [
        article["title"] + (". " + article["teaser"] if article.get("teaser") else "")
        for article in articles
    ]
    embeddings = embed_batch(texts)
    vectors = []
    for article, vector in zip(articles, embeddings):
        article["_vector"] = vector
        vectors.append(
            {
                **{k: v for k, v in article.items() if k not in ("fullText", "_vector")},
                "embedding": {
                    "model": "all-mpnet-base-v2",
                    "dimensions": len(vector),
                    "vector": vector,
                },
            }
        )

    save(vectors, f"{folder}/{date_str}_vectors.json")

    return articles


def dedupe_articles(articles: list[dict], threshold: float = 0.97) -> list[dict]:
    """Remove near-duplicate articles within the same source only.
    Handles outlets that publish the same story multiple times across different feeds."""
    by_source: dict[str, list] = {}
    for article in articles:
        by_source.setdefault(article["source"], []).append(article)

    kept = []
    for source_articles in by_source.values():
        seen = []
        for article in source_articles:
            if not any(cosine_similarity(article["_vector"], k["_vector"]) >= threshold for k in seen):
                seen.append(article)
                kept.append(article)
    return kept


_SKIP_TITLE_RE = re.compile(
    r"(?i)^how to (watch|stream|follow)\b"
    r"|^where to (watch|stream)\b"
    r"|\btv channels?\b"                                # schedule/streaming guides
    r"|\blive streams?\b"                               # streaming guides
    r"|\bbest[- ]dressed\b"
    r"|\bworst[- ]dressed\b"
    r"|\bafter[- ]party (looks|photos|pics|outfits)\b"
    r"|\bred carpet looks\b"
    r"|\bsee the best.*\blooks\b"
    r"|\bbehind[- ]the[- ]scenes\b"                    # any "behind the scenes" article
    r"|\b(photos?|pics?|pictures?|images?|gallery)\s*from\b"
    r"|\ball the looks\b"
    r"|\bstars who (wore|dared)\b"
    r"|\blive\s*:\s"                                    # live blog mid-title (e.g. "War live: ...")
    r"|\bpostmortem\b"                                  # trade publication postmortems/analysis
    r"|^from the .{0,20} desk\b"                        # newsletter roundups (e.g. "From The Sports Desk")
    r"|\bdaily open\b"                                  # CNBC Daily Open newsletter
)


def _is_clusterable(article: dict) -> bool:
    """Return False for guide, gallery, and fashion articles that pollute clusters."""
    return not _SKIP_TITLE_RE.search(article.get("title", ""))


def find_clusters(articles: list[dict], threshold: float, min_pair: float = 0.55) -> list[dict]:
    """Cluster articles by similarity, then strip outliers whose best match in the cluster is below min_pair."""
    print(f"\nComparing {len(articles)} articles across sources (threshold: {threshold}, min_pair: {min_pair})...")

    # Build full similarity matrix in one numpy matmul (vectors are pre-normalized → dot product = cosine sim)
    vectors = np.array([a["_vector"] for a in articles], dtype=np.float32)
    sim_matrix = vectors @ vectors.T  # (n, n)

    # Find all cross-source pairs above threshold
    rows, cols = np.where(sim_matrix >= threshold)
    matches = []
    for i, j in zip(rows.tolist(), cols.tolist()):
        if i >= j:
            continue
        if articles[i]["source"] == articles[j]["source"]:
            continue
        matches.append((float(sim_matrix[i, j]), i, j))

    print(f"Found {len(matches)} cross-source matches above threshold...")
    matches.sort(reverse=True)

    # Union-find clustering
    parent = list(range(len(articles)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for _, i, j in matches:
        union(i, j)

    cluster_map = {}
    for idx in range(len(articles)):
        cluster_map.setdefault(find(idx), []).append(idx)

    # Build score lookup for fast access
    score_cache = {}
    for score, i, j in matches:
        score_cache[(min(i, j), max(i, j))] = score

    def pair_score(i, j):
        return score_cache.get((min(i, j), max(i, j)), 0.0)

    # Strip outliers: remove any article whose best similarity to any other
    # article in the cluster is below min_pair
    def prune(indices):
        if len(indices) <= 1:
            return indices
        kept = list(indices)
        changed = True
        while changed:
            changed = False
            next_kept = []
            for i in kept:
                best = max((pair_score(i, j) for j in kept if j != i), default=0.0)
                if best >= min_pair:
                    next_kept.append(i)
                else:
                    changed = True
            kept = next_kept
        return kept

    clusters = []
    for root, indices in cluster_map.items():
        pruned = prune(indices)
        if not pruned:
            continue

        # Cap to 1 article per source (keep the one with the highest max pair score)
        by_source: dict[str, list] = {}
        for i in pruned:
            by_source.setdefault(articles[i]["source"], []).append(i)
        capped = []
        for src_indices in by_source.values():
            best_i = max(src_indices, key=lambda i: max(
                (pair_score(i, j) for j in pruned if j != i), default=0.0
            ))
            capped.append(best_i)

        sources = {articles[i]["source"] for i in capped}
        clusters.append(
            {
                "storyId": f"story_{root}",
                "sourceCount": len(sources),
                "unique": len(sources) == 1,
                "_articles": [articles[i] for i in capped],
            }
        )

    clusters.sort(key=lambda c: c["sourceCount"], reverse=True)
    return clusters


def check_dropped(articles: list[dict], threshold: float, min_score: float = 0.50):
    """Show all cross-source pairs below threshold but above min_score, sorted by score desc."""
    vectors = np.array([a["_vector"] for a in articles], dtype=np.float32)
    sim_matrix = vectors @ vectors.T

    pairs = []
    rows, cols = np.where((sim_matrix >= min_score) & (sim_matrix < threshold))
    for i, j in zip(rows.tolist(), cols.tolist()):
        if i >= j:
            continue
        if articles[i]["source"] == articles[j]["source"]:
            continue
        pairs.append((float(sim_matrix[i, j]), articles[i], articles[j]))

    pairs.sort(key=lambda x: x[0], reverse=True)
    print(f"\n{'═' * 60}")
    print(f"DROPPED PAIRS (score {min_score:.2f}–{threshold:.2f}), {len(pairs)} total")
    print(f"{'═' * 60}")
    for score, a, b in pairs:
        print(f"\n  {score:.3f}  [{a['source']}] {a['title'][:60]}")
        print(f"         [{b['source']}] {b['title'][:60]}")


def check_clusters(clusters: list[dict], top_n: int = 30):
    """Print similarity stats for each cluster to spot weak groupings."""
    print(f"\n{'═' * 60}")
    print(f"CLUSTER QUALITY CHECK (top {top_n} by source count)")
    print(f"{'═' * 60}")
    for cluster in clusters[:top_n]:
        arts = cluster["_articles"]
        sources = [a["source"] for a in arts]
        titles = [a["title"] for a in arts]

        # Compute all pairwise similarities within the cluster
        pairs = list(combinations(range(len(arts)), 2))
        if pairs:
            scores = [cosine_similarity(arts[i]["_vector"], arts[j]["_vector"]) for i, j in pairs]
            min_s, avg_s, max_s = min(scores), sum(scores) / len(scores), max(scores)
            # Find the weakest pair
            weak_i, weak_j = min(pairs, key=lambda p: cosine_similarity(arts[p[0]]["_vector"], arts[p[1]]["_vector"]))
            flag = " ⚠️ " if min_s < 0.60 else ""
        else:
            min_s = avg_s = max_s = 1.0
            flag = ""

        print(f"\n{flag}[{cluster['sourceCount']} sources] min={min_s:.2f} avg={avg_s:.2f} max={max_s:.2f}")
        for t, s in zip(titles, sources):
            print(f"  [{s}] {t[:70]}")
        if pairs and min_s < 0.70:
            print(f"  ↳ weakest pair: [{arts[weak_i]['source']}] vs [{arts[weak_j]['source']}] = {cosine_similarity(arts[weak_i]['_vector'], arts[weak_j]['_vector']):.2f}")


def _latest_published(articles: list[dict]) -> str:
    """Return the most recent publishedAt across articles as an ISO string, or now if none."""
    dates = [_parse_date(a.get("publishedAt")) for a in articles]
    dates = [d for d in dates if d]
    if not dates:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    latest = max(dates)
    if not latest.tzinfo:
        latest = latest.replace(tzinfo=timezone.utc)
    return latest.strftime("%Y-%m-%dT%H:%M:%SZ")


def enrich_cluster(cluster: dict) -> dict | None:
    """Single API call to generate title, summary, and category for a cluster."""
    articles = cluster["_articles"]
    titles = [a["title"] for a in articles]
    texts = [a.get("fullText") or a.get("teaser") or "" for a in articles]
    texts = [t for t in texts if t.strip()]

    enriched = enrich(titles, texts)
    if enriched is None:
        return None

    return {
        "storyId": cluster["storyId"],
        "sourceCount": cluster["sourceCount"],
        "mergedTitle": enriched["mergedTitle"],
        "mergedSummary": enriched["mergedSummary"],
        "category": enriched["category"],
        "mostRecentUpdate": _latest_published(articles),
        "articles": [{"source": a["source"], "url": a["url"], "imageUrl": a.get("imageUrl", "")} for a in articles],
    }


def _parse_date(date_str: str) -> datetime | None:
    """Parse ISO or RFC 2822 date strings into a timezone-aware datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def _ts():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def main():
    args = parse_args()
    now_utc = datetime.now(timezone.utc)
    date_str = args.date or get_today()
    t_start = datetime.now(timezone.utc)
    print(f"[{_ts()}] Pipeline started")

    # ── Step 1: Scrape + summarize + vectorize all sources ───────
    all_articles = []

    if args.from_cache:
        print("Loading articles from cache (skipping scrape + summarize)...")
        for name in SOURCES:
            path = f"output/{name}/{date_str}_articles.json"
            if not os.path.exists(path):
                print(f"  Warning: no cache found for {name} at {path}")
                continue
            with open(path) as f:
                articles = json.load(f)
            print(f"  [{name.upper()}] Embedding {len(articles)} cached articles...")
            texts = [
                a["title"] + (". " + a["teaser"] if a.get("teaser") else "")
                for a in articles
            ]
            for article, vector in zip(articles, embed_batch(texts)):
                article["_vector"] = vector
            all_articles.extend(articles)
            print(f"  [{name.upper()}] Loaded {len(articles)} articles")
    else:
        def _run_source(item):
            name, scrape_fn = item
            print(f"\n{'─' * 50}\nProcessing: {name.upper()}\n{'─' * 50}")
            return run_source(name, scrape_fn, date_str, args.limit)

        with ThreadPoolExecutor(max_workers=40) as pool:
            futures = {pool.submit(_run_source, item): item[0] for item in SOURCES.items()}
            for future in as_completed(futures):
                all_articles.extend(future.result())
        print(f"[{_ts()}] Scraping done — {len(all_articles)} articles")

    # ── Step 2: Filter to target date ───────────────────────────
    # Skip when loading from cache — articles were already filtered at scrape time
    if not args.from_cache:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = target_dt - timedelta(hours=12)   # noon UTC day before (timezone overlap)
        end_dt = target_dt + timedelta(days=1)     # midnight UTC end of target day
        before = len(all_articles)

        def _in_window(a):
            dt = _parse_date(a.get("publishedAt"))
            if not dt:
                return False
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return cutoff <= dt < end_dt

        all_articles = [a for a in all_articles if _in_window(a)]
        print(f"\nDate filter: {before} → {len(all_articles)} articles for {date_str}")

    # ── Step 2b: Deduplicate near-identical articles (wire reposts) ─
    before = len(all_articles)
    all_articles = dedupe_articles(all_articles, threshold=0.97)
    print(f"[{_ts()}] Embedding + dedup done — {len(all_articles)} articles")

    # ── Step 3: Cluster (exclude AP wire + guide/gallery articles) ──
    cluster_articles = [a for a in all_articles if a["source"] != "AP News" and _is_clusterable(a)]
    print(f"Clustering {len(cluster_articles)} articles (AP + guides/galleries excluded)")
    raw_clusters = find_clusters(cluster_articles, args.threshold)
    top_raw = [c for c in raw_clusters if c["sourceCount"] >= 2][:100]
    print(f"[{_ts()}] Clustering done — {len(top_raw)} multi-source clusters")

    # ── Step 3b: Check/dropped mode — print stats and exit ───────
    if args.check:
        check_clusters(raw_clusters)
        return
    if args.dropped:
        check_dropped(cluster_articles, args.threshold)
        return

    # ── Step 4: Load existing stories, build URL → story lookup ──
    existing = fetch_today(date_str)
    url_to_story = {}
    for story in existing:
        for article in story.get("articles", []):
            url_to_story[article["url"]] = story

    def _find_cached(cluster_articles: list[dict]):
        """Return existing story if 2+ URLs overlap, else None."""
        urls = {a["url"] for a in cluster_articles}
        matches = {}
        for url in urls:
            story = url_to_story.get(url)
            if story:
                sid = story["storyId"]
                matches[sid] = matches.get(sid, 0) + 1
        best_id, best_count = max(matches.items(), key=lambda x: x[1], default=(None, 0))
        if best_count >= 2:
            return next(s for s in existing if s["storyId"] == best_id)
        return None

    # ── Step 5: Enrich only new/changed clusters ─────────────────
    print(f"\nEnriching {len(top_raw)} clusters (reusing cached where possible)...")
    clusters = [None] * len(top_raw)
    reused = 0

    def _enrich(args):
        i, cluster = args
        articles = cluster["_articles"]
        cached = _find_cached(articles)
        if cached:
            cached_urls = {a["url"] for a in cached.get("articles", [])}
            new_urls = {a["url"] for a in articles} - cached_urls
            if not new_urls:
                # Nothing changed — reuse summary, use new storyId (fresh DynamoDB write)
                return i, {
                    "storyId": cluster["storyId"],
                    "sourceCount": cluster["sourceCount"],
                    "mergedTitle": cached["mergedTitle"],
                    "mergedSummary": cached["mergedSummary"],
                    "category": cached["category"],
                    "mostRecentUpdate": _latest_published(articles),
                    "articles": [{"source": a["source"], "url": a["url"], "imageUrl": a.get("imageUrl", "")} for a in articles],
                }, True
        print(f"\n[{i + 1}/{len(top_raw)}] {articles[0]['title'][:65]}")
        result = enrich_cluster(cluster)
        return i, result, False

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_enrich, (i, c)): i for i, c in enumerate(top_raw)}
        for future in as_completed(futures):
            i, result, was_cached = future.result()
            clusters[i] = result
            if was_cached:
                reused += 1

    clusters = [c for c in clusters if c is not None]
    print(f"\nReused {reused} cached stories, enriched {len(clusters)} ({len(top_raw) - len(clusters)} failed)")
    print(f"[{_ts()}] Enrichment done")

    # ── Step 5: Save + write to DynamoDB ────────────────────────
    clusters_path = f"output/{date_str}_clusters.json"
    save(clusters, clusters_path)
    write_stories(clusters, date_str)
    print(f"[{_ts()}] DynamoDB write done")

    elapsed = (datetime.now(timezone.utc) - t_start).seconds
    print(f"\n{'═' * 50}")
    print(f"Total time:       {elapsed // 60}m {elapsed % 60}s")
    print(f"Total stories:    {len(clusters)}")
    print("\nTop matched stories:")
    for cluster in clusters[:5]:
        sources = " + ".join(a["source"] for a in cluster["articles"])
        print(f"\n• [{sources}] {cluster['mergedTitle']}")


if __name__ == "__main__":
    main()
