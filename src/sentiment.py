# =====================================================
# SENTIMENT ANALYSIS MODULE
# =====================================================
#
# This module analyzes the emotional tone of news articles.
#
# WHAT IS SENTIMENT ANALYSIS?
# ---------------------------
# Sentiment analysis determines whether text expresses:
# - POSITIVE feelings (good news, optimism, success)
# - NEGATIVE feelings (bad news, concern, criticism)
# - NEUTRAL tone (factual, balanced, objective)
#
# WHY IS THIS USEFUL FOR NEWS?
# ----------------------------
# 1. Understand the tone of coverage
# 2. Compare how different sources frame the same story
# 3. Filter news by mood (e.g., "show me positive news")
# 4. Detect bias in reporting
#
# LANGCHAIN CONCEPTS IN THIS MODULE:
# ----------------------------------
# 1. Structured Output - Getting specific format from LLM
# 2. Few-Shot Prompting - Giving examples in the prompt
# 3. Output Parsing - Converting LLM response to Python data
#
# =====================================================

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article


# =====================================================
# SENTIMENT VALUES
# =====================================================
#
# We define the possible sentiment values as a list.
# This makes it easy to validate Claude's response.
#
# In more advanced setups, you might use Python's Enum:
#   from enum import Enum
#   class Sentiment(Enum):
#       POSITIVE = "positive"
#       NEGATIVE = "negative"
#       NEUTRAL = "neutral"
#
# But for simplicity, we use a list here.
#
# =====================================================

VALID_SENTIMENTS = ["positive", "negative", "neutral"]


# =====================================================
# THE SENTIMENT ANALYSIS PROMPT
# =====================================================
#
# KEY TECHNIQUE: Few-Shot Prompting
# ---------------------------------
# We give Claude EXAMPLES of how to classify sentiment.
# This helps it understand what we consider positive,
# negative, or neutral in a NEWS context.
#
# Why examples matter:
# - "Stock market crashes" is clearly negative
# - "Scientists discover cure" is clearly positive
# - "Government announces policy" could be neutral
#
# Without examples, Claude might interpret sentiment
# differently than we intend.
#
# =====================================================

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
"Company reports record profits and plans expansion" → positive
"Earthquake devastates coastal city, thousands displaced" → negative
"Government announces new policy on immigration" → neutral
"Scientists discover breakthrough treatment for cancer" → positive
"Stock market plunges amid economic concerns" → negative
"Annual report shows mixed results for tech sector" → neutral

You MUST respond with EXACTLY this format:
SENTIMENT: <positive/negative/neutral>
CONFIDENCE: <high/medium/low>
REASON: <one sentence explaining why>

Rules:
1. Choose ONE sentiment only
2. Be consistent - similar articles should get similar ratings
3. When in doubt between positive/negative and neutral, lean toward neutral
4. Consider the IMPACT of the news, not just the language used"""),

    ("human", """Analyze the sentiment of this news article:

TITLE: {title}

CONTENT: {content}

Sentiment analysis:""")
])


# =====================================================
# CREATE THE LLM
# =====================================================
#
# WHY LOW TEMPERATURE (0.1)?
# --------------------------
# For sentiment analysis, we want CONSISTENCY.
# The same article should always get the same sentiment.
#
# Temperature controls randomness:
# - 0.0 = Always pick the most likely response (deterministic)
# - 0.1 = Very slight variation (what we use)
# - 0.5 = Moderate creativity
# - 1.0 = High creativity/randomness
#
# For classification tasks, low temperature is best.
#
# =====================================================

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
    """Return the (lazily-built) sentiment-analysis chain."""
    global _chain
    if _chain is None:
        _chain = SENTIMENT_PROMPT | create_llm() | StrOutputParser()
    return _chain


# =====================================================
# PARSING THE RESPONSE
# =====================================================
#
# Claude returns text like:
#   "SENTIMENT: negative
#    CONFIDENCE: high
#    REASON: The article describes a disaster with casualties."
#
# We need to convert this to a Python dictionary:
#   {
#       "sentiment": "negative",
#       "confidence": "high",
#       "reason": "The article describes..."
#   }
#
# This is called OUTPUT PARSING - a crucial skill when
# working with LLMs because they return unstructured text.
#
# =====================================================

def parse_sentiment_response(response: str) -> dict:
    """
    Parse Claude's sentiment response into structured data.

    PARAMETERS:
    -----------
    response : str
        Raw text from Claude in format:
        "SENTIMENT: positive
         CONFIDENCE: high
         REASON: ..."

    RETURNS:
    --------
    dict with keys:
        - sentiment: "positive", "negative", or "neutral"
        - confidence: "high", "medium", or "low"
        - reason: explanation string

    EDGE CASES HANDLED:
    -------------------
    1. Extra whitespace
    2. Different capitalizations
    3. Missing fields (defaults provided)
    4. Invalid sentiment values (defaults to "neutral")
    """

    result = {
        "sentiment": "neutral",    # Default if parsing fails
        "confidence": "medium",
        "reason": "Unable to determine sentiment"
    }

    # Split response into lines and process each
    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Parse SENTIMENT line
        if line.upper().startswith("SENTIMENT:"):
            value = line.split(":", 1)[1].strip().lower()
            # Validate against allowed values
            if value in VALID_SENTIMENTS:
                result["sentiment"] = value
            else:
                # If Claude returns something unexpected, default to neutral
                result["sentiment"] = "neutral"

        # Parse CONFIDENCE line
        elif line.upper().startswith("CONFIDENCE:"):
            value = line.split(":", 1)[1].strip().lower()
            if value in ["high", "medium", "low"]:
                result["confidence"] = value

        # Parse REASON line
        elif line.upper().startswith("REASON:"):
            value = line.split(":", 1)[1].strip()
            result["reason"] = value

    return result


# =====================================================
# ANALYZE SINGLE ARTICLE
# =====================================================

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

    print(f"  Analyzing sentiment: {title[:40]}...")

    response = chain.invoke({
        "title": title,
        "content": content,
    })

    parsed = parse_sentiment_response(response)

    article.sentiment = parsed["sentiment"]
    article.sentiment_confidence = parsed["confidence"]
    article.sentiment_reason = parsed["reason"]

    indicator = {
        "positive": "[+]",
        "negative": "[-]",
        "neutral": "[=]",
    }.get(parsed["sentiment"], "[=]")

    print(f"    -> {indicator} {parsed['sentiment']} ({parsed['confidence']} confidence)")

    return article


# =====================================================
# ANALYZE MULTIPLE ARTICLES
# =====================================================

def analyze_sentiments(articles: list[Article]) -> list[Article]:
    """Run sentiment analysis on every article, defaulting to neutral on error."""

    print("\n" + "=" * 50)
    print("ANALYZING ARTICLE SENTIMENTS")
    print("=" * 50)

    analyzed: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}]", end="")

        try:
            analyzed_article = analyze_sentiment(article)
            analyzed.append(analyzed_article)
        except Exception as e:
            print(f"  Error: {e}")
            article.sentiment = "neutral"
            article.sentiment_confidence = "low"
            article.sentiment_reason = f"Error during analysis: {str(e)}"
            analyzed.append(article)

    print("\n" + "=" * 50)
    print("SENTIMENT ANALYSIS COMPLETE")
    print("=" * 50)

    return analyzed


# =====================================================
# HELPER FUNCTIONS
# =====================================================

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
        print(f"Invalid sentiment: {sentiment}")
        print(f"Valid options: {', '.join(VALID_SENTIMENTS)}")
        return []

    return [
        article for article in articles
        if (article.sentiment or "neutral") == sentiment
    ]


def display_sentiment_summary(articles: list[Article]) -> None:
    """
    Display a visual summary of sentiments.
    """

    summary = get_sentiment_summary(articles)

    print("\n" + "=" * 60)
    print("SENTIMENT SUMMARY")
    print("=" * 60)

    # Visual bars
    for sentiment in ["positive", "negative", "neutral"]:
        count = summary[sentiment]
        percentage = summary["breakdown"][sentiment]

        # Create visual bar (each █ = 5%)
        bar_length = int(percentage / 5)
        bar = "█" * bar_length

        # Emoji
        emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}[sentiment]

        print(f"\n  {emoji} {sentiment.upper()}")
        print(f"     {bar} {count} articles ({percentage}%)")

    print(f"\n  Total articles analyzed: {summary['total']}")
    print("=" * 60)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING SENTIMENT ANALYSIS")
    print("=" * 60)

    test_articles = [
        Article(
            title="Tech Company Reports Record Profits, Plans Major Expansion",
            summary="""The technology giant announced record-breaking quarterly
            profits of $50 billion, exceeding analyst expectations by 20%. The CEO
            revealed plans to hire 10,000 new employees and expand into three new
            markets. Investors responded positively, with stock prices rising 15%.""",
            source="Test",
            url="",
        ),
        Article(
            title="Earthquake Devastates Coastal Region, Thousands Displaced",
            summary="""A magnitude 7.2 earthquake struck the coastal region early
            this morning, causing widespread destruction. Initial reports indicate
            hundreds of casualties and thousands of displaced residents. Emergency
            services are overwhelmed, and international aid has been requested.""",
            source="Test",
            url="",
        ),
        Article(
            title="Government Announces New Environmental Regulations",
            summary="""The Environmental Protection Agency released new guidelines
            for industrial emissions that will take effect next year. The regulations
            set specific limits on carbon output and require annual compliance reports.
            Industry groups and environmental advocates are reviewing the details.""",
            source="Test",
            url="",
        ),
    ]

    print("\n--- Analyzing Test Articles ---")
    analyzed = analyze_sentiments(test_articles)

    print("\n--- Results ---")
    for article in analyzed:
        print(f"\n📰 {article.title[:50]}...")
        emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}
        print(f"   Sentiment: {emoji.get(article.sentiment, '😐')} {article.sentiment}")
        print(f"   Confidence: {article.sentiment_confidence}")
        print(f"   Reason: {article.sentiment_reason}")

    print("\n--- Summary ---")
    display_sentiment_summary(analyzed)
