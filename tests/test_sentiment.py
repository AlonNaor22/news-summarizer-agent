"""Tests for src/sentiment.py — mocks the LLM chain singleton."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

import src.sentiment as sentiment
from src.sentiment import SentimentResult
from src.models import Article


def _make_article(**kwargs):
    defaults = dict(
        title="Test Article",
        source="TestSource",
        url="http://example.com",
        summary="This is a summary that is long enough to require sentiment analysis.",
    )
    defaults.update(kwargs)
    return Article(**defaults)


@pytest.fixture(autouse=True)
def reset_chain():
    original = sentiment._chain
    yield
    sentiment._chain = original


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_analyze_sentiment_happy_path():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = SentimentResult(
        sentiment="positive", confidence="high", reason="The article reports good news."
    )
    sentiment._chain = mock_chain

    article = _make_article()
    result = sentiment.analyze_sentiment(article)

    assert result.sentiment == "positive"
    assert result.sentiment_confidence == "high"
    assert result.sentiment_reason == "The article reports good news."
    mock_chain.invoke.assert_called_once()


def test_analyze_sentiment_negative():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = SentimentResult(
        sentiment="negative", confidence="medium", reason="Bad news reported."
    )
    sentiment._chain = mock_chain

    result = sentiment.analyze_sentiment(_make_article())
    assert result.sentiment == "negative"


# ---------------------------------------------------------------------------
# Short-content shortcut (no LLM call)
# ---------------------------------------------------------------------------


def test_analyze_sentiment_skips_short_content():
    mock_chain = MagicMock()
    sentiment._chain = mock_chain

    article = _make_article(summary="", description="Short")
    result = sentiment.analyze_sentiment(article)

    mock_chain.invoke.assert_not_called()
    assert result.sentiment == "neutral"
    assert result.sentiment_confidence == "low"


# ---------------------------------------------------------------------------
# LLM exception → graceful default
# ---------------------------------------------------------------------------


def test_analyze_sentiments_handles_llm_error():
    # Batch runs through the async path → mock ainvoke.
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
    sentiment._chain = mock_chain

    article = _make_article()
    results = sentiment.analyze_sentiments([article])

    assert len(results) == 1
    assert results[0].sentiment == "neutral"
    assert results[0].sentiment_confidence == "low"


# ---------------------------------------------------------------------------
# SentimentResult Pydantic model — malformed structured-output edge cases
# ---------------------------------------------------------------------------


def test_sentiment_result_rejects_invalid_sentiment():
    with pytest.raises(ValidationError):
        SentimentResult(sentiment="unknown", confidence="high", reason="test")


def test_sentiment_result_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        SentimentResult(sentiment="positive", confidence="very_high", reason="test")
