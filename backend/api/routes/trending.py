"""
Trending API Routes

Endpoints for trending topics and keyword analysis.
"""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, Query

from src.trending import detect_trends, get_trending_keywords, get_trending_entities

from api.dependencies import get_app_state

router = APIRouter()


@router.get("/trending")
async def get_trending_topics(
    use_llm: bool = Query(True, description="Use AI for smart trend detection"),
    top_n: int = Query(10, description="Number of top keywords to return")
):
    """
    Get trending topics across all articles.

    - **use_llm**: If true, uses AI to identify themes and patterns
    - **top_n**: Number of top keywords to return

    Returns keyword trends, entity trends, and AI-detected themes.
    """
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {
            "keyword_trends": [],
            "entity_trends": {"people": [], "organizations": [], "locations": []},
            "llm_trends": [],
            "total_articles": 0
        }

    # Detect trends
    trends = detect_trends(articles, use_llm=use_llm)

    # Store in app state
    state.trends = trends

    return {
        **trends,
        "total_articles": len(articles)
    }


@router.get("/trending/fast")
async def get_trending_fast(
    top_n: int = Query(10, description="Number of top keywords to return")
):
    """
    Get trending keywords quickly (no AI analysis).

    This is faster and doesn't use API calls, but only provides
    keyword frequency analysis without intelligent theme detection.
    """
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {
            "keyword_trends": [],
            "entity_trends": {"people": [], "organizations": [], "locations": []},
            "total_articles": 0
        }

    keyword_trends = get_trending_keywords(articles, top_n=top_n)
    entity_trends = get_trending_entities(articles, top_n=5)

    return {
        "keyword_trends": keyword_trends,
        "entity_trends": entity_trends,
        "total_articles": len(articles)
    }


@router.get("/trending/keywords")
async def get_keywords(
    top_n: int = Query(20, description="Number of keywords to return")
):
    """
    Get trending keywords with article counts.
    """
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {"keywords": [], "total_articles": 0}

    keywords = get_trending_keywords(articles, top_n=top_n)

    return {
        "keywords": keywords,
        "total_articles": len(articles)
    }


@router.get("/trending/entities")
async def get_entities(
    top_n: int = Query(10, description="Number of entities per type")
):
    """
    Get trending people, organizations, and locations.
    """
    state = get_app_state()
    articles = state.articles

    if not articles:
        return {
            "people": [],
            "organizations": [],
            "locations": [],
            "total_articles": 0
        }

    entities = get_trending_entities(articles, top_n=top_n)

    return {
        **entities,
        "total_articles": len(articles)
    }


@router.get("/trending/keyword/{keyword}")
async def get_articles_by_keyword(keyword: str):
    """
    Get all articles containing a specific keyword.
    """
    state = get_app_state()
    keyword_lower = keyword.lower()

    matching = []
    for article in state.articles:
        for kw in article.get("keywords", []):
            if keyword_lower == kw.lower():
                matching.append(article)
                break

    return {
        "keyword": keyword,
        "articles": matching,
        "total": len(matching)
    }
