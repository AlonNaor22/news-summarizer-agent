# =====================================================
# TRENDING TOPICS DETECTION MODULE
# =====================================================
#
# This module identifies trending topics across all articles.
#
# WHAT IS TREND DETECTION?
# ------------------------
# Trend detection finds patterns across multiple articles:
# - Which topics appear most frequently?
# - What themes connect different stories?
# - Are there emerging topics gaining attention?
#
# TWO APPROACHES TO TREND DETECTION:
# ----------------------------------
#
# APPROACH 1: Statistical (Simple)
# - Count keyword frequencies from tagger.py
# - Most frequent = trending
# - Fast, no API calls needed
# - Limited: Can't understand context
#
# APPROACH 2: LLM-Based (Smart)
# - Send all articles to Claude
# - Ask it to identify themes and trends
# - Slower, costs API calls
# - Powerful: Understands context, groups related topics
#
# We implement BOTH approaches in this module!
#
# LANGCHAIN CONCEPTS IN THIS MODULE:
# ----------------------------------
# 1. Multi-Document Reasoning - Analyzing many docs together
# 2. Large Context Windows - Claude can process many articles
# 3. Structured Output - Getting organized trend data back
#
# =====================================================

import logging
from typing import Literal
from collections import Counter

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article

logger = logging.getLogger(__name__)


class Trend(BaseModel):
    """A single trend identified across multiple articles."""

    name: str = Field(description="Short name for the trend")
    strength: Literal["high", "medium", "low"] = Field(
        description="high: 4+ articles, medium: 2-3 articles, low: 1 significant article"
    )
    description: str = Field(description="One-sentence explanation of the trend")
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords associated with this trend (lowercase)",
    )
    article_count: int = Field(
        default=0,
        description="Number of articles related to this trend",
    )

    @field_validator("keywords", mode="after")
    @classmethod
    def _lowercase_keywords(cls, value: list[str]) -> list[str]:
        return [kw.strip().lower() for kw in value if kw and kw.strip()]


class TrendList(BaseModel):
    """Wrapper so Claude returns a list of trends as a structured object."""

    trends: list[Trend] = Field(description="3-5 major trends across the articles")


# =====================================================
# APPROACH 1: STATISTICAL TRENDING
# =====================================================
#
# This approach uses data we already have from tagger.py.
# It's fast and free (no API calls), but less intelligent.
#
# HOW IT WORKS:
# 1. Collect all keywords from all articles
# 2. Count how many times each appears
# 3. Most frequent = trending
#
# LIMITATIONS:
# - "AI" and "artificial intelligence" counted separately
# - Can't understand that "tech stocks" and "market rally"
#   might be part of the same story
# - No context about WHY something is trending
#
# =====================================================

def get_trending_keywords(articles: list[Article], top_n: int = 10) -> list[dict]:
    """Return the top ``top_n`` keywords sorted by frequency across articles."""

    keyword_counter: Counter = Counter()
    keyword_to_articles: dict[str, list[str]] = {}

    for article in articles:
        keywords = article.keywords
        title = article.title or "Untitled"

        for keyword in keywords:
            keyword = keyword.lower().strip()

            keyword_counter[keyword] += 1

            if keyword not in keyword_to_articles:
                keyword_to_articles[keyword] = []
            keyword_to_articles[keyword].append(title)

    top_keywords = keyword_counter.most_common(top_n)

    total_articles = len(articles)
    trends: list[dict] = []

    for keyword, count in top_keywords:
        percentage = (count / total_articles * 100) if total_articles > 0 else 0

        trends.append({
            "keyword": keyword,
            "count": count,
            "percentage": round(percentage, 1),
            "articles": keyword_to_articles.get(keyword, []),
        })

    return trends


def get_trending_entities(articles: list[Article], top_n: int = 5) -> dict:
    """Return the top ``top_n`` people/orgs/locations across all articles."""

    people_counter: Counter = Counter()
    org_counter: Counter = Counter()
    location_counter: Counter = Counter()

    for article in articles:
        for person in article.people:
            people_counter[person] += 1
        for org in article.organizations:
            org_counter[org] += 1
        for location in article.locations:
            location_counter[location] += 1

    return {
        "people": people_counter.most_common(top_n),
        "organizations": org_counter.most_common(top_n),
        "locations": location_counter.most_common(top_n),
    }


# =====================================================
# APPROACH 2: LLM-BASED TRENDING
# =====================================================
#
# This approach uses Claude to analyze ALL articles together
# and identify trends with context and understanding.
#
# KEY LANGCHAIN CONCEPT: Multi-Document Reasoning
# -----------------------------------------------
# Instead of analyzing one article at a time, we send
# ALL articles to Claude in a single request.
#
# Claude's large context window (200K tokens) means it
# can "see" all articles at once and find patterns that
# span multiple stories.
#
# Example: Claude might notice that 5 different articles
# about "AI", "tech stocks", and "semiconductor shortage"
# are all part of a broader "AI industry boom" trend.
#
# =====================================================

TREND_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a news analyst expert at identifying trends and themes.

Your job is to analyze multiple news articles and identify:
1. MAJOR TRENDS - Topics that appear across multiple articles
2. EMERGING THEMES - Connections between seemingly different stories
3. KEY NARRATIVES - The bigger stories behind individual articles

Rules:
1. Identify 3-5 major trends
2. Group related stories together (e.g., different AI articles = one AI trend)
3. Strength is based on how many articles relate to the trend:
   - high: 4+ articles
   - medium: 2-3 articles
   - low: 1 article but significant topic
4. Look for non-obvious connections between stories
5. Consider both explicit topics and implicit themes
6. Provide 3-5 lowercase keywords per trend"""),

    ("human", """Analyze these {article_count} news articles and identify the major trends:

{articles_text}""")
])


def create_trend_llm():
    """
    Create Claude LLM for trend analysis.

    WHY HIGHER MAX_TOKENS?
    ----------------------
    Trend analysis produces longer output than sentiment.
    We need room for multiple trends with descriptions.

    WHY MODERATE TEMPERATURE (0.3)?
    -------------------------------
    We want some creativity in finding non-obvious trends,
    but not so much that it invents connections that don't exist.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found!")

    settings = LLM_SETTINGS["trending"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


_chain = None


def create_trend_chain():
    """Return the (lazily-built) trend-analysis chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`TrendList` instance instead of free-form text.
    """
    global _chain
    if _chain is None:
        llm = create_trend_llm().with_structured_output(TrendList)
        _chain = TREND_ANALYSIS_PROMPT | llm
    return _chain


def format_articles_for_trend_analysis(articles: list[Article]) -> str:
    """Render every article into a single text block for the LLM prompt."""

    formatted_parts = []

    for i, article in enumerate(articles, 1):
        title = article.title or "Untitled"
        category = article.category or "Uncategorized"
        summary = article.summary or article.description or "No summary"
        keywords = article.keywords

        article_text = f"""--- ARTICLE {i} ---
TITLE: {title}
CATEGORY: {category}
SUMMARY: {summary}
KEYWORDS: {', '.join(keywords) if keywords else 'None'}
"""
        formatted_parts.append(article_text)

    return "\n".join(formatted_parts)


# =====================================================
# MAIN TREND DETECTION FUNCTION
# =====================================================

def detect_trends(articles: list[Article], use_llm: bool = True) -> dict:
    """
    Detect trending topics across all articles.

    This function combines BOTH approaches:
    1. Statistical: Fast keyword counting
    2. LLM-based: Smart theme detection

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to analyze (should have keywords from tagger)
    use_llm : bool
        Whether to use Claude for smart analysis (default: True)
        Set to False for faster, free analysis

    RETURNS:
    --------
    dict with keys:
        - keyword_trends: Top keywords by frequency
        - entity_trends: Top people/orgs/locations
        - llm_trends: Smart trends from Claude (if use_llm=True)

    EXAMPLE:
    --------
    >>> trends = detect_trends(articles)
    >>> print(trends["llm_trends"][0]["name"])
    "AI Industry Growth"
    >>> print(trends["keyword_trends"][0]["keyword"])
    "artificial intelligence"
    """

    logger.info("=" * 50)
    logger.info("DETECTING TRENDING TOPICS")
    logger.info("=" * 50)

    result = {
        "keyword_trends": [],
        "entity_trends": {},
        "llm_trends": []
    }

    # -------------------------------------------------
    # STEP 1: Statistical Analysis (Fast, Free)
    # -------------------------------------------------
    logger.info("Analyzing keyword frequencies...")
    result["keyword_trends"] = get_trending_keywords(articles, top_n=10)
    result["entity_trends"] = get_trending_entities(articles, top_n=5)

    logger.info("Found %d trending keywords", len(result["keyword_trends"]))

    # -------------------------------------------------
    # STEP 2: LLM Analysis (Smart, Costs API)
    # -------------------------------------------------
    if use_llm and len(articles) >= 2:
        logger.info("Asking Claude to identify themes...")

        try:
            chain = create_trend_chain()

            # Format all articles for Claude
            articles_text = format_articles_for_trend_analysis(articles)

            # Call the chain — returns a validated TrendList
            trend_list: TrendList = chain.invoke({
                "article_count": len(articles),
                "articles_text": articles_text
            })

            # Convert to the legacy dict shape that display_trends / callers expect
            result["llm_trends"] = [trend.model_dump() for trend in trend_list.trends]

            logger.info("Identified %d major trends", len(result["llm_trends"]))

        except Exception as e:
            logger.error("Error in LLM analysis: %s", e)
            result["llm_trends"] = []

    elif not use_llm:
        logger.info("Skipping LLM analysis (use_llm=False)")

    elif len(articles) < 2:
        logger.info("Skipping LLM analysis (need at least 2 articles)")

    logger.info("=" * 50)
    logger.info("TREND DETECTION COMPLETE")
    logger.info("=" * 50)

    return result


# =====================================================
# DISPLAY FUNCTIONS
# =====================================================

def display_trends(trends: dict) -> None:
    """Log trending topics in a readable format."""

    logger.info("=" * 60)
    logger.info("📈 TRENDING TOPICS")
    logger.info("=" * 60)

    # -------------------------------------------------
    # Display LLM-detected trends (most insightful)
    # -------------------------------------------------
    if trends.get("llm_trends"):
        logger.info("🔥 MAJOR TRENDS (AI Analysis)")
        logger.info("-" * 40)

        for i, trend in enumerate(trends["llm_trends"], 1):
            # Strength indicator
            strength_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(trend["strength"], "⚪")

            logger.info("  %d. %s %s", i, trend["name"], strength_emoji)
            logger.info("     Strength: %s (%d articles)", trend["strength"], trend["article_count"])
            logger.info("     %s", trend["description"])

            if trend["keywords"]:
                logger.info("     Keywords: %s", ", ".join(trend["keywords"][:5]))

    # -------------------------------------------------
    # Display keyword frequency trends
    # -------------------------------------------------
    logger.info("🏷️  TOP KEYWORDS")
    logger.info("-" * 40)

    for i, kw_data in enumerate(trends.get("keyword_trends", [])[:7], 1):
        keyword = kw_data["keyword"]
        count = kw_data["count"]
        percentage = kw_data["percentage"]

        # Visual bar
        bar = "█" * min(count, 10)

        logger.info("  %d. %s", i, keyword)
        logger.info("     %s %d articles (%s%%)", bar, count, percentage)

    # -------------------------------------------------
    # Display entity trends
    # -------------------------------------------------
    entity_trends = trends.get("entity_trends", {})

    if entity_trends.get("people"):
        logger.info("👤 TRENDING PEOPLE")
        logger.info("-" * 40)
        for name, count in entity_trends["people"]:
            logger.info("  • %s (%d mentions)", name, count)

    if entity_trends.get("organizations"):
        logger.info("🏢 TRENDING ORGANIZATIONS")
        logger.info("-" * 40)
        for name, count in entity_trends["organizations"]:
            logger.info("  • %s (%d mentions)", name, count)

    if entity_trends.get("locations"):
        logger.info("📍 TRENDING LOCATIONS")
        logger.info("-" * 40)
        for name, count in entity_trends["locations"]:
            logger.info("  • %s (%d mentions)", name, count)

    logger.info("=" * 60)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING TREND DETECTION")
    print("=" * 60)

    test_articles = [
        Article(
            title="Apple Unveils New AI-Powered iPhone Features",
            summary="Apple announced revolutionary AI capabilities in its latest iPhone, including real-time translation and smart photo editing.",
            category="Technology",
            keywords=["artificial intelligence", "smartphones", "apple"],
            people=["Tim Cook"],
            organizations=["Apple"],
            locations=["California"],
            source="Test",
            url="",
        ),
        Article(
            title="Google's AI Chatbot Gains Million Users",
            summary="Google's new AI assistant has reached one million users within its first week, competing directly with ChatGPT.",
            category="Technology",
            keywords=["artificial intelligence", "chatbot", "google"],
            people=["Sundar Pichai"],
            organizations=["Google", "OpenAI"],
            locations=["Silicon Valley"],
            source="Test",
            url="",
        ),
        Article(
            title="Tech Stocks Rally on AI Optimism",
            summary="Technology stocks surged today as investors bet on artificial intelligence growth. NVIDIA and Microsoft led gains.",
            category="Business",
            keywords=["artificial intelligence", "stocks", "investment"],
            organizations=["NVIDIA", "Microsoft"],
            locations=["Wall Street"],
            source="Test",
            url="",
        ),
        Article(
            title="Climate Summit Reaches Historic Agreement",
            summary="World leaders agreed to ambitious emission targets at the Paris climate summit, marking a turning point in environmental policy.",
            category="World News",
            keywords=["climate change", "environment", "policy"],
            people=["Emmanuel Macron"],
            organizations=["United Nations"],
            locations=["Paris"],
            source="Test",
            url="",
        ),
        Article(
            title="Renewable Energy Investment Hits Record High",
            summary="Global investment in renewable energy reached $500 billion this year, driven by government incentives and falling costs.",
            category="Business",
            keywords=["climate change", "renewable energy", "investment"],
            source="Test",
            url="",
        ),
    ]

    print(f"\nAnalyzing {len(test_articles)} test articles...")

    # Detect trends
    trends = detect_trends(test_articles, use_llm=True)

    # Display results
    display_trends(trends)

    # Show raw LLM trends for debugging
    print("\n--- Raw LLM Trends ---")
    for trend in trends.get("llm_trends", []):
        print(f"\n{trend}")
