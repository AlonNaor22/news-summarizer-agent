"""Tests for the shared article-processing pipeline (src/pipeline.py).

The per-article LLM calls are patched out; these tests exercise the pipeline's
orchestration — that every stage runs and that categorize and tag overlap.
"""

import asyncio

from src.models import Article
from src.pipeline import process_articles_async


def _make_articles(n: int) -> list[Article]:
    return [
        Article(
            title=f"Article {i}",
            source="S",
            url=f"http://example.com/{i}",
            description="A sufficiently long description for processing purposes.",
        )
        for i in range(n)
    ]


def test_process_articles_populates_all_stage_fields(monkeypatch):
    """Every stage runs: summary, category, tags, and sentiment are all set."""

    async def fake_summarize(article):
        article.summary = f"summary:{article.title}"
        return article

    async def fake_categorize(article):
        article.category = "Technology"
        return article

    async def fake_tag(article):
        article.keywords = ["kw"]
        return article

    async def fake_sentiment(article):
        article.sentiment = "positive"
        return article

    monkeypatch.setattr("src.summarizer.summarize_article_async", fake_summarize)
    monkeypatch.setattr("src.categorizer.categorize_article_async", fake_categorize)
    monkeypatch.setattr("src.tagger.tag_article_async", fake_tag)
    monkeypatch.setattr("src.sentiment.analyze_sentiment_async", fake_sentiment)

    result = asyncio.run(process_articles_async(_make_articles(3)))

    assert len(result) == 3
    for article in result:
        assert article.summary == f"summary:{article.title}"
        assert article.category == "Technology"
        assert article.keywords == ["kw"]
        assert article.sentiment == "positive"


def test_categorize_and_tag_run_concurrently(monkeypatch):
    """Categorize and tag overlap: each blocks until the other has started.

    If the pipeline ran these stages serially, ``fake_categorize`` would wait
    on an event that ``fake_tag`` never gets to set, the ``wait_for`` would time
    out, and the run would raise — failing the test.
    """
    cat_started = asyncio.Event()
    tag_started = asyncio.Event()

    async def fake_summarize(article):
        article.summary = "s"
        return article

    async def fake_categorize(article):
        cat_started.set()
        await asyncio.wait_for(tag_started.wait(), timeout=3)
        article.category = "Technology"
        return article

    async def fake_tag(article):
        tag_started.set()
        await asyncio.wait_for(cat_started.wait(), timeout=3)
        article.keywords = ["kw"]
        return article

    async def fake_sentiment(article):
        article.sentiment = "neutral"
        return article

    monkeypatch.setattr("src.summarizer.summarize_article_async", fake_summarize)
    monkeypatch.setattr("src.categorizer.categorize_article_async", fake_categorize)
    monkeypatch.setattr("src.tagger.tag_article_async", fake_tag)
    monkeypatch.setattr("src.sentiment.analyze_sentiment_async", fake_sentiment)

    articles = [
        Article(title="A", source="S", url="http://example.com/a", description="x" * 60)
    ]
    result = asyncio.run(process_articles_async(articles))

    assert result[0].category == "Technology"
    assert result[0].keywords == ["kw"]
