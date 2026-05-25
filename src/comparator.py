# =====================================================
# MULTI-SOURCE COMPARATOR MODULE
# =====================================================
#
# This module compares how different news sources
# cover the SAME story or event.
#
# WHY COMPARE SOURCES?
# --------------------
# Different news outlets often cover the same event but:
# - Emphasize different aspects
# - Use different language (tone, word choice)
# - Include/exclude certain facts
# - Frame the story from different perspectives
#
# Example: A new government policy announcement
# - Source A: "Historic reform will help millions"
# - Source B: "Controversial policy faces opposition"
# - Source C: "New policy details released today"
#
# Same event, three different framings!
#
# WHAT THIS MODULE DOES:
# ----------------------
# 1. Groups articles covering the same story
# 2. Compares coverage between sources
# 3. Identifies differences in:
#    - Facts included/excluded
#    - Tone and sentiment
#    - Emphasis and framing
#    - Potential bias
#
# LANGCHAIN CONCEPTS IN THIS MODULE:
# ----------------------------------
# 1. Multi-Document Comparison - Comparing several docs about same topic
# 2. Complex Structured Output - Detailed comparison results
# 3. Chain Building - Using previous modules (similarity, sentiment)
#
# =====================================================

from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS, SIMILARITY_THRESHOLDS
from src.models import Article
from src.similarity import calculate_combined_similarity


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


# =====================================================
# STEP 1: GROUP ARTICLES BY STORY
# =====================================================
#
# Before comparing, we need to find articles that cover
# the SAME story. This is different from "similar" -
# we want articles about the EXACT SAME event.
#
# Criteria for "same story":
# - Very high similarity score (> 0.5)
# - Same category
# - Published around the same time
# - Similar entities mentioned
#
# =====================================================

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


# =====================================================
# STEP 2: LLM-BASED COMPARISON
# =====================================================
#
# Once we have articles about the same story, we ask
# Claude to compare them in depth.
#
# Claude will analyze:
# - What facts each source includes/excludes
# - How each source frames the story
# - Differences in tone and language
# - Potential bias or perspective
#
# This is MULTI-DOCUMENT COMPARISON - a powerful
# LangChain pattern for analyzing related documents.
#
# =====================================================

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
    """
    Create Claude LLM for source comparison.

    WHY TEMPERATURE = 0.2?
    ----------------------
    Comparison requires careful, objective analysis.
    We don't want Claude to be creative or speculative.
    Low temperature = sticks to what's in the articles.

    WHY HIGH MAX_TOKENS?
    --------------------
    Comparison output is detailed:
    - Summary
    - Common facts
    - Analysis for each source
    - Key differences
    - Assessment

    We need room for thorough analysis.
    """
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


# =====================================================
# MAIN COMPARISON FUNCTION
# =====================================================

def compare_sources(articles: list[Article]) -> StoryComparison:
    """Run a deep comparison of how each source covered the same story."""

    if len(articles) < 2:
        return StoryComparison(error="Need at least 2 articles to compare")

    sources = [art.source or "Unknown" for art in articles]
    print(f"\n🔍 Comparing coverage from: {', '.join(sources)}")

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

    print("\n" + "=" * 50)
    print("COMPARING SAME STORY ACROSS SOURCES")
    print("=" * 50)

    print("\n📊 Finding stories with multiple sources...")
    stories = find_same_story_articles(articles)

    if not stories:
        print("   No stories found with multiple sources.")
        print("   (Need same story from different news outlets)")
        return []

    print(f"   Found {len(stories)} stories with multiple sources")

    comparisons: list[StoryComparison] = []

    for i, story in enumerate(stories, 1):
        print(f"\n[{i}/{len(stories)}] Analyzing: {story['story_title'][:40]}...")
        print(f"   Sources: {', '.join(story['sources'])}")

        try:
            comparison = compare_sources(story["articles"])
            comparison.story_title = story["story_title"]
            comparisons.append(comparison)
        except Exception as e:
            print(f"   Error comparing: {e}")

    print("\n" + "=" * 50)
    print("COMPARISON COMPLETE")
    print("=" * 50)

    return comparisons


# =====================================================
# QUICK COMPARISON (Without grouping)
# =====================================================
#
# Sometimes you already know which articles to compare.
# These functions let you compare specific articles directly.
#
# =====================================================

def quick_compare(article_a: Article, article_b: Article) -> StoryComparison:
    """Compare two specific articles directly without group detection."""
    return compare_sources([article_a, article_b])


# =====================================================
# DISPLAY FUNCTIONS
# =====================================================

def display_comparison(comparison: StoryComparison) -> None:
    """Display a source comparison in readable format."""

    print("\n" + "=" * 60)
    print("📰 MULTI-SOURCE COMPARISON")
    print("=" * 60)

    title = (comparison.story_title or "Unknown")[:50]
    print(f"\n📋 STORY: {title}...")
    print(f"   Sources: {', '.join(comparison.sources)}")

    print(f"\n📝 SUMMARY:")
    print(f"   {comparison.story_summary or 'No summary available'}")

    if comparison.common_facts:
        print(f"\n✅ COMMON FACTS (all sources agree):")
        for fact in comparison.common_facts:
            print(f"   • {fact}")

    if comparison.source_analyses:
        print(f"\n📊 SOURCE-BY-SOURCE ANALYSIS:")
        print("-" * 40)

        for source, analysis in comparison.source_analyses.items():
            tone_emoji = {
                "positive": "😊",
                "negative": "😟",
                "neutral": "😐",
            }.get(analysis.tone, "❓")

            print(f"\n   📰 {source} {tone_emoji}")
            print(f"      Tone: {analysis.tone}")
            print(f"      Focus: {analysis.emphasis or 'Unknown'}")

            if analysis.unique_details and analysis.unique_details.lower() != "none":
                print(f"      Unique info: {analysis.unique_details}")

            if analysis.potential_bias and analysis.potential_bias.lower() not in ("none", "none detected"):
                print(f"      ⚠️  Potential bias: {analysis.potential_bias}")

    if comparison.key_differences:
        print(f"\n⚡ KEY DIFFERENCES:")
        for diff in comparison.key_differences:
            print(f"   • {diff}")

    if comparison.overall_assessment:
        print(f"\n🎯 OVERALL ASSESSMENT:")
        print(f"   {comparison.overall_assessment}")

    print("\n" + "=" * 60)


def display_all_comparisons(comparisons: list[StoryComparison]) -> None:
    """Display all story comparisons."""

    if not comparisons:
        print("\nNo multi-source stories found to compare.")
        return

    print("\n" + "=" * 60)
    print(f"📊 FOUND {len(comparisons)} STORIES WITH MULTIPLE SOURCES")
    print("=" * 60)

    for i, comparison in enumerate(comparisons, 1):
        print(f"\n{'─' * 60}")
        print(f"STORY {i} of {len(comparisons)}")
        display_comparison(comparison)


# =====================================================
# BIAS DETECTION HELPERS
# =====================================================
#
# These functions help identify potential bias patterns.
#
# =====================================================

def summarize_bias_findings(comparisons: list[StoryComparison]) -> dict:
    """
    Summarize bias findings across all comparisons.

    RETURNS:
    --------
    dict with:
        - sources_analyzed: List of all sources
        - bias_mentions: Dict of source → bias findings
        - tone_distribution: Dict of source → tone counts
    """

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


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING MULTI-SOURCE COMPARATOR")
    print("=" * 60)

    test_articles = [
        Article(
            title="Tech Giants Announce Major AI Partnership",
            summary="""Apple, Google, and Microsoft announced a historic partnership
            to develop AI safety standards. The collaboration, first of its kind,
            aims to ensure responsible AI development. Industry experts praised
            the move as a significant step forward for technology governance.
            The companies will share research and establish common guidelines.""",
            source="TechCrunch",
            category="Technology",
            keywords=["artificial intelligence", "partnership", "technology", "safety"],
            organizations=["Apple", "Google", "Microsoft"],
            sentiment="positive",
            url="",
        ),
        Article(
            title="Big Tech Forms AI Alliance Amid Regulatory Pressure",
            summary="""Facing increasing regulatory scrutiny, Apple, Google, and
            Microsoft have formed an alliance on AI development. Critics suggest
            the partnership may be an attempt to preempt government regulation.
            The announcement comes as Congress considers new AI oversight laws.
            Consumer advocates expressed concerns about industry self-regulation.""",
            source="The Guardian",
            category="Technology",
            keywords=["artificial intelligence", "regulation", "technology", "government"],
            organizations=["Apple", "Google", "Microsoft", "Congress"],
            sentiment="neutral",
            url="",
        ),
        Article(
            title="Apple, Google, Microsoft Unite on AI Standards",
            summary="""Three major technology companies announced a joint initiative
            on AI safety standards today. The partnership will focus on developing
            guidelines for responsible AI deployment. Representatives from each
            company will form a working group to draft initial recommendations.
            The initiative is expected to produce its first report within six months.""",
            source="Reuters",
            category="Technology",
            keywords=["artificial intelligence", "standards", "technology"],
            organizations=["Apple", "Google", "Microsoft"],
            sentiment="neutral",
            url="",
        ),
        Article(
            title="Climate Summit Yields Historic Agreement",
            summary="""World leaders reached a landmark climate agreement in Paris,
            committing to aggressive emission reduction targets. The deal includes
            $100 billion in funding for developing nations. Environmental groups
            celebrated the agreement as a turning point in climate action.""",
            source="BBC News",
            category="World News",
            keywords=["climate change", "environment", "international", "policy"],
            organizations=["United Nations"],
            locations=["Paris"],
            sentiment="positive",
            url="",
        ),
        Article(
            title="Climate Deal Raises Economic Concerns",
            summary="""The Paris climate agreement announced today has drawn mixed
            reactions. While environmental groups applauded the targets, business
            leaders warned of potential economic impacts. Some industries face
            significant compliance costs under the new framework. Critics argue
            the agreement may hurt American competitiveness.""",
            source="Fox Business",
            category="World News",
            keywords=["climate change", "economy", "business", "policy"],
            locations=["Paris"],
            sentiment="negative",
            url="",
        ),
    ]

    # -------------------------------------------------
    # Test 1: Find same-story groups
    # -------------------------------------------------
    print("\n--- Test 1: Finding Same-Story Groups ---")
    stories = find_same_story_articles(test_articles)
    print(f"\nFound {len(stories)} stories with multiple sources:")
    for story in stories:
        print(f"  • {story['story_title'][:40]}...")
        print(f"    Sources: {', '.join(story['sources'])}")

    # -------------------------------------------------
    # Test 2: Compare all stories
    # -------------------------------------------------
    print("\n\n--- Test 2: Comparing All Stories ---")
    comparisons = compare_all_stories(test_articles)
    display_all_comparisons(comparisons)

    # -------------------------------------------------
    # Test 3: Bias summary
    # -------------------------------------------------
    if comparisons:
        print("\n\n--- Test 3: Bias Summary ---")
        bias_summary = summarize_bias_findings(comparisons)
        print(f"\nSources analyzed: {', '.join(bias_summary['sources_analyzed'])}")

        if bias_summary["bias_mentions"]:
            print("\nBias mentions by source:")
            for source, biases in bias_summary["bias_mentions"].items():
                print(f"  {source}: {biases}")
        else:
            print("\nNo significant bias detected across sources.")
