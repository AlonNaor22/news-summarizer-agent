# News Summarizer Agent

An AI-powered command-line agent that fetches the latest news articles from multiple sources, summarizes them using Claude AI, categorizes them by topic, extracts keywords and entities, and allows you to ask follow-up questions about current events.

## Features

### Core Features
- **News Fetching**: Fetch articles from RSS feeds (BBC, NPR, Reuters) or NewsAPI
- **AI Summarization**: Uses Claude AI to generate concise summaries of each article
- **Topic Categorization**: Classifies articles into categories (Politics, Technology, Business, etc.)
- **Interactive Q&A**: Ask questions about the news with conversation memory for follow-ups

### Enhanced Features
- **Multiple News Sources**: Support for both RSS feeds and NewsAPI
- **Keyword & Entity Extraction**: Automatically extracts keywords, people, organizations, and locations
- **Search**: Search articles by keyword across titles, summaries, and tags
- **Export**: Save articles as JSON or Markdown files
- **Statistics**: View word counts, reading times, and category breakdowns
- **Date Filtering**: Filter articles by today, yesterday, week, or month

## Demo

```
> fetch

FETCHING NEWS
============================================================
Step 1/4: Fetching articles from RSS feeds...
Step 2/4: Summarizing articles with Claude...
Step 3/4: Categorizing articles...
Step 4/4: Extracting keywords and entities...

FETCH COMPLETE!
  Total articles: 15
  Categories: 5
    - Technology: 4 articles
    - World News: 3 articles
    - Business: 3 articles
  Top keywords: artificial intelligence, climate, stocks

> search technology

Found 4 article(s):
  [2] [Technology] Apple announces new AI features...
      Match in: title, keywords

> tags

TRENDING KEYWORDS & ENTITIES
============================================================
TOP KEYWORDS
  artificial intelligence: 3
  climate change: 2

PEOPLE MENTIONED
  Tim Cook: 2
  Elon Musk: 1

> save md

SAVED AS MARKDOWN
  File: output/news_2026-01-18_143052.md
```

## Installation

### Prerequisites

- Python 3.9 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) A NewsAPI key ([get one here](https://newsapi.org/))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/news-summarizer-agent.git
   cd news-summarizer-agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API key**
   ```bash
   # Copy the example env file
   cp .env.example .env

   # Edit .env and add your API keys
   # ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
   # NEWS_API_KEY=xxxxx (optional)
   ```

5. **Run the agent**
   ```bash
   python main.py
   ```

## Usage

### Available Commands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch news from RSS feeds (default) |
| `fetch newsapi` | Fetch from NewsAPI |
| `fetch both` | Fetch from RSS + NewsAPI |
| `show` | Display all fetched articles |
| `show <number>` | Show specific article in detail |
| `category` | List all categories |
| `category <name>` | Show articles in a specific category |
| `tags` | Show trending keywords and entities |
| `tags <number>` | Show tags for a specific article |
| `search <keyword>` | Search articles by keyword |
| `save` | Save articles as JSON (default) |
| `save md` | Save articles as Markdown |
| `stats` | Show overall statistics |
| `stats <number>` | Show stats for a specific article |
| `filter today` | Show articles from today |
| `filter week` | Show articles from last 7 days |
| `ask <question>` | Ask a question about the articles |
| `sources` | List available news sources |
| `clear` | Clear conversation history |
| `help` | Show available commands |
| `quit` | Exit the program |

### Example Session

```bash
# Start the agent
python main.py

# Fetch the latest news
> fetch

# Fetch from NewsAPI instead
> fetch newsapi

# View all articles
> show

# View a specific article (includes tags and reading time)
> show 3

# Filter by category
> category Technology

# Search for articles
> search climate

# View trending keywords and entities
> tags

# View statistics
> stats

# Filter by date
> filter today

# Save to file
> save md

# Ask questions (supports follow-ups!)
> ask What are the main headlines today?
> ask Tell me more about the first one

# Exit
> quit
```

## Project Structure

```
news-summarizer-agent/
├── main.py               # CLI entry point
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env.example          # API key template
├── .gitignore            # Git ignore rules
├── README.md             # This file
│
├── src/
│   ├── __init__.py       # Package init
│   ├── news_fetcher.py   # RSS feed + NewsAPI fetching
│   ├── summarizer.py     # Claude AI summarization
│   ├── categorizer.py    # Topic classification
│   ├── tagger.py         # Keyword & entity extraction
│   └── qa_chain.py       # Q&A with memory
│
└── output/               # Saved summaries (generated)
    ├── news_2026-01-18.json
    └── news_2026-01-18.md
```

## How It Works

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   RSS Feeds     │     │   Summarizer    │     │  Categorizer    │
│   + NewsAPI     │ --> │  (Claude AI)    │ --> │  (Claude AI)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        v
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    User CLI     │ <-- │   Q&A Chain     │ <-- │     Tagger      │
│    (main.py)    │     │  (with memory)  │     │  (Claude AI)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Technologies Used

- **[LangChain](https://python.langchain.com/)** - AI application framework
- **[Claude AI](https://www.anthropic.com/claude)** - Large language model for summarization and Q&A
- **[feedparser](https://feedparser.readthedocs.io/)** - RSS feed parsing
- **[NewsAPI](https://newsapi.org/)** - News aggregator API (optional)
- **Python 3.9+** - Programming language

### Key LangChain Concepts

This project demonstrates several LangChain patterns:

1. **Prompt Templates** - Structured prompts with variables
2. **Chains (LCEL)** - Connecting prompt → LLM → parser using `|` operator
3. **Output Parsing** - Cleaning and validating AI responses
4. **Conversation Memory** - Maintaining chat history with `MessagesPlaceholder`
5. **Structured Output** - Extracting keywords and entities in a specific format

## Configuration

Edit `config.py` to customize:

```python
# Change the Claude model
MODEL_NAME = "claude-sonnet-4-5-20250929"  # or "claude-haiku-4-5-20251001"

# Adjust creativity (0 = focused, 1 = creative)
TEMPERATURE = 0.3

# Add more RSS feeds
RSS_FEEDS = {
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "Your Source": "https://example.com/rss",
}

# NewsAPI sources
NEWSAPI_SOURCES = ["bbc-news", "cnn", "techcrunch", "reuters"]

# Modify categories
CATEGORIES = ["Politics", "Business", "Technology", ...]
```

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
Make sure you've created a `.env` file with your API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### "No articles found"
- Check your internet connection
- Some RSS feeds may be temporarily unavailable
- Try running `fetch` again or use `fetch newsapi`

### Rate limiting
If you hit API rate limits, wait a few moments and try again. Consider using `claude-haiku-4-5-20251001` for faster, cheaper requests.

### NewsAPI not working
- Make sure you have a valid NEWS_API_KEY in your `.env` file
- Free tier is limited to 100 requests/day
- Use `sources` command to check if API key is configured

## Contributing

Contributions are welcome! Feel free to:
- Add new RSS feed sources
- Improve summarization prompts
- Add new features (email digest, web UI, etc.)
- Fix bugs and improve documentation

## License

MIT License - feel free to use this project for learning and building your own applications.

## Acknowledgments

- Built with [LangChain](https://langchain.com/) and [Claude AI](https://anthropic.com/)
- News content from BBC, NPR, Reuters RSS feeds and NewsAPI
