from __future__ import annotations

import argparse
import time
from pathlib import Path

from geosurvey_rag.knowledge_sources import crawl_sources
from geosurvey_rag.ingestion import build_index, knowledge_changed, load_manifest
from geosurvey_rag.settings import settings


def reindex_if_needed(
    source_dir: Path,
    index_dir: Path,
    force: bool = False,
    crawl_first: bool = False,
) -> dict:
    crawl_result = crawl_sources() if crawl_first else None
    changed = force or knowledge_changed(source_dir, index_dir)
    if not changed:
        manifest = load_manifest(index_dir) or {}
        return {
            "updated": False,
            "reason": "knowledge_not_changed",
            "crawl": crawl_result,
            "manifest": manifest,
        }

    chunk_count = build_index(source_dir, index_dir)
    manifest = load_manifest(index_dir) or {}
    return {
        "updated": True,
        "reason": "force" if force else "knowledge_changed",
        "chunk_count": chunk_count,
        "crawl": crawl_result,
        "manifest": manifest,
    }


def watch(source_dir: Path, index_dir: Path, interval_seconds: int, crawl_first: bool = False) -> None:
    print(f"Watching {source_dir} every {interval_seconds}s")
    while True:
        result = reindex_if_needed(source_dir, index_dir, crawl_first=crawl_first)
        if result["updated"]:
            print(f"Rebuilt index with {result['chunk_count']} chunks")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-update GeoSurveyRAG knowledge index.")
    parser.add_argument("--source", type=Path, default=settings.knowledge_dir)
    parser.add_argument("--index", type=Path, default=settings.index_dir)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--once", action="store_true", help="Check once and exit.")
    parser.add_argument("--force", action="store_true", help="Rebuild even when files are unchanged.")
    parser.add_argument("--crawl-first", action="store_true", help="Run configured crawler before checking index.")
    args = parser.parse_args()

    if args.once:
        print(reindex_if_needed(args.source, args.index, args.force, args.crawl_first))
        return

    watch(args.source, args.index, args.interval, args.crawl_first)


if __name__ == "__main__":
    main()
