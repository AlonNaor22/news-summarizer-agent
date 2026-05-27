"""Tests for src/qa_chain.py — patches the LLM on the instance."""

import asyncio
from unittest.mock import MagicMock

import pytest

from src.qa_chain import NewsQAChain
from src.models import Article


def _make_articles(n=2):
    return [
        Article(
            title=f"Article {i}",
            source="TestSource",
            url=f"http://example.com/{i}",
            summary="A test summary for Q&A.",
        )
        for i in range(n)
    ]


@pytest.fixture
def qa(monkeypatch):
    """NewsQAChain with the internal chain swapped for a mock."""
    chain = NewsQAChain()
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Mocked answer."
    chain.chain = mock_chain
    chain.load_articles(_make_articles())
    return chain


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_ask_returns_chain_response(qa):
    answer = qa.ask("What is the main story?")
    assert answer == "Mocked answer."
    qa.chain.invoke.assert_called_once()


def test_ask_appends_to_history(qa):
    qa.ask("First question?")
    qa.ask("Follow-up question?")
    history = qa.get_history()
    assert len(history) == 4  # 2 human + 2 ai messages


def test_clear_history_resets_conversation(qa):
    qa.ask("Hello?")
    qa.clear_history()
    assert qa.get_history() == []


# ---------------------------------------------------------------------------
# No articles loaded
# ---------------------------------------------------------------------------


def test_ask_no_articles_returns_message():
    chain = NewsQAChain()
    mock_chain = MagicMock()
    chain.chain = mock_chain

    answer = chain.ask("What's happening?")
    assert "no articles" in answer.lower()
    mock_chain.invoke.assert_not_called()


# ---------------------------------------------------------------------------
# Context is cached
# ---------------------------------------------------------------------------


def test_articles_context_cached_in_load():
    chain = NewsQAChain()
    articles = _make_articles(3)
    chain.load_articles(articles)
    context_after_load = chain._articles_context
    assert context_after_load != ""
    # Calling load_articles again rebuilds the cache
    chain.load_articles(articles[:1])
    assert chain._articles_context != context_after_load


# ---------------------------------------------------------------------------
# Streaming (.astream)
# ---------------------------------------------------------------------------


def test_astream_yields_chunks_and_commits_history():
    """Patch the inner chain's .astream so we control what flows out."""

    async def run():
        qa = NewsQAChain()

        async def fake_astream(_inputs):
            for piece in ["Hello", " ", "world"]:
                yield piece

        fake = MagicMock()
        fake.astream = fake_astream
        qa.chain = fake
        qa.load_articles(_make_articles())

        collected = []
        async for chunk in qa.astream("What's up?"):
            collected.append(chunk)
        return qa, collected

    qa, collected = asyncio.run(run())

    assert collected == ["Hello", " ", "world"]
    history = qa.get_history()
    assert len(history) == 2
    assert history[0].content == "What's up?"
    assert history[1].content == "Hello world"


def test_astream_no_articles_yields_notice():
    async def run():
        qa = NewsQAChain()
        chunks = []
        async for chunk in qa.astream("Anything?"):
            chunks.append(chunk)
        return qa, chunks

    qa, chunks = asyncio.run(run())
    assert len(chunks) == 1
    assert "no articles" in chunks[0].lower()
    assert qa.get_history() == []
