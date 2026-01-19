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

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from collections import Counter

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, MODEL_NAME


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

def get_trending_keywords(articles: list[dict], top_n: int = 10) -> list[dict]:
    """
    Get trending topics based on keyword frequency.

    This is the SIMPLE approach - just count keywords.

    PARAMETERS:
    -----------
    articles : list[dict]
        Articles with 'keywords' field (from tagger.py)
    top_n : int
        Number of top trends to return (default: 10)

    RETURNS:
    --------
    list[dict]
        List of trending topics, each with:
        - keyword: The trending term
        - count: How many articles mention it
        - percentage: What % of articles mention it
        - articles: List of article titles mentioning it

    EXAMPLE:
    --------
    >>> trends = get_trending_keywords(articles, top_n=5)
    >>> print(trends[0])
    {
        "keyword": "artificial intelligence",
        "count": 8,
        "percentage": 53.3,
        "articles": ["AI Breakthrough...", "Tech Giants..."]
    }
    """

    # Step 1: Collect all keywords
    # We use Counter, a special dict for counting things
    keyword_counter = Counter()

    # Also track which articles mention each keyword
    keyword_to_articles = {}

    for article in articles:
        # Get keywords (default to empty list if none)
        keywords = article.get("keywords", [])
        title = article.get("title", "Untitled")

        for keyword in keywords:
            # Normalize to lowercase for consistent counting
            keyword = keyword.lower().strip()

            # Count it
            keyword_counter[keyword] += 1

            # Track which article mentioned it
            if keyword not in keyword_to_articles:
                keyword_to_articles[keyword] = []
            keyword_to_articles[keyword].append(title)

    # Step 2: Get the top N keywords
    # Counter.most_common(n) returns [(item, count), ...]
    top_keywords = keyword_counter.most_common(top_n)

    # Step 3: Build result with full information
    total_articles = len(articles)
    trends = []

    for keyword, count in top_keywords:
        percentage = (count / total_articles * 100) if total_articles > 0 else 0

        trends.append({
            "keyword": keyword,
            "count": count,
            "percentage": round(percentage, 1),
            "articles": keyword_to_articles.get(keyword, [])
        })

    return trends


def get_trending_entities(articles: list[dict], top_n: int = 5) -> dict:
    """
    Get trending people, organizations, and locations.

    Similar to get_trending_keywords but for named entities.

    RETURNS:
    --------
    dict with keys:
        - people: Top mentioned people
        - organizations: Top mentioned orgs
        - locations: Top mentioned places
    """

    # Counters for each entity type
    people_counter = Counter()
    org_counter = Counter()
    location_counter = Counter()

    for article in articles:
        for person in article.get("people", []):
            people_counter[person] += 1
        for org in article.get("organizations", []):
            org_counter[org] += 1
        for location in article.get("locations", []):
            location_counter[location] += 1

    return {
        "people": people_counter.most_common(top_n),
        "organizations": org_counter.most_common(top_n),
        "locations": location_counter.most_common(top_n)
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

You MUST respond in this EXACT format:

TREND 1: <trend name>
STRENGTH: <high/medium/low>
DESCRIPTION: <one sentence explaining the trend>
RELATED KEYWORDS: <keyword1, keyword2, keyword3>
ARTICLE COUNT: <number of articles related to this trend>

TREND 2: <trend name>
...

Rules:
1. Identify 3-5 major trends
2. Group related stories together (e.g., different AI articles = one AI trend)
3. STRENGTH is based on how many articles relate to it:
   - high: 4+ articles
   - medium: 2-3 articles
   - low: 1 article but significant topic
4. Look for non-obvious connections between stories
5. Consider both explicit topics and implicit themes"""),

    ("human", """Analyze these {article_count} news articles and identify the major trends:

{articles_text}

Identify the trends:""")
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

    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.3,  # Moderate: some creativity for insights
        max_tokens=1000,  # Longer output for multiple trends
        api_key=ANTHROPIC_API_KEY
    )


def create_trend_chain():
    """
    Create the trend analysis chain.

    This chain takes ALL articles and identifies trends.
    """
    llm = create_trend_llm()
    parser = StrOutputParser()
    chain = TREND_ANALYSIS_PROMPT | llm | parser
    return chain


def format_articles_for_trend_analysis(articles: list[dict]) -> str:
    """
    Format all articles into a single text block for Claude.

    WHY DO THIS?
    ------------
    Claude needs to see all articles together to find patterns.
    We format them consistently so Claude can easily compare them.

    We include:
    - Title (most important)
    - Category (helps group related articles)
    - Summary (the content to analyze)
    - Keywords (if available, helps Claude see explicit topics)

    PARAMETERS:
    -----------
    articles : list[dict]
        All articles to analyze

    RETURNS:
    --------
    str
        Formatted text block with all articles
    """

    formatted_parts = []

    for i, article in enumerate(articles, 1):
        title = article.get("title", "Untitled")
        category = article.get("category", "Uncategorized")
        summary = article.get("summary", article.get("description", "No summary"))
        keywords = article.get("keywords", [])

        # Format each article
        article_text = f"""--- ARTICLE {i} ---
TITLE: {title}
CATEGORY: {category}
SUMMARY: {summary}
KEYWORDS: {', '.join(keywords) if keywords else 'None'}
"""
        formatted_parts.append(article_text)

    return "\n".join(formatted_parts)


def parse_trend_response(response: str) -> list[dict]:
    """
    Parse Claude's trend analysis into structured data.

    INPUT (from Claude):
    --------------------
    "TREND 1: AI Industry Growth
     STRENGTH: high
     DESCRIPTION: Multiple articles discuss AI advancements...
     RELATED KEYWORDS: artificial intelligence, machine learning
     ARTICLE COUNT: 5

     TREND 2: Economic Concerns
     ..."

    OUTPUT (Python list):
    ---------------------
    [
        {
            "name": "AI Industry Growth",
            "strength": "high",
            "description": "Multiple articles discuss...",
            "keywords": ["artificial intelligence", "machine learning"],
            "article_count": 5
        },
        ...
    ]
    """

    trends = []
    current_trend = None

    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Start of new trend
        if line.upper().startswith("TREND"):
            # Save previous trend if exists
            if current_trend:
                trends.append(current_trend)

            # Parse trend name: "TREND 1: AI Growth" → "AI Growth"
            if ":" in line:
                # Handle "TREND 1: Name" format
                parts = line.split(":", 1)
                if len(parts) > 1:
                    name = parts[1].strip()
                else:
                    name = "Unknown Trend"
            else:
                name = "Unknown Trend"

            current_trend = {
                "name": name,
                "strength": "medium",
                "description": "",
                "keywords": [],
                "article_count": 0
            }

        # Parse trend properties
        elif current_trend:
            if line.upper().startswith("STRENGTH:"):
                value = line.split(":", 1)[1].strip().lower()
                if value in ["high", "medium", "low"]:
                    current_trend["strength"] = value

            elif line.upper().startswith("DESCRIPTION:"):
                current_trend["description"] = line.split(":", 1)[1].strip()

            elif line.upper().startswith("RELATED KEYWORDS:"):
                keywords_str = line.split(":", 1)[1].strip()
                current_trend["keywords"] = [
                    kw.strip().lower()
                    for kw in keywords_str.split(",")
                    if kw.strip()
                ]

            elif line.upper().startswith("ARTICLE COUNT:"):
                try:
                    count_str = line.split(":", 1)[1].strip()
                    # Handle "5" or "5 articles" format
                    count = int(count_str.split()[0])
                    current_trend["article_count"] = count
                except (ValueError, IndexError):
                    current_trend["article_count"] = 0

    # Don't forget the last trend!
    if current_trend:
        trends.append(current_trend)

    return trends


# =====================================================
# MAIN TREND DETECTION FUNCTION
# =====================================================

def detect_trends(articles: list[dict], use_llm: bool = True) -> dict:
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

    print("\n" + "=" * 50)
    print("DETECTING TRENDING TOPICS")
    print("=" * 50)

    result = {
        "keyword_trends": [],
        "entity_trends": {},
        "llm_trends": []
    }

    # -------------------------------------------------
    # STEP 1: Statistical Analysis (Fast, Free)
    # -------------------------------------------------
    print("\n📊 Analyzing keyword frequencies...")
    result["keyword_trends"] = get_trending_keywords(articles, top_n=10)
    result["entity_trends"] = get_trending_entities(articles, top_n=5)

    print(f"   Found {len(result['keyword_trends'])} trending keywords")

    # -------------------------------------------------
    # STEP 2: LLM Analysis (Smart, Costs API)
    # -------------------------------------------------
    if use_llm and len(articles) >= 2:
        print("\n🤖 Asking Claude to identify themes...")

        try:
            chain = create_trend_chain()

            # Format all articles for Claude
            articles_text = format_articles_for_trend_analysis(articles)

            # Call the chain
            response = chain.invoke({
                "article_count": len(articles),
                "articles_text": articles_text
            })

            # Parse the response
            result["llm_trends"] = parse_trend_response(response)

            print(f"   Identified {len(result['llm_trends'])} major trends")

        except Exception as e:
            print(f"   Error in LLM analysis: {e}")
            result["llm_trends"] = []

    elif not use_llm:
        print("\n   (Skipping LLM analysis - use_llm=False)")

    elif len(articles) < 2:
        print("\n   (Skipping LLM analysis - need at least 2 articles)")

    print("\n" + "=" * 50)
    print("TREND DETECTION COMPLETE")
    print("=" * 50)

    return result


# =====================================================
# DISPLAY FUNCTIONS
# =====================================================

def display_trends(trends: dict) -> None:
    """
    Display trending topics in a readable format.
    """

    print("\n" + "=" * 60)
    print("📈 TRENDING TOPICS")
    print("=" * 60)

    # -------------------------------------------------
    # Display LLM-detected trends (most insightful)
    # -------------------------------------------------
    if trends.get("llm_trends"):
        print("\n🔥 MAJOR TRENDS (AI Analysis)")
        print("-" * 40)

        for i, trend in enumerate(trends["llm_trends"], 1):
            # Strength indicator
            strength_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(trend["strength"], "⚪")

            print(f"\n  {i}. {trend['name']} {strength_emoji}")
            print(f"     Strength: {trend['strength']} ({trend['article_count']} articles)")
            print(f"     {trend['description']}")

            if trend["keywords"]:
                print(f"     Keywords: {', '.join(trend['keywords'][:5])}")

    # -------------------------------------------------
    # Display keyword frequency trends
    # -------------------------------------------------
    print("\n\n🏷️  TOP KEYWORDS")
    print("-" * 40)

    for i, kw_data in enumerate(trends.get("keyword_trends", [])[:7], 1):
        keyword = kw_data["keyword"]
        count = kw_data["count"]
        percentage = kw_data["percentage"]

        # Visual bar
        bar = "█" * min(count, 10)

        print(f"  {i}. {keyword}")
        print(f"     {bar} {count} articles ({percentage}%)")

    # -------------------------------------------------
    # Display entity trends
    # -------------------------------------------------
    entity_trends = trends.get("entity_trends", {})

    if entity_trends.get("people"):
        print("\n\n👤 TRENDING PEOPLE")
        print("-" * 40)
        for name, count in entity_trends["people"]:
            print(f"  • {name} ({count} mentions)")

    if entity_trends.get("organizations"):
        print("\n🏢 TRENDING ORGANIZATIONS")
        print("-" * 40)
        for name, count in entity_trends["organizations"]:
            print(f"  • {name} ({count} mentions)")

    if entity_trends.get("locations"):
        print("\n📍 TRENDING LOCATIONS")
        print("-" * 40)
        for name, count in entity_trends["locations"]:
            print(f"  • {name} ({count} mentions)")

    print("\n" + "=" * 60)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING TREND DETECTION")
    print("=" * 60)

    # Test articles with some overlapping themes
    test_articles = [
        {
            "title": "Apple Unveils New AI-Powered iPhone Features",
            "summary": "Apple announced revolutionary AI capabilities in its latest iPhone, including real-time translation and smart photo editing.",
            "category": "Technology",
            "keywords": ["artificial intelligence", "smartphones", "apple"],
            "people": ["Tim Cook"],
            "organizations": ["Apple"],
            "locations": ["California"]
        },
        {
            "title": "Google's AI Chatbot Gains Million Users",
            "summary": "Google's new AI assistant has reached one million users within its first week, competing directly with ChatGPT.",
            "category": "Technology",
            "keywords": ["artificial intelligence", "chatbot", "google"],
            "people": ["Sundar Pichai"],
            "organizations": ["Google", "OpenAI"],
            "locations": ["Silicon Valley"]
        },
        {
            "title": "Tech Stocks Rally on AI Optimism",
            "summary": "Technology stocks surged today as investors bet on artificial intelligence growth. NVIDIA and Microsoft led gains.",
            "category": "Business",
            "keywords": ["artificial intelligence", "stocks", "investment"],
            "people": [],
            "organizations": ["NVIDIA", "Microsoft"],
            "locations": ["Wall Street"]
        },
        {
            "title": "Climate Summit Reaches Historic Agreement",
            "summary": "World leaders agreed to ambitious emission targets at the Paris climate summit, marking a turning point in environmental policy.",
            "category": "World News",
            "keywords": ["climate change", "environment", "policy"],
            "people": ["Emmanuel Macron"],
            "organizations": ["United Nations"],
            "locations": ["Paris"]
        },
        {
            "title": "Renewable Energy Investment Hits Record High",
            "summary": "Global investment in renewable energy reached $500 billion this year, driven by government incentives and falling costs.",
            "category": "Business",
            "keywords": ["climate change", "renewable energy", "investment"],
            "people": [],
            "organizations": [],
            "locations": []
        },
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
