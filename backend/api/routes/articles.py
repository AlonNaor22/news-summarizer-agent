"""Articles API routes — fetching, processing, and managing news articles."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.categorizer import categorize_articles
from src.models import Article
from src.news_fetcher import fetch_news
from src.sentiment import analyze_sentiments
from src.summarizer import summarize_articles
from src.tagger import tag_articles

from api.dependencies import get_app_state

router = APIRouter()


class FetchRequest(BaseModel):
    """Request model for fetching articles."""
    source: str = "rss"  # "rss", "newsapi", or "both"
    max_per_source: int = 5
    process: bool = True  # Whether to summarize/categorize/tag


@router.post("/fetch")
async def fetch_articles(request: FetchRequest):
    """Fetch raw articles and (optionally) run the full processing pipeline."""
    try:
        articles = fetch_news(
            source=request.source,
            max_per_source=request.max_per_source,
        )

        if not articles:
            return {"articles": [], "total": 0, "message": "No articles fetched"}

        if request.process:
            articles = summarize_articles(articles)
            articles = categorize_articles(articles)
            articles = tag_articles(articles)
            articles = analyze_sentiments(articles)

        for i, article in enumerate(articles):
            article.id = i

        state = get_app_state()
        state.articles = articles

        state.qa_chain.load_articles(articles)

        return {
            "articles": articles,
            "total": len(articles),
            "message": f"Successfully fetched and processed {len(articles)} articles",
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
    offset: int = Query(0, description="Offset for pagination"),
):
    """Return stored articles, applying any of the supported filters."""
    state = get_app_state()
    articles: list[Article] = list(state.articles)

    if category:
        articles = [a for a in articles if (a.category or "").lower() == category.lower()]

    if sentiment:
        articles = [a for a in articles if (a.sentiment or "").lower() == sentiment.lower()]

    if source:
        articles = [a for a in articles if source.lower() in (a.source or "").lower()]

    if keyword:
        keyword_lower = keyword.lower()
        articles = [
            a for a in articles
            if keyword_lower in (a.title or "").lower()
            or keyword_lower in (a.summary or "").lower()
            or any(keyword_lower in kw.lower() for kw in a.keywords)
        ]

    total = len(articles)
    articles = articles[offset:offset + limit]

    return {
        "articles": articles,
        "total": total,
        "limit": limit,
        "offset": offset,
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
    limit: int = Query(20, description="Maximum results"),
):
    """Search articles by title, summary, or keywords."""
    state = get_app_state()
    query_lower = q.lower()

    results = []
    for article in state.articles:
        score = 0

        if query_lower in (article.title or "").lower():
            score += 3

        if query_lower in (article.summary or "").lower():
            score += 2

        for kw in article.keywords:
            if query_lower in kw.lower():
                score += 1
                break

        if score > 0:
            results.append({"article": article, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "results": [r["article"] for r in results[:limit]],
        "total": len(results),
        "query": q,
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
            "by_source": {},
        }

    by_category: dict[str, int] = {}
    for article in articles:
        cat = article.category or "Other"
        by_category[cat] = by_category.get(cat, 0) + 1

    by_sentiment = {"positive": 0, "negative": 0, "neutral": 0}
    for article in articles:
        sent = article.sentiment or "neutral"
        if sent in by_sentiment:
            by_sentiment[sent] += 1

    by_source: dict[str, int] = {}
    for article in articles:
        src = article.source or "Unknown"
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total": len(articles),
        "by_category": by_category,
        "by_sentiment": by_sentiment,
        "by_source": by_source,
    }


@router.delete("/articles")
async def clear_articles():
    """Clear all stored articles."""
    state = get_app_state()
    state.clear()
    return {"message": "All articles cleared"}
