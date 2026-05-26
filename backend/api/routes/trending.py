"""Trending API routes — trending topics and keyword analysis."""

from fastapi import APIRouter, Depends, Query

from src.trending import detect_trends, get_trending_keywords, get_trending_entities

from api.dependencies import AppState, get_session_state

router = APIRouter()


@router.get("/trending")
def get_trending_topics(
    use_llm: bool = Query(True, description="Use AI for smart trend detection"),
    top_n: int = Query(10, description="Number of top keywords to return"),
    state: AppState = Depends(get_session_state),
):
    """
    Get trending topics across all articles.

    - **use_llm**: If true, uses AI to identify themes and patterns
    - **top_n**: Number of top keywords to return

    Returns keyword trends, entity trends, and AI-detected themes.
    """
    articles = state.articles

    if not articles:
        return {
            "keyword_trends": [],
            "entity_trends": {"people": [], "organizations": [], "locations": []},
            "llm_trends": [],
            "total_articles": 0
        }

    trends = detect_trends(articles, use_llm=use_llm)

    state.trends = trends

    return {
        **trends,
        "total_articles": len(articles)
    }


@router.get("/trending/fast")
async def get_trending_fast(
    top_n: int = Query(10, description="Number of top keywords to return"),
    state: AppState = Depends(get_session_state),
):
    """
    Get trending keywords quickly (no AI analysis).

    This is faster and doesn't use API calls, but only provides
    keyword frequency analysis without intelligent theme detection.
    """
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
    top_n: int = Query(20, description="Number of keywords to return"),
    state: AppState = Depends(get_session_state),
):
    """
    Get trending keywords with article counts.
    """
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
    top_n: int = Query(10, description="Number of entities per type"),
    state: AppState = Depends(get_session_state),
):
    """
    Get trending people, organizations, and locations.
    """
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
async def get_articles_by_keyword(
    keyword: str,
    state: AppState = Depends(get_session_state),
):
    """Return all articles tagged with the given keyword (case-insensitive)."""
    keyword_lower = keyword.lower()

    matching = []
    for article in state.articles:
        for kw in article.keywords:
            if keyword_lower == kw.lower():
                matching.append(article)
                break

    return {
        "keyword": keyword,
        "articles": matching,
        "total": len(matching),
    }
