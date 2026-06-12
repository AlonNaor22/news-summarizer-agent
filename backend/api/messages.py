"""Centralized client-facing text for the API layer.

Collecting the user-visible ``HTTPException`` detail strings and response
``message``/``error`` fields in one place keeps wording consistent and makes
adding a second language later a drop-in change. Internal log messages, LLM
prompt text, and enum/identifier values deliberately live elsewhere — only
copy that can reach an API client belongs here.

Parameterized messages are exposed as small helper functions so call sites
stay declarative (``messages.article_not_found(aid)``) instead of re-deriving
the wording with their own f-strings.
"""

import uuid

# --- Articles ---------------------------------------------------------------
NO_ARTICLES_FETCHED = "No articles fetched"
ALL_ARTICLES_CLEARED = "All articles cleared"
ARTICLE_NOT_FOUND = "Article not found"


def fetch_succeeded(count: int) -> str:
    """Success message for a completed fetch + processing run."""
    return f"Successfully fetched and processed {count} articles"


def fetch_failed(request_id: uuid.UUID) -> str:
    """500 detail for an unhandled fetch error, carrying the log correlation id."""
    return f"Internal error processing fetch (id={request_id})"


def article_not_found(article_id: int) -> str:
    """404 detail naming the specific missing article id."""
    return f"Article {article_id} not found"


# --- Q&A --------------------------------------------------------------------
NO_ARTICLES_LOADED = "No articles loaded. Please fetch articles first."
CONVERSATION_HISTORY_CLEARED = "Conversation history cleared"


def qa_failed(request_id: uuid.UUID) -> str:
    """Error detail for an unhandled Q&A error (used by both /qa/ask and its SSE stream)."""
    return f"Internal error answering question (id={request_id})"


# --- Comparison -------------------------------------------------------------
NEED_TWO_TO_COMPARE = "Need at least 2 articles to compare"
NO_MULTISOURCE_STORIES = "No multi-source stories found for bias analysis"


# --- Sentiment --------------------------------------------------------------
INVALID_SENTIMENT_TYPE = "Invalid sentiment type. Use: positive, negative, or neutral"
