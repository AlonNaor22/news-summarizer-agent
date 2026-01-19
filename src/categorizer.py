# =====================================================
# CATEGORIZER MODULE
# =====================================================
#
# This module classifies articles into categories using Claude.
#
# KEY DIFFERENCE FROM SUMMARIZER:
# - Summarizer: "Write a paragraph about this"
# - Categorizer: "Pick ONE option from this list"
#
# This is called CLASSIFICATION - a common AI task.
#
# =====================================================

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Import our settings
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE, CATEGORIES


# =====================================================
# THE CATEGORIZATION PROMPTS
# =====================================================
#
# We have TWO prompts:
# 1. CATEGORIZE_PROMPT - Single category (simple)
# 2. MULTI_CATEGORIZE_PROMPT - Primary + Secondary (detailed)
#
# =====================================================

# ----- SINGLE CATEGORY PROMPT -----
# Use this when you only need one category per article
CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a news article classifier. Your job is to categorize news articles into exactly ONE category.

Available categories:
{categories}

Rules:
1. Respond with ONLY the category name, nothing else
2. Choose the single most relevant category
3. If unsure, choose "Other"
4. Do not explain your choice, just output the category name"""),

    ("human", """Categorize this article:

TITLE: {title}

SUMMARY: {summary}

Category:""")
])


# ----- MULTI-CATEGORY PROMPT -----
# Use this when articles might fit multiple categories
# Returns a PRIMARY category and optional SECONDARY categories
MULTI_CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a news article classifier. Articles often cover multiple topics.
Your job is to identify the PRIMARY category and any SECONDARY categories.

Available categories:
{categories}

Rules:
1. PRIMARY = The main focus of the article (required)
2. SECONDARY = Other relevant topics (optional, can be "None")
3. Use this EXACT format:
   PRIMARY: <category>
   SECONDARY: <category1>, <category2> or None

Example responses:
---
PRIMARY: Technology
SECONDARY: Business
---
PRIMARY: Politics
SECONDARY: None
---
PRIMARY: Health
SECONDARY: Science, Business"""),

    ("human", """Categorize this article:

TITLE: {title}

SUMMARY: {summary}

Categories:""")
])


def create_llm():
    """Create Claude LLM instance."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found! Check your .env file.")

    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.1,  # Very low temperature for consistent classification
        max_tokens=50,    # Category names are short
        api_key=ANTHROPIC_API_KEY
    )


def create_categorize_chain():
    """
    Create a chain for categorizing articles.

    WHY TEMPERATURE = 0.1?
    ----------------------
    For classification, we want CONSISTENT results.
    - Same article should always get same category
    - Low temperature = less randomness = more predictable

    Compare to summarization where we used 0.3:
    - Summaries can have slight variation in wording
    - Categories must be exact matches
    """
    llm = create_llm()
    parser = StrOutputParser()
    chain = CATEGORIZE_PROMPT | llm | parser
    return chain


def clean_category(raw_category: str) -> str:
    """
    Clean up Claude's response to get just the category.

    WHY DO WE NEED THIS?
    --------------------
    Even with strict prompts, AI might respond:
    - "Technology"           ← Perfect
    - "Technology."          ← Has a period
    - "The category is Technology"  ← Extra words
    - "technology"           ← Wrong case

    This function handles these edge cases.

    PARAMETERS:
    -----------
    raw_category : str
        Raw response from Claude

    RETURNS:
    --------
    str
        Cleaned category name that matches our list
    """
    # Remove whitespace and common punctuation
    cleaned = raw_category.strip().strip(".,!?\"'")

    # Check if it matches any of our categories (case-insensitive)
    for category in CATEGORIES:
        if category.lower() == cleaned.lower():
            return category  # Return the properly-cased version

        # Also check if the category is contained in the response
        # This handles "The category is Technology" → "Technology"
        if category.lower() in cleaned.lower():
            return category

    # If no match found, return "Other"
    return "Other"


def categorize_article(article: dict) -> dict:
    """
    Categorize a single article.

    PARAMETERS:
    -----------
    article : dict
        Article with 'title' and 'summary' (or 'description') keys

    RETURNS:
    --------
    dict
        Same article with 'category' key added
    """
    chain = create_categorize_chain()

    title = article.get("title", "Untitled")

    # Use summary if available, otherwise use description
    summary = article.get("summary", article.get("description", ""))

    if not summary:
        article["category"] = "Other"
        return article

    print(f"  Categorizing: {title[:40]}...")

    # Create the categories string for the prompt
    categories_str = "\n".join(f"- {cat}" for cat in CATEGORIES)

    # Call the chain
    raw_response = chain.invoke({
        "categories": categories_str,
        "title": title,
        "summary": summary
    })

    # Clean up the response
    category = clean_category(raw_response)
    article["category"] = category

    print(f"    -> {category}")

    return article


def categorize_articles(articles: list[dict]) -> list[dict]:
    """
    Categorize multiple articles.

    PARAMETERS:
    -----------
    articles : list[dict]
        List of articles (should already have summaries)

    RETURNS:
    --------
    list[dict]
        Same articles with 'category' key added to each
    """
    print("\n" + "="*50)
    print("CATEGORIZING ARTICLES")
    print("="*50)

    categorized = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}]", end="")

        try:
            categorized_article = categorize_article(article)
            categorized.append(categorized_article)
        except Exception as e:
            print(f"  Error: {e}")
            article["category"] = "Other"
            categorized.append(article)

    print("\n" + "="*50)
    print("CATEGORIZATION COMPLETE")
    print("="*50)

    return categorized


# =====================================================
# MULTI-CATEGORY FUNCTIONS
# =====================================================
#
# These functions handle articles that fit multiple categories.
# They return both PRIMARY and SECONDARY categories.
#
# =====================================================

def create_multi_categorize_chain():
    """
    Create a chain for multi-category classification.

    This chain returns PRIMARY and SECONDARY categories.
    """
    llm = ChatAnthropic(
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=100,  # Slightly more for multiple categories
        api_key=ANTHROPIC_API_KEY
    )
    parser = StrOutputParser()
    chain = MULTI_CATEGORIZE_PROMPT | llm | parser
    return chain


def parse_multi_category_response(response: str) -> dict:
    """
    Parse Claude's multi-category response.

    INPUT FORMAT (from Claude):
        "PRIMARY: Technology
         SECONDARY: Business, Science"

    OUTPUT FORMAT (Python dict):
        {
            "primary": "Technology",
            "secondary": ["Business", "Science"]
        }

    This function handles various edge cases in Claude's response.
    """
    result = {
        "primary": "Other",
        "secondary": []
    }

    lines = response.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Parse PRIMARY category
        if line.upper().startswith("PRIMARY"):
            # "PRIMARY: Technology" → "Technology"
            parts = line.split(":", 1)
            if len(parts) > 1:
                primary = parts[1].strip()
                # Clean and validate
                result["primary"] = clean_category(primary)

        # Parse SECONDARY categories
        elif line.upper().startswith("SECONDARY"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                secondary_str = parts[1].strip()

                # Handle "None" case
                if secondary_str.lower() == "none":
                    result["secondary"] = []
                else:
                    # "Business, Science" → ["Business", "Science"]
                    secondary_list = [s.strip() for s in secondary_str.split(",")]
                    # Clean each category
                    result["secondary"] = [
                        clean_category(s) for s in secondary_list
                        if clean_category(s) != "Other"  # Don't include "Other" in secondary
                    ]

    return result


def categorize_article_multi(article: dict) -> dict:
    """
    Categorize an article with PRIMARY and SECONDARY categories.

    PARAMETERS:
    -----------
    article : dict
        Article with 'title' and 'summary' (or 'description') keys

    RETURNS:
    --------
    dict
        Article with added keys:
        - 'category': Primary category (string)
        - 'secondary_categories': List of secondary categories

    EXAMPLE:
    --------
    >>> article = {"title": "Apple Stock Surges on iPhone News", ...}
    >>> result = categorize_article_multi(article)
    >>> print(result["category"])
    "Technology"
    >>> print(result["secondary_categories"])
    ["Business"]
    """
    chain = create_multi_categorize_chain()

    title = article.get("title", "Untitled")
    summary = article.get("summary", article.get("description", ""))

    if not summary:
        article["category"] = "Other"
        article["secondary_categories"] = []
        return article

    print(f"  Categorizing: {title[:40]}...")

    categories_str = "\n".join(f"- {cat}" for cat in CATEGORIES)

    # Call the chain
    raw_response = chain.invoke({
        "categories": categories_str,
        "title": title,
        "summary": summary
    })

    # Parse the response
    parsed = parse_multi_category_response(raw_response)

    article["category"] = parsed["primary"]
    article["secondary_categories"] = parsed["secondary"]

    # Display result
    secondary_str = ", ".join(parsed["secondary"]) if parsed["secondary"] else "None"
    print(f"    -> Primary: {parsed['primary']}")
    print(f"    -> Secondary: {secondary_str}")

    return article


def categorize_articles_multi(articles: list[dict]) -> list[dict]:
    """
    Categorize multiple articles with multi-category support.
    """
    print("\n" + "="*50)
    print("CATEGORIZING ARTICLES (Multi-Category)")
    print("="*50)

    categorized = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}]", end="")

        try:
            categorized_article = categorize_article_multi(article)
            categorized.append(categorized_article)
        except Exception as e:
            print(f"  Error: {e}")
            article["category"] = "Other"
            article["secondary_categories"] = []
            categorized.append(article)

    print("\n" + "="*50)
    print("CATEGORIZATION COMPLETE")
    print("="*50)

    return categorized


def display_multi_categories(articles: list[dict]) -> None:
    """
    Display articles with their primary and secondary categories.
    """
    print("\n" + "="*60)
    print("ARTICLES WITH MULTIPLE CATEGORIES")
    print("="*60)

    for article in articles:
        print(f"\n📰 {article['title'][:50]}...")
        print(f"   Primary:   {article.get('category', 'Other')}")

        secondary = article.get('secondary_categories', [])
        if secondary:
            print(f"   Secondary: {', '.join(secondary)}")
        else:
            print(f"   Secondary: None")


def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    """
    Group articles by their category.

    This is useful for displaying articles organized by topic.

    PARAMETERS:
    -----------
    articles : list[dict]
        List of categorized articles

    RETURNS:
    --------
    dict[str, list[dict]]
        Dictionary where keys are categories and values are lists of articles

    EXAMPLE:
    --------
    >>> grouped = group_by_category(articles)
    >>> print(grouped.keys())
    dict_keys(['Technology', 'Politics', 'Sports'])
    >>> print(len(grouped['Technology']))
    5
    """
    grouped = {}

    for article in articles:
        category = article.get("category", "Other")

        # Create the list if this is the first article in this category
        if category not in grouped:
            grouped[category] = []

        grouped[category].append(article)

    return grouped


def display_by_category(articles: list[dict]) -> None:
    """
    Display articles grouped by category.
    """
    grouped = group_by_category(articles)

    print("\n" + "="*60)
    print("ARTICLES BY CATEGORY")
    print("="*60)

    for category, category_articles in grouped.items():
        print(f"\n📁 {category.upper()} ({len(category_articles)} articles)")
        print("-"*40)

        for article in category_articles:
            print(f"  • {article['title'][:50]}...")
            print(f"    Source: {article['source']}")


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING CATEGORIZER")
    print("="*60)

    # -------------------------------------------------
    # TEST 1: Articles that fit MULTIPLE categories
    # -------------------------------------------------
    # These articles intentionally span multiple topics
    # to demonstrate multi-category classification

    multi_topic_articles = [
        {
            "title": "Apple Stock Surges After Revolutionary AI iPhone Announcement",
            "summary": "Apple's stock price jumped 15% today after the company unveiled an iPhone with groundbreaking AI features. Wall Street analysts predict the technology could reshape the smartphone industry and boost Apple's market cap significantly.",
            "source": "Tech Business Daily"
        },
        {
            "title": "New Government Policy Aims to Boost Tech Industry with Tax Breaks",
            "summary": "Congress passed legislation offering tax incentives for technology companies investing in AI research. The bill, supported by both parties, is expected to create thousands of new jobs in the tech sector.",
            "source": "Political Tech News"
        },
        {
            "title": "Olympic Athlete Uses AI Technology to Break World Record",
            "summary": "A sprinter broke the 100-meter world record using AI-powered training systems developed by scientists at MIT. The technology analyzes biomechanics to optimize performance.",
            "source": "Sports Science Weekly"
        },
    ]

    print("\n" + "="*60)
    print("TEST 1: Multi-Category Classification")
    print("="*60)
    print("These articles span multiple topics...")

    # Use multi-category classification
    multi_categorized = categorize_articles_multi(multi_topic_articles)
    display_multi_categories(multi_categorized)

    # -------------------------------------------------
    # TEST 2: Standard single-category articles
    # -------------------------------------------------

    single_topic_articles = [
        {
            "title": "Lakers Win Championship in Overtime Thriller",
            "summary": "The Los Angeles Lakers defeated the Boston Celtics in a dramatic game 7 overtime victory to claim the NBA championship.",
            "source": "Sports Weekly"
        },
        {
            "title": "Scientists Discover New Species in Amazon",
            "summary": "Researchers have identified a previously unknown species of frog in the Amazon rainforest that may have medicinal properties.",
            "source": "Science Today"
        },
    ]

    print("\n\n" + "="*60)
    print("TEST 2: Single-Category Classification")
    print("="*60)
    print("These articles have one clear topic...")

    # Use single-category classification
    single_categorized = categorize_articles(single_topic_articles)

    for article in single_categorized:
        print(f"\n📰 {article['title']}")
        print(f"   Category: {article['category']}")
