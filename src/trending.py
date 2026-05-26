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
    """Create Claude LLM for trend analysis."""
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



def detect_trends(articles: list[Article], use_llm: bool = True) -> dict:
    """Detect trending topics using statistical keyword counts and (optionally) LLM analysis."""

    logger.info("=" * 50)
    logger.info("DETECTING TRENDING TOPICS")
    logger.info("=" * 50)

    result = {
        "keyword_trends": [],
        "entity_trends": {},
        "llm_trends": []
    }

    logger.info("Analyzing keyword frequencies...")
    result["keyword_trends"] = get_trending_keywords(articles, top_n=10)
    result["entity_trends"] = get_trending_entities(articles, top_n=5)

    logger.info("Found %d trending keywords", len(result["keyword_trends"]))

    if use_llm and len(articles) >= 2:
        logger.info("Asking Claude to identify themes...")

        try:
            chain = create_trend_chain()
            articles_text = format_articles_for_trend_analysis(articles)
            trend_list: TrendList = chain.invoke({
                "article_count": len(articles),
                "articles_text": articles_text
            })
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



def display_trends(trends: dict) -> None:
    """Log trending topics in a readable format."""

    logger.info("=" * 60)
    logger.info("📈 TRENDING TOPICS")
    logger.info("=" * 60)

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

