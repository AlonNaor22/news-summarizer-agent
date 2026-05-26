"""Comparison API routes — comparing how different sources cover the same story."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List

from src.comparator import (
    find_same_story_articles,
    compare_sources,
    compare_all_stories,
    summarize_bias_findings
)

from api.dependencies import AppState, get_session_state

router = APIRouter()


class CompareRequest(BaseModel):
    """Request model for comparing specific articles."""
    article_ids: List[int]


@router.get("/comparison/stories")
async def get_same_story_groups(state: AppState = Depends(get_session_state)):
    """Find groups of articles that cover the same story across different sources."""
    if len(state.articles) < 2:
        return {"stories": [], "total": 0}

    stories = find_same_story_articles(state.articles)

    result = []
    for story in stories:
        article_ids = []
        for art in story["articles"]:
            try:
                article_ids.append(state.articles.index(art))
            except ValueError:
                article_ids.append(-1)

        result.append({
            "story_title": story["story_title"],
            "sources": story["sources"],
            "source_count": story["source_count"],
            "article_ids": article_ids,
        })

    return {"stories": result, "total": len(result)}


@router.get("/comparison")
def compare_all(state: AppState = Depends(get_session_state)):
    """
    Compare all stories that have multiple source coverage.

    This performs a full analysis comparing how different news sources
    cover the same events, identifying:
    - Common facts
    - Different emphases
    - Potential bias
    """
    if len(state.articles) < 2:
        return {"comparisons": [], "total": 0}

    comparisons = compare_all_stories(state.articles)

    return {
        "comparisons": comparisons,
        "total": len(comparisons)
    }


@router.post("/comparison/specific")
async def compare_specific_articles(
    request: CompareRequest,
    state: AppState = Depends(get_session_state),
):
    """
    Compare specific articles by their IDs.

    Use this when you want to manually select which articles to compare.
    """
    articles_to_compare = []
    for aid in request.article_ids:
        if aid < 0 or aid >= len(state.articles):
            raise HTTPException(status_code=404, detail=f"Article {aid} not found")
        articles_to_compare.append(state.articles[aid])

    if len(articles_to_compare) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 articles to compare"
        )

    comparison = compare_sources(articles_to_compare)

    return comparison


@router.get("/comparison/bias")
async def get_bias_analysis(state: AppState = Depends(get_session_state)):
    """
    Get bias analysis summary across all comparisons.

    Shows which sources have been flagged for potential bias
    and their overall tone distribution.
    """
    if len(state.articles) < 2:
        return {
            "sources_analyzed": [],
            "bias_mentions": {},
            "tone_distribution": {}
        }

    comparisons = compare_all_stories(state.articles)

    if not comparisons:
        return {
            "sources_analyzed": [],
            "bias_mentions": {},
            "tone_distribution": {},
            "message": "No multi-source stories found for bias analysis"
        }

    bias_summary = summarize_bias_findings(comparisons)

    return bias_summary


@router.get("/sources")
async def get_sources(state: AppState = Depends(get_session_state)):
    """List all distinct news sources in the current article set."""
    sources: dict[str, dict] = {}
    for article in state.articles:
        source = article.source or "Unknown"
        if source not in sources:
            sources[source] = {"count": 0, "categories": set()}
        sources[source]["count"] += 1
        sources[source]["categories"].add(article.category or "Other")

    result = [
        {
            "name": name,
            "article_count": data["count"],
            "categories": list(data["categories"]),
        }
        for name, data in sources.items()
    ]

    result.sort(key=lambda x: x["article_count"], reverse=True)

    return {"sources": result, "total": len(result)}
