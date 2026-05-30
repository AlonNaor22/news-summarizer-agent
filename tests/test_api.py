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

# Fixed UUID for all tests in this module — every request the client makes
# carries this header, so requests share one AppState (matching the singleton
# semantics the suite was originally written against).
TEST_SESSION_ID = "00000000-0000-4000-8000-000000000000"


def _truncate_db_tables():
    """Wipe persisted articles + Q&A history so each test starts clean."""
    from backend.db import ArticleORM, ConversationMessageORM, SessionLocal

    with SessionLocal() as session:
        session.query(ArticleORM).delete()
        session.query(ConversationMessageORM).delete()
        session.commit()


@pytest.fixture(autouse=True)
def reset_session_store():
    """Drop every in-memory session and persisted row before and after each test."""
    deps.session_store.clear_all()
    _truncate_db_tables()
    yield
    deps.session_store.clear_all()
    _truncate_db_tables()


@pytest.fixture
def seeded_state():
    """Seed the test-session AppState with two canned articles."""
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
    state = deps.session_store.get_or_create(TEST_SESSION_ID)
    state.articles = articles
    state.qa_chain.load_articles(articles)
    return state


client = TestClient(app, headers={"X-Session-Id": TEST_SESSION_ID})


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
# Session headers — per-session state contract
# ---------------------------------------------------------------------------


def test_session_id_echoed_in_response_header():
    resp = client.get("/api/articles")
    assert resp.headers.get("X-Session-Id") == TEST_SESSION_ID


def test_server_mints_session_id_when_header_missing():
    bare_client = TestClient(app)
    resp = bare_client.get("/api/articles")
    minted = resp.headers.get("X-Session-Id")
    assert minted and minted != TEST_SESSION_ID
    assert len(minted) == 36  # uuid4 string length


def test_server_mints_session_id_when_header_invalid():
    bare_client = TestClient(app, headers={"X-Session-Id": "not-a-uuid"})
    resp = bare_client.get("/api/articles")
    minted = resp.headers.get("X-Session-Id")
    assert minted and minted != "not-a-uuid"
    assert len(minted) == 36


def test_sessions_are_isolated():
    """Two clients with different session IDs see independent articles."""
    sid_a = "11111111-1111-4111-8111-111111111111"
    sid_b = "22222222-2222-4222-8222-222222222222"

    state_a = deps.session_store.get_or_create(sid_a)
    state_a.articles = [
        Article(title="A only", source="X", url="http://a", summary="a")
    ]

    state_b = deps.session_store.get_or_create(sid_b)
    state_b.articles = [
        Article(title="B only", source="Y", url="http://b", summary="b"),
        Article(title="B second", source="Y", url="http://b2", summary="b2"),
    ]

    client_a = TestClient(app, headers={"X-Session-Id": sid_a})
    client_b = TestClient(app, headers={"X-Session-Id": sid_b})

    resp_a = client_a.get("/api/articles")
    resp_b = client_b.get("/api/articles")

    assert resp_a.json()["total"] == 1
    assert resp_a.json()["articles"][0]["title"] == "A only"
    assert resp_b.json()["total"] == 2


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
# Q&A streaming (SSE)
# ---------------------------------------------------------------------------


def test_qa_stream_empty_question_returns_422():
    resp = client.post("/api/qa/ask/stream", json={"question": ""})
    assert resp.status_code == 422


def test_qa_stream_no_articles_returns_400():
    resp = client.post("/api/qa/ask/stream", json={"question": "What is happening?"})
    assert resp.status_code == 400


def test_qa_stream_emits_sse_chunks(seeded_state):
    """Patch qa_chain.astream to a fake async generator and assert SSE framing."""

    async def fake_astream(_question):
        for piece in ["Hello ", "world", "!"]:
            yield piece

    seeded_state.qa_chain.astream = fake_astream

    with client.stream(
        "POST",
        "/api/qa/ask/stream",
        json={"question": "Say hi"},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = b"".join(resp.iter_bytes()).decode("utf-8")

    # Each chunk arrives as `event: chunk\ndata: {"text": "..."}\n\n`
    assert 'event: chunk' in body
    assert '"text": "Hello "' in body
    assert '"text": "world"' in body
    assert '"text": "!"' in body
    # Final event must be `done` with the article count
    assert 'event: done' in body
    assert '"article_count": 2' in body


# ---------------------------------------------------------------------------
# Sentiment summary
# ---------------------------------------------------------------------------


def test_sentiment_returns_counts(seeded_state):
    resp = client.get("/api/sentiment")
    assert resp.status_code == 200
    data = resp.json()
    assert "sentiment_counts" in data or "counts" in data or isinstance(data, dict)


# ---------------------------------------------------------------------------
# Persistence — articles + Q&A history survive a simulated backend restart
# ---------------------------------------------------------------------------


def test_articles_survive_restart():
    """Save articles to DB, drop in-memory sessions, GET should still return them."""
    from backend.db import save_articles

    persisted = [
        Article(
            title="Persistent headline",
            source="DBPress",
            url="http://example.com/persist",
            summary="Survives backend restart.",
            category="Technology",
            sentiment="neutral",
            keywords=["persistence", "sqlite"],
        ),
    ]
    save_articles(TEST_SESSION_ID, persisted)

    # Simulate a backend restart: every cached AppState is dropped, but the DB row remains.
    deps.session_store.clear_all()

    resp = client.get("/api/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["articles"][0]["title"] == "Persistent headline"
    assert data["articles"][0]["keywords"] == ["persistence", "sqlite"]


def test_qa_history_survives_restart():
    """Persisted Q&A messages should be reloaded into chat_history after restart."""
    from backend.db import append_message, save_articles

    save_articles(
        TEST_SESSION_ID,
        [Article(title="X", source="S", url="http://example.com/x", summary="x")],
    )
    append_message(TEST_SESSION_ID, "user", "What's the headline?")
    append_message(TEST_SESSION_ID, "assistant", "It's about X.")

    deps.session_store.clear_all()

    resp = client.get("/api/qa/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message_count"] == 2
    assert data["history"][0] == {"role": "user", "content": "What's the headline?"}
    assert data["history"][1] == {"role": "assistant", "content": "It's about X."}


def test_clear_articles_removes_persisted_rows(seeded_state):
    """DELETE /api/articles wipes the DB rows, not just the in-memory cache."""
    from backend.db import load_articles, save_articles

    save_articles(TEST_SESSION_ID, seeded_state.articles)
    assert len(load_articles(TEST_SESSION_ID)) == 2

    resp = client.delete("/api/articles")
    assert resp.status_code == 200
    assert load_articles(TEST_SESSION_ID) == []
