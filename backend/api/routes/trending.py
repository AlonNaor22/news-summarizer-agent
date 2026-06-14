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
    """Return trending topics across all articles: keyword trends, entity trends, and AI themes."""
    articles = state.articles

    if not articles:
        return {
            "keyword_trends": [],
            "entity_trends": {"people": [], "organizations": [], "locations": []},
            "llm_trends": [],
            "total_articles": 0
        }

    # Cache per session, keyed by use_llm: detect_trends fires Claude calls, so
    # repeat requests over the same article set reuse the prior result.
    cache = state.trends_cache
    if cache is not None and cache["use_llm"] == use_llm:
        trends = cache["data"]
    else:
        trends = detect_trends(articles, use_llm=use_llm)
        state.trends_cache = {"use_llm": use_llm, "data": trends}

    return {
        **trends,
        "total_articles": len(articles)
    }


@router.get("/trending/fast")
async def get_trending_fast(
    top_n: int = Query(10, description="Number of top keywords to return"),
    state: AppState = Depends(get_session_state),
):
    """Return trending keywords/entities by frequency only — fast, no LLM calls."""
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
    """Return trending keywords with their article counts."""
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
    """Return trending people, organizations, and locations."""
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
