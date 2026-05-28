"""Retrieval-augmented generation helpers — embed articles into a local Chroma
vector store and run semantic search over them.

Embeddings come from a local sentence-transformers model (no API key needed);
the index persists at ``./chroma_db`` so re-runs don't re-embed everything.

Typical usage::

    from src.rag import embed_articles, semantic_search

    embed_articles(articles)              # one-shot indexing after fetch
    hits = semantic_search("AI regulation", k=5)
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.models import Article

logger = logging.getLogger(__name__)


DEFAULT_PERSIST_DIR = os.path.abspath(os.path.join(os.getcwd(), "chroma_db"))
DEFAULT_COLLECTION = "news_articles"
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


_embeddings_singleton: Optional[HuggingFaceEmbeddings] = None
_embeddings_lock = threading.Lock()


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return a process-wide HuggingFaceEmbeddings instance.

    Loading a sentence-transformers model takes a few seconds and ~80MB of
    RAM, so we share one instance across calls.
    """
    global _embeddings_singleton
    if _embeddings_singleton is None:
        with _embeddings_lock:
            if _embeddings_singleton is None:
                logger.info("Loading embedding model: %s", DEFAULT_EMBED_MODEL)
                _embeddings_singleton = HuggingFaceEmbeddings(
                    model_name=DEFAULT_EMBED_MODEL,
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embeddings_singleton


def _article_to_document(article: Article, article_idx: int) -> Document:
    """Render an Article into the text + metadata used for embedding/retrieval."""
    parts = [
        f"Title: {article.title or ''}",
        f"Category: {article.category or ''}",
        f"Summary: {article.summary or article.description or ''}",
    ]
    if article.keywords:
        parts.append("Keywords: " + ", ".join(article.keywords))
    page_content = "\n".join(p for p in parts if p.strip())

    metadata = {
        "article_idx": article_idx,
        "title": article.title or "",
        "source": article.source or "",
        "url": article.url or "",
        "category": article.category or "",
    }
    return Document(page_content=page_content, metadata=metadata)


def get_vectorstore(
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> Chroma:
    """Open (or create) the persistent Chroma collection."""
    return Chroma(
        collection_name=collection_name,
        embedding_function=_get_embeddings(),
        persist_directory=persist_directory,
    )


def embed_articles(
    articles: list[Article],
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    reset: bool = True,
) -> int:
    """Embed ``articles`` into the local Chroma collection. Returns the count added.

    ``reset=True`` (default) wipes the existing collection first so the index
    matches the current article set exactly — important because the Q&A and
    search routes look up articles by index into the in-memory list.
    """
    if not articles:
        logger.info("embed_articles called with no articles; skipping")
        return 0

    vectorstore = get_vectorstore(persist_directory, collection_name)

    if reset:
        try:
            vectorstore.reset_collection()
        except Exception:
            logger.warning("reset_collection failed; recreating", exc_info=True)
            vectorstore = get_vectorstore(persist_directory, collection_name)

    documents = [_article_to_document(a, i) for i, a in enumerate(articles)]
    ids = [f"article-{i}" for i in range(len(articles))]
    vectorstore.add_documents(documents=documents, ids=ids)

    logger.info(
        "Embedded %d articles into collection '%s'", len(documents), collection_name
    )
    return len(documents)


def semantic_search(
    query: str,
    articles: list[Article],
    k: int = 5,
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> list[Article]:
    """Return the top-``k`` articles most semantically similar to ``query``.

    Looks up matches in the persisted Chroma collection, then maps them back to
    the in-memory ``articles`` list via the stored ``article_idx`` metadata so
    callers get full Article objects (not just the embedded text).
    """
    if not query or not articles:
        return []

    vectorstore = get_vectorstore(persist_directory, collection_name)
    try:
        matches = vectorstore.similarity_search(query, k=min(k, len(articles)))
    except Exception:
        logger.exception("semantic_search query failed")
        return []

    results: list[Article] = []
    seen: set[int] = set()
    for doc in matches:
        idx = doc.metadata.get("article_idx")
        if idx is None or idx in seen or idx < 0 or idx >= len(articles):
            continue
        seen.add(idx)
        results.append(articles[idx])
    return results


def clear_index(
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> None:
    """Drop the persisted collection. Mainly useful for tests and CLI resets."""
    try:
        vectorstore = get_vectorstore(persist_directory, collection_name)
        vectorstore.reset_collection()
    except Exception:
        logger.warning("clear_index: reset_collection failed; deleting dir", exc_info=True)
        if os.path.isdir(persist_directory):
            shutil.rmtree(persist_directory, ignore_errors=True)
