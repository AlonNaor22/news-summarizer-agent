# =====================================================
# Q&A CHAIN WITH MEMORY
# =====================================================
#
# This module allows users to ask follow-up questions
# about news articles. It remembers the conversation!
#
# KEY CONCEPT: MEMORY
# -------------------
# By default, each AI call is independent - Claude doesn't
# remember previous messages. Memory fixes this by:
#
# 1. Storing all messages (human + AI) in a list
# 2. Sending the FULL history with each new question
# 3. Claude sees the whole conversation, enabling follow-ups
#
# =====================================================

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article

logger = logging.getLogger(__name__)


# =====================================================
# THE Q&A PROMPT WITH MEMORY
# =====================================================
#
# Notice the special placeholder: MessagesPlaceholder
#
# This is where previous conversation messages get inserted.
# It's like a "slot" that gets filled with chat history.
#
# =====================================================

QA_PROMPT = ChatPromptTemplate.from_messages([
    # System message: Sets the AI's role and gives it the articles
    ("system", """You are a helpful news assistant. You help users understand news articles.

You have access to the following news articles:

{articles_context}

---

Instructions:
1. Answer questions based on the articles above
2. If asked about something not in the articles, say so
3. Be concise but informative
4. You can compare articles, identify themes, or explain details
5. Reference specific articles by their title when relevant"""),

    # This placeholder is WHERE the conversation history goes
    # It will be replaced with all previous human/AI messages
    MessagesPlaceholder(variable_name="chat_history"),

    # The current question from the user
    ("human", "{question}")
])


class NewsQAChain:
    """
    A Q&A system with memory for asking questions about news articles.

    WHY A CLASS?
    ------------
    We use a class here because we need to STORE state:
    - The articles we're discussing
    - The conversation history

    A regular function can't remember things between calls.
    A class can store data in `self.variable`.

    USAGE:
    ------
    >>> qa = NewsQAChain()
    >>> qa.load_articles(articles)
    >>> answer1 = qa.ask("What's the main tech news?")
    >>> answer2 = qa.ask("Tell me more about that")  # Remembers context!
    """

    def __init__(self):
        """Initialize with empty article list, empty history, and a built chain."""
        self.articles: list[Article] = []
        self.chat_history: list = []
        self._articles_context: str = ""
        self.llm = self._create_llm()
        self.chain = self._create_chain()

    def _create_llm(self):
        """Create the Claude LLM instance."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found!")

        settings = LLM_SETTINGS["qa"]
        return ChatAnthropic(
            model=MODEL_NAME,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            api_key=ANTHROPIC_API_KEY,
        )

    def _create_chain(self):
        """Create the Q&A chain."""
        parser = StrOutputParser()
        return QA_PROMPT | self.llm | parser

    def load_articles(self, articles: list[Article]) -> None:
        """Store the articles to answer questions over and reset chat history."""
        self.articles = articles
        self.chat_history = []
        self._articles_context = self._format_articles_for_context()

        logger.info("Loaded %d articles into Q&A system", len(articles))

    def _format_articles_for_context(self) -> str:
        """Render the loaded articles into the text block Claude references."""
        if not self.articles:
            return "No articles loaded."

        formatted = []

        for i, article in enumerate(self.articles, 1):
            article_text = f"""ARTICLE {i}:
Title: {article.title or 'Untitled'}
Category: {article.category or 'Uncategorized'}
Source: {article.source or 'Unknown'}
Summary: {article.summary or article.description or 'No summary available'}
"""
            formatted.append(article_text)

        return "\n".join(formatted)

    def ask(self, question: str) -> str:
        """
        Ask a question about the loaded articles.

        The magic happens here:
        1. We send the articles context
        2. We send ALL previous messages (chat_history)
        3. We send the new question
        4. Claude responds with full context
        5. We save both question and answer to history

        PARAMETERS:
        -----------
        question : str
            The user's question

        RETURNS:
        --------
        str
            Claude's answer
        """
        if not self.articles:
            return "No articles loaded. Please load articles first."

        # Call the chain with:
        # - articles_context: The news articles (pre-built in load_articles)
        # - chat_history: Previous conversation
        # - question: Current question
        response = self.chain.invoke({
            "articles_context": self._articles_context,
            "chat_history": self.chat_history,
            "question": question
        })

        # Save this exchange to memory
        # HumanMessage and AIMessage are LangChain's way to store chat
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=response))

        return response

    def clear_history(self) -> None:
        """
        Clear conversation history but keep articles.

        Use this to start a fresh conversation about the same articles.
        """
        self.chat_history = []
        logger.info("Conversation history cleared")

    def get_history(self) -> list:
        """
        Get the conversation history.

        Useful for debugging or displaying past conversation.
        """
        return self.chat_history

    def display_history(self) -> None:
        """Log the conversation history in a readable format."""
        if not self.chat_history:
            logger.info("No conversation history yet.")
            return

        logger.info("=" * 60)
        logger.info("CONVERSATION HISTORY")
        logger.info("=" * 60)

        for msg in self.chat_history:
            if isinstance(msg, HumanMessage):
                logger.info("You: %s", msg.content)
            elif isinstance(msg, AIMessage):
                logger.info("AI: %s", msg.content)


# =====================================================
# CONVENIENCE FUNCTION
# =====================================================
# For simple use cases where you don't need a class

def quick_qa(articles: list[Article], question: str) -> str:
    """
    Quick one-off question (no memory).

    Use this for single questions where you don't need follow-ups.

    PARAMETERS:
    -----------
    articles : list[dict]
        The articles to ask about
    question : str
        Your question

    RETURNS:
    --------
    str
        The answer
    """
    qa = NewsQAChain()
    qa.load_articles(articles)
    return qa.ask(question)


# =====================================================
# TEST CODE
# =====================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING Q&A CHAIN WITH MEMORY")
    print("="*60)

    test_articles = [
        Article(
            title="Apple Unveils Revolutionary AI-Powered iPhone",
            summary="Apple announced its latest iPhone featuring advanced AI capabilities including real-time language translation, intelligent photo editing, and a new Siri powered by large language models. The device also boasts improved battery life of up to 30 hours and a new titanium design.",
            category="Technology",
            source="TechCrunch",
            url="",
        ),
        Article(
            title="Federal Reserve Holds Interest Rates Steady",
            summary="The Federal Reserve decided to maintain current interest rates at 5.25%, citing mixed economic signals. Chair Powell indicated that future decisions would depend on inflation data over the coming months. Markets responded positively to the news.",
            category="Business",
            source="Reuters",
            url="",
        ),
        Article(
            title="Scientists Discover New Treatment for Alzheimer's",
            summary="Researchers at MIT have developed a promising new drug that shows significant improvement in Alzheimer's patients during clinical trials. The treatment targets protein buildup in the brain and showed 35% slower cognitive decline compared to placebo groups.",
            category="Health",
            source="Science Daily",
            url="",
        ),
    ]

    # Create Q&A system and load articles
    print("\n--- Setting Up Q&A System ---")
    qa = NewsQAChain()
    qa.load_articles(test_articles)

    # Simulate a conversation with follow-up questions
    print("\n--- Starting Conversation ---")
    print("(Watch how the AI remembers previous questions!)\n")

    # Question 1
    print("="*60)
    q1 = "What are the main technology news today?"
    print(f"🧑 You: {q1}")
    a1 = qa.ask(q1)
    print(f"\n🤖 AI: {a1}")

    # Question 2 (follow-up - requires memory!)
    print("\n" + "="*60)
    q2 = "What specific AI features does it have?"
    print(f"🧑 You: {q2}")
    print("   (Note: 'it' refers to iPhone from previous answer)")
    a2 = qa.ask(q2)
    print(f"\n🤖 AI: {a2}")

    # Question 3 (another follow-up)
    print("\n" + "="*60)
    q3 = "How does this compare to the health news?"
    print(f"🧑 You: {q3}")
    a3 = qa.ask(q3)
    print(f"\n🤖 AI: {a3}")

    # Show conversation history
    print("\n" + "="*60)
    print("--- Full Conversation History ---")
    qa.display_history()

    # Demonstrate clearing history
    print("\n" + "="*60)
    print("--- Clearing History ---")
    qa.clear_history()

    # Now asking about "it" won't work (no context)
    q4 = "Tell me more about it"
    print(f"\n🧑 You: {q4}")
    print("   (After clearing, AI doesn't know what 'it' means)")
    a4 = qa.ask(q4)
    print(f"\n🤖 AI: {a4}")
