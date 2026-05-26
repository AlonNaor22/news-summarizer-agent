import logging
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article
from src.retry_utils import retried_invoke
from src.timing import timeit

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = ["positive", "negative", "neutral"]


class SentimentResult(BaseModel):
    """Structured sentiment-analysis output from Claude."""

    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the article"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="How confident the classifier is in the sentiment label"
    )
    reason: str = Field(
        description="One-sentence explanation for the chosen sentiment"
    )


SENTIMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a sentiment analysis expert for news articles.

Your job is to analyze the emotional tone of news articles and classify them as:
- POSITIVE: Good news, success stories, optimistic outlook, achievements
- NEGATIVE: Bad news, failures, disasters, criticism, concerning developments
- NEUTRAL: Factual reporting, balanced coverage, no strong emotional tone

IMPORTANT: News articles are often written to sound neutral even when covering
negative events. Focus on WHAT is being reported, not HOW it's written.

Examples:
---------
"Company reports record profits and plans expansion" -> positive
"Earthquake devastates coastal city, thousands displaced" -> negative
"Government announces new policy on immigration" -> neutral
"Scientists discover breakthrough treatment for cancer" -> positive
"Stock market plunges amid economic concerns" -> negative
"Annual report shows mixed results for tech sector" -> neutral

Rules:
1. Choose ONE sentiment only
2. Be consistent - similar articles should get similar ratings
3. When in doubt between positive/negative and neutral, lean toward neutral
4. Consider the IMPACT of the news, not just the language used
5. Provide a one-sentence reason for your choice"""),

    ("human", """Analyze the sentiment of this news article:

TITLE: {title}

CONTENT: {content}""")
])



def create_llm():
    """Create Claude LLM configured for sentiment analysis."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found!")

    settings = LLM_SETTINGS["sentiment"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


_chain = None


def create_sentiment_chain():
    """Return the (lazily-built) sentiment-analysis chain.

    Uses LangChain's structured-output binding so Claude returns a validated
    :class:`SentimentResult` instance instead of free-form text.
    """
    global _chain
    if _chain is None:
        llm = create_llm().with_structured_output(SentimentResult)
        _chain = SENTIMENT_PROMPT | llm
    return _chain



@timeit
def analyze_sentiment(article: Article) -> Article:
    """Populate ``article.sentiment``, ``.sentiment_confidence``, ``.sentiment_reason``."""

    chain = create_sentiment_chain()

    title = article.title or "Untitled"
    content = article.summary or article.description or ""

    if not content or len(content.strip()) < 30:
        article.sentiment = "neutral"
        article.sentiment_confidence = "low"
        article.sentiment_reason = "Insufficient content for analysis"
        return article

    logger.info("Analyzing sentiment: %s...", title[:40])

    result: SentimentResult = retried_invoke(chain, {
        "title": title,
        "content": content,
    })

    article.sentiment = result.sentiment
    article.sentiment_confidence = result.confidence
    article.sentiment_reason = result.reason

    indicator = {
        "positive": "[+]",
        "negative": "[-]",
        "neutral": "[=]",
    }.get(result.sentiment, "[=]")

    logger.info("  -> %s %s (%s confidence)", indicator, result.sentiment, result.confidence)

    return article



def analyze_sentiments(articles: list[Article]) -> list[Article]:
    """Run sentiment analysis on every article, defaulting to neutral on error."""

    logger.info("=" * 50)
    logger.info("ANALYZING ARTICLE SENTIMENTS")
    logger.info("=" * 50)

    analyzed: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            analyzed_article = analyze_sentiment(article)
            analyzed.append(analyzed_article)
        except Exception as e:
            logger.error("Error analyzing sentiment: %s", e)
            article.sentiment = "neutral"
            article.sentiment_confidence = "low"
            article.sentiment_reason = f"Error during analysis: {str(e)}"
            analyzed.append(article)

    logger.info("=" * 50)
    logger.info("SENTIMENT ANALYSIS COMPLETE")
    logger.info("=" * 50)

    return analyzed



def get_sentiment_summary(articles: list[Article]) -> dict:
    """Return per-sentiment counts and a percentage breakdown."""

    counts = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
    }

    for article in articles:
        sentiment = article.sentiment or "neutral"
        if sentiment in counts:
            counts[sentiment] += 1
        else:
            counts["neutral"] += 1

    total = len(articles)

    breakdown = {}
    for sentiment, count in counts.items():
        percentage = (count / total * 100) if total > 0 else 0
        breakdown[sentiment] = round(percentage, 1)

    return {
        **counts,
        "total": total,
        "breakdown": breakdown,
    }


def filter_by_sentiment(articles: list[Article], sentiment: str) -> list[Article]:
    """Return articles whose ``sentiment`` field matches ``sentiment``."""

    sentiment = sentiment.lower()
    if sentiment not in VALID_SENTIMENTS:
        logger.warning("Invalid sentiment: %s. Valid options: %s", sentiment, ", ".join(VALID_SENTIMENTS))
        return []

    return [
        article for article in articles
        if (article.sentiment or "neutral") == sentiment
    ]


def display_sentiment_summary(articles: list[Article]) -> None:
    """Log a visual summary of sentiments."""

    summary = get_sentiment_summary(articles)

    logger.info("=" * 60)
    logger.info("SENTIMENT SUMMARY")
    logger.info("=" * 60)

    # Visual bars
    for sentiment in ["positive", "negative", "neutral"]:
        count = summary[sentiment]
        percentage = summary["breakdown"][sentiment]

        # Create visual bar (each █ = 5%)
        bar_length = int(percentage / 5)
        bar = "█" * bar_length

        # Emoji
        emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}[sentiment]

        logger.info("  %s %s", emoji, sentiment.upper())
        logger.info("     %s %d articles (%s%%)", bar, count, percentage)

    logger.info("  Total articles analyzed: %d", summary["total"])
    logger.info("=" * 60)
