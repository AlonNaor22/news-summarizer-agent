"""Mutable state container for the News Summarizer Agent CLI."""

from dataclasses import dataclass, field
from typing import Any

from src.models import Article


@dataclass
class AgentState:
    """Holds the agent's articles, Q&A chain, and analysis caches."""

    articles: list[Article] = field(default_factory=list)
    qa_chain: Any | None = None
    is_running: bool = True
    trends_cache: dict | None = None
    relationships_cache: dict | None = None
    comparisons_cache: list | None = None
