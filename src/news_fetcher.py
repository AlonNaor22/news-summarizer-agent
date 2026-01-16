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

# Import our settings from config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RSS_FEEDS, MAX_ARTICLES_PER_SOURCE


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
