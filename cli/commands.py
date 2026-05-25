"""Per-command handlers and the ``process_command`` dispatcher.

Each handler takes the mutable :class:`AgentState` as its first argument so
state and behavior stay decoupled. ``process_command`` parses the user input
and routes to the appropriate handler.
"""

import json
import os
from datetime import datetime, timedelta

from dateutil import parser as date_parser

from src.news_fetcher import fetch_news as _fetch_articles
from src.summarizer import summarize_articles
from src.categorizer import categorize_articles, group_by_category
from src.qa_chain import NewsQAChain
from src.tagger import tag_articles, get_all_keywords, get_all_entities
from src.sentiment import (
    analyze_sentiments,
    get_sentiment_summary,
    filter_by_sentiment,
    display_sentiment_summary,
)
from src.trending import detect_trends, display_trends
from src.similarity import (
    find_similar_articles,
    analyze_article_relationships,
    display_similar_articles,
    display_all_relationships,
)
from src.comparator import (
    compare_all_stories,
    display_all_comparisons,
    find_same_story_articles,
)

from config import (
    RSS_FEEDS,
    NEWSAPI_SOURCES,
    NEWSAPI_CATEGORIES,
    NEWS_API_KEY,
    WORDS_PER_MINUTE,
    SIMILARITY_THRESHOLDS,
)

from cli import display
from cli.display import header, hr
from cli.state import AgentState


# =====================================================
# CORE COMMANDS
# =====================================================

def fetch_news(state: AgentState, source: str = "rss") -> None:
    """Fetch, summarize, categorize, tag, and analyze articles."""
    header("FETCHING NEWS")

    # Clearing caches from previous fetch — old analysis is now invalid.
    state.trends_cache = None
    state.relationships_cache = None
    state.comparisons_cache = None

    source_name = {
        "rss": "RSS feeds",
        "newsapi": "NewsAPI",
        "both": "RSS feeds and NewsAPI",
    }.get(source, "RSS feeds")

    print(f"\nStep 1/5: Fetching articles from {source_name}...")
    raw_articles = _fetch_articles(source=source)

    if not raw_articles:
        print("No articles found. Please check your internet connection.")
        return

    print("\nStep 2/5: Summarizing articles with Claude...")
    summarized = summarize_articles(raw_articles)

    print("\nStep 3/5: Categorizing articles...")
    categorized = categorize_articles(summarized)

    print("\nStep 4/5: Extracting keywords and entities...")
    tagged = tag_articles(categorized)

    print("\nStep 5/5: Analyzing sentiment...")
    state.articles = analyze_sentiments(tagged)

    state.qa_chain = NewsQAChain()
    state.qa_chain.load_articles(state.articles)

    header("FETCH COMPLETE!")
    print(f"  Total articles: {len(state.articles)}")

    grouped = group_by_category(state.articles)
    print(f"  Categories: {len(grouped)}")
    for cat, arts in grouped.items():
        print(f"    - {cat}: {len(arts)} articles")

    all_keywords = get_all_keywords(state.articles)
    if all_keywords:
        top_keywords = list(all_keywords.keys())[:5]
        print(f"  Top keywords: {', '.join(top_keywords)}")

    sentiment_summary = get_sentiment_summary(state.articles)
    print(f"  Sentiment: 😊 {sentiment_summary['positive']} positive, "
          f"😟 {sentiment_summary['negative']} negative, "
          f"😐 {sentiment_summary['neutral']} neutral")

    print("\nType 'show' to see articles, 'sentiment' for mood analysis,")
    print("or 'trending' to see what's hot!")


def show_articles(state: AgentState, article_num: int | None = None) -> None:
    """Display all articles, or one article in detail when ``article_num`` is given."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if article_num is not None:
        if 1 <= article_num <= len(state.articles):
            article = state.articles[article_num - 1]
            stats = _calculate_article_stats(article)

            header(f"ARTICLE {article_num}")
            print(f"\nTitle:    {article['title']}")
            print(f"Source:   {article['source']}")
            print(f"Category: {article.get('category', 'Uncategorized')}")
            print(f"Date:     {article.get('published', 'Unknown')}")
            print(f"Reading:  {stats['reading_time_display']} ({stats['word_count']} words)")

            sentiment = article.get('sentiment', 'unknown')
            sentiment_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(sentiment, "❓")
            print(f"Sentiment: {sentiment_emoji} {sentiment}")
            if article.get('sentiment_reason'):
                print(f"          ({article['sentiment_reason']})")

            print(f"\nSummary:")
            print(f"  {article.get('summary', 'No summary available')}")

            keywords = article.get("keywords", [])
            people = article.get("people", [])
            organizations = article.get("organizations", [])
            locations = article.get("locations", [])

            if keywords or people or organizations or locations:
                print(f"\nTags:")
                if keywords:
                    print(f"  🏷️  Keywords: {', '.join(keywords)}")
                if people:
                    print(f"  👤 People: {', '.join(people)}")
                if organizations:
                    print(f"  🏢 Orgs: {', '.join(organizations)}")
                if locations:
                    print(f"  📍 Places: {', '.join(locations)}")

            print(f"\nURL: {article.get('url', 'No URL')}")
            hr("=")
        else:
            print(f"\nInvalid article number. Choose between 1 and {len(state.articles)}")
        return

    header(f"ALL ARTICLES ({len(state.articles)} total)")

    for i, article in enumerate(state.articles, 1):
        category = article.get('category', '?')
        title = article['title'][:50]
        print(f"\n  [{i}] [{category}] {title}...")
        print(f"      Source: {article['source']}")

    hr("-", lead_newline=True)
    print("Tip: Type 'show <number>' to see full details")
    print("     Example: show 3")


def show_category(state: AgentState, category_name: str | None = None) -> None:
    """List categories, or show all articles in a specific category."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    grouped = group_by_category(state.articles)

    if category_name is None:
        header("CATEGORIES")
        for cat, arts in grouped.items():
            print(f"\n  {cat} ({len(arts)} articles)")
            for art in arts[:2]:
                print(f"    - {art['title'][:45]}...")
            if len(arts) > 2:
                print(f"    ... and {len(arts) - 2} more")
        hr("-", lead_newline=True)
        print("Tip: Type 'category <name>' to see all articles in a category")
        print("     Example: category Technology")
        return

    matched_category = None
    for cat in grouped.keys():
        if cat.lower() == category_name.lower():
            matched_category = cat
            break

    if matched_category is None:
        print(f"\nCategory '{category_name}' not found.")
        print(f"Available categories: {', '.join(grouped.keys())}")
        return

    articles_in_cat = grouped[matched_category]
    header(f"{matched_category.upper()} ({len(articles_in_cat)} articles)")

    for i, article in enumerate(articles_in_cat, 1):
        print(f"\n  [{i}] {article['title'][:50]}...")
        print(f"      Source: {article['source']}")
        summary = article.get('summary', '')[:100]
        print(f"      {summary}...")


def ask_question(state: AgentState, question: str) -> None:
    """Ask a question against the loaded articles via the Q&A chain."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if state.qa_chain is None:
        state.qa_chain = NewsQAChain()
        state.qa_chain.load_articles(state.articles)

    hr("-", lead_newline=True)
    print("Thinking...")
    answer = state.qa_chain.ask(question)
    hr("-")
    print(f"\n{answer}")
    hr("-", lead_newline=True)
    print("Tip: You can ask follow-up questions - I remember the conversation!")


def show_sources(state: AgentState) -> None:
    """Display available news sources (RSS and NewsAPI)."""
    header("AVAILABLE NEWS SOURCES")

    print("\n📡 RSS FEEDS (free, no API key needed)")
    hr("-", width=40)
    for name, url in RSS_FEEDS.items():
        print(f"  • {name}")
        print(f"    {url}")

    print("\n🌐 NEWSAPI SOURCES")
    hr("-", width=40)
    if NEWS_API_KEY:
        print("  Status: ✓ API key configured")
    else:
        print("  Status: ✗ No API key (add NEWS_API_KEY to .env)")
        print("  Get a free key at: https://newsapi.org/")

    print("\n  Sources:")
    for source in NEWSAPI_SOURCES:
        print(f"    • {source}")

    print("\n  Categories:")
    for category in NEWSAPI_CATEGORIES:
        print(f"    • {category}")

    hr("=", lead_newline=True)
    print("Usage: fetch rss | fetch newsapi | fetch both")
    hr("=")


def show_tags(state: AgentState, article_num: int | None = None) -> None:
    """Show keywords/entities for one article, or the top trending ones overall."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if article_num is not None:
        if 1 <= article_num <= len(state.articles):
            article = state.articles[article_num - 1]
            header(f"TAGS FOR ARTICLE {article_num}")
            print(f"\n📰 {article['title']}")

            keywords = article.get("keywords", [])
            people = article.get("people", [])
            organizations = article.get("organizations", [])
            locations = article.get("locations", [])

            print(f"\n🏷️  Keywords: {', '.join(keywords) if keywords else 'None'}")
            print(f"👤 People: {', '.join(people) if people else 'None'}")
            print(f"🏢 Organizations: {', '.join(organizations) if organizations else 'None'}")
            print(f"📍 Locations: {', '.join(locations) if locations else 'None'}")
        else:
            print(f"\nInvalid article number. Choose between 1 and {len(state.articles)}")
        return

    header("TRENDING KEYWORDS & ENTITIES")

    all_keywords = get_all_keywords(state.articles)
    print("\n🏷️  TOP KEYWORDS")
    hr("-", width=40)
    if all_keywords:
        for keyword, count in list(all_keywords.items())[:10]:
            bar = "█" * count
            print(f"  {keyword}: {bar} ({count})")
    else:
        print("  No keywords extracted")

    all_entities = get_all_entities(state.articles)

    print("\n👤 PEOPLE MENTIONED")
    hr("-", width=40)
    if all_entities["people"]:
        for name, count in list(all_entities["people"].items())[:5]:
            print(f"  {name}: {count} mention(s)")
    else:
        print("  No people mentioned")

    print("\n🏢 ORGANIZATIONS")
    hr("-", width=40)
    if all_entities["organizations"]:
        for name, count in list(all_entities["organizations"].items())[:5]:
            print(f"  {name}: {count} mention(s)")
    else:
        print("  No organizations mentioned")

    print("\n📍 LOCATIONS")
    hr("-", width=40)
    if all_entities["locations"]:
        for name, count in list(all_entities["locations"].items())[:5]:
            print(f"  {name}: {count} mention(s)")
    else:
        print("  No locations mentioned")

    hr("-", lead_newline=True)
    print("Tip: Use 'tags <number>' to see tags for a specific article")


def search_articles(state: AgentState, query: str) -> None:
    """Search articles by keyword across title, summary, keywords, and entities."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if not query or len(query.strip()) < 2:
        print("\nPlease enter a search term (at least 2 characters).")
        return

    query = query.lower().strip()
    matches = []

    for article in state.articles:
        searchable_parts = [
            article.get("title", ""),
            article.get("summary", ""),
            article.get("description", ""),
            article.get("category", ""),
            " ".join(article.get("keywords", [])),
            " ".join(article.get("people", [])),
            " ".join(article.get("organizations", [])),
            " ".join(article.get("locations", [])),
        ]

        searchable_text = " ".join(searchable_parts).lower()

        if query in searchable_text:
            matches.append(article)

    header(f"SEARCH RESULTS FOR: '{query}'")

    if not matches:
        print("\nNo articles found matching your search.")
        print("Try a different keyword or use 'show' to see all articles.")
        return

    print(f"\nFound {len(matches)} article(s):\n")

    for i, article in enumerate(matches, 1):
        original_idx = state.articles.index(article) + 1

        match_locations = []
        if query in article.get("title", "").lower():
            match_locations.append("title")
        if query in article.get("summary", "").lower():
            match_locations.append("summary")
        if query in " ".join(article.get("keywords", [])).lower():
            match_locations.append("keywords")
        if query in " ".join(article.get("people", [])).lower():
            match_locations.append("people")
        if query in " ".join(article.get("organizations", [])).lower():
            match_locations.append("organizations")
        if query in " ".join(article.get("locations", [])).lower():
            match_locations.append("locations")

        category = article.get('category', '?')
        title = article['title'][:50]

        print(f"  [{original_idx}] [{category}] {title}...")
        print(f"      Source: {article['source']}")
        print(f"      Match in: {', '.join(match_locations)}")
        print()

    hr("-")
    print("Tip: Use 'show <number>' to see full article details")


def save_articles(state: AgentState, format_type: str = "json") -> None:
    """Save articles to disk in JSON or Markdown."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}/")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if format_type.lower() == "json":
        _save_as_json(state, output_dir, timestamp)
    elif format_type.lower() in ["md", "markdown"]:
        _save_as_markdown(state, output_dir, timestamp)
    else:
        print(f"Unknown format: {format_type}")
        print("Valid options: json, md")


def _save_as_json(state: AgentState, output_dir: str, timestamp: str) -> None:
    """Write the article list to a timestamped JSON file."""
    filename = f"{output_dir}/news_{timestamp}.json"

    data = {
        "metadata": {
            "saved_at": datetime.now().isoformat(),
            "total_articles": len(state.articles),
            "categories": list(group_by_category(state.articles).keys()),
        },
        "articles": state.articles,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    header("SAVED AS JSON")
    print(f"\n  File: {filename}")
    print(f"  Articles: {len(state.articles)}")
    print(f"  Size: {os.path.getsize(filename):,} bytes")
    print("\nYou can load this file in Python with:")
    print(f"  import json")
    print(f"  with open('{filename}') as f:")
    print(f"      data = json.load(f)")


def _save_as_markdown(state: AgentState, output_dir: str, timestamp: str) -> None:
    """Write the article list to a timestamped Markdown file."""
    filename = f"{output_dir}/news_{timestamp}.md"

    lines = []

    date_str = datetime.now().strftime("%B %d, %Y at %H:%M")
    lines.append(f"# News Summary")
    lines.append(f"")
    lines.append(f"*Generated on {date_str}*")
    lines.append(f"")
    lines.append(f"**Total Articles:** {len(state.articles)}")
    lines.append(f"")

    grouped = group_by_category(state.articles)

    lines.append("## Table of Contents")
    lines.append("")
    for category in grouped.keys():
        anchor = category.lower().replace(" ", "-")
        lines.append(f"- [{category}](#{anchor}) ({len(grouped[category])} articles)")
    lines.append("")
    lines.append("---")
    lines.append("")

    for category, articles in grouped.items():
        lines.append(f"## {category}")
        lines.append("")

        for i, article in enumerate(articles, 1):
            lines.append(f"### {i}. {article['title']}")
            lines.append("")

            lines.append(f"**Source:** {article['source']}")
            if article.get('published'):
                lines.append(f"  ")
                lines.append(f"**Published:** {article['published']}")
            lines.append("")

            lines.append(f"**Summary:**")
            lines.append(f"")
            lines.append(f"> {article.get('summary', 'No summary available')}")
            lines.append("")

            keywords = article.get("keywords", [])
            if keywords:
                tags_str = " ".join([f"`{kw}`" for kw in keywords])
                lines.append(f"**Keywords:** {tags_str}")
                lines.append("")

            people = article.get("people", [])
            orgs = article.get("organizations", [])
            locations = article.get("locations", [])

            if people or orgs or locations:
                lines.append("**Entities:**")
                if people:
                    lines.append(f"- People: {', '.join(people)}")
                if orgs:
                    lines.append(f"- Organizations: {', '.join(orgs)}")
                if locations:
                    lines.append(f"- Locations: {', '.join(locations)}")
                lines.append("")

            if article.get('url'):
                lines.append(f"[Read full article]({article['url']})")
                lines.append("")

            lines.append("---")
            lines.append("")

    lines.append("*Generated by News Summarizer Agent*")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    header("SAVED AS MARKDOWN")
    print(f"\n  File: {filename}")
    print(f"  Articles: {len(state.articles)}")
    print(f"  Size: {os.path.getsize(filename):,} bytes")
    print("\nYou can open this file in:")
    print("  - Any text editor")
    print("  - VS Code (with preview)")
    print("  - GitHub (renders automatically)")
    print("  - Notion, Obsidian, etc.")


def _calculate_article_stats(article: dict) -> dict:
    """Return word count, char count, and human-readable reading time."""
    text = article.get("summary", article.get("description", ""))

    words = text.split()
    word_count = len(words)
    char_count = len(text.replace(" ", ""))

    reading_time_minutes = word_count / WORDS_PER_MINUTE
    reading_time_seconds = int(reading_time_minutes * 60)

    if reading_time_seconds < 60:
        reading_time_display = f"{reading_time_seconds} sec"
    else:
        minutes = reading_time_seconds // 60
        seconds = reading_time_seconds % 60
        if seconds > 0:
            reading_time_display = f"{minutes} min {seconds} sec"
        else:
            reading_time_display = f"{minutes} min"

    return {
        "word_count": word_count,
        "char_count": char_count,
        "reading_time_seconds": reading_time_seconds,
        "reading_time_display": reading_time_display,
    }


def show_stats(state: AgentState, article_num: int | None = None) -> None:
    """Show stats for one article, or aggregate stats across all of them."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if article_num is not None:
        if 1 <= article_num <= len(state.articles):
            article = state.articles[article_num - 1]
            stats = _calculate_article_stats(article)

            header(f"STATISTICS FOR ARTICLE {article_num}")
            print(f"\n📰 {article['title'][:50]}...")
            print(f"\n📊 Summary Statistics:")
            print(f"   Words:        {stats['word_count']}")
            print(f"   Characters:   {stats['char_count']}")
            print(f"   Reading time: {stats['reading_time_display']}")
            print(f"\n📁 Category: {article.get('category', 'Uncategorized')}")
            print(f"📡 Source:   {article.get('source', 'Unknown')}")

            keywords = article.get("keywords", [])
            entities = (
                article.get("people", [])
                + article.get("organizations", [])
                + article.get("locations", [])
            )
            print(f"\n🏷️  Keywords: {len(keywords)}")
            print(f"👤 Entities: {len(entities)}")
        else:
            print(f"\nInvalid article number. Choose between 1 and {len(state.articles)}")
        return

    header("OVERALL STATISTICS")

    total_words = 0
    total_chars = 0
    total_reading_seconds = 0
    total_keywords = 0
    total_entities = 0

    for article in state.articles:
        stats = _calculate_article_stats(article)
        total_words += stats["word_count"]
        total_chars += stats["char_count"]
        total_reading_seconds += stats["reading_time_seconds"]
        total_keywords += len(article.get("keywords", []))
        total_entities += len(article.get("people", []))
        total_entities += len(article.get("organizations", []))
        total_entities += len(article.get("locations", []))

    total_minutes = total_reading_seconds // 60
    remaining_seconds = total_reading_seconds % 60

    print(f"\n📰 ARTICLES")
    print(f"   Total articles: {len(state.articles)}")

    grouped = group_by_category(state.articles)
    print(f"   Categories:     {len(grouped)}")
    for cat, arts in grouped.items():
        pct = (len(arts) / len(state.articles)) * 100
        bar = "█" * int(pct / 5)
        print(f"     {cat}: {len(arts)} ({pct:.0f}%) {bar}")

    print(f"\n📊 CONTENT")
    print(f"   Total words:      {total_words:,}")
    print(f"   Total characters: {total_chars:,}")
    print(f"   Avg words/article: {total_words // len(state.articles)}")

    print(f"\n⏱️  READING TIME")
    print(f"   Total: {total_minutes} min {remaining_seconds} sec")
    print(f"   Average per article: {total_reading_seconds // len(state.articles)} sec")

    print(f"\n🏷️  TAGS")
    print(f"   Total keywords: {total_keywords}")
    print(f"   Total entities: {total_entities}")
    print(f"   Avg keywords/article: {total_keywords / len(state.articles):.1f}")

    sources = {}
    for article in state.articles:
        source = article.get("source", "Unknown")
        sources[source] = sources.get(source, 0) + 1

    print(f"\n📡 SOURCES")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"   {source}: {count} article(s)")

    hr("-", lead_newline=True)
    print("Tip: Use 'stats <number>' for individual article stats")


def _parse_article_date(article: dict) -> datetime | None:
    """Parse an article's 'published' field into a ``datetime``, or ``None``."""
    date_str = article.get("published", "")

    if not date_str:
        return None

    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        return None


def filter_by_date(state: AgentState, date_range: str) -> None:
    """Show articles published within a date range: today/yesterday/week/month."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    now = datetime.now()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    date_range = date_range.lower().strip()
    end_cutoff = None

    if date_range == "today":
        cutoff = today_midnight
        range_description = "today"
    elif date_range == "yesterday":
        cutoff = today_midnight - timedelta(days=1)
        end_cutoff = today_midnight
        range_description = "yesterday"
    elif date_range == "week":
        cutoff = now - timedelta(days=7)
        range_description = "the last 7 days"
    elif date_range == "month":
        cutoff = now - timedelta(days=30)
        range_description = "the last 30 days"
    else:
        print(f"\nUnknown date range: {date_range}")
        print("Valid options: today, yesterday, week, month")
        return

    matches = []
    no_date_count = 0

    for article in state.articles:
        article_date = _parse_article_date(article)

        if article_date is None:
            no_date_count += 1
            continue

        if date_range == "yesterday":
            if cutoff <= article_date < end_cutoff:
                matches.append(article)
        else:
            if article_date >= cutoff:
                matches.append(article)

    header(f"ARTICLES FROM {range_description.upper()}")

    if not matches:
        print(f"\nNo articles found from {range_description}.")
        if no_date_count > 0:
            print(f"({no_date_count} articles have no date information)")
        return

    print(f"\nFound {len(matches)} article(s) from {range_description}:\n")

    for article in matches:
        original_idx = state.articles.index(article) + 1
        category = article.get('category', '?')
        title = article['title'][:45]
        published = article.get('published', 'Unknown date')

        print(f"  [{original_idx}] [{category}] {title}...")
        print(f"      📅 {published}")
        print(f"      📡 {article['source']}")
        print()

    if no_date_count > 0:
        print(f"Note: {no_date_count} article(s) excluded (no date info)")

    hr("-")
    print("Tip: Use 'show <number>' for full article details")


def clear_history(state: AgentState) -> None:
    """Clear Q&A conversation history."""
    if state.qa_chain:
        state.qa_chain.clear_history()
        print("\nConversation history cleared.")
    else:
        print("\nNo conversation history to clear.")


# =====================================================
# ADVANCED FEATURE COMMANDS
# =====================================================

def show_sentiment(state: AgentState, sentiment_filter: str | None = None) -> None:
    """Show overall sentiment breakdown, or only articles matching ``sentiment_filter``."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if sentiment_filter:
        sentiment_filter = sentiment_filter.lower()
        if sentiment_filter not in ["positive", "negative", "neutral"]:
            print(f"\nInvalid sentiment: {sentiment_filter}")
            print("Valid options: positive, negative, neutral")
            return

        filtered = filter_by_sentiment(state.articles, sentiment_filter)

        emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}[sentiment_filter]
        header(f"{emoji} {sentiment_filter.upper()} ARTICLES")

        if not filtered:
            print(f"\nNo {sentiment_filter} articles found.")
            return

        print(f"\nFound {len(filtered)} {sentiment_filter} article(s):\n")

        for article in filtered:
            original_idx = state.articles.index(article) + 1
            title = article['title'][:45]
            reason = article.get('sentiment_reason', '')[:50]

            print(f"  [{original_idx}] {title}...")
            print(f"      {reason}")
            print()

        return

    display_sentiment_summary(state.articles)

    hr("-", lead_newline=True)
    print("Tip: Use 'sentiment positive' to see only positive news")
    print("     Use 'sentiment negative' to see concerning news")


def show_trending(state: AgentState, use_llm: bool = True) -> None:
    """Show trending topics across all articles (cached when possible)."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if state.trends_cache and state.trends_cache.get("use_llm") == use_llm:
        print("\n(Using cached trend analysis)")
        display_trends(state.trends_cache["data"])
        return

    trends = detect_trends(state.articles, use_llm=use_llm)

    state.trends_cache = {
        "use_llm": use_llm,
        "data": trends,
    }

    display_trends(trends)

    if use_llm:
        hr("-", lead_newline=True)
        print("Tip: Use 'trending fast' for quick analysis without AI")


def show_similar(state: AgentState, article_num: int) -> None:
    """Find articles similar to the given article number."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if not (1 <= article_num <= len(state.articles)):
        print(f"\nInvalid article number. Choose between 1 and {len(state.articles)}")
        return

    target = state.articles[article_num - 1]

    print(f"\n🔍 Finding articles similar to #{article_num}...")

    similar = find_similar_articles(
        target_article=target,
        all_articles=state.articles,
        threshold=SIMILARITY_THRESHOLDS["find_similar_cli"],
        max_results=5,
    )

    display_similar_articles(target, similar)

    if similar:
        hr("-", lead_newline=True)
        print("Tip: Use 'show <number>' to read a similar article")


def show_related(state: AgentState) -> None:
    """Show all pairwise article relationships, statistical and LLM-detected."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if len(state.articles) < 2:
        print("\nNeed at least 2 articles to find relationships.")
        return

    if state.relationships_cache:
        print("\n(Using cached relationship analysis)")
        display_all_relationships(state.relationships_cache)
        return

    print("\n🔍 Analyzing article relationships...")

    analysis = analyze_article_relationships(state.articles, use_llm=True)

    state.relationships_cache = analysis

    display_all_relationships(analysis)


def show_comparison(state: AgentState) -> None:
    """Compare how different sources cover the same story."""
    if not state.articles:
        print("\nNo articles loaded. Use 'fetch' first.")
        return

    if len(state.articles) < 2:
        print("\nNeed at least 2 articles to compare sources.")
        return

    sources = set(art.get("source", "") for art in state.articles)
    if len(sources) < 2:
        print("\nAll articles are from the same source.")
        print("Use 'fetch both' to get articles from multiple sources.")
        return

    if state.comparisons_cache:
        print("\n(Using cached comparison analysis)")
        display_all_comparisons(state.comparisons_cache)
        return

    print("\n🔍 Looking for same stories covered by multiple sources...")

    story_groups = find_same_story_articles(state.articles)

    if not story_groups:
        print("\nNo stories found that are covered by multiple sources.")
        print("\nThis can happen when:")
        print("  - Articles are about different topics")
        print("  - Sources are covering different events")
        print("\nTry 'fetch both' to get more diverse coverage.")
        return

    print(f"\nFound {len(story_groups)} story/stories with multiple source coverage:")
    for i, group in enumerate(story_groups, 1):
        print(f"  {i}. \"{group['story_title'][:40]}...\"")
        print(f"     Sources: {', '.join(group['sources'])}")

    comparisons = compare_all_stories(state.articles)

    state.comparisons_cache = comparisons

    display_all_comparisons(comparisons)

    hr("-", lead_newline=True)
    print("Tip: This analysis shows how different outlets")
    print("     frame the same story - helpful for spotting bias!")


# =====================================================
# COMMAND DISPATCHER
# =====================================================

def process_command(state: AgentState, user_input: str) -> None:
    """Parse ``user_input`` and route it to the matching handler."""
    parts = user_input.strip().split(maxsplit=1)
    if not parts:
        return

    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else None

    if command in ['quit', 'exit', 'q']:
        print("\nGoodbye! Stay informed!")
        state.is_running = False

    elif command == 'help':
        display.display_help()

    elif command == 'fetch':
        source = args.lower() if args else "rss"
        if source not in ["rss", "newsapi", "both"]:
            print(f"Unknown source: {source}")
            print("Valid options: rss, newsapi, both")
            return
        fetch_news(state, source=source)

    elif command == 'show':
        if args:
            try:
                num = int(args)
                show_articles(state, num)
            except ValueError:
                print("Usage: show <number>")
                print("Example: show 3")
        else:
            show_articles(state)

    elif command == 'category':
        show_category(state, args)

    elif command == 'tags':
        if args:
            try:
                num = int(args)
                show_tags(state, num)
            except ValueError:
                print("Usage: tags <number>")
                print("Example: tags 3")
        else:
            show_tags(state)

    elif command == 'search':
        if args:
            search_articles(state, args)
        else:
            print("Usage: search <keyword>")
            print("Example: search technology")
            print("Example: search climate change")

    elif command == 'save':
        format_type = args.lower() if args else "json"
        save_articles(state, format_type)

    elif command == 'stats':
        if args:
            try:
                num = int(args)
                show_stats(state, num)
            except ValueError:
                print("Usage: stats <number>")
                print("Example: stats 3")
        else:
            show_stats(state)

    elif command == 'filter':
        if args:
            filter_by_date(state, args)
        else:
            print("Usage: filter <date_range>")
            print("Options: today, yesterday, week, month")
            print("Example: filter today")
            print("Example: filter week")

    elif command == 'ask':
        if args:
            ask_question(state, args)
        else:
            print("Usage: ask <your question>")
            print("Example: ask What's the latest technology news?")

    elif command == 'sources':
        show_sources(state)

    elif command == 'clear':
        clear_history(state)

    elif command == 'sentiment':
        show_sentiment(state, args)

    elif command == 'trending':
        if args and args.lower() == "fast":
            show_trending(state, use_llm=False)
        else:
            show_trending(state, use_llm=True)

    elif command == 'similar':
        if args:
            try:
                num = int(args)
                show_similar(state, num)
            except ValueError:
                print("Usage: similar <number>")
                print("Example: similar 3")
        else:
            print("Usage: similar <number>")
            print("Example: similar 3")
            print("\nThis finds articles similar to the specified article.")

    elif command == 'related':
        show_related(state)

    elif command == 'compare':
        show_comparison(state)

    else:
        if state.articles:
            print(f"\nUnknown command '{command}'. Treating as a question...")
            ask_question(state, user_input)
        else:
            print(f"\nUnknown command: '{command}'")
            print("Type 'help' to see available commands.")
