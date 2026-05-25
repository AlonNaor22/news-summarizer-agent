"""Shared dependencies and state management for the API."""

from src.models import Article
from src.qa_chain import NewsQAChain


class AppState:
    """In-memory application state shared across all FastAPI route handlers."""

    def __init__(self):
        self.articles: list[Article] = []
        self.qa_chain: NewsQAChain = NewsQAChain()
        self.trends: dict = {}
        self.relationships: dict = {}

    def clear(self):
        """Reset every field — articles, Q&A history, trend/relationship caches."""
        self.articles = []
        self.qa_chain = NewsQAChain()
        self.trends = {}
        self.relationships = {}


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Get the global app state."""
    return app_state
