"""Similarity API routes — finding similar and related articles."""

from fastapi import APIRouter, HTTPException, Query

from src.similarity import (
    find_similar_articles,
    analyze_article_relationships,
    calculate_combined_similarity
)

from api.dependencies import get_app_state

router = APIRouter()


@router.get("/articles/{article_id}/similar")
async def get_similar_articles(
    article_id: int,
    threshold: float = Query(0.2, description="Minimum similarity score (0-1)"),
    max_results: int = Query(5, description="Maximum similar articles to return"),
    use_llm: bool = Query(False, description="Use AI for relationship analysis")
):
    """
    Find articles similar to a specific article.

    - **article_id**: ID of the target article
    - **threshold**: Minimum similarity score (0.0 to 1.0)
    - **max_results**: Maximum number of similar articles
    - **use_llm**: If true, uses AI for deeper relationship analysis
    """
    state = get_app_state()

    if article_id < 0 or article_id >= len(state.articles):
        raise HTTPException(status_code=404, detail="Article not found")

    target = state.articles[article_id]
    similar = find_similar_articles(
        target,
        state.articles,
        threshold=threshold,
        max_results=max_results,
    )

    similar_articles = []
    for art in similar:
        # find_similar_articles returns model_copy()'d Articles — they're not
        # identical to the originals, so look up by title for the ID.
        try:
            art_id = next(
                i for i, original in enumerate(state.articles)
                if original.title == art.title
            )
        except StopIteration:
            art_id = -1

        similar_articles.append({
            "id": art_id,
            "title": art.title,
            "category": art.category,
            "source": art.source,
            "similarity": art.similarity or {},
        })

    return {
        "target": {
            "id": article_id,
            "title": target.title,
            "category": target.category,
        },
        "similar_articles": similar_articles,
        "total": len(similar),
    }


@router.get("/relationships")
async def get_all_relationships(
    use_llm: bool = Query(True, description="Use AI for relationship analysis")
):
    """
    Analyze relationships between all articles.

    Returns both statistical (keyword-based) and AI-detected relationships.
    """
    state = get_app_state()

    if not state.articles:
        return {
            "statistical_pairs": [],
            "llm_pairs": [],
            "article_connections": {},
            "total_articles": 0
        }

    analysis = analyze_article_relationships(state.articles, use_llm=use_llm)

    # Store in app state
    state.relationships = analysis

    return {
        **analysis,
        "total_articles": len(state.articles)
    }


@router.get("/relationships/pairs")
async def get_related_pairs(
    threshold: float = Query(0.3, description="Minimum similarity for pairs"),
    limit: int = Query(20, description="Maximum pairs to return")
):
    """
    Get pairs of related articles based on keyword similarity.
    """
    state = get_app_state()
    articles = state.articles

    if len(articles) < 2:
        return {"pairs": [], "total": 0}

    pairs = []

    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            similarity = calculate_combined_similarity(articles[i], articles[j])

            if similarity["overall"] >= threshold:
                pairs.append({
                    "article_a": {
                        "id": i,
                        "title": articles[i].title,
                    },
                    "article_b": {
                        "id": j,
                        "title": articles[j].title,
                    },
                    "similarity": similarity,
                })

    pairs.sort(key=lambda x: x["similarity"]["overall"], reverse=True)

    return {
        "pairs": pairs[:limit],
        "total": len(pairs),
    }


@router.get("/compare/{article_id_a}/{article_id_b}")
async def compare_two_articles(article_id_a: int, article_id_b: int):
    """
    Compare two specific articles and get their similarity.
    """
    state = get_app_state()

    if article_id_a < 0 or article_id_a >= len(state.articles):
        raise HTTPException(status_code=404, detail=f"Article {article_id_a} not found")

    if article_id_b < 0 or article_id_b >= len(state.articles):
        raise HTTPException(status_code=404, detail=f"Article {article_id_b} not found")

    article_a = state.articles[article_id_a]
    article_b = state.articles[article_id_b]

    similarity = calculate_combined_similarity(article_a, article_b)

    return {
        "article_a": {
            "id": article_id_a,
            "title": article_a.title,
            "category": article_a.category,
        },
        "article_b": {
            "id": article_id_b,
            "title": article_b.title,
            "category": article_b.category,
        },
        "similarity": similarity,
    }
