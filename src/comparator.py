import logging
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS, SIMILARITY_THRESHOLDS
from src.models import Article
from src.similarity import calculate_combined_similarity

logger = logging.getLogger(__name__)


class SourceAnalysis(BaseModel):
    """Per-source breakdown of a multi-source comparison."""

    source: str = Field(description="Name of the news source")
    tone: Literal["positive", "negative", "neutral"] = Field(
        description="Emotional tone of this source's coverage",
    )
    emphasis: str = Field(description="What this source focuses on")
    unique_details: str = Field(
        default="None",
        description="Facts only this source mentions, or 'None'",
    )
    potential_bias: str = Field(
        default="None detected",
        description="Apparent bias or slant, or 'None detected'",
    )


class ComparisonResult(BaseModel):
    """Raw structured comparison output from Claude.

    ``source_analyses`` is a list (Claude's natural form). Callers consume the
    enriched :class:`StoryComparison` instead, which re-keys this list by
    source name to match the frontend JSON contract.
    """

    story_summary: str = Field(
        description="Neutral 2-3 sentence summary of what happened",
    )
    common_facts: list[str] = Field(
        default_factory=list,
        description="Facts that every source agrees on",
    )
    source_analyses: list[SourceAnalysis] = Field(
        default_factory=list,
        description="Per-source tone/emphasis/unique-details/bias breakdown",
    )
    key_differences: list[str] = Field(
        default_factory=list,
        description="Major differences between the sources",
    )
    overall_assessment: str = Field(
        default="",
        description="1-2 sentences on coverage quality and diversity of perspectives",
    )


class StoryComparison(BaseModel):
    """A :class:`ComparisonResult` enriched with story-level metadata.

    Returned by :func:`compare_sources`. ``source_analyses`` is keyed by
    source name so the FastAPI JSON response and frontend ``Compare.jsx``
    can keep iterating over ``Object.entries(...)``.
    """

    story_summary: str = ""
    common_facts: list[str] = Field(default_factory=list)
    source_analyses: dict[str, SourceAnalysis] = Field(default_factory=dict)
    key_differences: list[str] = Field(default_factory=list)
    overall_assessment: str = ""
    sources: list[str] = Field(default_factory=list)
    article_count: int = 0
    story_title: str | None = None
    error: str | None = None


def group_articles_by_story(
    articles: list[Article],
    similarity_threshold: float = SIMILARITY_THRESHOLDS["same_story"],
) -> list[list[Article]]:
    """Cluster articles into groups (size ≥ 2) covering the same story."""

    n = len(articles)
    if n < 2:
        return []

    assigned: set[int] = set()
    groups: list[list[Article]] = []

    for i in range(n):
        if i in assigned:
            continue

        group: list[Article] = [articles[i]]
        assigned.add(i)

        for j in range(i + 1, n):
            if j in assigned:
                continue

            similarity = calculate_combined_similarity(articles[i], articles[j])

            if similarity["overall"] < similarity_threshold:
                continue

            group.append(articles[j])
            assigned.add(j)

        if len(group) >= 2:
            groups.append(group)

    return groups


def find_same_story_articles(
    articles: list[Article],
    min_group_size: int = 2,
) -> list[dict]:
    """Return structured groups of multi-source coverage of the same story."""

    groups = group_articles_by_story(articles)

    stories: list[dict] = []

    for group in groups:
        if len(group) < min_group_size:
            continue

        story_title = group[0].title or "Unknown Story"
        sources = list({art.source or "Unknown" for art in group})

        stories.append({
            "story_title": story_title,
            "articles": group,
            "sources": sources,
            "source_count": len(sources),
        })

    stories.sort(key=lambda x: x["source_count"], reverse=True)

    return stories


COMPARISON_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert media analyst who compares how different news sources cover the same story.

Your job is to analyze multiple articles about the SAME event and identify:
1. COMMON FACTS - What all sources agree on
2. UNIQUE DETAILS - Facts only mentioned by one source
3. FRAMING DIFFERENCES - How each source presents the story
4. TONE ANALYSIS - The emotional tone of each source
5. POTENTIAL BIAS - Any apparent bias or slant

Provide one SourceAnalysis entry per source (using the source names shown in the input).
Use "None" / "None detected" for unique_details / potential_bias when nothing notable.

Rules:
1. Be objective - don't favor any source
2. Focus on factual differences, not minor wording changes
3. Note if one source seems more complete than others
4. Identify loaded language if present
5. If sources mostly agree, say so"""),

    ("human", """Compare how these {source_count} sources cover the same story:

{articles_text}""")
])


def create_comparison_llm():
    """Create Claude LLM for source comparison."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found!")

    settings = LLM_SETTINGS["comparison"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


_chain = None


def create_comparison_chain():
    """Return the (lazily-built) source-comparison chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`ComparisonResult` instead of free-form text.
    """
    global _chain
    if _chain is None:
        llm = create_comparison_llm().with_structured_output(ComparisonResult)
        _chain = COMPARISON_PROMPT | llm
    return _chain


def format_articles_for_comparison(articles: list[Article]) -> str:
    """Render every article for the source-comparison prompt."""
    formatted = []

    for i, article in enumerate(articles, 1):
        source = article.source or "Unknown Source"
        title = article.title or "Untitled"
        summary = article.summary or article.description or "No content"
        sentiment = article.sentiment or "unknown"
        keywords = article.keywords

        text = f"""--- SOURCE {i}: {source} ---
TITLE: {title}
CONTENT: {summary}
SENTIMENT: {sentiment}
KEYWORDS: {', '.join(keywords) if keywords else 'None'}
"""
        formatted.append(text)

    return "\n".join(formatted)


def compare_sources(articles: list[Article]) -> StoryComparison:
    """Run a deep comparison of how each source covered the same story."""

    if len(articles) < 2:
        return StoryComparison(error="Need at least 2 articles to compare")

    sources = [art.source or "Unknown" for art in articles]
    logger.info("Comparing coverage from: %s", ", ".join(sources))

    chain = create_comparison_chain()
    articles_text = format_articles_for_comparison(articles)

    structured: ComparisonResult = chain.invoke({
        "source_count": len(articles),
        "articles_text": articles_text,
    })

    return StoryComparison(
        story_summary=structured.story_summary,
        common_facts=structured.common_facts,
        # Re-key list[SourceAnalysis] -> dict keyed by source name for the
        # frontend's Object.entries(source_analyses) call.
        source_analyses={entry.source: entry for entry in structured.source_analyses},
        key_differences=structured.key_differences,
        overall_assessment=structured.overall_assessment,
        sources=sources,
        article_count=len(articles),
    )


def compare_all_stories(articles: list[Article]) -> list[StoryComparison]:
    """Find all multi-source stories and run :func:`compare_sources` on each."""

    logger.info("=" * 50)
    logger.info("COMPARING SAME STORY ACROSS SOURCES")
    logger.info("=" * 50)

    logger.info("Finding stories with multiple sources...")
    stories = find_same_story_articles(articles)

    if not stories:
        logger.info("No stories found with multiple sources.")
        return []

    logger.info("Found %d stories with multiple sources", len(stories))

    comparisons: list[StoryComparison] = []

    for i, story in enumerate(stories, 1):
        logger.info("[%d/%d] Analyzing: %s...", i, len(stories), story["story_title"][:40])
        logger.info("  Sources: %s", ", ".join(story["sources"]))

        try:
            comparison = compare_sources(story["articles"])
            comparison.story_title = story["story_title"]
            comparisons.append(comparison)
        except Exception as e:
            logger.error("Error comparing story: %s", e)

    logger.info("=" * 50)
    logger.info("COMPARISON COMPLETE")
    logger.info("=" * 50)

    return comparisons


def quick_compare(article_a: Article, article_b: Article) -> StoryComparison:
    """Compare two specific articles directly without group detection."""
    return compare_sources([article_a, article_b])


def display_comparison(comparison: StoryComparison) -> None:
    """Log a source comparison in readable format."""

    logger.info("=" * 60)
    logger.info("MULTI-SOURCE COMPARISON")
    logger.info("=" * 60)

    title = (comparison.story_title or "Unknown")[:50]
    logger.info("STORY: %s...", title)
    logger.info("  Sources: %s", ", ".join(comparison.sources))

    logger.info("SUMMARY:")
    logger.info("  %s", comparison.story_summary or "No summary available")

    if comparison.common_facts:
        logger.info("COMMON FACTS (all sources agree):")
        for fact in comparison.common_facts:
            logger.info("  • %s", fact)

    if comparison.source_analyses:
        logger.info("SOURCE-BY-SOURCE ANALYSIS:")
        logger.info("-" * 40)

        for source, analysis in comparison.source_analyses.items():
            tone_emoji = {
                "positive": "😊",
                "negative": "😟",
                "neutral": "😐",
            }.get(analysis.tone, "❓")

            logger.info("  %s %s", source, tone_emoji)
            logger.info("     Tone: %s", analysis.tone)
            logger.info("     Focus: %s", analysis.emphasis or "Unknown")

            if analysis.unique_details and analysis.unique_details.lower() != "none":
                logger.info("     Unique info: %s", analysis.unique_details)

            if analysis.potential_bias and analysis.potential_bias.lower() not in ("none", "none detected"):
                logger.info("     Potential bias: %s", analysis.potential_bias)

    if comparison.key_differences:
        logger.info("KEY DIFFERENCES:")
        for diff in comparison.key_differences:
            logger.info("  • %s", diff)

    if comparison.overall_assessment:
        logger.info("OVERALL ASSESSMENT:")
        logger.info("  %s", comparison.overall_assessment)

    logger.info("=" * 60)


def display_all_comparisons(comparisons: list[StoryComparison]) -> None:
    """Log all story comparisons."""

    if not comparisons:
        logger.info("No multi-source stories found to compare.")
        return

    logger.info("=" * 60)
    logger.info("FOUND %d STORIES WITH MULTIPLE SOURCES", len(comparisons))
    logger.info("=" * 60)

    for i, comparison in enumerate(comparisons, 1):
        logger.info("-" * 60)
        logger.info("STORY %d of %d", i, len(comparisons))
        display_comparison(comparison)


def summarize_bias_findings(comparisons: list[StoryComparison]) -> dict:
    """Summarize bias findings across all comparisons."""

    sources_analyzed: set[str] = set()
    bias_mentions: dict[str, list[str]] = {}
    tone_distribution: dict[str, dict[str, int]] = {}

    for comparison in comparisons:
        for source, analysis in comparison.source_analyses.items():
            sources_analyzed.add(source)

            bias = analysis.potential_bias
            if bias and bias.lower() not in ("none", "none detected", ""):
                bias_mentions.setdefault(source, []).append(bias)

            tone_distribution.setdefault(
                source, {"positive": 0, "negative": 0, "neutral": 0}
            )
            if analysis.tone in tone_distribution[source]:
                tone_distribution[source][analysis.tone] += 1

    return {
        "sources_analyzed": list(sources_analyzed),
        "bias_mentions": bias_mentions,
        "tone_distribution": tone_distribution,
    }
