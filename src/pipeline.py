"""Shared article processing pipeline used by both the CLI and the FastAPI backend."""

from src.models import Article
from src.summarizer import summarize_articles
from src.categorizer import categorize_articles
from src.tagger import tag_articles
from src.sentiment import analyze_sentiments


def process_articles(articles: list[Article]) -> list[Article]:
    """Run the four-stage pipeline on a list of articles and return the result.

    Stages: summarize → categorize → tag → sentiment.
    """
    articles = summarize_articles(articles)
    articles = categorize_articles(articles)
    articles = tag_articles(articles)
    articles = analyze_sentiments(articles)
    return articles
