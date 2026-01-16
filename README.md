# News Summarizer Agent

An AI-powered command-line agent that fetches the latest news articles from RSS feeds, summarizes them using Claude AI, categorizes them by topic, and allows you to ask follow-up questions about current events.

## Features

- **News Fetching**: Automatically fetches articles from multiple RSS feeds (BBC, NPR, Reuters)
- **AI Summarization**: Uses Claude AI to generate concise summaries of each article
- **Topic Categorization**: Classifies articles into categories (Politics, Technology, Business, etc.)
- **Interactive Q&A**: Ask questions about the news with conversation memory for follow-ups
- **No News API Key Required**: Uses free RSS feeds - only needs an Anthropic API key

## Demo

```
> fetch

FETCHING NEWS
============================================================
Step 1/3: Fetching articles from RSS feeds...
Step 2/3: Summarizing articles with Claude...
Step 3/3: Categorizing articles...

FETCH COMPLETE!
  Total articles: 15
  Categories: 5
    - Technology: 4 articles
    - World News: 3 articles
    - Business: 3 articles

> ask What's the most important tech news today?

The most significant technology news is about Apple's announcement
of new AI-powered features in their latest iPhone...

> ask Tell me more about those AI features

Building on the Apple announcement, the AI features include
real-time language translation, intelligent photo editing...
```

## Installation

### Prerequisites

- Python 3.9 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))

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

   # Edit .env and add your Anthropic API key
   # ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
   ```

5. **Run the agent**
   ```bash
   python main.py
   ```

## Usage

### Available Commands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch latest news from RSS feeds |
| `show` | Display all fetched articles |
| `show <number>` | Show specific article in detail |
| `category` | List all categories |
| `category <name>` | Show articles in a specific category |
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

# View all articles
> show

# View a specific article
> show 3

# Filter by category
> category Technology

# Ask questions (supports follow-ups!)
> ask What are the main headlines today?
> ask Tell me more about the first one
> ask How does this compare to last week?

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
└── src/
    ├── __init__.py       # Package init
    ├── news_fetcher.py   # RSS feed fetching
    ├── summarizer.py     # Claude AI summarization
    ├── categorizer.py    # Topic classification
    └── qa_chain.py       # Q&A with memory
```

## How It Works

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   RSS Feeds     │ --> │   Summarizer    │ --> │  Categorizer    │
│  (news_fetcher) │     │  (Claude AI)    │     │  (Claude AI)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        v
                        ┌─────────────────┐     ┌─────────────────┐
                        │    User CLI     │ <-- │   Q&A Chain     │
                        │    (main.py)    │     │  (with memory)  │
                        └─────────────────┘     └─────────────────┘
```

### Technologies Used

- **[LangChain](https://python.langchain.com/)** - AI application framework
- **[Claude AI](https://www.anthropic.com/claude)** - Large language model for summarization and Q&A
- **[feedparser](https://feedparser.readthedocs.io/)** - RSS feed parsing
- **Python 3.9+** - Programming language

### Key LangChain Concepts

This project demonstrates several LangChain patterns:

1. **Prompt Templates** - Structured prompts with variables
2. **Chains (LCEL)** - Connecting prompt → LLM → parser
3. **Output Parsing** - Cleaning and validating AI responses
4. **Conversation Memory** - Maintaining chat history for follow-ups

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
- Try running `fetch` again

### Rate limiting
If you hit API rate limits, wait a few moments and try again. Consider using `claude-haiku-4-5-20251001` for faster, cheaper requests.

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
- News content from BBC, NPR, Reuters RSS feeds
