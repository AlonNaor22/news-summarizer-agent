import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from config import ANTHROPIC_API_KEY, MODEL_NAME, LLM_SETTINGS
from src.models import Article

logger = logging.getLogger(__name__)

RAG_TOP_K = 5


QA_PROMPT = ChatPromptTemplate.from_messages([
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

    MessagesPlaceholder(variable_name="chat_history"),

    ("human", "{question}")
])


class NewsQAChain:
    """Q&A system with conversation memory over a loaded set of news articles.

    If ``collection_name`` is provided, ``ask``/``astream`` retrieve the top-K
    most relevant articles via :func:`src.rag.semantic_search` instead of
    stuffing the entire article set into the prompt. This shrinks token usage
    and improves answer focus. With ``collection_name=None`` (the default), the
    chain falls back to the original "all articles in context" behaviour —
    useful for unit tests that don't want to depend on the vector store.
    """

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize with empty article list, empty history, and a built chain."""
        self.collection_name = collection_name
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
        self._articles_context = self._format_articles(self.articles)

        logger.info("Loaded %d articles into Q&A system", len(articles))

    @staticmethod
    def _format_articles(articles: list[Article]) -> str:
        """Render an article list into the text block Claude references."""
        if not articles:
            return "No articles loaded."

        formatted = []

        for i, article in enumerate(articles, 1):
            article_text = f"""ARTICLE {i}:
Title: {article.title or 'Untitled'}
Category: {article.category or 'Uncategorized'}
Source: {article.source or 'Unknown'}
Summary: {article.summary or article.description or 'No summary available'}
"""
            formatted.append(article_text)

        return "\n".join(formatted)

    def _retrieve_context(self, question: str) -> str:
        """Return the article context to feed the prompt for ``question``.

        With a ``collection_name`` configured, runs semantic retrieval and
        formats only the top-K hits. Falls back to the full article context if
        retrieval is disabled, returns nothing, or raises.
        """
        if not self.collection_name or not self.articles:
            return self._articles_context

        try:
            from src.rag import semantic_search

            top = semantic_search(
                question,
                self.articles,
                k=RAG_TOP_K,
                collection_name=self.collection_name,
            )
        except Exception:
            logger.exception("RAG retrieval failed; using full article context")
            return self._articles_context

        if not top:
            return self._articles_context

        logger.info(
            "RAG retrieval: %d / %d articles selected for question",
            len(top),
            len(self.articles),
        )
        return self._format_articles(top)

    def ask(self, question: str) -> str:
        """Ask a question about the loaded articles; updates chat_history and returns the answer."""
        if not self.articles:
            return "No articles loaded. Please load articles first."

        context = self._retrieve_context(question)
        response = self.chain.invoke({
            "articles_context": context,
            "chat_history": self.chat_history,
            "question": question
        })

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=response))

        return response

    async def astream(self, question: str):
        """Async-stream the answer chunk by chunk; commits to chat_history once complete.

        Yields string chunks as they arrive from Claude. The full answer is appended to
        chat_history only after streaming finishes successfully, so a cancelled stream
        doesn't leave a partial AI message in the history.
        """
        if not self.articles:
            yield "No articles loaded. Please load articles first."
            return

        context = self._retrieve_context(question)
        collected: list[str] = []
        async for chunk in self.chain.astream({
            "articles_context": context,
            "chat_history": self.chat_history,
            "question": question,
        }):
            if chunk:
                collected.append(chunk)
                yield chunk

        full_answer = "".join(collected)
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=full_answer))

    def clear_history(self) -> None:
        """Clear conversation history but keep articles."""
        self.chat_history = []
        logger.info("Conversation history cleared")

    def get_history(self) -> list:
        """Return the conversation history."""
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



def quick_qa(articles: list[Article], question: str) -> str:
    """Single question with no memory — convenience wrapper around NewsQAChain."""
    qa = NewsQAChain()
    qa.load_articles(articles)
    return qa.ask(question)

