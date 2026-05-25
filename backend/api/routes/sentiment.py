"""Sentiment API routes — sentiment analysis of articles."""

from fastapi import APIRouter, Query
from typing import Optional

from src.sentiment import get_sentiment_summary, filter_by_sentiment

from api.dependencies import get_app_state

router = APIRouter()


@router.get("/sentiment")
async def get_sentiment_overview():
    """
    Get sentiment analysis summary for all articles.

    Returns counts and percentages for positive, negative, and neutral articles.
    """
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "breakdown": {"positive": 0, "negative": 0, "neutral": 0}
        }

    summary = get_sentiment_summary(articles)
    return summary


@router.get("/sentiment/{sentiment_type}")
async def get_articles_by_sentiment(
    sentiment_type: str,
    limit: int = Query(50, description="Maximum articles to return")
):
    """
    Get articles filtered by sentiment type.

    - **sentiment_type**: "positive", "negative", or "neutral"
    """
    state = get_app_state()

    if sentiment_type.lower() not in ["positive", "negative", "neutral"]:
        return {
            "error": "Invalid sentiment type. Use: positive, negative, or neutral",
            "articles": []
        }

    filtered = filter_by_sentiment(state.articles, sentiment_type)

    return {
        "sentiment": sentiment_type,
        "articles": filtered[:limit],
        "total": len(filtered)
    }


@router.get("/sentiment/distribution/by-category")
async def get_sentiment_by_category():
    """Sentiment distribution broken down by article category."""
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {"distribution": {}}

    distribution: dict[str, dict[str, int]] = {}

    for article in articles:
        category = article.category or "Other"
        sentiment = article.sentiment or "neutral"

        if category not in distribution:
            distribution[category] = {"positive": 0, "negative": 0, "neutral": 0}

        if sentiment in distribution[category]:
            distribution[category][sentiment] += 1

    return {"distribution": distribution}


@router.get("/sentiment/distribution/by-source")
async def get_sentiment_by_source():
    """Sentiment distribution broken down by news source."""
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {"distribution": {}}

    distribution: dict[str, dict[str, int]] = {}

    for article in articles:
        source = article.source or "Unknown"
        sentiment = article.sentiment or "neutral"

        if source not in distribution:
            distribution[source] = {"positive": 0, "negative": 0, "neutral": 0}

        if sentiment in distribution[source]:
            distribution[source][sentiment] += 1

    return {"distribution": distribution}
