# =====================================================
# NEWS SUMMARIZER AGENT - MAIN CLI
# =====================================================
#
# This is the main entry point for the application.
# It ties together all our modules:
#
# CORE MODULES (Must-Have):
#   - news_fetcher.py - Fetch from RSS/NewsAPI
#   - summarizer.py - Summarize with Claude
#   - categorizer.py - Classify by topic
#   - qa_chain.py - Q&A with memory
#   - tagger.py - Extract keywords/entities
#
# ADVANCED MODULES (Nice-to-Have):
#   - sentiment.py - Analyze article tone
#   - trending.py - Detect trending topics
#   - similarity.py - Find related articles
#   - comparator.py - Compare sources on same story
#
# Run with: python main.py
#
# =====================================================

import json
import os
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# -------------------------------------------------
# CORE MODULE IMPORTS
# -------------------------------------------------
from src.news_fetcher import fetch_all_news, fetch_from_rss, fetch_news
from src.summarizer import summarize_articles
from src.categorizer import categorize_articles, group_by_category
from src.qa_chain import NewsQAChain
from src.tagger import tag_articles, get_all_keywords, get_all_entities

# -------------------------------------------------
# ADVANCED MODULE IMPORTS
# -------------------------------------------------
# These are the modules we built for advanced features:
# - Sentiment: Analyzes positive/negative/neutral tone
# - Trending: Finds hot topics across articles
# - Similarity: Links related articles together
# - Comparator: Compares same story from different sources
from src.sentiment import analyze_sentiments, get_sentiment_summary, filter_by_sentiment, display_sentiment_summary
from src.trending import detect_trends, display_trends
from src.similarity import find_similar_articles, analyze_article_relationships, display_similar_articles, display_all_relationships
from src.comparator import compare_all_stories, display_all_comparisons, find_same_story_articles

from config import RSS_FEEDS, CATEGORIES, NEWSAPI_SOURCES, NEWSAPI_CATEGORIES, NEWS_API_KEY


class NewsSummarizerAgent:
    """
    The main News Summarizer Agent.

    This class orchestrates the entire workflow:

    CORE FEATURES:
    1. Fetch news from RSS feeds or NewsAPI
    2. Summarize articles with Claude
    3. Categorize articles by topic
    4. Extract keywords and entities
    5. Answer questions about the news

    ADVANCED FEATURES:
    6. Analyze sentiment (positive/negative/neutral)
    7. Detect trending topics
    8. Find similar/related articles
    9. Compare same story across sources

    USAGE:
    ------
    >>> agent = NewsSummarizerAgent()
    >>> agent.run()  # Starts the interactive CLI
    """

    def __init__(self):
        """Initialize the agent with empty state."""
        # -------------------------------------------------
        # CORE STATE
        # -------------------------------------------------
        self.articles = []          # Fetched and processed articles
        self.qa_chain = None        # Q&A system (created after fetching)
        self.is_running = True      # Controls main loop

        # -------------------------------------------------
        # ADVANCED FEATURE CACHES
        # -------------------------------------------------
        # We cache results from expensive operations so they
        # don't need to be recalculated every time.
        # These are cleared when new articles are fetched.
        self.trends_cache = None           # Cached trending topics
        self.relationships_cache = None    # Cached article relationships
        self.comparisons_cache = None      # Cached source comparisons

    def display_welcome(self):
        """Show welcome message and available commands."""
        print("\n" + "="*60)
        print("       WELCOME TO THE NEWS SUMMARIZER AGENT")
        print("="*60)
        print("""
This agent helps you:
  - Fetch the latest news from multiple sources
  - Get AI-powered summaries of articles
  - Categorize news by topic
  - Ask follow-up questions about the news

Type 'help' to see available commands.
Type 'fetch' to get started!
        """)
        print("="*60)

    def display_help(self):
        """Show available commands."""
        print("\n" + "-"*60)
        print("AVAILABLE COMMANDS")
        print("-"*60)
        print("""
  ─────────────────────────────────────────────────────────
  FETCHING & VIEWING
  ─────────────────────────────────────────────────────────
  fetch              Fetch news from RSS feeds (default)
  fetch rss          Fetch from RSS feeds only
  fetch newsapi      Fetch from NewsAPI only
  fetch both         Fetch from both sources

  show               Show all fetched articles
  show <number>      Show specific article in detail

  category           List all categories
  category <name>    Show articles in a specific category

  ─────────────────────────────────────────────────────────
  SEARCH & FILTER
  ─────────────────────────────────────────────────────────
  search <keyword>   Search articles by keyword
  filter today       Show articles from today
  filter week        Show articles from last 7 days

  ─────────────────────────────────────────────────────────
  ADVANCED ANALYSIS (NEW!)
  ─────────────────────────────────────────────────────────
  sentiment          Show sentiment breakdown (positive/negative/neutral)
  sentiment <type>   Filter by sentiment (positive/negative/neutral)

  trending           Detect and show trending topics
  trending fast      Quick analysis (keywords only, no AI)

  similar <number>   Find articles similar to article #
  related            Show all article relationships

  compare            Compare same story across different sources

  ─────────────────────────────────────────────────────────
  UTILITIES
  ─────────────────────────────────────────────────────────
  tags               Show trending keywords and entities
  tags <number>      Show tags for a specific article

  stats              Show overall statistics
  stats <number>     Show stats for a specific article

  save               Save articles as JSON (default)
  save md            Save articles as Markdown file

  ask <question>     Ask a question about the articles

  sources            List available news sources
  clear              Clear conversation history
  help               Show this help message
  quit / exit        Exit the program
""")
        print("-"*60)

    def fetch_news(self, source: str = "rss"):
        """
        Fetch, summarize, categorize, and analyze news.

        This is the main pipeline that:
        1. Fetches articles from the specified source
        2. Summarizes each article with Claude
        3. Categorizes articles by topic
        4. Extracts keywords and entities
        5. Analyzes sentiment (NEW!)
        6. Sets up Q&A system

        PARAMETERS:
        -----------
        source : str
            News source to use: "rss", "newsapi", or "both"
        """
        print("\n" + "="*60)
        print("FETCHING NEWS")
        print("="*60)

        # -------------------------------------------------
        # Clear caches from previous fetch
        # -------------------------------------------------
        # When we fetch new articles, old analysis is invalid
        self.trends_cache = None
        self.relationships_cache = None
        self.comparisons_cache = None

        # Step 1: Fetch articles from the specified source
        source_name = {
            "rss": "RSS feeds",
            "newsapi": "NewsAPI",
            "both": "RSS feeds and NewsAPI"
        }.get(source, "RSS feeds")

        print(f"\nStep 1/5: Fetching articles from {source_name}...")
        raw_articles = fetch_news(source=source, max_per_source=3)

        if not raw_articles:
            print("No articles found. Please check your internet connection.")
            return

        # Step 2: Summarize articles
        print("\nStep 2/5: Summarizing articles with Claude...")
        summarized = summarize_articles(raw_articles)

        # Step 3: Categorize articles
        print("\nStep 3/5: Categorizing articles...")
        categorized = categorize_articles(summarized)

        # Step 4: Extract keywords and entities
        print("\nStep 4/5: Extracting keywords and entities...")
        tagged = tag_articles(categorized)

        # Step 5: Analyze sentiment (NEW!)
        print("\nStep 5/5: Analyzing sentiment...")
        self.articles = analyze_sentiments(tagged)

        # Step 6: Set up Q&A system
        self.qa_chain = NewsQAChain()
        self.qa_chain.load_articles(self.articles)

        # Show summary
        print("\n" + "="*60)
        print("FETCH COMPLETE!")
        print("="*60)
        print(f"  Total articles: {len(self.articles)}")

        # Count by category
        grouped = group_by_category(self.articles)
        print(f"  Categories: {len(grouped)}")
        for cat, arts in grouped.items():
            print(f"    - {cat}: {len(arts)} articles")

        # Show top keywords
        all_keywords = get_all_keywords(self.articles)
        if all_keywords:
            top_keywords = list(all_keywords.keys())[:5]
            print(f"  Top keywords: {', '.join(top_keywords)}")

        # Show sentiment breakdown (NEW!)
        sentiment_summary = get_sentiment_summary(self.articles)
        print(f"  Sentiment: 😊 {sentiment_summary['positive']} positive, "
              f"😟 {sentiment_summary['negative']} negative, "
              f"😐 {sentiment_summary['neutral']} neutral")

        print("\nType 'show' to see articles, 'sentiment' for mood analysis,")
        print("or 'trending' to see what's hot!")

    def show_articles(self, article_num=None):
        """
        Display articles.

        If article_num is provided, show that specific article in detail.
        Otherwise, show a list of all articles.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Show specific article
        if article_num is not None:
            if 1 <= article_num <= len(self.articles):
                article = self.articles[article_num - 1]
                stats = self._calculate_article_stats(article)

                print("\n" + "="*60)
                print(f"ARTICLE {article_num}")
                print("="*60)
                print(f"\nTitle:    {article['title']}")
                print(f"Source:   {article['source']}")
                print(f"Category: {article.get('category', 'Uncategorized')}")
                print(f"Date:     {article.get('published', 'Unknown')}")
                print(f"Reading:  {stats['reading_time_display']} ({stats['word_count']} words)")

                # Show sentiment (NEW!)
                sentiment = article.get('sentiment', 'unknown')
                sentiment_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(sentiment, "❓")
                print(f"Sentiment: {sentiment_emoji} {sentiment}")
                if article.get('sentiment_reason'):
                    print(f"          ({article['sentiment_reason']})")

                print(f"\nSummary:")
                print(f"  {article.get('summary', 'No summary available')}")

                # Show tags
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
                print("="*60)
            else:
                print(f"\nInvalid article number. Choose between 1 and {len(self.articles)}")
            return

        # Show all articles (brief list)
        print("\n" + "="*60)
        print(f"ALL ARTICLES ({len(self.articles)} total)")
        print("="*60)

        for i, article in enumerate(self.articles, 1):
            category = article.get('category', '?')
            title = article['title'][:50]
            print(f"\n  [{i}] [{category}] {title}...")
            print(f"      Source: {article['source']}")

        print("\n" + "-"*60)
        print("Tip: Type 'show <number>' to see full details")
        print("     Example: show 3")

    def show_category(self, category_name=None):
        """
        Show articles filtered by category.

        If no category specified, list all categories.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        grouped = group_by_category(self.articles)

        # List all categories
        if category_name is None:
            print("\n" + "="*60)
            print("CATEGORIES")
            print("="*60)
            for cat, arts in grouped.items():
                print(f"\n  {cat} ({len(arts)} articles)")
                for art in arts[:2]:  # Show first 2
                    print(f"    - {art['title'][:45]}...")
                if len(arts) > 2:
                    print(f"    ... and {len(arts) - 2} more")
            print("\n" + "-"*60)
            print("Tip: Type 'category <name>' to see all articles in a category")
            print("     Example: category Technology")
            return

        # Find matching category (case-insensitive)
        matched_category = None
        for cat in grouped.keys():
            if cat.lower() == category_name.lower():
                matched_category = cat
                break

        if matched_category is None:
            print(f"\nCategory '{category_name}' not found.")
            print(f"Available categories: {', '.join(grouped.keys())}")
            return

        # Show articles in category
        articles_in_cat = grouped[matched_category]
        print("\n" + "="*60)
        print(f"{matched_category.upper()} ({len(articles_in_cat)} articles)")
        print("="*60)

        for i, article in enumerate(articles_in_cat, 1):
            print(f"\n  [{i}] {article['title'][:50]}...")
            print(f"      Source: {article['source']}")
            summary = article.get('summary', '')[:100]
            print(f"      {summary}...")

    def ask_question(self, question: str):
        """
        Ask a question about the articles.

        Uses the Q&A chain with memory for follow-up questions.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        if self.qa_chain is None:
            self.qa_chain = NewsQAChain()
            self.qa_chain.load_articles(self.articles)

        print("\n" + "-"*60)
        print("Thinking...")
        answer = self.qa_chain.ask(question)
        print("-"*60)
        print(f"\n{answer}")
        print("\n" + "-"*60)
        print("Tip: You can ask follow-up questions - I remember the conversation!")

    def show_sources(self):
        """Display available news sources (RSS and NewsAPI)."""
        print("\n" + "="*60)
        print("AVAILABLE NEWS SOURCES")
        print("="*60)

        # RSS Feeds
        print("\n📡 RSS FEEDS (free, no API key needed)")
        print("-"*40)
        for name, url in RSS_FEEDS.items():
            print(f"  • {name}")
            print(f"    {url}")

        # NewsAPI
        print("\n🌐 NEWSAPI SOURCES")
        print("-"*40)
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

        print("\n" + "="*60)
        print("Usage: fetch rss | fetch newsapi | fetch both")
        print("="*60)

    def show_tags(self, article_num=None):
        """
        Display tags (keywords and entities).

        If article_num is provided, show tags for that article.
        Otherwise, show trending keywords and entities across all articles.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Show tags for specific article
        if article_num is not None:
            if 1 <= article_num <= len(self.articles):
                article = self.articles[article_num - 1]
                print("\n" + "="*60)
                print(f"TAGS FOR ARTICLE {article_num}")
                print("="*60)
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
                print(f"\nInvalid article number. Choose between 1 and {len(self.articles)}")
            return

        # Show trending keywords and entities across all articles
        print("\n" + "="*60)
        print("TRENDING KEYWORDS & ENTITIES")
        print("="*60)

        # Keywords
        all_keywords = get_all_keywords(self.articles)
        print("\n🏷️  TOP KEYWORDS")
        print("-"*40)
        if all_keywords:
            for keyword, count in list(all_keywords.items())[:10]:
                bar = "█" * count
                print(f"  {keyword}: {bar} ({count})")
        else:
            print("  No keywords extracted")

        # Entities
        all_entities = get_all_entities(self.articles)

        print("\n👤 PEOPLE MENTIONED")
        print("-"*40)
        if all_entities["people"]:
            for name, count in list(all_entities["people"].items())[:5]:
                print(f"  {name}: {count} mention(s)")
        else:
            print("  No people mentioned")

        print("\n🏢 ORGANIZATIONS")
        print("-"*40)
        if all_entities["organizations"]:
            for name, count in list(all_entities["organizations"].items())[:5]:
                print(f"  {name}: {count} mention(s)")
        else:
            print("  No organizations mentioned")

        print("\n📍 LOCATIONS")
        print("-"*40)
        if all_entities["locations"]:
            for name, count in list(all_entities["locations"].items())[:5]:
                print(f"  {name}: {count} mention(s)")
        else:
            print("  No locations mentioned")

        print("\n" + "-"*60)
        print("Tip: Use 'tags <number>' to see tags for a specific article")

    def search_articles(self, query: str):
        """
        Search articles by keyword.

        This searches through:
        - Title
        - Summary / Description
        - Keywords
        - People, Organizations, Locations

        PARAMETERS:
        -----------
        query : str
            The search term (case-insensitive)

        HOW IT WORKS:
        -------------
        This is simple string matching - we check if the query
        appears anywhere in the article's text or tags.

        For more advanced search, you could:
        - Use fuzzy matching (fuzzywuzzy library)
        - Use embeddings and semantic search (LangChain)
        - Use a search engine (Elasticsearch)

        But for our purposes, simple matching works great!
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        if not query or len(query.strip()) < 2:
            print("\nPlease enter a search term (at least 2 characters).")
            return

        query = query.lower().strip()
        matches = []

        for article in self.articles:
            # Build searchable text from all article fields
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

            # Combine all parts into one searchable string
            searchable_text = " ".join(searchable_parts).lower()

            # Check if query appears in the text
            if query in searchable_text:
                matches.append(article)

        # Display results
        print("\n" + "="*60)
        print(f"SEARCH RESULTS FOR: '{query}'")
        print("="*60)

        if not matches:
            print("\nNo articles found matching your search.")
            print("Try a different keyword or use 'show' to see all articles.")
            return

        print(f"\nFound {len(matches)} article(s):\n")

        for i, article in enumerate(matches, 1):
            # Find the original index for reference
            original_idx = self.articles.index(article) + 1

            # Highlight where the match was found
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

        print("-"*60)
        print("Tip: Use 'show <number>' to see full article details")

    def save_articles(self, format_type: str = "json"):
        """
        Save articles to a file.

        PARAMETERS:
        -----------
        format_type : str
            Output format: "json" or "md" (markdown)

        FILE NAMING:
        ------------
        Files are saved with a timestamp:
        - output/news_2026-01-18_143052.json
        - output/news_2026-01-18_143052.md

        This ensures you don't overwrite previous saves.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Create output directory if it doesn't exist
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}/")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        if format_type.lower() == "json":
            self._save_as_json(output_dir, timestamp)
        elif format_type.lower() in ["md", "markdown"]:
            self._save_as_markdown(output_dir, timestamp)
        else:
            print(f"Unknown format: {format_type}")
            print("Valid options: json, md")

    def _save_as_json(self, output_dir: str, timestamp: str):
        """
        Save articles as JSON file.

        JSON (JavaScript Object Notation) is a standard format
        for storing structured data. It's great for:
        - Loading back into Python later
        - Sharing with other programs
        - APIs and web applications
        """
        filename = f"{output_dir}/news_{timestamp}.json"

        # Prepare data for JSON
        # We include metadata about when and how many articles
        data = {
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "total_articles": len(self.articles),
                "categories": list(group_by_category(self.articles).keys())
            },
            "articles": self.articles
        }

        # Write to file
        # indent=2 makes it human-readable (pretty-printed)
        # ensure_ascii=False allows non-English characters
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("\n" + "="*60)
        print("SAVED AS JSON")
        print("="*60)
        print(f"\n  File: {filename}")
        print(f"  Articles: {len(self.articles)}")
        print(f"  Size: {os.path.getsize(filename):,} bytes")
        print("\nYou can load this file in Python with:")
        print(f"  import json")
        print(f"  with open('{filename}') as f:")
        print(f"      data = json.load(f)")

    def _save_as_markdown(self, output_dir: str, timestamp: str):
        """
        Save articles as Markdown file.

        Markdown is a simple text format that's:
        - Human-readable in any text editor
        - Renders nicely on GitHub, Notion, etc.
        - Great for documentation and notes
        """
        filename = f"{output_dir}/news_{timestamp}.md"

        # Build markdown content
        lines = []

        # Header
        date_str = datetime.now().strftime("%B %d, %Y at %H:%M")
        lines.append(f"# News Summary")
        lines.append(f"")
        lines.append(f"*Generated on {date_str}*")
        lines.append(f"")
        lines.append(f"**Total Articles:** {len(self.articles)}")
        lines.append(f"")

        # Group by category
        grouped = group_by_category(self.articles)

        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        for category in grouped.keys():
            # Create anchor link (lowercase, spaces to hyphens)
            anchor = category.lower().replace(" ", "-")
            lines.append(f"- [{category}](#{anchor}) ({len(grouped[category])} articles)")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Articles by category
        for category, articles in grouped.items():
            lines.append(f"## {category}")
            lines.append("")

            for i, article in enumerate(articles, 1):
                # Article title as heading
                lines.append(f"### {i}. {article['title']}")
                lines.append("")

                # Metadata
                lines.append(f"**Source:** {article['source']}")
                if article.get('published'):
                    lines.append(f"  ")
                    lines.append(f"**Published:** {article['published']}")
                lines.append("")

                # Summary
                lines.append(f"**Summary:**")
                lines.append(f"")
                lines.append(f"> {article.get('summary', 'No summary available')}")
                lines.append("")

                # Tags
                keywords = article.get("keywords", [])
                if keywords:
                    tags_str = " ".join([f"`{kw}`" for kw in keywords])
                    lines.append(f"**Keywords:** {tags_str}")
                    lines.append("")

                # Entities
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

                # Link
                if article.get('url'):
                    lines.append(f"[Read full article]({article['url']})")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Footer
        lines.append("*Generated by News Summarizer Agent*")

        # Write to file
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print("\n" + "="*60)
        print("SAVED AS MARKDOWN")
        print("="*60)
        print(f"\n  File: {filename}")
        print(f"  Articles: {len(self.articles)}")
        print(f"  Size: {os.path.getsize(filename):,} bytes")
        print("\nYou can open this file in:")
        print("  - Any text editor")
        print("  - VS Code (with preview)")
        print("  - GitHub (renders automatically)")
        print("  - Notion, Obsidian, etc.")

    def _calculate_article_stats(self, article: dict) -> dict:
        """
        Calculate statistics for a single article.

        READING TIME CALCULATION:
        -------------------------
        Average adult reading speed is about 200-250 words per minute.
        We use 200 wpm for a comfortable reading pace.

        Formula: reading_time = word_count / 200

        PARAMETERS:
        -----------
        article : dict
            Article with 'summary' or 'description'

        RETURNS:
        --------
        dict with keys:
            - word_count: Number of words
            - char_count: Number of characters
            - reading_time_seconds: Estimated reading time in seconds
            - reading_time_display: Human-readable reading time
        """
        # Get the text content
        text = article.get("summary", article.get("description", ""))

        # Word count: split by whitespace
        words = text.split()
        word_count = len(words)

        # Character count (excluding spaces)
        char_count = len(text.replace(" ", ""))

        # Reading time calculation
        # Average reading speed: 200 words per minute
        words_per_minute = 200
        reading_time_minutes = word_count / words_per_minute
        reading_time_seconds = int(reading_time_minutes * 60)

        # Format reading time for display
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
            "reading_time_display": reading_time_display
        }

    def show_stats(self, article_num=None):
        """
        Display article statistics.

        If article_num is provided, show stats for that article.
        Otherwise, show overall statistics for all articles.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Show stats for specific article
        if article_num is not None:
            if 1 <= article_num <= len(self.articles):
                article = self.articles[article_num - 1]
                stats = self._calculate_article_stats(article)

                print("\n" + "="*60)
                print(f"STATISTICS FOR ARTICLE {article_num}")
                print("="*60)
                print(f"\n📰 {article['title'][:50]}...")
                print(f"\n📊 Summary Statistics:")
                print(f"   Words:        {stats['word_count']}")
                print(f"   Characters:   {stats['char_count']}")
                print(f"   Reading time: {stats['reading_time_display']}")
                print(f"\n📁 Category: {article.get('category', 'Uncategorized')}")
                print(f"📡 Source:   {article.get('source', 'Unknown')}")

                # Show keyword count
                keywords = article.get("keywords", [])
                entities = (
                    article.get("people", []) +
                    article.get("organizations", []) +
                    article.get("locations", [])
                )
                print(f"\n🏷️  Keywords: {len(keywords)}")
                print(f"👤 Entities: {len(entities)}")
            else:
                print(f"\nInvalid article number. Choose between 1 and {len(self.articles)}")
            return

        # Show overall statistics
        print("\n" + "="*60)
        print("OVERALL STATISTICS")
        print("="*60)

        # Calculate totals
        total_words = 0
        total_chars = 0
        total_reading_seconds = 0
        total_keywords = 0
        total_entities = 0

        for article in self.articles:
            stats = self._calculate_article_stats(article)
            total_words += stats["word_count"]
            total_chars += stats["char_count"]
            total_reading_seconds += stats["reading_time_seconds"]
            total_keywords += len(article.get("keywords", []))
            total_entities += len(article.get("people", []))
            total_entities += len(article.get("organizations", []))
            total_entities += len(article.get("locations", []))

        # Format total reading time
        total_minutes = total_reading_seconds // 60
        remaining_seconds = total_reading_seconds % 60

        print(f"\n📰 ARTICLES")
        print(f"   Total articles: {len(self.articles)}")

        # Category breakdown
        grouped = group_by_category(self.articles)
        print(f"   Categories:     {len(grouped)}")
        for cat, arts in grouped.items():
            pct = (len(arts) / len(self.articles)) * 100
            bar = "█" * int(pct / 5)  # Simple bar chart
            print(f"     {cat}: {len(arts)} ({pct:.0f}%) {bar}")

        print(f"\n📊 CONTENT")
        print(f"   Total words:      {total_words:,}")
        print(f"   Total characters: {total_chars:,}")
        print(f"   Avg words/article: {total_words // len(self.articles)}")

        print(f"\n⏱️  READING TIME")
        print(f"   Total: {total_minutes} min {remaining_seconds} sec")
        print(f"   Average per article: {total_reading_seconds // len(self.articles)} sec")

        print(f"\n🏷️  TAGS")
        print(f"   Total keywords: {total_keywords}")
        print(f"   Total entities: {total_entities}")
        print(f"   Avg keywords/article: {total_keywords / len(self.articles):.1f}")

        # Source breakdown
        sources = {}
        for article in self.articles:
            source = article.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1

        print(f"\n📡 SOURCES")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"   {source}: {count} article(s)")

        print("\n" + "-"*60)
        print("Tip: Use 'stats <number>' for individual article stats")

    def _parse_article_date(self, article: dict) -> datetime | None:
        """
        Parse the publication date from an article.

        Articles have dates in various formats:
        - "January 18, 2026 at 14:30"
        - "2026-01-18T14:30:00Z"
        - "Mon, 18 Jan 2026 14:30:00 GMT"

        The dateutil.parser is smart enough to handle most formats.

        RETURNS:
        --------
        datetime object or None if parsing fails
        """
        date_str = article.get("published", "")

        if not date_str:
            return None

        try:
            # dateutil.parser.parse() handles many date formats
            return date_parser.parse(date_str)
        except (ValueError, TypeError):
            return None

    def filter_by_date(self, date_range: str):
        """
        Filter articles by date range.

        PARAMETERS:
        -----------
        date_range : str
            One of: "today", "yesterday", "week", "month"

        DATE FILTERING LOGIC:
        ---------------------
        We calculate a cutoff datetime and compare each article's
        publication date against it.

        - today: cutoff = midnight today
        - yesterday: cutoff = midnight yesterday
        - week: cutoff = 7 days ago
        - month: cutoff = 30 days ago
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Get current time
        now = datetime.now()
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Calculate cutoff based on date_range
        date_range = date_range.lower().strip()

        if date_range == "today":
            cutoff = today_midnight
            range_description = "today"
        elif date_range == "yesterday":
            cutoff = today_midnight - timedelta(days=1)
            end_cutoff = today_midnight  # Yesterday only, not today
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

        # Filter articles
        matches = []
        no_date_count = 0

        for article in self.articles:
            article_date = self._parse_article_date(article)

            if article_date is None:
                no_date_count += 1
                continue

            # Special handling for "yesterday" (between two dates)
            if date_range == "yesterday":
                if cutoff <= article_date < end_cutoff:
                    matches.append(article)
            else:
                # For other ranges, just check if after cutoff
                if article_date >= cutoff:
                    matches.append(article)

        # Display results
        print("\n" + "="*60)
        print(f"ARTICLES FROM {range_description.upper()}")
        print("="*60)

        if not matches:
            print(f"\nNo articles found from {range_description}.")
            if no_date_count > 0:
                print(f"({no_date_count} articles have no date information)")
            return

        print(f"\nFound {len(matches)} article(s) from {range_description}:\n")

        for article in matches:
            # Find original index
            original_idx = self.articles.index(article) + 1
            category = article.get('category', '?')
            title = article['title'][:45]
            published = article.get('published', 'Unknown date')

            print(f"  [{original_idx}] [{category}] {title}...")
            print(f"      📅 {published}")
            print(f"      📡 {article['source']}")
            print()

        if no_date_count > 0:
            print(f"Note: {no_date_count} article(s) excluded (no date info)")

        print("-"*60)
        print("Tip: Use 'show <number>' for full article details")

    def clear_history(self):
        """Clear Q&A conversation history."""
        if self.qa_chain:
            self.qa_chain.clear_history()
            print("\nConversation history cleared.")
        else:
            print("\nNo conversation history to clear.")

    # =====================================================
    # ADVANCED FEATURE METHODS (NEW!)
    # =====================================================
    #
    # These methods implement the advanced features we built:
    # - Sentiment analysis
    # - Trending topics detection
    # - Similar article discovery
    # - Multi-source comparison
    #
    # =====================================================

    def show_sentiment(self, sentiment_filter: str = None):
        """
        Show sentiment analysis for articles.

        If sentiment_filter is provided, show only articles with that sentiment.
        Otherwise, show overall sentiment breakdown.

        PARAMETERS:
        -----------
        sentiment_filter : str, optional
            Filter by: "positive", "negative", or "neutral"

        LANGCHAIN CONNECTION:
        ---------------------
        This uses the sentiment.py module which:
        1. Sends each article to Claude
        2. Claude classifies as positive/negative/neutral
        3. Returns structured sentiment data
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Filter by specific sentiment
        if sentiment_filter:
            sentiment_filter = sentiment_filter.lower()
            if sentiment_filter not in ["positive", "negative", "neutral"]:
                print(f"\nInvalid sentiment: {sentiment_filter}")
                print("Valid options: positive, negative, neutral")
                return

            filtered = filter_by_sentiment(self.articles, sentiment_filter)

            emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}[sentiment_filter]
            print("\n" + "="*60)
            print(f"{emoji} {sentiment_filter.upper()} ARTICLES")
            print("="*60)

            if not filtered:
                print(f"\nNo {sentiment_filter} articles found.")
                return

            print(f"\nFound {len(filtered)} {sentiment_filter} article(s):\n")

            for article in filtered:
                # Find original index
                original_idx = self.articles.index(article) + 1
                title = article['title'][:45]
                reason = article.get('sentiment_reason', '')[:50]

                print(f"  [{original_idx}] {title}...")
                print(f"      {reason}")
                print()

            return

        # Show overall sentiment breakdown
        display_sentiment_summary(self.articles)

        print("\n" + "-"*60)
        print("Tip: Use 'sentiment positive' to see only positive news")
        print("     Use 'sentiment negative' to see concerning news")

    def show_trending(self, use_llm: bool = True):
        """
        Show trending topics across all articles.

        PARAMETERS:
        -----------
        use_llm : bool
            If True, use Claude for smart trend analysis
            If False, use fast keyword counting only

        LANGCHAIN CONNECTION:
        ---------------------
        When use_llm=True, this:
        1. Sends ALL articles to Claude at once
        2. Claude identifies themes that span multiple articles
        3. Returns grouped trends with explanations

        This demonstrates MULTI-DOCUMENT REASONING - one of
        the powerful patterns in LangChain.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        # Use cached results if available
        if self.trends_cache and self.trends_cache.get("use_llm") == use_llm:
            print("\n(Using cached trend analysis)")
            display_trends(self.trends_cache["data"])
            return

        # Run trend detection
        trends = detect_trends(self.articles, use_llm=use_llm)

        # Cache results
        self.trends_cache = {
            "use_llm": use_llm,
            "data": trends
        }

        # Display
        display_trends(trends)

        if use_llm:
            print("\n" + "-"*60)
            print("Tip: Use 'trending fast' for quick analysis without AI")

    def show_similar(self, article_num: int):
        """
        Find articles similar to a specific article.

        PARAMETERS:
        -----------
        article_num : int
            The article number to find similar ones for (1-indexed)

        HOW IT WORKS:
        -------------
        1. Takes the target article
        2. Compares it against all other articles
        3. Uses keyword overlap and entity matching
        4. Returns articles above a similarity threshold

        This uses JACCARD SIMILARITY to measure overlap.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        if not (1 <= article_num <= len(self.articles)):
            print(f"\nInvalid article number. Choose between 1 and {len(self.articles)}")
            return

        target = self.articles[article_num - 1]

        print(f"\n🔍 Finding articles similar to #{article_num}...")

        # Find similar articles
        similar = find_similar_articles(
            target_article=target,
            all_articles=self.articles,
            threshold=0.15,  # Lower threshold to find more matches
            max_results=5
        )

        # Display results
        display_similar_articles(target, similar)

        if similar:
            print("\n" + "-"*60)
            print("Tip: Use 'show <number>' to read a similar article")

    def show_related(self):
        """
        Show all relationships between articles.

        This analyzes ALL article pairs and shows:
        1. Statistical relationships (keyword overlap)
        2. LLM-detected relationships (semantic understanding)

        LANGCHAIN CONNECTION:
        ---------------------
        The LLM analysis sends all articles to Claude and asks
        it to identify which articles are related and WHY.
        This captures relationships that keyword matching misses.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        if len(self.articles) < 2:
            print("\nNeed at least 2 articles to find relationships.")
            return

        # Use cached results if available
        if self.relationships_cache:
            print("\n(Using cached relationship analysis)")
            display_all_relationships(self.relationships_cache)
            return

        print("\n🔍 Analyzing article relationships...")

        # Run relationship analysis
        analysis = analyze_article_relationships(self.articles, use_llm=True)

        # Cache results
        self.relationships_cache = analysis

        # Display
        display_all_relationships(analysis)

    def show_comparison(self):
        """
        Compare how different sources cover the same story.

        This is the most advanced feature:
        1. Finds articles covering the SAME event
        2. Compares how each source frames the story
        3. Identifies differences in tone, facts, and bias

        LANGCHAIN CONNECTION:
        ---------------------
        Uses Claude for deep multi-document comparison:
        - Identifies common facts vs unique details
        - Detects framing differences
        - Spots potential bias

        This demonstrates MULTI-SOURCE COMPARISON - analyzing
        how different perspectives describe the same event.
        """
        if not self.articles:
            print("\nNo articles loaded. Use 'fetch' first.")
            return

        if len(self.articles) < 2:
            print("\nNeed at least 2 articles to compare sources.")
            return

        # Check if we have articles from different sources
        sources = set(art.get("source", "") for art in self.articles)
        if len(sources) < 2:
            print("\nAll articles are from the same source.")
            print("Use 'fetch both' to get articles from multiple sources.")
            return

        # Use cached results if available
        if self.comparisons_cache:
            print("\n(Using cached comparison analysis)")
            display_all_comparisons(self.comparisons_cache)
            return

        print("\n🔍 Looking for same stories covered by multiple sources...")

        # First, show what story groups were found
        story_groups = find_same_story_articles(self.articles)

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

        # Run comparison
        comparisons = compare_all_stories(self.articles)

        # Cache results
        self.comparisons_cache = comparisons

        # Display
        display_all_comparisons(comparisons)

        print("\n" + "-"*60)
        print("Tip: This analysis shows how different outlets")
        print("     frame the same story - helpful for spotting bias!")

    def process_command(self, user_input: str):
        """
        Process a user command.

        This is the command parser that interprets user input
        and calls the appropriate method.
        """
        # Clean and parse input
        parts = user_input.strip().split(maxsplit=1)
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None

        # Route to appropriate handler
        if command in ['quit', 'exit', 'q']:
            print("\nGoodbye! Stay informed!")
            self.is_running = False

        elif command == 'help':
            self.display_help()

        elif command == 'fetch':
            # Parse optional source argument: fetch [rss|newsapi|both]
            source = args.lower() if args else "rss"
            if source not in ["rss", "newsapi", "both"]:
                print(f"Unknown source: {source}")
                print("Valid options: rss, newsapi, both")
                return
            self.fetch_news(source=source)

        elif command == 'show':
            if args:
                try:
                    num = int(args)
                    self.show_articles(num)
                except ValueError:
                    print("Usage: show <number>")
                    print("Example: show 3")
            else:
                self.show_articles()

        elif command == 'category':
            self.show_category(args)

        elif command == 'tags':
            if args:
                try:
                    num = int(args)
                    self.show_tags(num)
                except ValueError:
                    print("Usage: tags <number>")
                    print("Example: tags 3")
            else:
                self.show_tags()

        elif command == 'search':
            if args:
                self.search_articles(args)
            else:
                print("Usage: search <keyword>")
                print("Example: search technology")
                print("Example: search climate change")

        elif command == 'save':
            # Default to JSON if no format specified
            format_type = args.lower() if args else "json"
            self.save_articles(format_type)

        elif command == 'stats':
            if args:
                try:
                    num = int(args)
                    self.show_stats(num)
                except ValueError:
                    print("Usage: stats <number>")
                    print("Example: stats 3")
            else:
                self.show_stats()

        elif command == 'filter':
            if args:
                self.filter_by_date(args)
            else:
                print("Usage: filter <date_range>")
                print("Options: today, yesterday, week, month")
                print("Example: filter today")
                print("Example: filter week")

        elif command == 'ask':
            if args:
                self.ask_question(args)
            else:
                print("Usage: ask <your question>")
                print("Example: ask What's the latest technology news?")

        elif command == 'sources':
            self.show_sources()

        elif command == 'clear':
            self.clear_history()

        # -------------------------------------------------
        # ADVANCED FEATURE COMMANDS (NEW!)
        # -------------------------------------------------

        elif command == 'sentiment':
            # sentiment OR sentiment <type>
            self.show_sentiment(args)

        elif command == 'trending':
            # trending OR trending fast
            if args and args.lower() == "fast":
                self.show_trending(use_llm=False)
            else:
                self.show_trending(use_llm=True)

        elif command == 'similar':
            # similar <number>
            if args:
                try:
                    num = int(args)
                    self.show_similar(num)
                except ValueError:
                    print("Usage: similar <number>")
                    print("Example: similar 3")
            else:
                print("Usage: similar <number>")
                print("Example: similar 3")
                print("\nThis finds articles similar to the specified article.")

        elif command == 'related':
            self.show_related()

        elif command == 'compare':
            self.show_comparison()

        else:
            # If command not recognized, treat as a question
            if self.articles:
                print(f"\nUnknown command '{command}'. Treating as a question...")
                self.ask_question(user_input)
            else:
                print(f"\nUnknown command: '{command}'")
                print("Type 'help' to see available commands.")

    def run(self):
        """
        Main loop - runs the interactive CLI.

        This is the entry point that:
        1. Shows welcome message
        2. Waits for user input
        3. Processes commands
        4. Repeats until user quits
        """
        self.display_welcome()

        while self.is_running:
            try:
                # Get user input
                user_input = input("\n> ").strip()

                if user_input:
                    self.process_command(user_input)

            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                print("\n\nInterrupted. Type 'quit' to exit.")

            except Exception as e:
                print(f"\nError: {e}")
                print("Something went wrong. Please try again.")


# =====================================================
# ENTRY POINT
# =====================================================

if __name__ == "__main__":
    agent = NewsSummarizerAgent()
    agent.run()
