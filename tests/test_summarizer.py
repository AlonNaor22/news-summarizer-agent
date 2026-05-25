"""Tests for src/summarizer.py — mocks the LLM chain singleton."""

from unittest.mock import MagicMock

import pytest

import src.summarizer as summarizer
from src.models import Article


def _make_article(**kwargs):
    defaults = dict(
        title="Test Article",
        source="TestSource",
        url="http://example.com",
        description="This is a test description that is long enough to be summarized.",
    )
    defaults.update(kwargs)
    return Article(**defaults)


@pytest.fixture(autouse=True)
def reset_chain():
    """Ensure each test starts with a fresh chain slot."""
    original = summarizer._chain
    yield
    summarizer._chain = original


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_summarize_article_uses_chain_result():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "A canned summary."
    summarizer._chain = mock_chain

    article = _make_article(description="X" * 100)
    result = summarizer.summarize_article(article)

    assert result.summary == "A canned summary."
    mock_chain.invoke.assert_called_once()


def test_summarize_articles_batch():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Summary."
    summarizer._chain = mock_chain

    articles = [_make_article(description="D" * 100) for _ in range(3)]
    results = summarizer.summarize_articles(articles)

    assert len(results) == 3
    assert all(a.summary == "Summary." for a in results)
    assert mock_chain.invoke.call_count == 3


# ---------------------------------------------------------------------------
# Short-content shortcut (no LLM call)
# ---------------------------------------------------------------------------


def test_summarize_article_skips_short_content():
    mock_chain = MagicMock()
    summarizer._chain = mock_chain

    article = _make_article(description="Too short")
    result = summarizer.summarize_article(article)

    mock_chain.invoke.assert_not_called()
    assert "unavailable" in result.summary.lower()


# ---------------------------------------------------------------------------
# LLM exception → graceful default
# ---------------------------------------------------------------------------


def test_summarize_article_handles_llm_error():
    mock_chain = MagicMock()
    mock_chain.invoke.side_effect = RuntimeError("LLM unavailable")
    summarizer._chain = mock_chain

    article = _make_article(description="D" * 100)
    results = summarizer.summarize_articles([article])

    assert len(results) == 1
    assert "error" in results[0].summary.lower() or results[0].summary == ""
