# News Summarizer Agent

An AI-powered command-line agent that fetches the latest news articles from multiple sources, summarizes them using Claude AI, categorizes them by topic, analyzes sentiment, detects trends, and allows you to ask follow-up questions about current events.

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

### Advanced Features (NEW!)
- **Sentiment Analysis**: Analyze the emotional tone of articles (positive/negative/neutral)
- **Trending Topics**: Detect hot topics across all articles using AI
- **Similar Articles**: Find related articles using keyword and entity matching
- **Multi-Source Comparison**: Compare how different news sources cover the same story

## Demo

```
> fetch

FETCHING NEWS
============================================================
Step 1/5: Fetching articles from RSS feeds...
Step 2/5: Summarizing articles with Claude...
Step 3/5: Categorizing articles...
Step 4/5: Extracting keywords and entities...
Step 5/5: Analyzing sentiment...

FETCH COMPLETE!
  Total articles: 15
  Categories: 5
    - Technology: 4 articles
    - World News: 3 articles
    - Business: 3 articles
  Top keywords: artificial intelligence, climate, stocks
  Sentiment: 😊 5 positive, 😟 3 negative, 😐 7 neutral

> sentiment

SENTIMENT SUMMARY
============================================================
  😊 POSITIVE
     █████ 5 articles (33.3%)

  😟 NEGATIVE
     ███ 3 articles (20.0%)

  😐 NEUTRAL
     ███████ 7 articles (46.7%)

> trending

📈 TRENDING TOPICS
============================================================
🔥 MAJOR TRENDS (AI Analysis)

  1. AI Industry Growth 🔴
     Strength: high (5 articles)
     Multiple tech companies announcing AI features
     Keywords: artificial intelligence, technology, smartphones

  2. Climate Policy 🟡
     Strength: medium (3 articles)
     International climate discussions and agreements
     Keywords: climate change, environment, policy

> similar 1

📰 ARTICLES SIMILAR TO:
   "Apple Unveils New AI-Powered iPhone Features..."
============================================================
  1. Google Responds with AI Chatbot Update...
     Similarity: ████████ 65%
     Shared keywords: artificial intelligence, technology

  2. Tech Stocks Surge on AI Announcements...
     Similarity: █████ 45%
     Shared keywords: technology, artificial intelligence

> compare

📰 MULTI-SOURCE COMPARISON
============================================================
📋 STORY: Tech Giants Announce AI Partnership...
   Sources: TechCrunch, The Guardian, Reuters

📝 SUMMARY:
   Apple, Google, and Microsoft announced a joint AI safety initiative.

✅ COMMON FACTS (all sources agree):
   • Three major tech companies forming partnership
   • Focus on AI safety standards

📊 SOURCE-BY-SOURCE ANALYSIS:

   📰 TechCrunch 😊
      Tone: positive
      Focus: Innovation and industry progress

   📰 The Guardian 😐
      Tone: neutral
      Focus: Regulatory context and skepticism

   📰 Reuters 😐
      Tone: neutral
      Focus: Facts, timeline, official statements

⚡ KEY DIFFERENCES:
   • TechCrunch emphasizes innovation benefits
   • The Guardian questions regulatory motivations
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

#### Fetching & Viewing
| Command | Description |
|---------|-------------|
| `fetch` | Fetch news from RSS feeds (default) |
| `fetch newsapi` | Fetch from NewsAPI |
| `fetch both` | Fetch from RSS + NewsAPI |
| `show` | Display all fetched articles |
| `show <number>` | Show specific article in detail |
| `category` | List all categories |
| `category <name>` | Show articles in a specific category |

#### Search & Filter
| Command | Description |
|---------|-------------|
| `search <keyword>` | Search articles by keyword |
| `filter today` | Show articles from today |
| `filter week` | Show articles from last 7 days |

#### Advanced Analysis (NEW!)
| Command | Description |
|---------|-------------|
| `sentiment` | Show sentiment breakdown (positive/negative/neutral) |
| `sentiment <type>` | Filter by sentiment (e.g., `sentiment positive`) |
| `trending` | Detect trending topics using AI |
| `trending fast` | Quick trend analysis (keywords only, no AI) |
| `similar <number>` | Find articles similar to article # |
| `related` | Show all article relationships |
| `compare` | Compare same story across different sources |

#### Utilities
| Command | Description |
|---------|-------------|
| `tags` | Show trending keywords and entities |
| `tags <number>` | Show tags for a specific article |
| `stats` | Show overall statistics |
| `save` | Save articles as JSON (default) |
| `save md` | Save articles as Markdown |
| `ask <question>` | Ask a question about the articles |
| `sources` | List available news sources |
| `clear` | Clear conversation history |
| `help` | Show available commands |
| `quit` | Exit the program |

### Example Session

```bash
# Start the agent
python main.py

# Fetch the latest news (includes sentiment analysis)
> fetch

# View sentiment breakdown
> sentiment

# See only positive news
> sentiment positive

# Detect trending topics
> trending

# Find articles similar to article #1
> similar 1

# See all article relationships
> related

# Compare how different sources cover the same story
# (works best with 'fetch both' to get multiple sources)
> fetch both
> compare

# Ask questions (supports follow-ups!)
> ask What are the main headlines today?
> ask Tell me more about the first one

# Save to file
> save md

# Exit
> quit
```

## Project Structure

```
news-summarizer-agent/
├── main.py               # CLI entry point (all features integrated)
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env.example          # API key template
├── .gitignore            # Git ignore rules
├── README.md             # This file
│
├── src/
│   ├── __init__.py       # Package init
│   │
│   │   # Core Modules
│   ├── news_fetcher.py   # RSS feed + NewsAPI fetching
│   ├── summarizer.py     # Claude AI summarization
│   ├── categorizer.py    # Topic classification
│   ├── tagger.py         # Keyword & entity extraction
│   ├── qa_chain.py       # Q&A with memory
│   │
│   │   # Advanced Modules (NEW!)
│   ├── sentiment.py      # Sentiment analysis (positive/negative/neutral)
│   ├── trending.py       # Trending topics detection
│   ├── similarity.py     # Article relationship detection
│   └── comparator.py     # Multi-source story comparison
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
│     Tagger      │ --> │    Sentiment    │ --> │   Store in      │
│  (Claude AI)    │     │   (Claude AI)   │     │   Agent State   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
        ┌───────────────────────────────────────────────┤
        │                       │                       │
        v                       v                       v
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Trending     │     │   Similarity    │     │   Comparator    │
│   Detection     │     │    Matching     │     │  (Multi-Source) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                v
                    ┌─────────────────────┐
                    │    User CLI +       │
                    │    Q&A Chain        │
                    │    (with memory)    │
                    └─────────────────────┘
```

### Technologies Used

- **[LangChain](https://python.langchain.com/)** - AI application framework
- **[Claude AI](https://www.anthropic.com/claude)** - Large language model for all AI tasks
- **[feedparser](https://feedparser.readthedocs.io/)** - RSS feed parsing
- **[NewsAPI](https://newsapi.org/)** - News aggregator API (optional)
- **Python 3.9+** - Programming language

### Key LangChain Concepts

This project demonstrates several LangChain patterns:

#### Core Concepts
1. **Prompt Templates** - Structured prompts with variables (`ChatPromptTemplate`)
2. **Chains (LCEL)** - Connecting prompt → LLM → parser using `|` operator
3. **Output Parsing** - Cleaning and validating AI responses (`StrOutputParser`)
4. **Conversation Memory** - Maintaining chat history with `MessagesPlaceholder`

#### Advanced Concepts (NEW!)
5. **Structured Output** - Getting specific formats from LLM (sentiment, trends)
6. **Multi-Document Reasoning** - Analyzing patterns across multiple articles
7. **Temperature Tuning** - Low temp (0.1) for classification, higher (0.3) for insights
8. **Batch Processing** - Sending all articles at once for holistic analysis
9. **Multi-Source Comparison** - Comparing different perspectives on same event

### LangChain Patterns by Module

| Module | LangChain Pattern | Temperature |
|--------|-------------------|-------------|
| `summarizer.py` | Basic Chain (prompt \| llm \| parser) | 0.3 |
| `categorizer.py` | Classification with validation | 0.1 |
| `qa_chain.py` | Memory with MessagesPlaceholder | 0.3 |
| `sentiment.py` | Structured output parsing | 0.1 |
| `trending.py` | Multi-document reasoning | 0.3 |
| `similarity.py` | Pairwise comparison | 0.2 |
| `comparator.py` | Multi-source analysis | 0.2 |

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

### "No stories found for comparison"
- Use `fetch both` to get articles from multiple sources
- The compare feature needs the same story covered by different outlets
- Try fetching more articles or different time periods

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
