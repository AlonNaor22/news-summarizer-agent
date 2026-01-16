# =====================================================
# NEWS SUMMARIZER AGENT - MAIN CLI
# =====================================================
#
# This is the main entry point for the application.
# It ties together all our modules:
#   - news_fetcher.py (Phase 2)
#   - summarizer.py (Phase 3)
#   - categorizer.py (Phase 4)
#   - qa_chain.py (Phase 5)
#
# Run with: python main.py
#
# =====================================================

from src.news_fetcher import fetch_all_news, fetch_from_rss
from src.summarizer import summarize_articles
from src.categorizer import categorize_articles, group_by_category
from src.qa_chain import NewsQAChain
from config import RSS_FEEDS, CATEGORIES


class NewsSummarizerAgent:
    """
    The main News Summarizer Agent.

    This class orchestrates the entire workflow:
    1. Fetch news from RSS feeds
    2. Summarize articles with Claude
    3. Categorize articles by topic
    4. Answer questions about the news

    USAGE:
    ------
    >>> agent = NewsSummarizerAgent()
    >>> agent.run()  # Starts the interactive CLI
    """

    def __init__(self):
        """Initialize the agent with empty state."""
        self.articles = []          # Fetched and processed articles
        self.qa_chain = None        # Q&A system (created after fetching)
        self.is_running = True      # Controls main loop

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
  fetch          Fetch latest news from RSS feeds

  show           Show all fetched articles
  show <number>  Show specific article in detail

  category       List all categories
  category <name>  Show articles in a specific category

  ask <question> Ask a question about the articles
                 (supports follow-up questions!)

  sources        List available news sources

  clear          Clear conversation history

  help           Show this help message

  quit / exit    Exit the program
""")
        print("-"*60)

    def fetch_news(self):
        """
        Fetch, summarize, and categorize news.

        This is the main pipeline that:
        1. Fetches articles from RSS feeds
        2. Summarizes each article with Claude
        3. Categorizes articles by topic
        4. Sets up Q&A system
        """
        print("\n" + "="*60)
        print("FETCHING NEWS")
        print("="*60)

        # Step 1: Fetch from RSS feeds
        print("\nStep 1/3: Fetching articles from RSS feeds...")
        raw_articles = fetch_all_news(max_per_source=3)

        if not raw_articles:
            print("No articles found. Please check your internet connection.")
            return

        # Step 2: Summarize articles
        print("\nStep 2/3: Summarizing articles with Claude...")
        summarized = summarize_articles(raw_articles)

        # Step 3: Categorize articles
        print("\nStep 3/3: Categorizing articles...")
        self.articles = categorize_articles(summarized)

        # Step 4: Set up Q&A system
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

        print("\nType 'show' to see articles or 'ask <question>' to ask about them.")

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
                print("\n" + "="*60)
                print(f"ARTICLE {article_num}")
                print("="*60)
                print(f"\nTitle:    {article['title']}")
                print(f"Source:   {article['source']}")
                print(f"Category: {article.get('category', 'Uncategorized')}")
                print(f"Date:     {article.get('published', 'Unknown')}")
                print(f"\nSummary:")
                print(f"  {article.get('summary', 'No summary available')}")
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
        """Display available RSS feed sources."""
        print("\n" + "="*60)
        print("AVAILABLE NEWS SOURCES")
        print("="*60)
        for name, url in RSS_FEEDS.items():
            print(f"\n  {name}")
            print(f"    {url}")
        print("\n" + "="*60)

    def clear_history(self):
        """Clear Q&A conversation history."""
        if self.qa_chain:
            self.qa_chain.clear_history()
            print("\nConversation history cleared.")
        else:
            print("\nNo conversation history to clear.")

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
            self.fetch_news()

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
