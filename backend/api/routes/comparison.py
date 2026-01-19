"""
Comparison API Routes

Endpoints for comparing how different sources cover the same story.
"""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

from src.comparator import (
    find_same_story_articles,
    compare_sources,
    compare_all_stories,
    summarize_bias_findings
)

from api.dependencies import get_app_state

router = APIRouter()


class CompareRequest(BaseModel):
    """Request model for comparing specific articles."""
    article_ids: List[int]


@router.get("/comparison/stories")
async def get_same_story_groups():
    """
    Find stories that are covered by multiple sources.

    Returns groups of articles that cover the same event/story,
    which can then be compared for coverage differences.
    """
    state = get_app_state()

    if len(state.articles) < 2:
        return {"stories": [], "total": 0}

    stories = find_same_story_articles(state.articles)

    result = []
    for story in stories:
        result.append({
            "story_title": story["story_title"],
            "sources": story["sources"],
            "source_count": story["source_count"],
            "article_ids": [
                state.articles.index(art) if art in state.articles else -1
                for art in story["articles"]
            ]
        })

    return {"stories": result, "total": len(result)}


@router.get("/comparison")
async def compare_all():
    """
    Compare all stories that have multiple source coverage.

    This performs a full analysis comparing how different news sources
    cover the same events, identifying:
    - Common facts
    - Different emphases
    - Potential bias
    """
    state = get_app_state()

    if len(state.articles) < 2:
        return {"comparisons": [], "total": 0}

    comparisons = compare_all_stories(state.articles)

    return {
        "comparisons": comparisons,
        "total": len(comparisons)
    }


@router.post("/comparison/specific")
async def compare_specific_articles(request: CompareRequest):
    """
    Compare specific articles by their IDs.

    Use this when you want to manually select which articles to compare.
    """
    state = get_app_state()

    # Validate article IDs
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
async def get_bias_analysis():
    """
    Get bias analysis summary across all comparisons.

    Shows which sources have been flagged for potential bias
    and their overall tone distribution.
    """
    state = get_app_state()

    if len(state.articles) < 2:
        return {
            "sources_analyzed": [],
            "bias_mentions": {},
            "tone_distribution": {}
        }

    # First get all comparisons
    comparisons = compare_all_stories(state.articles)

    if not comparisons:
        return {
            "sources_analyzed": [],
            "bias_mentions": {},
            "tone_distribution": {},
            "message": "No multi-source stories found for bias analysis"
        }

    # Summarize bias findings
    bias_summary = summarize_bias_findings(comparisons)

    return bias_summary


@router.get("/sources")
async def get_sources():
    """
    Get list of all news sources in the current articles.
    """
    state = get_app_state()

    sources = {}
    for article in state.articles:
        source = article.get("source", "Unknown")
        if source not in sources:
            sources[source] = {"count": 0, "categories": set()}
        sources[source]["count"] += 1
        sources[source]["categories"].add(article.get("category", "Other"))

    result = [
        {
            "name": name,
            "article_count": data["count"],
            "categories": list(data["categories"])
        }
        for name, data in sources.items()
    ]

    # Sort by article count
    result.sort(key=lambda x: x["article_count"], reverse=True)

    return {"sources": result, "total": len(result)}
