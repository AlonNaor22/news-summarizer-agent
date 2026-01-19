"""
Articles API Routes

Endpoints for fetching, processing, and managing news articles.
"""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from src.news_fetcher import fetch_news
from src.summarizer import summarize_articles
from src.categorizer import categorize_articles
from src.tagger import tag_articles
from src.sentiment import analyze_sentiments

from api.dependencies import get_app_state

router = APIRouter()


class FetchRequest(BaseModel):
    """Request model for fetching articles."""
    source: str = "rss"  # "rss", "newsapi", or "both"
    max_per_source: int = 5
    process: bool = True  # Whether to summarize/categorize/tag


class ArticleResponse(BaseModel):
    """Response model for article data."""
    articles: list[dict]
    total: int


@router.post("/fetch")
async def fetch_articles(request: FetchRequest):
    """
    Fetch and optionally process news articles.

    - **source**: "rss", "newsapi", or "both"
    - **max_per_source**: Maximum articles per source/category
    - **process**: If true, summarize, categorize, tag, and analyze sentiment
    """
    try:
        # Fetch raw articles
        articles = fetch_news(
            source=request.source,
            max_per_source=request.max_per_source
        )

        if not articles:
            return {"articles": [], "total": 0, "message": "No articles fetched"}

        # Process articles if requested
        if request.process:
            articles = summarize_articles(articles)
            articles = categorize_articles(articles)
            articles = tag_articles(articles)
            articles = analyze_sentiments(articles)

        # Add unique IDs to articles
        for i, article in enumerate(articles):
            article["id"] = i

        # Store in app state
        state = get_app_state()
        state.articles = articles

        # Load into Q&A chain
        state.qa_chain.load_articles(articles)

        return {
            "articles": articles,
            "total": len(articles),
            "message": f"Successfully fetched and processed {len(articles)} articles"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles")
async def get_articles(
    category: Optional[str] = Query(None, description="Filter by category"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    source: Optional[str] = Query(None, description="Filter by source"),
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    limit: int = Query(50, description="Maximum articles to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Get all stored articles with optional filters.
    """
    state = get_app_state()
    articles = state.articles.copy()

    # Apply filters
    if category:
        articles = [a for a in articles if a.get("category", "").lower() == category.lower()]

    if sentiment:
        articles = [a for a in articles if a.get("sentiment", "").lower() == sentiment.lower()]

    if source:
        articles = [a for a in articles if source.lower() in a.get("source", "").lower()]

    if keyword:
        keyword_lower = keyword.lower()
        articles = [
            a for a in articles
            if keyword_lower in a.get("title", "").lower()
            or keyword_lower in a.get("summary", "").lower()
            or keyword_lower in str(a.get("keywords", [])).lower()
        ]

    # Apply pagination
    total = len(articles)
    articles = articles[offset:offset + limit]

    return {
        "articles": articles,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/articles/{article_id}")
async def get_article(article_id: int):
    """Get a single article by ID."""
    state = get_app_state()

    if article_id < 0 or article_id >= len(state.articles):
        raise HTTPException(status_code=404, detail="Article not found")

    return state.articles[article_id]


@router.get("/articles/search")
async def search_articles(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Maximum results")
):
    """
    Search articles by title, summary, or keywords.
    """
    state = get_app_state()
    query_lower = q.lower()

    results = []
    for article in state.articles:
        score = 0

        # Check title
        if query_lower in article.get("title", "").lower():
            score += 3

        # Check summary
        if query_lower in article.get("summary", "").lower():
            score += 2

        # Check keywords
        for kw in article.get("keywords", []):
            if query_lower in kw.lower():
                score += 1
                break

        if score > 0:
            results.append({"article": article, "score": score})

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "results": [r["article"] for r in results[:limit]],
        "total": len(results),
        "query": q
    }


@router.get("/stats")
async def get_stats():
    """Get statistics about the stored articles."""
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {
            "total": 0,
            "by_category": {},
            "by_sentiment": {},
            "by_source": {}
        }

    # Count by category
    by_category = {}
    for article in articles:
        cat = article.get("category", "Other")
        by_category[cat] = by_category.get(cat, 0) + 1

    # Count by sentiment
    by_sentiment = {"positive": 0, "negative": 0, "neutral": 0}
    for article in articles:
        sent = article.get("sentiment", "neutral")
        if sent in by_sentiment:
            by_sentiment[sent] += 1

    # Count by source
    by_source = {}
    for article in articles:
        src = article.get("source", "Unknown")
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total": len(articles),
        "by_category": by_category,
        "by_sentiment": by_sentiment,
        "by_source": by_source
    }


@router.delete("/articles")
async def clear_articles():
    """Clear all stored articles."""
    state = get_app_state()
    state.clear()
    return {"message": "All articles cleared"}
