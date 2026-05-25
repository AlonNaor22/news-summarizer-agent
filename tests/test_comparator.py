"""Tests for src/comparator.py — mocks the LLM chain singleton."""

from unittest.mock import MagicMock

import pytest

import src.comparator as comparator
from src.comparator import ComparisonResult, SourceAnalysis
from src.models import Article


def _make_article(title="Test", source="Source", category="Technology", **kwargs):
    return Article(
        title=title,
        source=source,
        url="http://example.com",
        summary="A test summary for comparison.",
        category=category,
        **kwargs,
    )


@pytest.fixture(autouse=True)
def reset_chain():
    original = comparator._chain
    yield
    comparator._chain = original


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_compare_sources_happy_path():
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = ComparisonResult(
        story_summary="AI was announced.",
        common_facts=["Fact A", "Fact B"],
        source_analyses=[
            SourceAnalysis(
                source="BBC",
                tone="positive",
                emphasis="Technology benefits",
            ),
            SourceAnalysis(
                source="Reuters",
                tone="neutral",
                emphasis="Economic impact",
            ),
        ],
        key_differences=["BBC is optimistic; Reuters is measured"],
        overall_assessment="Coverage is balanced.",
    )
    comparator._chain = mock_chain

    articles = [
        _make_article(title="AI news", source="BBC"),
        _make_article(title="AI news", source="Reuters"),
    ]
    result = comparator.compare_sources(articles)

    assert result.story_summary == "AI was announced."
    assert "BBC" in result.source_analyses
    assert "Reuters" in result.source_analyses
    mock_chain.invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Too few articles → no LLM call
# ---------------------------------------------------------------------------


def test_compare_sources_single_article_returns_error():
    mock_chain = MagicMock()
    comparator._chain = mock_chain

    result = comparator.compare_sources([_make_article()])

    mock_chain.invoke.assert_not_called()
    assert result.error is not None


# ---------------------------------------------------------------------------
# LLM exception → handled by the caller (compare_all_stories swallows)
# ---------------------------------------------------------------------------


def test_compare_all_stories_handles_llm_error(monkeypatch):
    mock_chain = MagicMock()
    mock_chain.invoke.side_effect = RuntimeError("LLM error")
    comparator._chain = mock_chain

    # Two articles from different sources on the same story (high similarity)
    a1 = _make_article(title="AI breakthrough", source="BBC",
                       category="Technology", keywords=["ai", "technology"])
    a2 = _make_article(title="AI breakthrough", source="Reuters",
                       category="Technology", keywords=["ai", "technology"])
    a1.similarity = {"combined": 0.9}
    a2.similarity = {"combined": 0.9}

    # Monkeypatch find_same_story_articles to avoid similarity computation
    monkeypatch.setattr(
        comparator, "find_same_story_articles",
        lambda arts: [{"story_title": "AI", "articles": [a1, a2], "sources": ["BBC", "Reuters"]}],
    )

    results = comparator.compare_all_stories([a1, a2])
    # compare_all_stories catches exceptions per story
    assert isinstance(results, list)
