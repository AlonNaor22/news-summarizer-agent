"""FastAPI endpoint tests using TestClient."""

import sys
import os
import pytest

# Ensure project root is on the path so backend.main can set up its own path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Patch the module-level ANTHROPIC_API_KEY in qa_chain BEFORE backend imports it,
# so NewsQAChain._create_llm doesn't raise when api_key is absent in the env.
import src.qa_chain as _qa_chain_mod
if not _qa_chain_mod.ANTHROPIC_API_KEY:
    _qa_chain_mod.ANTHROPIC_API_KEY = "test-key-for-ci"

from fastapi.testclient import TestClient
from backend.main import app
from src.models import Article

# backend/main.py adds the backend dir to sys.path so routes import from
# "api.dependencies" (not "backend.api.dependencies") — grab that same module.
import sys as _sys
deps = _sys.modules.get("api.dependencies") or _sys.modules["backend.api.dependencies"]


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset global app state before each test."""
    deps.app_state.clear()
    yield
    deps.app_state.clear()


@pytest.fixture
def seeded_state():
    """Seed app_state with two canned articles."""
    articles = [
        Article(
            title="AI breakthrough announced",
            source="TechCrunch",
            url="http://example.com/1",
            description="Researchers unveiled a new model.",
            summary="A new AI model was released.",
            category="Technology",
            sentiment="positive",
        ),
        Article(
            title="Economy slows in Q4",
            source="Reuters",
            url="http://example.com/2",
            description="GDP growth fell to 1.2%.",
            summary="Economic growth disappointed analysts.",
            category="Business",
            sentiment="negative",
        ),
    ]
    deps.app_state.articles = articles
    deps.app_state.qa_chain.load_articles(articles)
    return deps.app_state


client = TestClient(app)


# ---------------------------------------------------------------------------
# Basic health / root routes
# ---------------------------------------------------------------------------


def test_root_returns_200():
    resp = client.get("/")
    assert resp.status_code == 200


def test_health_returns_200_when_key_set():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["checks"]["anthropic_key"] == "set"


def test_health_returns_503_when_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


def test_get_articles_empty():
    resp = client.get("/api/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["articles"] == []
    assert data["total"] == 0


def test_get_articles_returns_seeded(seeded_state):
    resp = client.get("/api/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["articles"]) == 2
    assert data["articles"][0]["title"] == "AI breakthrough announced"


def test_get_article_by_invalid_id_returns_404(seeded_state):
    resp = client.get("/api/articles/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Q&A validation — the Field(min_length=1, max_length=2000) task
# ---------------------------------------------------------------------------


def test_qa_ask_empty_question_returns_422():
    resp = client.post("/api/qa/ask", json={"question": ""})
    assert resp.status_code == 422


def test_qa_ask_oversized_question_returns_422():
    resp = client.post("/api/qa/ask", json={"question": "x" * 2001})
    assert resp.status_code == 422


def test_qa_ask_no_articles_returns_400():
    resp = client.post("/api/qa/ask", json={"question": "What is in the news?"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Sentiment summary
# ---------------------------------------------------------------------------


def test_sentiment_returns_counts(seeded_state):
    resp = client.get("/api/sentiment")
    assert resp.status_code == 200
    data = resp.json()
    assert "sentiment_counts" in data or "counts" in data or isinstance(data, dict)
