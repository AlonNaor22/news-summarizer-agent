"""Shared article processing pipeline used by both the CLI and the FastAPI backend."""

import asyncio

from src.models import Article
from src.summarizer import summarize_articles_async
from src.categorizer import categorize_articles_async
from src.tagger import tag_articles_async
from src.sentiment import analyze_sentiments_async


async def process_articles_async(articles: list[Article]) -> list[Article]:
    """Run the four-stage pipeline asynchronously and return the result.

    Stages: summarize → categorize → tag → sentiment.

    Within each stage, per-article Claude calls are dispatched concurrently
    via :func:`asyncio.gather` (throttled by ``LLM_CONCURRENCY``). Sharing a
    single event loop across stages avoids the cost of ``asyncio.run`` per
    stage and lets async callers (e.g. FastAPI handlers) await directly.
    """
    articles = await summarize_articles_async(articles)
    articles = await categorize_articles_async(articles)
    articles = await tag_articles_async(articles)
    articles = await analyze_sentiments_async(articles)
    return articles


def process_articles(articles: list[Article]) -> list[Article]:
    """Sync wrapper around :func:`process_articles_async` for non-async callers."""
    return asyncio.run(process_articles_async(articles))
