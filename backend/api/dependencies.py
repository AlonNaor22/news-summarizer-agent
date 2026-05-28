"""Per-session state management for the API.

Each client gets its own AppState (articles + Q&A memory + caches), keyed by the
X-Session-Id header. Sessions idle beyond SESSION_TTL_SECONDS are evicted by a
background cleanup task. See README "Multi-User Session Management" for the
design rationale.
"""

import logging
import re
import threading
import time
import uuid
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
    embeddings to (see ``src/rag.py``). Each session gets its own collection
    so semantic search and RAG-backed Q&A stay isolated between users.
    """

    def __init__(self):
        self.collection_name: str = f"session-{uuid.uuid4().hex[:16]}"
        self.articles: list[Article] = []
        self.qa_chain: NewsQAChain = NewsQAChain(collection_name=self.collection_name)
        self.trends: dict = {}
        self.relationships: dict = {}

    def clear(self):
        """Reset every field — articles, Q&A history, trend/relationship caches."""
        from src.rag import clear_index

        try:
            clear_index(collection_name=self.collection_name)
        except Exception:
            logger.warning("Failed to clear RAG index for session", exc_info=True)

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
                state = AppState()
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
