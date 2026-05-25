"""Display helpers: headers, dividers, and static welcome/help screens."""

WIDTH = 60


def hr(char: str = "-", *, lead_newline: bool = False, width: int = WIDTH) -> None:
    """Print a horizontal rule of `char` repeated `width` times."""
    prefix = "\n" if lead_newline else ""
    print(prefix + char * width)


def header(title: str, char: str = "=", *, width: int = WIDTH) -> None:
    """Print a section header: top rule (with leading newline), title, bottom rule."""
    print("\n" + char * width)
    print(title)
    print(char * width)


def display_welcome() -> None:
    """Show welcome message and available commands."""
    header("       WELCOME TO THE NEWS SUMMARIZER AGENT")
    print("""
This agent helps you:
  - Fetch the latest news from multiple sources
  - Get AI-powered summaries of articles
  - Categorize news by topic
  - Ask follow-up questions about the news

Type 'help' to see available commands.
Type 'fetch' to get started!
        """)
    hr("=")


def display_help() -> None:
    """Show available commands."""
    header("AVAILABLE COMMANDS", char="-")
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
    hr("-")
