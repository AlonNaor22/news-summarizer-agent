"""Fetch news articles from RSS feeds and NewsAPI into :class:`Article` instances."""

import logging
from typing import Optional

import feedparser
import requests
from dateutil import parser as date_parser

from config import (
    MAX_ARTICLES_PER_SOURCE,
    NEWS_API_KEY,
    NEWSAPI_CATEGORIES,
    RSS_FEEDS,
)
from src.models import Article

logger = logging.getLogger(__name__)


def fetch_from_rss(feed_url: str, source_name: str, max_articles: int = 5) -> list[Article]:
    """Fetch up to ``max_articles`` from a single RSS feed as ``Article`` instances."""

    logger.info("Fetching from %s...", source_name)
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        logger.warning("Could not fetch from %s", source_name)
        return []

    articles: list[Article] = []
    for entry in feed.entries[:max_articles]:
        articles.append(
            Article(
                title=entry.get("title", "No title"),
                description=entry.get("summary", entry.get("description", "")),
                url=entry.get("link", ""),
                source=source_name,
                published=parse_date(entry.get("published", "")),
            )
        )

    logger.info("Found %d articles from %s", len(articles), source_name)
    return articles


def parse_date(date_string: str) -> Optional[str]:
    """Parse arbitrary date strings into ``"Month DD, YYYY at HH:MM"`` form."""
    if not date_string:
        return None

    try:
        parsed_date = date_parser.parse(date_string)
        return parsed_date.strftime("%B %d, %Y at %H:%M")
    except (ValueError, TypeError):
        return date_string


def fetch_all_news(max_per_source: int = None) -> list[Article]:
    """Fetch articles from every RSS feed configured in :data:`config.RSS_FEEDS`."""

    if max_per_source is None:
        max_per_source = MAX_ARTICLES_PER_SOURCE

    all_articles: list[Article] = []

    logger.info("=" * 50)
    logger.info("FETCHING NEWS FROM RSS FEEDS")
    logger.info("=" * 50)

    for source_name, feed_url in RSS_FEEDS.items():
        articles = fetch_from_rss(feed_url, source_name, max_per_source)
        all_articles.extend(articles)

    logger.info("=" * 50)
    logger.info("TOTAL: %d articles fetched", len(all_articles))
    logger.info("=" * 50)

    return all_articles


def display_articles(articles: list[Article]) -> None:
    """Log a human-readable summary of a list of articles."""

    for i, article in enumerate(articles, 1):
        logger.info("=" * 60)
        logger.info("ARTICLE %d", i)
        logger.info("=" * 60)
        logger.info("Title:       %s", article.title)
        logger.info("Source:      %s", article.source)
        logger.info("Published:   %s", article.published)
        logger.info("URL:         %s", article.url)
        logger.info("Description:")
        logger.info("  %s...", article.description[:300])


def fetch_from_newsapi(
    api_key: str,
    category: str = None,
    sources: list = None,
    query: str = None,
    max_articles: int = 10,
) -> list[Article]:
    """Fetch articles from NewsAPI's top-headlines endpoint."""

    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "apiKey": api_key,
        "language": "en",
        "pageSize": max_articles,
    }

    if sources:
        params["sources"] = ",".join(sources)
    elif category:
        params["category"] = category
        params["country"] = "us"

    if query:
        params["q"] = query

    logger.info("Fetching from NewsAPI...")
    if category:
        logger.info("  Category: %s", category)
    if sources:
        logger.info("  Sources: %s", ", ".join(sources))

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            logger.warning("NewsAPI error: %s", data.get("message", "Unknown error"))
            return []

        articles: list[Article] = []
        for item in data.get("articles", []):
            articles.append(
                Article(
                    title=item.get("title") or "No title",
                    description=item.get("description") or item.get("content", "") or "",
                    url=item.get("url", ""),
                    source=(item.get("source") or {}).get("name", "Unknown"),
                    published=parse_date(item.get("publishedAt", "")),
                    author=item.get("author"),
                    image_url=item.get("urlToImage"),
                )
            )

        logger.info("Found %d articles from NewsAPI", len(articles))
        return articles

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching from NewsAPI: %s", e)
        return []


def fetch_all_newsapi(
    api_key: str = None,
    categories: list = None,
    max_per_category: int = 5,
) -> list[Article]:
    """Fetch top headlines from NewsAPI for every configured category."""

    if api_key is None:
        api_key = NEWS_API_KEY

    if not api_key:
        logger.warning("NewsAPI key not found! Add NEWS_API_KEY to your .env file")
        return []

    if categories is None:
        categories = NEWSAPI_CATEGORIES

    all_articles: list[Article] = []

    logger.info("=" * 50)
    logger.info("FETCHING NEWS FROM NEWSAPI")
    logger.info("=" * 50)

    for category in categories:
        articles = fetch_from_newsapi(
            api_key=api_key,
            category=category,
            max_articles=max_per_category,
        )
        all_articles.extend(articles)

    logger.info("=" * 50)
    logger.info("TOTAL: %d articles fetched from NewsAPI", len(all_articles))
    logger.info("=" * 50)

    return all_articles


def fetch_news(source: str = "rss", max_per_source: int = None) -> list[Article]:
    """Fetch from RSS, NewsAPI, or both — depending on ``source``."""

    if max_per_source is None:
        max_per_source = MAX_ARTICLES_PER_SOURCE

    source = source.lower()

    if source == "rss":
        return fetch_all_news(max_per_source=max_per_source)

    if source == "newsapi":
        return fetch_all_newsapi(max_per_category=max_per_source)

    if source == "both":
        rss_articles = fetch_all_news(max_per_source=max_per_source)
        newsapi_articles = fetch_all_newsapi(max_per_category=max_per_source)
        return rss_articles + newsapi_articles

    logger.warning("Unknown source: %s. Valid options: rss, newsapi, both", source)
    return []


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING NEWS FETCHER")
    print("=" * 60)

    print("\n--- Test 1: Fetch from BBC News ---")
    bbc_articles = fetch_from_rss(
        "http://feeds.bbci.co.uk/news/rss.xml",
        "BBC News",
        max_articles=3,
    )

    if bbc_articles:
        display_articles(bbc_articles)

    print("\n\n--- Test 2: Fetch from ALL sources ---")
    all_articles = fetch_all_news(max_per_source=2)
    print(f"\nFetched {len(all_articles)} total articles!")

    print("\nShowing first 3 articles:")
    display_articles(all_articles[:3])
