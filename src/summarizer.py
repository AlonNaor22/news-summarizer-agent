import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article
from src.retry_utils import retried_invoke
from src.timing import timeit

logger = logging.getLogger(__name__)



def create_llm():
    """Create and return a configured Claude LLM instance."""

    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY not found!\n"
            "Please create a .env file with your API key.\n"
            "See .env.example for the format."
        )

    settings = LLM_SETTINGS["summarize"]
    return ChatAnthropic(
        model=MODEL_NAME,
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        api_key=ANTHROPIC_API_KEY,
    )


SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a professional news summarizer. Your job is to:
1. Read news articles carefully
2. Extract the most important information
3. Write clear, concise summaries

Guidelines:
- Keep summaries to 3-4 sentences
- Focus on WHO, WHAT, WHEN, WHERE, WHY
- Be objective and neutral
- Don't add opinions or speculation
- If the content is unclear, say so"""),

    ("human", """Please summarize this news article:

TITLE: {title}

CONTENT: {content}

Provide a clear, concise summary:""")
])


# Lazily-built singleton: reused across all articles instead of paying the LLM
# client construction cost per article.
_chain = None


def create_summary_chain():
    """Return the (lazily-built) summarization chain."""
    global _chain
    if _chain is None:
        _chain = SUMMARY_PROMPT | create_llm() | StrOutputParser()
    return _chain



@timeit
def summarize_article(article: Article) -> Article:
    """Set ``article.summary`` via Claude and return the article."""

    chain = create_summary_chain()

    content = article.description
    title = article.title or "Untitled"

    if not content or len(content.strip()) < 50:
        article.summary = "Summary unavailable - article content too short."
        return article

    logger.info("Summarizing: %s...", title[:50])

    summary = retried_invoke(chain, {
        "title": title,
        "content": content,
    })

    article.summary = summary

    return article


def summarize_articles(articles: list[Article]) -> list[Article]:
    """Summarize every article in ``articles``, returning the same list."""

    logger.info("=" * 50)
    logger.info("SUMMARIZING ARTICLES WITH CLAUDE")
    logger.info("=" * 50)

    summarized: list[Article] = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        logger.info("[%d/%d]", i, total)

        try:
            summarized_article = summarize_article(article)
            summarized.append(summarized_article)
        except Exception as e:
            logger.error("Error summarizing: %s", e)
            article.summary = f"Error: Could not summarize - {str(e)}"
            summarized.append(article)

    logger.info("=" * 50)
    logger.info("COMPLETED: %d articles summarized", len(summarized))
    logger.info("=" * 50)

    return summarized


def display_summary(article: Article) -> None:
    """Log a summarized article in a readable format."""
    logger.info("=" * 60)
    logger.info("📰 %s", article.title)
    logger.info("=" * 60)
    logger.info("Source: %s", article.source)
    logger.info("Published: %s", article.published or "Unknown")
    logger.info("📝 SUMMARY:")
    logger.info("   %s", article.summary or "No summary available")
    logger.info("🔗 %s", article.url)

