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

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, MODEL_NAME

# Import our similarity module for grouping related articles
from src.similarity import calculate_combined_similarity


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
    articles: list[dict],
    similarity_threshold: float = 0.4
) -> list[list[dict]]:
    """
    Group articles that cover the same story/event.

    ALGORITHM:
    ----------
    1. Compare all article pairs
    2. If similarity > threshold, they might be same story
    3. Build clusters of related articles
    4. Return groups with 2+ articles (can compare)

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to analyze
    similarity_threshold : float
        Minimum similarity to consider "same story"
        Default 0.4 = 40% overlap needed

    RETURNS:
    --------
    list[list[dict]]
        Groups of articles covering the same story
        Each group has 2+ articles from different sources

    EXAMPLE:
    --------
    >>> groups = group_articles_by_story(articles)
    >>> print(len(groups))
    3  # Found 3 different stories covered by multiple sources
    >>> print(len(groups[0]))
    2  # First story covered by 2 different sources
    """

    n = len(articles)
    if n < 2:
        return []

    # Track which articles have been assigned to a group
    assigned = set()

    # Build groups
    groups = []

    for i in range(n):
        if i in assigned:
            continue

        # Start a new potential group with this article
        group = [articles[i]]
        assigned.add(i)

        # Find other articles that cover the same story
        for j in range(i + 1, n):
            if j in assigned:
                continue

            # Check if same story (high similarity + different source)
            similarity = calculate_combined_similarity(articles[i], articles[j])

            # Must be similar enough
            if similarity["overall"] < similarity_threshold:
                continue

            # Prefer different sources (that's the point of comparison!)
            source_i = articles[i].get("source", "").lower()
            source_j = articles[j].get("source", "").lower()

            # Add to group
            group.append(articles[j])
            assigned.add(j)

        # Only keep groups with 2+ articles (need multiple to compare)
        if len(group) >= 2:
            groups.append(group)

    return groups


def find_same_story_articles(
    articles: list[dict],
    min_group_size: int = 2
) -> list[dict]:
    """
    Find stories covered by multiple sources.

    This is a higher-level function that returns structured
    information about each story group.

    RETURNS:
    --------
    list[dict]
        Each dict contains:
        - story_title: A descriptive title for the story
        - articles: List of articles covering this story
        - sources: List of sources covering this story
        - source_count: Number of different sources
    """

    groups = group_articles_by_story(articles)

    stories = []

    for group in groups:
        if len(group) < min_group_size:
            continue

        # Use the first article's title as the story title
        # (In production, you might use LLM to generate a neutral title)
        story_title = group[0].get("title", "Unknown Story")

        # Get unique sources
        sources = list(set(art.get("source", "Unknown") for art in group))

        stories.append({
            "story_title": story_title,
            "articles": group,
            "sources": sources,
            "source_count": len(sources)
        })

    # Sort by number of sources (more sources = more interesting)
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

You MUST respond in this EXACT format:

STORY SUMMARY:
<2-3 sentence neutral summary of what happened>

COMMON FACTS:
- <fact that all sources mention>
- <another common fact>

SOURCE ANALYSIS:

SOURCE: <source name 1>
TONE: <positive/negative/neutral>
EMPHASIS: <what this source focuses on>
UNIQUE DETAILS: <facts only this source mentions, or "None">
POTENTIAL BIAS: <any apparent bias, or "None detected">

SOURCE: <source name 2>
TONE: <positive/negative/neutral>
EMPHASIS: <what this source focuses on>
UNIQUE DETAILS: <facts only this source mentions, or "None">
POTENTIAL BIAS: <any apparent bias, or "None detected">

KEY DIFFERENCES:
- <major difference 1>
- <major difference 2>

OVERALL ASSESSMENT:
<1-2 sentences about the coverage quality and diversity of perspectives>

Rules:
1. Be objective - don't favor any source
2. Focus on factual differences, not minor wording changes
3. Note if one source seems more complete than others
4. Identify loaded language if present
5. If sources mostly agree, say so"""),

    ("human", """Compare how these {source_count} sources cover the same story:

{articles_text}

Provide your analysis:""")
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

    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.2,   # Low for objective analysis
        max_tokens=2000,   # Long output for detailed comparison
        api_key=ANTHROPIC_API_KEY
    )


def create_comparison_chain():
    """Create the comparison analysis chain."""
    llm = create_comparison_llm()
    parser = StrOutputParser()
    return COMPARISON_PROMPT | llm | parser


def format_articles_for_comparison(articles: list[dict]) -> str:
    """
    Format articles for comparison analysis.

    We include full details since we're doing deep comparison.
    """
    formatted = []

    for i, article in enumerate(articles, 1):
        source = article.get("source", "Unknown Source")
        title = article.get("title", "Untitled")
        summary = article.get("summary", article.get("description", "No content"))
        sentiment = article.get("sentiment", "unknown")
        keywords = article.get("keywords", [])

        text = f"""--- SOURCE {i}: {source} ---
TITLE: {title}
CONTENT: {summary}
SENTIMENT: {sentiment}
KEYWORDS: {', '.join(keywords) if keywords else 'None'}
"""
        formatted.append(text)

    return "\n".join(formatted)


def parse_comparison_response(response: str, articles: list[dict]) -> dict:
    """
    Parse Claude's comparison analysis into structured data.

    This is complex parsing because the output has multiple sections
    and nested information about each source.

    RETURNS:
    --------
    dict with:
        - story_summary: Neutral summary of the event
        - common_facts: List of facts all sources agree on
        - source_analyses: Dict mapping source → analysis
        - key_differences: List of major differences
        - overall_assessment: Final assessment text
    """

    result = {
        "story_summary": "",
        "common_facts": [],
        "source_analyses": {},
        "key_differences": [],
        "overall_assessment": ""
    }

    # Track current parsing state
    current_section = None
    current_source = None

    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect section headers
        if line.upper().startswith("STORY SUMMARY:"):
            current_section = "summary"
            # Check if content is on same line
            content = line.split(":", 1)
            if len(content) > 1 and content[1].strip():
                result["story_summary"] = content[1].strip()
            continue

        elif line.upper().startswith("COMMON FACTS:"):
            current_section = "common_facts"
            continue

        elif line.upper().startswith("SOURCE ANALYSIS:"):
            current_section = "source_analysis"
            continue

        elif line.upper().startswith("SOURCE:"):
            current_section = "source_detail"
            source_name = line.split(":", 1)[1].strip()
            current_source = source_name
            result["source_analyses"][source_name] = {
                "tone": "",
                "emphasis": "",
                "unique_details": "",
                "potential_bias": ""
            }
            continue

        elif line.upper().startswith("KEY DIFFERENCES:"):
            current_section = "differences"
            current_source = None
            continue

        elif line.upper().startswith("OVERALL ASSESSMENT:"):
            current_section = "assessment"
            content = line.split(":", 1)
            if len(content) > 1 and content[1].strip():
                result["overall_assessment"] = content[1].strip()
            continue

        # Parse content based on current section
        if current_section == "summary" and not result["story_summary"]:
            result["story_summary"] = line

        elif current_section == "common_facts":
            if line.startswith("-") or line.startswith("•"):
                fact = line.lstrip("-•").strip()
                if fact:
                    result["common_facts"].append(fact)

        elif current_section == "source_detail" and current_source:
            if line.upper().startswith("TONE:"):
                result["source_analyses"][current_source]["tone"] = line.split(":", 1)[1].strip().lower()
            elif line.upper().startswith("EMPHASIS:"):
                result["source_analyses"][current_source]["emphasis"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("UNIQUE DETAILS:"):
                result["source_analyses"][current_source]["unique_details"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("POTENTIAL BIAS:"):
                result["source_analyses"][current_source]["potential_bias"] = line.split(":", 1)[1].strip()

        elif current_section == "differences":
            if line.startswith("-") or line.startswith("•"):
                diff = line.lstrip("-•").strip()
                if diff:
                    result["key_differences"].append(diff)

        elif current_section == "assessment" and not result["overall_assessment"]:
            result["overall_assessment"] = line

    return result


# =====================================================
# MAIN COMPARISON FUNCTION
# =====================================================

def compare_sources(articles: list[dict]) -> dict:
    """
    Compare how different sources cover the same story.

    PARAMETERS:
    -----------
    articles : list[dict]
        Articles covering the SAME story (2+ articles)

    RETURNS:
    --------
    dict with detailed comparison analysis

    EXAMPLE:
    --------
    >>> # Articles about same event from BBC, CNN, Fox
    >>> comparison = compare_sources([bbc_article, cnn_article, fox_article])
    >>> print(comparison["story_summary"])
    "World leaders met in Paris for climate summit..."
    >>> print(comparison["key_differences"])
    ["BBC emphasizes international cooperation",
     "Fox focuses on economic costs"]
    """

    if len(articles) < 2:
        return {
            "error": "Need at least 2 articles to compare",
            "story_summary": "",
            "common_facts": [],
            "source_analyses": {},
            "key_differences": [],
            "overall_assessment": ""
        }

    # Get sources for display
    sources = [art.get("source", "Unknown") for art in articles]
    print(f"\n🔍 Comparing coverage from: {', '.join(sources)}")

    chain = create_comparison_chain()

    # Format articles
    articles_text = format_articles_for_comparison(articles)

    # Call Claude
    response = chain.invoke({
        "source_count": len(articles),
        "articles_text": articles_text
    })

    # Parse response
    result = parse_comparison_response(response, articles)

    # Add metadata
    result["sources"] = sources
    result["article_count"] = len(articles)

    return result


def compare_all_stories(articles: list[dict]) -> list[dict]:
    """
    Find all multi-source stories and compare them.

    This is the main function that:
    1. Groups articles by story
    2. Compares each story across sources
    3. Returns all comparisons

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles (will find same-story groups)

    RETURNS:
    --------
    list[dict]
        Comparison results for each story group
    """

    print("\n" + "=" * 50)
    print("COMPARING SAME STORY ACROSS SOURCES")
    print("=" * 50)

    # Step 1: Find stories covered by multiple sources
    print("\n📊 Finding stories with multiple sources...")
    stories = find_same_story_articles(articles)

    if not stories:
        print("   No stories found with multiple sources.")
        print("   (Need same story from different news outlets)")
        return []

    print(f"   Found {len(stories)} stories with multiple sources")

    # Step 2: Compare each story
    comparisons = []

    for i, story in enumerate(stories, 1):
        print(f"\n[{i}/{len(stories)}] Analyzing: {story['story_title'][:40]}...")
        print(f"   Sources: {', '.join(story['sources'])}")

        try:
            comparison = compare_sources(story["articles"])
            comparison["story_title"] = story["story_title"]
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

def quick_compare(article_a: dict, article_b: dict) -> dict:
    """
    Quickly compare two specific articles.

    Use this when you already know which articles to compare,
    rather than auto-detecting same-story groups.

    PARAMETERS:
    -----------
    article_a : dict
        First article
    article_b : dict
        Second article

    RETURNS:
    --------
    dict
        Comparison analysis
    """
    return compare_sources([article_a, article_b])


# =====================================================
# DISPLAY FUNCTIONS
# =====================================================

def display_comparison(comparison: dict) -> None:
    """
    Display a source comparison in readable format.
    """

    print("\n" + "=" * 60)
    print("📰 MULTI-SOURCE COMPARISON")
    print("=" * 60)

    # Story summary
    print(f"\n📋 STORY: {comparison.get('story_title', 'Unknown')[:50]}...")
    print(f"   Sources: {', '.join(comparison.get('sources', []))}")

    print(f"\n📝 SUMMARY:")
    print(f"   {comparison.get('story_summary', 'No summary available')}")

    # Common facts
    common_facts = comparison.get("common_facts", [])
    if common_facts:
        print(f"\n✅ COMMON FACTS (all sources agree):")
        for fact in common_facts:
            print(f"   • {fact}")

    # Source analysis
    source_analyses = comparison.get("source_analyses", {})
    if source_analyses:
        print(f"\n📊 SOURCE-BY-SOURCE ANALYSIS:")
        print("-" * 40)

        for source, analysis in source_analyses.items():
            tone = analysis.get("tone", "unknown")
            tone_emoji = {
                "positive": "😊",
                "negative": "😟",
                "neutral": "😐"
            }.get(tone, "❓")

            print(f"\n   📰 {source} {tone_emoji}")
            print(f"      Tone: {tone}")
            print(f"      Focus: {analysis.get('emphasis', 'Unknown')}")

            unique = analysis.get("unique_details", "None")
            if unique and unique.lower() != "none":
                print(f"      Unique info: {unique}")

            bias = analysis.get("potential_bias", "None detected")
            if bias and bias.lower() not in ["none", "none detected"]:
                print(f"      ⚠️  Potential bias: {bias}")

    # Key differences
    differences = comparison.get("key_differences", [])
    if differences:
        print(f"\n⚡ KEY DIFFERENCES:")
        for diff in differences:
            print(f"   • {diff}")

    # Overall assessment
    assessment = comparison.get("overall_assessment", "")
    if assessment:
        print(f"\n🎯 OVERALL ASSESSMENT:")
        print(f"   {assessment}")

    print("\n" + "=" * 60)


def display_all_comparisons(comparisons: list[dict]) -> None:
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

def summarize_bias_findings(comparisons: list[dict]) -> dict:
    """
    Summarize bias findings across all comparisons.

    RETURNS:
    --------
    dict with:
        - sources_analyzed: List of all sources
        - bias_mentions: Dict of source → bias findings
        - tone_distribution: Dict of source → tone counts
    """

    sources_analyzed = set()
    bias_mentions = {}
    tone_distribution = {}

    for comparison in comparisons:
        for source, analysis in comparison.get("source_analyses", {}).items():
            sources_analyzed.add(source)

            # Track bias mentions
            bias = analysis.get("potential_bias", "")
            if bias and bias.lower() not in ["none", "none detected", ""]:
                if source not in bias_mentions:
                    bias_mentions[source] = []
                bias_mentions[source].append(bias)

            # Track tone distribution
            tone = analysis.get("tone", "unknown")
            if source not in tone_distribution:
                tone_distribution[source] = {"positive": 0, "negative": 0, "neutral": 0}
            if tone in tone_distribution[source]:
                tone_distribution[source][tone] += 1

    return {
        "sources_analyzed": list(sources_analyzed),
        "bias_mentions": bias_mentions,
        "tone_distribution": tone_distribution
    }


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING MULTI-SOURCE COMPARATOR")
    print("=" * 60)

    # Test articles: Same story from different sources
    # These simulate how different outlets might cover the same event
    test_articles = [
        {
            "title": "Tech Giants Announce Major AI Partnership",
            "summary": """Apple, Google, and Microsoft announced a historic partnership
            to develop AI safety standards. The collaboration, first of its kind,
            aims to ensure responsible AI development. Industry experts praised
            the move as a significant step forward for technology governance.
            The companies will share research and establish common guidelines.""",
            "source": "TechCrunch",
            "category": "Technology",
            "keywords": ["artificial intelligence", "partnership", "technology", "safety"],
            "people": [],
            "organizations": ["Apple", "Google", "Microsoft"],
            "sentiment": "positive"
        },
        {
            "title": "Big Tech Forms AI Alliance Amid Regulatory Pressure",
            "summary": """Facing increasing regulatory scrutiny, Apple, Google, and
            Microsoft have formed an alliance on AI development. Critics suggest
            the partnership may be an attempt to preempt government regulation.
            The announcement comes as Congress considers new AI oversight laws.
            Consumer advocates expressed concerns about industry self-regulation.""",
            "source": "The Guardian",
            "category": "Technology",
            "keywords": ["artificial intelligence", "regulation", "technology", "government"],
            "people": [],
            "organizations": ["Apple", "Google", "Microsoft", "Congress"],
            "sentiment": "neutral"
        },
        {
            "title": "Apple, Google, Microsoft Unite on AI Standards",
            "summary": """Three major technology companies announced a joint initiative
            on AI safety standards today. The partnership will focus on developing
            guidelines for responsible AI deployment. Representatives from each
            company will form a working group to draft initial recommendations.
            The initiative is expected to produce its first report within six months.""",
            "source": "Reuters",
            "category": "Technology",
            "keywords": ["artificial intelligence", "standards", "technology"],
            "people": [],
            "organizations": ["Apple", "Google", "Microsoft"],
            "sentiment": "neutral"
        },
        {
            "title": "Climate Summit Yields Historic Agreement",
            "summary": """World leaders reached a landmark climate agreement in Paris,
            committing to aggressive emission reduction targets. The deal includes
            $100 billion in funding for developing nations. Environmental groups
            celebrated the agreement as a turning point in climate action.""",
            "source": "BBC News",
            "category": "World News",
            "keywords": ["climate change", "environment", "international", "policy"],
            "people": [],
            "organizations": ["United Nations"],
            "locations": ["Paris"],
            "sentiment": "positive"
        },
        {
            "title": "Climate Deal Raises Economic Concerns",
            "summary": """The Paris climate agreement announced today has drawn mixed
            reactions. While environmental groups applauded the targets, business
            leaders warned of potential economic impacts. Some industries face
            significant compliance costs under the new framework. Critics argue
            the agreement may hurt American competitiveness.""",
            "source": "Fox Business",
            "category": "World News",
            "keywords": ["climate change", "economy", "business", "policy"],
            "people": [],
            "organizations": [],
            "locations": ["Paris"],
            "sentiment": "negative"
        },
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
