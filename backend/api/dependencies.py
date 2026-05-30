"""Per-session state management for the API.

Each client gets its own AppState (articles + Q&A memory + caches), keyed by the
X-Session-Id header. Sessions idle beyond SESSION_TTL_SECONDS are evicted by a
background cleanup task. Articles and Q&A history are persisted to the SQLite
database (see ``backend/db.py``) so they survive a backend restart — the in-memory
``AppState`` is hydrated from the DB on first access for a known session_id.
See README "Multi-User Session Management" for the design rationale.
"""

import logging
import re
import threading
import time
import uuid
from typing import Optional

from fastapi import Request

from src.models import Article
from src.qa_chain import NewsQAChain

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 60 * 60  # 1 hour of inactivity

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class AppState:
    """Per-session in-memory state — articles, Q&A chain, derived caches.

    ``collection_name`` is the Chroma collection this session writes its
    embeddings to (see ``src/rag.py``). It's derived deterministically from
    ``session_id`` so the same collection is reused across restarts, keeping
    semantic search aligned with the persisted article order.

    When ``session_id`` is provided, the constructor reloads any persisted
    articles and Q&A history from the database so the session resumes where
    it left off. Constructing ``AppState()`` with no session_id (used by unit
    tests) skips persistence entirely.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id: str = session_id or ""
        suffix = (session_id or uuid.uuid4().hex).replace("-", "")[:32]
        self.collection_name: str = f"session-{suffix}"
        self.articles: list[Article] = []
        self.qa_chain: NewsQAChain = NewsQAChain(collection_name=self.collection_name)
        self.trends: dict = {}
        self.relationships: dict = {}

        if self.session_id:
            self._hydrate_from_db()

    def _hydrate_from_db(self) -> None:
        """Reload persisted articles + Q&A history for this session.

        Best-effort: any DB failure is logged and the in-memory state stays
        empty rather than blocking the request. The Chroma collection is not
        rebuilt here — ``NewsQAChain`` falls back to its full-context prompt
        if semantic search returns nothing, so Q&A still works after restart.
        """
        try:
            from backend.db import load_articles, load_messages
            from langchain_core.messages import AIMessage, HumanMessage
        except Exception:
            logger.warning("DB hydration imports failed", exc_info=True)
            return

        try:
            articles = load_articles(self.session_id)
        except Exception:
            logger.warning("Failed to load persisted articles", exc_info=True)
            articles = []

        if articles:
            for i, article in enumerate(articles):
                article.id = i
            self.articles = articles
            self.qa_chain.load_articles(articles)
            logger.info(
                "session hydrated from DB",
                extra={"session_id": self.session_id, "article_count": len(articles)},
            )

        try:
            messages = load_messages(self.session_id)
        except Exception:
            logger.warning("Failed to load persisted Q&A history", exc_info=True)
            messages = []

        if messages:
            self.qa_chain.chat_history = [
                HumanMessage(content=content)
                if role == "user"
                else AIMessage(content=content)
                for role, content in messages
            ]

    def set_articles(self, articles: list[Article]) -> None:
        """Replace the in-memory article set and persist it to the database.

        Resets the Q&A chain's chat history (in-memory and persisted) because
        a new article set invalidates prior conversation context.
        """
        self.articles = articles
        self.qa_chain.load_articles(articles)

        if not self.session_id:
            return
        try:
            from backend.db import clear_messages, save_articles

            save_articles(self.session_id, articles)
            clear_messages(self.session_id)
        except Exception:
            logger.warning("Failed to persist articles for session", exc_info=True)

    def persist_qa_exchange(self, question: str, answer: str) -> None:
        """Append a user question + assistant answer pair to the persisted history."""
        if not self.session_id or not answer:
            return
        try:
            from backend.db import append_message

            append_message(self.session_id, "user", question)
            append_message(self.session_id, "assistant", answer)
        except Exception:
            logger.warning("Failed to persist Q&A exchange", exc_info=True)

    def clear_qa_history(self) -> None:
        """Reset Q&A chat history in memory and on disk."""
        self.qa_chain.clear_history()
        if not self.session_id:
            return
        try:
            from backend.db import clear_messages

            clear_messages(self.session_id)
        except Exception:
            logger.warning("Failed to clear persisted Q&A history", exc_info=True)

    def clear(self):
        """Reset every field — articles, Q&A history, RAG index, persisted rows."""
        from src.rag import clear_index

        try:
            clear_index(collection_name=self.collection_name)
        except Exception:
            logger.warning("Failed to clear RAG index for session", exc_info=True)

        if self.session_id:
            try:
                from backend.db import clear_articles, clear_messages

                clear_articles(self.session_id)
                clear_messages(self.session_id)
            except Exception:
                logger.warning(
                    "Failed to clear persisted state for session", exc_info=True
                )

        self.articles = []
        self.qa_chain = NewsQAChain(collection_name=self.collection_name)
        self.trends = {}
        self.relationships = {}


class SessionStore:
    """Thread-safe per-session AppState store with TTL eviction.

    The lock guards the dict and last-seen map so the cleanup task can run
    concurrently with route handlers (which execute on FastAPI's threadpool).
    """

    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS):
        self._sessions: dict[str, AppState] = {}
        self._last_seen: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> AppState:
        with self._lock:
            now = time.monotonic()
            state = self._sessions.get(session_id)
            if state is None:
                state = AppState(session_id=session_id)
                self._sessions[session_id] = state
                logger.info("session created", extra={"session_id": session_id})
            self._last_seen[session_id] = now
            return state

    def cleanup_expired(self) -> int:
        """Drop sessions whose last activity is older than the TTL. Returns count."""
        now = time.monotonic()
        with self._lock:
            expired = [
                sid for sid, ts in self._last_seen.items()
                if now - ts > self._ttl
            ]
            for sid in expired:
                self._sessions.pop(sid, None)
                self._last_seen.pop(sid, None)
        if expired:
            logger.info("sessions evicted", extra={"count": len(expired)})
        return len(expired)

    def clear_all(self):
        """Wipe every session — used by tests."""
        with self._lock:
            self._sessions.clear()
            self._last_seen.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)


session_store = SessionStore()


def _is_valid_session_id(sid: str) -> bool:
    return bool(sid) and bool(_UUID_RE.match(sid))


def resolve_session_id(request: Request) -> str:
    """Read X-Session-Id from the request, validating shape or minting a new UUID.

    Result is stashed on request.state so the dependency and middleware see the
    same value. Called from the session middleware in backend/main.py.
    """
    incoming = request.headers.get("X-Session-Id", "")
    sid = incoming if _is_valid_session_id(incoming) else str(uuid.uuid4())
    request.state.session_id = sid
    return sid


def get_session_state(request: Request) -> AppState:
    """FastAPI dependency: return the AppState for this request's session."""
    sid = getattr(request.state, "session_id", None) or resolve_session_id(request)
    return session_store.get_or_create(sid)
