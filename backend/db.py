"""SQLAlchemy persistence layer — engine, ORM models, and per-session helpers.

The default database lives at ``./news.db`` (SQLite) so dev runs need no setup.
Set ``DATABASE_URL`` to point at Postgres etc. in production.

Articles and Q&A history are keyed by ``session_id`` (the same UUID the frontend
stores in localStorage and sends via the ``X-Session-Id`` header), so each
session's data survives a backend restart but stays isolated from other users.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    delete,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.models import Article

logger = logging.getLogger(__name__)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./news.db")


# SQLite requires check_same_thread=False because SessionLocal is invoked from
# FastAPI's threadpool, which uses worker threads other than the one that
# created the connection. The flag is safe given each request opens its own
# SessionLocal() context.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class ArticleORM(Base):
    """Persistent representation of :class:`src.models.Article`.

    ``position`` is the article's display index within its session — both the
    in-memory ``Article.id`` and the RAG ``article_idx`` metadata are aligned
    to this value so semantic search keeps working after a restart.
    """

    __tablename__ = "articles"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    position = Column(Integer, nullable=False)

    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False)

    description = Column(Text, default="")
    summary = Column(Text, default="")
    published = Column(String, nullable=True)

    category = Column(String, nullable=True)
    secondary_categories = Column(JSON, default=list)

    sentiment = Column(String, nullable=True)
    sentiment_confidence = Column(String, nullable=True)
    sentiment_reason = Column(Text, nullable=True)

    keywords = Column(JSON, default=list)
    people = Column(JSON, default=list)
    organizations = Column(JSON, default=list)
    locations = Column(JSON, default=list)

    author = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    similarity = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationMessageORM(Base):
    """One Q&A turn, persisted with ordering so history can be replayed."""

    __tablename__ = "conversation_messages"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    role = Column(String(16), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    """Create all tables. Idempotent — safe to call at startup."""
    Base.metadata.create_all(bind=engine)


def _article_to_orm(session_id: str, position: int, article: Article) -> ArticleORM:
    return ArticleORM(
        session_id=session_id,
        position=position,
        title=article.title,
        source=article.source,
        url=article.url,
        description=article.description or "",
        summary=article.summary or "",
        published=article.published,
        category=article.category,
        secondary_categories=list(article.secondary_categories or []),
        sentiment=article.sentiment,
        sentiment_confidence=article.sentiment_confidence,
        sentiment_reason=article.sentiment_reason,
        keywords=list(article.keywords or []),
        people=list(article.people or []),
        organizations=list(article.organizations or []),
        locations=list(article.locations or []),
        author=article.author,
        image_url=article.image_url,
        similarity=article.similarity,
    )


def _orm_to_article(orm: ArticleORM) -> Article:
    return Article(
        title=orm.title,
        source=orm.source,
        url=orm.url,
        description=orm.description or "",
        summary=orm.summary or "",
        published=orm.published,
        category=orm.category,
        secondary_categories=list(orm.secondary_categories or []),
        sentiment=orm.sentiment,
        sentiment_confidence=orm.sentiment_confidence,
        sentiment_reason=orm.sentiment_reason,
        keywords=list(orm.keywords or []),
        people=list(orm.people or []),
        organizations=list(orm.organizations or []),
        locations=list(orm.locations or []),
        author=orm.author,
        image_url=orm.image_url,
        id=orm.position,
        similarity=orm.similarity,
    )


def save_articles(session_id: str, articles: list[Article]) -> None:
    """Replace the persisted article set for ``session_id`` with ``articles``.

    Wipes any prior rows for the session first so the indices in the DB match
    the new in-memory list one-to-one.
    """
    with SessionLocal() as session:
        session.execute(delete(ArticleORM).where(ArticleORM.session_id == session_id))
        for i, article in enumerate(articles):
            session.add(_article_to_orm(session_id, i, article))
        session.commit()


def load_articles(session_id: str) -> list[Article]:
    """Return persisted articles for ``session_id``, ordered by position."""
    with SessionLocal() as session:
        rows = (
            session.query(ArticleORM)
            .filter(ArticleORM.session_id == session_id)
            .order_by(ArticleORM.position)
            .all()
        )
        return [_orm_to_article(row) for row in rows]


def clear_articles(session_id: str) -> None:
    """Delete every persisted article for ``session_id``."""
    with SessionLocal() as session:
        session.execute(delete(ArticleORM).where(ArticleORM.session_id == session_id))
        session.commit()


def append_message(session_id: str, role: str, content: str) -> None:
    """Append one Q&A message (``"user"`` or ``"assistant"``) to the history."""
    with SessionLocal() as session:
        next_pos = (
            session.query(ConversationMessageORM)
            .filter(ConversationMessageORM.session_id == session_id)
            .count()
        )
        session.add(
            ConversationMessageORM(
                session_id=session_id,
                position=next_pos,
                role=role,
                content=content,
            )
        )
        session.commit()


def load_messages(session_id: str) -> list[tuple[str, str]]:
    """Return ``[(role, content), ...]`` for the persisted history, in order."""
    with SessionLocal() as session:
        rows = (
            session.query(ConversationMessageORM)
            .filter(ConversationMessageORM.session_id == session_id)
            .order_by(ConversationMessageORM.position)
            .all()
        )
        return [(row.role, row.content) for row in rows]


def clear_messages(session_id: str) -> None:
    """Delete every persisted Q&A message for ``session_id``."""
    with SessionLocal() as session:
        session.execute(
            delete(ConversationMessageORM).where(
                ConversationMessageORM.session_id == session_id
            )
        )
        session.commit()
