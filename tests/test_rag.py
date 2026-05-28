"""Tests for src/rag.py — vector embedding and semantic search.

These tests load the real sentence-transformers model and write to a temp
Chroma collection. They exercise the actual retrieval behaviour (not mocks),
so the cost is one model load shared across the module.
"""

import uuid

import pytest

from src.models import Article
from src.rag import clear_index, embed_articles, semantic_search


@pytest.fixture(scope="module")
def collection_name():
    """A fresh per-test-module collection that is wiped after the tests run."""
    name = f"test-rag-{uuid.uuid4().hex[:8]}"
    yield name
    clear_index(collection_name=name)


@pytest.fixture(scope="module")
def articles():
    return [
        Article(
            title="EU Parliament Approves AI Act",
            source="Reuters",
            url="http://example.com/1",
            summary=(
                "European lawmakers passed sweeping new rules for artificial "
                "intelligence systems, setting compliance requirements for "
                "high-risk applications."
            ),
            category="Politics",
        ),
        Article(
            title="Lakers Beat Celtics in Overtime",
            source="ESPN",
            url="http://example.com/2",
            summary="LeBron James scored 35 points in a thrilling overtime win.",
            category="Sports",
        ),
        Article(
            title="White House AI Safety Executive Order",
            source="NPR",
            url="http://example.com/3",
            summary=(
                "The administration released an order requiring frontier model "
                "developers to report safety testing results."
            ),
            category="Politics",
        ),
        Article(
            title="Apple Reveals New iPhone Camera",
            source="The Verge",
            url="http://example.com/4",
            summary="Apple unveiled a larger main sensor for low-light photos.",
            category="Technology",
        ),
    ]


def test_embed_articles_returns_count(collection_name, articles):
    n = embed_articles(articles, collection_name=collection_name)
    assert n == len(articles)


def test_embed_empty_list_returns_zero(collection_name):
    assert embed_articles([], collection_name=collection_name) == 0


def test_semantic_search_finds_topic_without_keyword(collection_name, articles):
    """The word 'regulation' isn't in any summary, but AI-policy articles still surface."""
    embed_articles(articles, collection_name=collection_name)
    hits = semantic_search(
        "What's happening with AI regulation?",
        articles,
        k=2,
        collection_name=collection_name,
    )
    assert len(hits) == 2
    titles = " ".join(h.title for h in hits)
    assert "AI Act" in titles or "AI Safety" in titles
    assert "Lakers" not in titles


def test_semantic_search_returns_correct_topic_for_sports(collection_name, articles):
    embed_articles(articles, collection_name=collection_name)
    hits = semantic_search(
        "NBA basketball game last night",
        articles,
        k=1,
        collection_name=collection_name,
    )
    assert len(hits) == 1
    assert "Lakers" in hits[0].title


def test_semantic_search_empty_query_returns_empty(collection_name, articles):
    assert semantic_search("", articles, k=5, collection_name=collection_name) == []


def test_semantic_search_no_articles_returns_empty(collection_name):
    assert semantic_search("anything", [], k=5, collection_name=collection_name) == []


def test_embed_articles_reset_replaces_collection(collection_name, articles):
    """Calling embed_articles a second time should overwrite, not append."""
    embed_articles(articles, collection_name=collection_name)
    embed_articles(articles[:2], collection_name=collection_name)
    hits = semantic_search(
        "AI safety", articles[:2], k=5, collection_name=collection_name
    )
    # Only 2 articles in the collection now, so we get at most 2 back.
    assert len(hits) <= 2
