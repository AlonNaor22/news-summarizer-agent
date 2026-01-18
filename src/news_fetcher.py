# =====================================================
# NEWS FETCHER MODULE
# =====================================================
#
# This module fetches news articles from RSS feeds.
#
# WHAT IS RSS?
# RSS (Really Simple Syndication) is a standard format that
# websites use to share their latest content. Think of it
# like a "subscription" - instead of visiting a website,
# you can read their RSS feed to get updates.
#
# HOW IT WORKS:
# 1. We send a request to an RSS feed URL
# 2. The website returns XML data with articles
# 3. feedparser library converts XML into Python objects
# 4. We extract the information we need (title, link, etc.)
#
# =====================================================

import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from typing import Optional

# For making HTTP requests to NewsAPI
import requests

# Import our settings from config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    RSS_FEEDS,
    MAX_ARTICLES_PER_SOURCE,
    NEWS_API_KEY,
    NEWSAPI_SOURCES,
    NEWSAPI_CATEGORIES
)


def fetch_from_rss(feed_url: str, source_name: str, max_articles: int = 5) -> list[dict]:
    """
    Fetch articles from a single RSS feed.

    PARAMETERS:
    -----------
    feed_url : str
        The URL of the RSS feed (e.g., "http://feeds.bbci.co.uk/news/rss.xml")

    source_name : str
        A friendly name for the source (e.g., "BBC News")

    max_articles : int
        Maximum number of articles to fetch (default: 5)

    RETURNS:
    --------
    list[dict]
        A list of article dictionaries, each containing:
        - title: Article headline
        - description: Short summary from the feed
        - url: Link to full article
        - source: Name of the news source
        - published: Publication date

    EXAMPLE:
    --------
    >>> articles = fetch_from_rss(
    ...     "http://feeds.bbci.co.uk/news/rss.xml",
    ...     "BBC News",
    ...     max_articles=3
    ... )
    >>> print(articles[0]["title"])
    "Breaking: Major Event Happens"
    """

    # Step 1: Parse the RSS feed
    # feedparser.parse() downloads the feed and converts XML to Python
    print(f"  Fetching from {source_name}...")
    feed = feedparser.parse(feed_url)

    # Step 2: Check if the feed was fetched successfully
    # feed.bozo is True if there was an error parsing
    if feed.bozo and not feed.entries:
        print(f"  Warning: Could not fetch from {source_name}")
        return []

    # Step 3: Extract articles from the feed
    articles = []

    # feed.entries contains all the articles
    # We use [:max_articles] to limit how many we get
    for entry in feed.entries[:max_articles]:

        # Step 4: Extract data from each entry
        # We use .get() method which returns None if the field doesn't exist
        # This prevents errors if an article is missing some data

        article = {
            # The headline of the article
            "title": entry.get("title", "No title"),

            # Short description/summary (RSS feeds often include this)
            "description": entry.get("summary", entry.get("description", "")),

            # Link to the full article
            "url": entry.get("link", ""),

            # Which news source this came from
            "source": source_name,

            # When the article was published
            "published": parse_date(entry.get("published", "")),
        }

        articles.append(article)

    print(f"  Found {len(articles)} articles from {source_name}")
    return articles


def parse_date(date_string: str) -> Optional[str]:
    """
    Convert various date formats to a readable string.

    RSS feeds use different date formats. This function handles
    that complexity and returns a consistent format.

    PARAMETERS:
    -----------
    date_string : str
        A date in any format (e.g., "Mon, 15 Jan 2024 10:30:00 GMT")

    RETURNS:
    --------
    str or None
        Formatted date string (e.g., "January 15, 2024") or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # date_parser.parse() is smart - it can understand many date formats
        parsed_date = date_parser.parse(date_string)
        # Format it nicely for display
        return parsed_date.strftime("%B %d, %Y at %H:%M")
    except (ValueError, TypeError):
        # If we can't parse the date, just return the original string
        return date_string


def fetch_all_news(max_per_source: int = None) -> list[dict]:
    """
    Fetch articles from ALL configured RSS feeds.

    This function loops through all the feeds defined in config.py
    and collects articles from each one.

    PARAMETERS:
    -----------
    max_per_source : int, optional
        Maximum articles per source. Uses config default if not specified.

    RETURNS:
    --------
    list[dict]
        Combined list of articles from all sources

    EXAMPLE:
    --------
    >>> all_articles = fetch_all_news(max_per_source=3)
    >>> print(f"Total articles: {len(all_articles)}")
    Total articles: 15
    """

    if max_per_source is None:
        max_per_source = MAX_ARTICLES_PER_SOURCE

    all_articles = []

    print("\n" + "="*50)
    print("FETCHING NEWS FROM RSS FEEDS")
    print("="*50)

    # Loop through each feed defined in config.py
    # RSS_FEEDS is a dictionary: {"Source Name": "feed_url"}
    for source_name, feed_url in RSS_FEEDS.items():
        articles = fetch_from_rss(feed_url, source_name, max_per_source)
        all_articles.extend(articles)  # Add to our master list

    print("="*50)
    print(f"TOTAL: {len(all_articles)} articles fetched")
    print("="*50 + "\n")

    return all_articles


def display_articles(articles: list[dict]) -> None:
    """
    Display articles in a readable format.

    This is a helper function to see what we fetched.

    PARAMETERS:
    -----------
    articles : list[dict]
        List of article dictionaries to display
    """

    for i, article in enumerate(articles, 1):
        print(f"\n{'='*60}")
        print(f"ARTICLE {i}")
        print(f"{'='*60}")
        print(f"Title:       {article['title']}")
        print(f"Source:      {article['source']}")
        print(f"Published:   {article['published']}")
        print(f"URL:         {article['url']}")
        print(f"\nDescription:")
        print(f"  {article['description'][:300]}...")  # First 300 chars


# =====================================================
# NEWSAPI FUNCTIONS
# =====================================================
#
# NewsAPI is an alternative to RSS feeds. It provides:
# - Access to 80,000+ news sources
# - Search by keyword, category, or source
# - Structured JSON responses
#
# Free tier: 100 requests/day
# Sign up: https://newsapi.org/
#
# =====================================================

def fetch_from_newsapi(
    api_key: str,
    category: str = None,
    sources: list = None,
    query: str = None,
    max_articles: int = 10
) -> list[dict]:
    """
    Fetch articles from NewsAPI.

    NewsAPI offers two main endpoints:
    1. Top Headlines - Breaking news by category or source
    2. Everything - Search all articles by keyword

    PARAMETERS:
    -----------
    api_key : str
        Your NewsAPI key

    category : str, optional
        News category (business, technology, science, health, etc.)
        Note: Cannot use category AND sources together

    sources : list, optional
        Specific sources like ["bbc-news", "cnn", "techcrunch"]
        Note: Cannot use sources AND category together

    query : str, optional
        Search keyword (e.g., "artificial intelligence")

    max_articles : int
        Maximum articles to return (default: 10)

    RETURNS:
    --------
    list[dict]
        List of article dictionaries

    EXAMPLE:
    --------
    >>> articles = fetch_from_newsapi(
    ...     api_key="your-key",
    ...     category="technology",
    ...     max_articles=5
    ... )
    """

    # Base URL for NewsAPI top headlines
    url = "https://newsapi.org/v2/top-headlines"

    # Build request parameters
    params = {
        "apiKey": api_key,
        "language": "en",
        "pageSize": max_articles,
    }

    # Add optional filters
    # Note: NewsAPI doesn't allow category + sources together
    if sources:
        params["sources"] = ",".join(sources)
    elif category:
        params["category"] = category
        params["country"] = "us"  # Required when using category

    if query:
        params["q"] = query

    print(f"  Fetching from NewsAPI...")
    if category:
        print(f"    Category: {category}")
    if sources:
        print(f"    Sources: {', '.join(sources)}")

    try:
        # Make the HTTP request
        response = requests.get(url, params=params, timeout=10)

        # Check for errors
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        # Check API response status
        if data.get("status") != "ok":
            print(f"  NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        # Convert NewsAPI format to our format
        articles = []
        for item in data.get("articles", []):
            article = {
                "title": item.get("title", "No title"),
                "description": item.get("description") or item.get("content", ""),
                "url": item.get("url", ""),
                "source": item.get("source", {}).get("name", "Unknown"),
                "published": parse_date(item.get("publishedAt", "")),
                "author": item.get("author"),  # NewsAPI includes author
                "image_url": item.get("urlToImage"),  # NewsAPI includes images
            }
            articles.append(article)

        print(f"  Found {len(articles)} articles from NewsAPI")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching from NewsAPI: {e}")
        return []


def fetch_all_newsapi(
    api_key: str = None,
    categories: list = None,
    max_per_category: int = 5
) -> list[dict]:
    """
    Fetch articles from NewsAPI across multiple categories.

    This is similar to fetch_all_news() for RSS, but uses NewsAPI.

    PARAMETERS:
    -----------
    api_key : str, optional
        Your NewsAPI key. Uses config if not provided.

    categories : list, optional
        Categories to fetch. Uses config if not provided.

    max_per_category : int
        Max articles per category (default: 5)

    RETURNS:
    --------
    list[dict]
        Combined list of articles from all categories
    """

    # Use config values if not provided
    if api_key is None:
        api_key = NEWS_API_KEY

    if not api_key:
        print("\n⚠️  NewsAPI key not found!")
        print("   Add NEWS_API_KEY to your .env file")
        print("   Get a free key at: https://newsapi.org/")
        return []

    if categories is None:
        categories = NEWSAPI_CATEGORIES

    all_articles = []

    print("\n" + "="*50)
    print("FETCHING NEWS FROM NEWSAPI")
    print("="*50)

    for category in categories:
        articles = fetch_from_newsapi(
            api_key=api_key,
            category=category,
            max_articles=max_per_category
        )
        all_articles.extend(articles)

    print("="*50)
    print(f"TOTAL: {len(all_articles)} articles fetched from NewsAPI")
    print("="*50 + "\n")

    return all_articles


def fetch_news(source: str = "rss", max_per_source: int = None) -> list[dict]:
    """
    Unified function to fetch news from any source.

    This is the main function to use - it handles both RSS and NewsAPI.

    PARAMETERS:
    -----------
    source : str
        Which source to use:
        - "rss" (default): Fetch from RSS feeds
        - "newsapi": Fetch from NewsAPI
        - "both": Fetch from both sources

    max_per_source : int, optional
        Maximum articles per source/category

    RETURNS:
    --------
    list[dict]
        List of articles from the specified source(s)

    EXAMPLE:
    --------
    >>> articles = fetch_news("rss")        # From RSS feeds
    >>> articles = fetch_news("newsapi")    # From NewsAPI
    >>> articles = fetch_news("both")       # From both
    """

    if max_per_source is None:
        max_per_source = MAX_ARTICLES_PER_SOURCE

    source = source.lower()

    if source == "rss":
        return fetch_all_news(max_per_source=max_per_source)

    elif source == "newsapi":
        return fetch_all_newsapi(max_per_category=max_per_source)

    elif source == "both":
        rss_articles = fetch_all_news(max_per_source=max_per_source)
        newsapi_articles = fetch_all_newsapi(max_per_category=max_per_source)
        return rss_articles + newsapi_articles

    else:
        print(f"Unknown source: {source}")
        print("Valid options: rss, newsapi, both")
        return []


# =====================================================
# TEST CODE
# =====================================================
# This code only runs if you execute this file directly:
#   python src/news_fetcher.py
#
# It won't run when you import this module elsewhere.
# This is a common Python pattern for testing.
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING NEWS FETCHER")
    print("="*60)

    # Test 1: Fetch from a single source
    print("\n--- Test 1: Fetch from BBC News ---")
    bbc_articles = fetch_from_rss(
        "http://feeds.bbci.co.uk/news/rss.xml",
        "BBC News",
        max_articles=3
    )

    # Display what we got
    if bbc_articles:
        display_articles(bbc_articles)

    # Test 2: Fetch from all sources
    print("\n\n--- Test 2: Fetch from ALL sources ---")
    all_articles = fetch_all_news(max_per_source=2)
    print(f"\nFetched {len(all_articles)} total articles!")

    # Show first 3
    print("\nShowing first 3 articles:")
    display_articles(all_articles[:3])
