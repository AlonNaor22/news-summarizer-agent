# =====================================================
# SUMMARIZER MODULE
# =====================================================
#
# This module uses Claude (via LangChain) to summarize articles.
#
# LANGCHAIN CONCEPTS USED:
#
# 1. ChatAnthropic - The LLM (AI model) we talk to
# 2. ChatPromptTemplate - Instructions with placeholders
# 3. Chain (using |) - Connects prompt → LLM → output
#
# =====================================================

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Import our settings
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, MODEL_NAME, TEMPERATURE, MAX_TOKENS


# =====================================================
# STEP 1: CREATE THE LLM (The AI Brain)
# =====================================================
#
# ChatAnthropic is LangChain's way to connect to Claude.
# We configure it with:
#   - model: Which Claude version to use
#   - temperature: Creativity level (0=focused, 1=creative)
#   - max_tokens: Maximum length of response
#
# =====================================================

def create_llm():
    """
    Create and return a configured Claude LLM instance.

    We put this in a function so we can:
    1. Check if API key exists before creating
    2. Reuse the same configuration everywhere
    """

    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY not found!\n"
            "Please create a .env file with your API key.\n"
            "See .env.example for the format."
        )

    llm = ChatAnthropic(
        model=MODEL_NAME,           # e.g., "claude-sonnet-4-5-20250929"
        temperature=TEMPERATURE,     # 0.3 - slightly creative but focused
        max_tokens=MAX_TOKENS,       # 500 tokens max per response
        api_key=ANTHROPIC_API_KEY
    )

    return llm


# =====================================================
# STEP 2: CREATE THE PROMPT TEMPLATE
# =====================================================
#
# A prompt template is like a form letter with blanks.
#
# Example:
#   "Dear {name}, thank you for {action}."
#
# We fill in {name} and {action} later.
#
# For our summarizer, we have {title} and {content}.
#
# =====================================================

# This is the instruction we send to Claude
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    # "system" message sets the AI's role and behavior
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

    # "human" message is what the user sends
    # {title} and {content} are placeholders we fill in later
    ("human", """Please summarize this news article:

TITLE: {title}

CONTENT: {content}

Provide a clear, concise summary:""")
])


# =====================================================
# STEP 3: CREATE THE CHAIN
# =====================================================
#
# A "chain" connects components together using the | operator.
#
# prompt | llm | parser
#    ↓      ↓      ↓
#  Fill   Send   Convert
#  in     to     response
#  vars   Claude to string
#
# =====================================================

def create_summary_chain():
    """
    Create a chain that summarizes articles.

    WHAT IS A CHAIN?
    ----------------
    A chain is a pipeline that connects:
    1. Prompt Template (fills in variables)
    2. LLM (sends to Claude, gets response)
    3. Output Parser (converts response to string)

    The | operator connects them:
        prompt | llm | parser

    RETURNS:
    --------
    A chain object that you can call with .invoke()
    """

    llm = create_llm()

    # StrOutputParser converts Claude's response to a plain string
    parser = StrOutputParser()

    # Connect them: prompt → llm → parser
    # This is called LCEL (LangChain Expression Language)
    chain = SUMMARY_PROMPT | llm | parser

    return chain


# =====================================================
# STEP 4: THE MAIN SUMMARIZE FUNCTION
# =====================================================

def summarize_article(article: dict) -> dict:
    """
    Summarize a single article using Claude.

    PARAMETERS:
    -----------
    article : dict
        An article dictionary with keys: title, description, url, source

    RETURNS:
    --------
    dict
        The original article with a new "summary" key added

    EXAMPLE:
    --------
    >>> article = {"title": "Big News", "description": "Something happened..."}
    >>> result = summarize_article(article)
    >>> print(result["summary"])
    "A significant event occurred today..."
    """

    # Create the chain
    chain = create_summary_chain()

    # Get the content to summarize
    # We use description from RSS (or empty string if missing)
    content = article.get("description", "")
    title = article.get("title", "Untitled")

    # Check if we have content
    if not content or len(content.strip()) < 50:
        article["summary"] = "Summary unavailable - article content too short."
        return article

    print(f"  Summarizing: {title[:50]}...")

    # Call the chain with our variables
    # .invoke() runs the chain: fills prompt → sends to Claude → returns string
    summary = chain.invoke({
        "title": title,
        "content": content
    })

    # Add summary to the article
    article["summary"] = summary

    return article


def summarize_articles(articles: list[dict]) -> list[dict]:
    """
    Summarize multiple articles.

    PARAMETERS:
    -----------
    articles : list[dict]
        List of article dictionaries

    RETURNS:
    --------
    list[dict]
        Same articles with "summary" key added to each
    """

    print("\n" + "="*50)
    print("SUMMARIZING ARTICLES WITH CLAUDE")
    print("="*50)

    summarized = []
    total = len(articles)

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}]", end="")

        try:
            summarized_article = summarize_article(article)
            summarized.append(summarized_article)
        except Exception as e:
            print(f"  Error summarizing: {e}")
            article["summary"] = f"Error: Could not summarize - {str(e)}"
            summarized.append(article)

    print("\n" + "="*50)
    print(f"COMPLETED: {len(summarized)} articles summarized")
    print("="*50)

    return summarized


def display_summary(article: dict) -> None:
    """
    Display a summarized article nicely.
    """
    print(f"\n{'='*60}")
    print(f"📰 {article['title']}")
    print(f"{'='*60}")
    print(f"Source: {article['source']}")
    print(f"Published: {article.get('published', 'Unknown')}")
    print(f"\n📝 SUMMARY:")
    print(f"   {article.get('summary', 'No summary available')}")
    print(f"\n🔗 {article['url']}")


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING SUMMARIZER")
    print("="*60)

    # Test with a sample article
    test_article = {
        "title": "Global Leaders Meet to Discuss Climate Action",
        "description": """
        World leaders from over 150 countries gathered in Geneva today
        for an emergency summit on climate change. The meeting, which
        was called after record-breaking temperatures were recorded
        across three continents last month, aims to establish new
        emissions targets and funding mechanisms for developing nations.

        The UN Secretary-General opened the summit with a stark warning:
        "We are running out of time. The decisions we make this week
        will determine the future of our planet." Key topics on the
        agenda include carbon pricing, renewable energy investment,
        and climate adaptation funding.

        Several major economies have already signaled their willingness
        to increase their commitments, though disagreements remain over
        how costs should be distributed between developed and developing
        nations.
        """,
        "url": "https://example.com/climate-summit",
        "source": "Test News",
        "published": "January 16, 2026"
    }

    print("\n--- Original Article ---")
    print(f"Title: {test_article['title']}")
    print(f"Content length: {len(test_article['description'])} characters")

    print("\n--- Calling Claude to Summarize ---")
    result = summarize_article(test_article)

    print("\n--- Result ---")
    display_summary(result)
