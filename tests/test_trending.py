"""Tests for src/trending.py — mocks the LLM chain singleton."""

from unittest.mock import MagicMock

import pytest

import src.trending as trending
from src.trending import Trend, TrendList
from src.models import Article


def _make_article(title="Test", keywords=None, **kwargs):
    return Article(
        title=title,
        source="TestSource",
        url="http://example.com",
        summary="A test summary long enough for analysis.",
        keywords=keywords or ["ai", "technology"],
        **kwargs,
    )


@pytest.fixture(autouse=True)
def reset_chain():
    original = trending._chain
    yield
    trending._chain = original


# ---------------------------------------------------------------------------
# Statistical trending (no LLM call)
# ---------------------------------------------------------------------------


def test_detect_trends_no_llm_returns_keyword_trends():
    articles = [
        _make_article(keywords=["ai", "technology"]),
        _make_article(keywords=["ai", "research"]),
    ]
    result = trending.detect_trends(articles, use_llm=False)

    assert "keyword_trends" in result
    keywords = [kw["keyword"] for kw in result["keyword_trends"]]
    assert "ai" in keywords
    assert result["llm_trends"] == []


# ---------------------------------------------------------------------------
# LLM-backed trending (happy path)
# ---------------------------------------------------------------------------


def test_detect_trends_llm_uses_chain_result():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = TrendList(
        trends=[
            Trend(
                name="AI Growth",
                strength="high",
                description="AI is growing rapidly.",
                keywords=["ai"],
                article_count=2,
            )
        ]
    )
    trending._chain = mock_chain

    articles = [_make_article(), _make_article(title="Article 2")]
    result = trending.detect_trends(articles, use_llm=True)

    assert len(result["llm_trends"]) == 1
    assert result["llm_trends"][0]["name"] == "AI Growth"
    mock_chain.invoke.assert_called_once()


# ---------------------------------------------------------------------------
# LLM exception → graceful fallback
# ---------------------------------------------------------------------------


def test_detect_trends_llm_error_falls_back_to_empty():
    mock_chain = MagicMock()
    mock_chain.invoke.side_effect = RuntimeError("LLM error")
    trending._chain = mock_chain

    articles = [_make_article(), _make_article()]
    result = trending.detect_trends(articles, use_llm=True)

    assert result["llm_trends"] == []
    # Statistical trends should still be present
    assert "keyword_trends" in result
