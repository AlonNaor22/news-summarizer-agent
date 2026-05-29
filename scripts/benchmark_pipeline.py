"""One-off wall-clock benchmark for the async LLM pipeline.

Fetches ~10 articles via RSS and runs the four-stage pipeline
(summarize → categorize → tag → sentiment), printing each stage's
wall-clock so we can verify the asyncio.gather speedup.

Run from the repo root:
    venv/Scripts/python scripts/benchmark_pipeline.py
"""

import asyncio
import logging
import time

import sys
import pathlib

# Ensure repo root is on sys.path so `src.*` imports work when invoked directly.
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from src.news_fetcher import fetch_news
from src.summarizer import summarize_articles_async
from src.categorizer import categorize_articles_async
from src.tagger import tag_articles_async
from src.sentiment import analyze_sentiments_async


async def _stage(label, coro):
    t0 = time.monotonic()
    result = await coro
    elapsed = time.monotonic() - t0
    print(f"  {label:<14} {elapsed:6.2f}s  ({len(result)} articles)")
    return result


async def main():
    print("Fetching articles via RSS (max_per_source=2)...")
    articles = fetch_news(source="rss", max_per_source=2)
    articles = articles[:10]
    print(f"  -> fetched {len(articles)} articles\n")

    if not articles:
        print("No articles fetched; aborting.")
        return

    print("Running async pipeline (LLM_CONCURRENCY=5):")
    t0 = time.monotonic()
    articles = await _stage("summarize", summarize_articles_async(articles))
    articles = await _stage("categorize", categorize_articles_async(articles))
    articles = await _stage("tag", tag_articles_async(articles))
    articles = await _stage("sentiment", analyze_sentiments_async(articles))
    total = time.monotonic() - t0

    print(f"\nTotal pipeline wall-clock: {total:.2f}s "
          f"({total / max(len(articles), 1):.2f}s per article)")
    print(f"Sequential baseline at ~2s per call x 4 stages x {len(articles)} articles "
          f"~= {len(articles) * 8:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
