"""
Shared dependencies and state management for the API.
"""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.qa_chain import NewsQAChain


class AppState:
    """
    Application state to store articles and Q&A chain.
    This allows sharing state across API endpoints.
    """

    def __init__(self):
        self.articles: list[dict] = []
        self.qa_chain: NewsQAChain = NewsQAChain()
        self.trends: dict = {}
        self.relationships: dict = {}

    def clear(self):
        """Clear all stored data."""
        self.articles = []
        self.qa_chain = NewsQAChain()
        self.trends = {}
        self.relationships = {}


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Get the global app state."""
    return app_state
