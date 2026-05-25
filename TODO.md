# TODO — News Summarizer Agent

> Audit date: 2026-05-25

**Summary:** Strong feature breadth (CLI + FastAPI + React all wired to a real Claude/LangChain pipeline with sentiment, trending, similarity, and multi-source comparison) is undermined by a 1571-line god-class CLI, an LLM that gets re-instantiated for every single article, broken CI, and a real Anthropic API key sitting in plaintext on disk — the kind of issues a senior reviewer would flag in the first ten minutes.

> **How to use this file:** every open `- [ ]` item is followed by a fenced `Prompt for a new chat` block. Copy the contents of the block, start a new conversation in this repo, paste, and a fresh agent will execute that one task. Completed items (`- [x]`) record what changed and where.
>
> **Model labels:** each prompt header reads `Prompt for a new chat (model: Sonnet)` or `(model: Opus)`. Use Sonnet for well-defined, localized changes (the default). Use Opus for tasks marked as such — they involve architectural decisions, multi-file coordination, async correctness, or new infra (Docker, RAG, SQLite, streaming).

## 1. Code Quality

- [x] 🔴 ~~Split main.py (1571 lines, `NewsSummarizerAgent` class) into focused modules~~ — replaced the god-class with a [cli/](cli/) package: [state.py](cli/state.py) (`AgentState` dataclass for articles + qa_chain + caches), [display.py](cli/display.py) (`header`/`hr` helpers + welcome/help screens), [commands.py](cli/commands.py) (per-command handlers + `process_command` dispatcher), and [main.py](cli/main.py) (`run()` loop + `main()` entry). Root [main.py](main.py) is a 9-line shim. Output is byte-identical to the original under diff; all 40 tests pass.

- [x] 🔴 ~~Stop re-creating the `ChatAnthropic` LLM inside every per-article call~~ — each `src/` module now has a lazy `_chain` singleton (e.g. [summarizer.py:121](src/summarizer.py:121)), so the LLM client is built once per process instead of once per article.
- [x] 🔴 ~~Remove the duplicated `sys.path.append(...)` hack~~ — added [pyproject.toml](pyproject.toml) (installable with `pip install -e .`) and stripped the path hack from all 9 `src/` files and all 7 `backend/api/` files. The single remaining hack lives in [backend/main.py](backend/main.py) so `uvicorn backend.main:app` keeps working without an install step.
- [x] 🔴 ~~Replace the `list[dict]` article representation with a Pydantic `Article` model~~ — defined once in [src/models.py](src/models.py) (required `title`/`source`/`url` + optional `description`/`summary`/`published`/`category`/`secondary_categories`/`sentiment{,_confidence,_reason}`/`keywords`/`people`/`organizations`/`locations`/`author`/`image_url`/`id`/`similarity`). [news_fetcher.py](src/news_fetcher.py) now returns `list[Article]`, every downstream `src/` module (summarizer, categorizer, tagger, sentiment, trending, similarity, comparator, qa_chain) and all six `backend/api/routes/*.py` files accept and return `Article` instances with FastAPI handling JSON serialization. [cli/state.py](cli/state.py) + [cli/commands.py](cli/commands.py) updated to attribute access; [tests/test_categorizer.py](tests/test_categorizer.py) and [tests/test_similarity.py](tests/test_similarity.py) now construct `Article` objects. All 40 tests pass.

- [x] 🟡 ~~[main.py:1559](main.py:1559) — bare-ish `except Exception as e` in the main loop~~ — now catches `KeyboardInterrupt`, `EOFError`, and `(ValueError, KeyError, IndexError)` explicitly so unexpected exceptions propagate with a real traceback.
- [x] 🟡 ~~Replace manual LLM output parsing in `src/sentiment.py`, `src/tagger.py`, `src/categorizer.py`, `src/trending.py`, `src/similarity.py`, `src/comparator.py`~~ — every chain now uses LangChain's `llm.with_structured_output(Model)` against a Pydantic model defined in the same module: [SentimentResult](src/sentiment.py), [ArticleTags](src/tagger.py), [MultiCategoryResult](src/categorizer.py), [Trend](src/trending.py)/[TrendList](src/trending.py), [RelatedPair](src/similarity.py)/[RelatedPairList](src/similarity.py), [SourceAnalysis](src/comparator.py)/[ComparisonResult](src/comparator.py). All six `parse_*_response` line-splitters are deleted; the legacy dict shape that downstream display/summary code expects is preserved by small `_pair_list_to_dicts` / `_comparison_to_dict` adapters where needed. `tests/test_tagger.py` and `tests/test_categorizer.py` now exercise the Pydantic models + a mocked structured chain instead of the old text parsers; all 40 tests still pass.

- [x] 🟡 ~~Unused imports in [main.py:33](main.py:33)~~ — trimmed to just `fetch_news`.
- [x] 🟡 ~~Magic numbers scattered across the codebase~~ — added `SIMILARITY_THRESHOLDS` and `WORDS_PER_MINUTE` to [config.py](config.py); removed the hardcoded `max_per_source=3` override in `main.py` so it now uses `MAX_ARTICLES_PER_SOURCE` from config.
- [x] 🟡 ~~`MAX_TOKENS = 500` overridden in every module~~ — added a single `LLM_SETTINGS` dict in [config.py](config.py) keyed by task (`summarize`, `categorize`, `tag`, `sentiment`, `trending`, `similarity`, `comparison`, `qa`); every `create_llm()` now reads its temperature and max_tokens from that one place.
- [x] 🟡 ~~Most CLI methods in [main.py](main.py) have no return type hints~~ — added `-> None` (or appropriate `int | None` for optional args) to all 22 public/private methods of `NewsSummarizerAgent`.
- [x] 🟢 ~~[src/__init__.py](src/__init__.py) is a tutorial comment with no code~~ — replaced with a one-line docstring.
- [x] 🟢 ~~Print statements are used as logging throughout `src/` ([summarizer.py:190](src/summarizer.py:190), [news_fetcher.py:80](src/news_fetcher.py:80), etc.). Replace with `logging.getLogger(__name__)` — library code shouldn't print.~~ — added `import logging` + `logger = logging.getLogger(__name__)` to all 9 `src/` modules; replaced every progress/warning/error `print()` with `logger.info` / `logger.warning` / `logger.error`; `__main__` test blocks left untouched. Added `logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")` to [main.py](main.py) and [backend/main.py](backend/main.py). All 40 tests pass.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Replace print() calls in src/ modules with proper logging.
Library code shouldn't print to stdout.

At the top of each src/*.py file add:
    import logging
    logger = logging.getLogger(__name__)

Replace every print(...) with logger.info / logger.warning /
logger.error based on context. Progress messages like
"Summarizing: ..." are .info; errors caught in try/except should
be .warning or .error.

Do NOT replace print() in:
- The `if __name__ == "__main__":` test blocks at the bottom of
  each file
- main.py (CLI is allowed to print to stdout)
- backend/main.py (uvicorn handles its own logging)

After: confirm pytest tests/ still passes. Optionally add
logging.basicConfig(level=logging.INFO) in main.py and
backend/main.py so users see the messages.
```

## 2. Error Handling

- [ ] 🔴 [src/news_fetcher.py:81](src/news_fetcher.py:81) — `feedparser.parse(feed_url)` has **no timeout**. A slow RSS feed will hang the entire fetch. Wrap with `requests.get(url, timeout=10)` and pass bytes to feedparser.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
src/news_fetcher.py:81 — feedparser.parse(feed_url) has no
timeout. A slow RSS feed hangs the entire fetch pipeline.

Fix: wrap with requests.get(feed_url, timeout=10) and pass the
response.content (bytes) into feedparser.parse() instead of the
URL. Catch requests.exceptions.RequestException and return [] with
a warning log (same behavior as the current bozo-check fallback).

Verify pytest tests/ still passes and that an unreachable URL
(e.g., http://10.255.255.1/rss.xml) fails within ~10s instead of
hanging.
```

- [ ] 🔴 [backend/api/routes/articles.py:87](backend/api/routes/articles.py:87), [qa.py:66](backend/api/routes/qa.py:66) — `raise HTTPException(status_code=500, detail=str(e))` leaks raw Python exception messages (including potential stack-trace info and API keys in some LangChain errors) to HTTP clients. Log the exception server-side and return a sanitized message.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
backend/api/routes/articles.py:87 and backend/api/routes/qa.py:66
raise HTTPException(status_code=500, detail=str(e)). This leaks
raw Python exception messages — including potential API keys or
stack info from LangChain errors — to HTTP clients.

Fix in both files: log the full exception server-side with
logger.exception(...) and return a sanitized detail like
"Internal error processing fetch" or "Internal error answering
question". Add a request-id (uuid4) to logs for cross-referencing.

Verify by triggering an error (e.g., POST /api/fetch with no API
key configured) and confirming the HTTP response no longer
contains internal details.
```

- [ ] 🟡 No retry/backoff on Anthropic API calls. A transient 529 rate-limit kills the whole fetch pipeline. Use `tenacity` for exponential backoff on `summarize_articles`, `categorize_articles`, `tag_articles`, `analyze_sentiments` — these are the four loops that hit Claude N times.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add retry/backoff to Anthropic API calls. A transient 529
(overloaded) currently kills the whole fetch pipeline.

Install tenacity (add to pyproject.toml dependencies). Wrap the
.invoke() calls in the four batch loops:
- src/summarizer.py summarize_articles
- src/categorizer.py categorize_articles
- src/tagger.py tag_articles
- src/sentiment.py analyze_sentiments

Use exponential backoff with max 5 attempts and a 60s cap,
retrying only on anthropic.APIStatusError where status_code is
429 or 529, or on anthropic.APIConnectionError.

Verify pytest tests/ still passes. Optionally add a unit test
that mocks ChatAnthropic to fail twice then succeed.
```

- [ ] 🟡 [src/news_fetcher.py:313](src/news_fetcher.py:313) — NewsAPI request has `timeout=10` but the except block swallows the error with a print and returns `[]`. The caller can't distinguish "no articles" from "network down" from "bad API key". Return a `Result` type or raise a custom exception.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
src/news_fetcher.py:313 — the NewsAPI request catches
requests.exceptions.RequestException, prints, and returns [].
The caller can't tell "no articles" from "network down" from
"bad API key".

Fix: define custom exceptions in src/news_fetcher.py:
    class NewsAPIError(Exception): pass
    class NewsAPIAuthError(NewsAPIError): pass
    class NewsAPIRateLimitError(NewsAPIError): pass

Map 401 → NewsAPIAuthError, 429 → NewsAPIRateLimitError, other
failures → NewsAPIError. Let them propagate from
fetch_from_newsapi. Update fetch_all_newsapi to catch + log +
skip the failing category but continue with the rest.

Verify pytest tests/ still passes.
```

- [ ] 🟡 [backend/api/routes/qa.py:36](backend/api/routes/qa.py:36) — `request.question` has no validation. A 100KB question or empty string both reach the LLM. Add `Field(..., min_length=1, max_length=2000)` to the Pydantic model.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
backend/api/routes/qa.py:36 — request.question has no length
validation. A 100KB question or empty string both reach the LLM.

Fix: in the QuestionRequest Pydantic model, change `question: str`
to `question: str = Field(..., min_length=1, max_length=2000)`.

Add a test in tests/test_api.py asserting a 422 response for
empty and oversized questions (use FastAPI TestClient).
```

- [ ] 🟡 [main.py:653](main.py:653) — `os.makedirs(output_dir)` will silently re-raise on race condition. Use `os.makedirs(output_dir, exist_ok=True)`.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
main.py around line 653 has:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

This has a race condition. Replace with one line:
    os.makedirs(output_dir, exist_ok=True)

(Remove the surrounding `if not exists:` check.) Two-line change.
```

- [ ] 🟡 Empty `except (ValueError, IndexError)` in [src/trending.py:415](src/trending.py:415) and [src/similarity.py:579](src/similarity.py:579) silently swallows parse errors and leaves fields at default values. At minimum, log a warning.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
src/trending.py:415 and src/similarity.py:579 each have
`except (ValueError, IndexError)` blocks that silently swallow
parse errors and leave fields at defaults.

Fix: add logger.warning("Could not parse ... from LLM response:
%s", line) in each except block so failures are visible. Use
logging.getLogger(__name__) at the top of the module.

Note: if the structured-outputs refactor (section 1) lands first,
these parsers are deleted entirely and this task is moot.
```

## 3. Architecture & Structure

- [ ] 🔴 [backend/api/dependencies.py:37](backend/api/dependencies.py:37) — `app_state = AppState()` is a module-level global mutable singleton. Every user shares the same articles and Q&A history. Acceptable for a demo, but you need to either acknowledge this in the README or move to a per-session store (Redis, in-memory dict keyed by session ID). At minimum, document the limitation.

```
Prompt for a new chat (model: Opus)
-----------------------------------
backend/api/dependencies.py:37 — `app_state = AppState()` is a
module-level global. Every user of the deployed backend shares
the same articles and Q&A history.

Pick ONE and apply:
1. Quick: add a "Limitations" section to README acknowledging
   single-user state, and add a DELETE /api/state endpoint so
   users can reset between demos.
2. Better: refactor to per-session state keyed by a session ID
   (cookie or X-Session-Id header). Use dict[session_id,
   AppState] in dependencies.py with a TTL cleanup task. Update
   every route handler to read session_id from the request.

Whichever you pick, confirm pytest tests/ still passes. The
architectural CHOICE is the portfolio-relevant part — document it.
```

- [x] 🔴 ~~Extract `Display`, `CommandRouter`, and `AgentState` from `NewsSummarizerAgent`~~ — satisfied by the section-1 split above ([cli/display.py](cli/display.py) + [cli/commands.py](cli/commands.py) + [cli/state.py](cli/state.py)).

- [ ] 🔴 The backend duplicates the orchestration logic from `main.py`'s `fetch_news`. Both call `summarize_articles → categorize_articles → tag_articles → analyze_sentiments` in sequence. Extract this to `src/pipeline.py` and call it from both entry points.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
main.py's fetch_news method and backend/api/routes/articles.py's
fetch_articles handler both call summarize_articles →
categorize_articles → tag_articles → analyze_sentiments in
sequence. That's duplicated orchestration.

Create src/pipeline.py with one function:
    def process_articles(articles: list[dict]) -> list[dict]:
        # runs the four-stage pipeline
        ...

Call it from both entry points. The function must be importable
without instantiating any app state.

Verify: pytest tests/ still passes. The CLI fetch produces the
same result as before. The /api/fetch endpoint produces the same
result.
```

- [ ] 🟡 FastAPI route handlers are `async def` but call **synchronous** LangChain code that blocks the event loop ([backend/api/routes/articles.py:64](backend/api/routes/articles.py:64), [qa.py:57](backend/api/routes/qa.py:57)). Either make them `def` (let FastAPI run them in a threadpool) or use `await asyncio.to_thread(...)` for the LLM calls. As-is, the server serves one request at a time during a fetch.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
FastAPI route handlers in backend/api/routes/articles.py:64 and
backend/api/routes/qa.py:57 are `async def` but call synchronous
LangChain code that blocks the event loop. The server serves one
request at a time during a fetch.

Pick ONE approach and apply across all five long-running endpoints
(/api/fetch, /api/qa/ask, /api/trending, /api/relationships,
/api/comparison):
1. Drop the `async` — `def` route handlers run in a threadpool.
2. Keep `async def` but wrap LLM calls with `await
   asyncio.to_thread(blocking_func, ...)`.

Verify the dev server still responds to a second request while
the first is mid-fetch.

Stretch: if section 7's "concurrent LLM calls" task lands first,
switch to LangChain's native `.ainvoke()` async API — those two
tasks reinforce each other.
```

- [ ] 🟡 [config.py:118](config.py:118) defines `CORS_ORIGINS` but [backend/main.py:52](backend/main.py:52) hardcodes the same list instead of importing from config. Either source from config or delete the dead constant in config.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
config.py defines CORS_ORIGINS but backend/main.py:52 hardcodes
the same list inline instead of importing from config.

Fix: in backend/main.py, import CORS_ORIGINS from config and pass
it to CORSMiddleware. Delete the inline list.

Verify uvicorn still starts and the frontend (localhost:5173) can
still call the backend.
```

- [ ] 🟡 [src/comparator.py:51](src/comparator.py:51) imports `from src.similarity import calculate_combined_similarity` while all other src/ modules import via the sys.path hack. Inconsistent — a sign the package boundary isn't well-defined.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
src/comparator.py imports `from src.similarity import
calculate_combined_similarity` (absolute, via the project root).
With the package now installed via pyproject.toml, this works —
but it's stylistically inconsistent if other src/ modules use a
different style.

Audit src/ for cross-module imports and pick one consistent style:
- `from src.foo import bar` (absolute) — currently used in
  comparator.py
- `from .foo import bar` (relative, sibling) — preferred for
  modules inside the same package

Apply consistently across all src/ files. Verify pytest tests/
still passes.
```

- [ ] 🟢 [src/qa_chain.py:115](src/qa_chain.py:115) — `_create_chain` is called once in `__init__` but `_format_articles_for_context` is recomputed on every `ask()`. For a long conversation with 30 articles, this re-formats the context 30 times. Cache it when articles are loaded.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
src/qa_chain.py — _format_articles_for_context is called inside
every ask() call. For a 30-message conversation with 30 articles,
the same text block is built 30 times.

Fix: cache the formatted string in load_articles(). Add
`self._articles_context: str = ""` in __init__, populate it at
the end of load_articles, and reference self._articles_context in
ask() instead of recomputing.

Verify pytest tests/ still passes.
```

## 4. Tests

- [ ] 🔴 No tests cover any module that calls Claude — [src/summarizer.py](src/summarizer.py), [src/sentiment.py](src/sentiment.py), [src/trending.py](src/trending.py), [src/comparator.py](src/comparator.py), [src/qa_chain.py](src/qa_chain.py). Add tests that mock `ChatAnthropic` (use `unittest.mock.patch`) — being able to test LLM code without hitting the API is a top-tier portfolio skill.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add unit tests that mock ChatAnthropic for the modules that hit
Claude:
- src/summarizer.py
- src/sentiment.py
- src/trending.py
- src/comparator.py
- src/qa_chain.py

Approach: patch the module-level _chain singleton (added by the
LLM-caching refactor) with a unittest.mock.MagicMock whose
.invoke() returns a canned string. Example:

    from unittest.mock import MagicMock
    import src.summarizer as summarizer
    summarizer._chain = MagicMock()
    summarizer._chain.invoke.return_value = "A canned summary."
    result = summarizer.summarize_article({"title": "T",
                                           "description": "D"*100})
    assert result["summary"] == "A canned summary."

Each module needs at least:
1. Happy-path test that the chain is invoked and the response is
   parsed correctly.
2. Test that an exception from the LLM is caught and the function
   returns a sensible default (sentiment="neutral",
   summary="Error: ...").

Put new tests in tests/test_<module>.py. Target: pytest tests/
goes from 40 to ~60 passing.
```

- [ ] 🔴 No tests for any FastAPI endpoint. Add `tests/test_api.py` using `fastapi.testclient.TestClient` — covers articles, sentiment, trending, qa routes at minimum. A reviewer can run this in 10 seconds to verify the API contract.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add tests/test_api.py using fastapi.testclient.TestClient covering
the FastAPI endpoints.

Strategy: use a pytest fixture that resets app_state in
backend/api/dependencies.py and seeds it with canned articles
before each test, then clears after. Mock src/qa_chain's LLM so
the /api/qa/ask test doesn't need a real API call.

Cover at minimum:
- GET / returns 200
- GET /api/health returns 200
- GET /api/articles returns the seeded articles
- GET /api/articles/999 returns 404
- POST /api/qa/ask returns 400 when no articles loaded
- GET /api/sentiment returns counts

After: pytest tests/ should include ~10 new tests and pass.
```

- [ ] 🟡 [tests/conftest.py:5](tests/conftest.py:5) — `sample_article` fixture is defined but never used by any test. Either use it or delete it.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
tests/conftest.py defines a `sample_article` fixture that no test
currently uses.

Either:
- Delete the fixture (one-line cleanup), or
- Use it in tests that need a sample article (e.g., the LLM-mocked
  tests being added in the Claude-mocking task).

Pick one and apply. Verify pytest tests/ still passes.
```

- [ ] 🟡 [tests/test_categorizer.py](tests/test_categorizer.py) only tests pure-Python helpers (`clean_category`, `parse_multi_category_response`, `group_by_category`) — these are the easy bits. Tests don't cover the full `categorize_article` pipeline because there's no LLM mocking infrastructure. Add it.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
tests/test_categorizer.py only tests pure-Python helpers. Add
tests that mock the LLM and cover the full categorize_article
and categorize_articles flow.

Mock src.categorizer._single_chain (the lazy singleton from the
LLM caching refactor) with a MagicMock whose .invoke() returns a
canned category string. Assert that:
- categorize_article(article) sets article['category'] correctly
- categorize_article handles a missing summary gracefully (returns
  category="Other")
- categorize_articles handles per-item errors without crashing
  the batch

Add 3-5 tests to the existing file. Confirm pytest tests/ count
increases.
```

- [ ] 🟡 No edge-case tests for empty input, malformed Claude responses, or NewsAPI 401/429 errors. Add tests asserting that `parse_sentiment_response("garbage")` returns the documented default rather than crashing.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add edge-case tests for the parser functions and error paths:
- parse_sentiment_response("garbage") returns the documented
  neutral default
- parse_multi_category_response("PRIMARY: Politics\n") with no
  SECONDARY line returns secondary=[]
- parse_trend_response with multiple PAIR entries lacking
  RELATIONSHIP still parses names correctly
- fetch_from_newsapi returns [] when the API responds with
  status="error"

Extend tests/test_sentiment.py (create if needed),
tests/test_categorizer.py, tests/test_trending.py (create),
tests/test_news_fetcher.py (create — see separate task).

Note: if the structured-outputs refactor lands first, parser
functions are deleted — replace these with tests that the
Pydantic models reject malformed input.
```

- [ ] 🟡 No tests for [src/news_fetcher.py](src/news_fetcher.py). Mock `feedparser.parse` and `requests.get` and assert article structure.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add tests/test_news_fetcher.py. Mock feedparser.parse and
requests.get (use pytest-mock or unittest.mock).

Cover at minimum:
- fetch_from_rss returns the documented article dict structure
  given a canned feedparser result
- fetch_from_rss returns [] when feed.bozo is True and
  feed.entries is empty
- fetch_from_newsapi returns [] when the API responds with
  status="error"
- fetch_from_newsapi parses items into the documented structure
  on status="ok"
- parse_date handles "Mon, 18 Jan 2026 14:30:00 GMT" and returns a
  formatted string

Confirm pytest tests/ count increases by ~5.
```

- [ ] 🟢 No frontend tests at all — add at least one Vitest test for `SentimentBadge` rendering and one for the `api.js` client (mock axios).

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add frontend tests using Vitest.

In frontend/package.json devDependencies, add: vitest,
@testing-library/react, @testing-library/jest-dom, jsdom. Add a
"test" script: "vitest". Configure jsdom in vite.config.js under
test:{}.

Create frontend/src/components/SentimentBadge.test.jsx with at
least:
- Renders "positive" label and 😊 emoji when sentiment="positive"
- Renders "Unknown" when sentiment is undefined

Create frontend/src/services/api.test.js with at least:
- articlesApi.fetch posts to /fetch with the right body shape
  (mock axios with vi.mock)

Run `npm test` from frontend/ and confirm both pass.
```

## 5. Documentation

- [ ] 🔴 [README.md:1](README.md:1) — CI badge points to a workflow on the `main` branch but the repo is on `master`. The badge will perpetually show "no status" or red. Fix the workflow branch (see DevOps below) — the badge will then work.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README.md line 1 has a CI badge pointing at a workflow that
triggers on `main` but the repo's default branch is `master`. The
badge will never go green.

Two-part fix:
1. In .github/workflows/ci.yml line 5, change `branches: [main]`
   to `branches: [main, master]` (covers both names).
2. In README.md line 1, the badge URL may auto-detect the default
   branch; if it shows "no status" after the CI fix, append
   "?branch=master" to the badge image URL.

Push and confirm the badge renders green on the next commit.

(Land this in the same commit as the CI install-step fix from
section 6.)
```

- [ ] 🔴 [README.md:33](README.md:33) — claims "Real-time Updates: See articles as they're fetched and processed". There is no streaming, SSE, or websockets in the codebase — the frontend polls after the request completes. Either remove the claim or implement streaming (which would be impressive — see section 7).

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README.md line 33 claims "Real-time Updates: See articles as
they're fetched and processed". There is no streaming/SSE/
websockets in the code — the frontend just polls after the request
completes.

Pick one:
1. Quick: delete the line, or rewrite to "Progress feedback during
   fetch" (a loading spinner — what actually happens).
2. Better: implement streaming (see the Q&A streaming task in
   section 7) and keep the claim.

Don't ship claims the code doesn't back up.
```

- [ ] 🔴 [README.md:34](README.md:34) — claims "Interactive Charts: Visualize sentiment distribution and category breakdowns". The dashboard renders CSS bars, not charts. Either install `recharts`/`chart.js` and use it, or rewrite the claim as "visual sentiment bars".

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README.md line 34 claims "Interactive Charts: Visualize sentiment
distribution and category breakdowns". The Dashboard renders CSS
bars, not charts.

Pick one:
1. Quick: rewrite the line to "Sentiment distribution bars and
   category breakdowns" (honest).
2. Better: install recharts (`cd frontend && npm install
   recharts`) and replace the CSS bar block in
   frontend/src/pages/Dashboard.jsx with a real <PieChart> or
   <BarChart>.

If you choose option 2, verify it renders by running `npm run dev`
and visiting the dashboard.
```

- [ ] 🟡 [README.md:114-149](README.md:114) — "Web Interface Screenshots" section has no actual screenshots. Take 3–4 screenshots (Dashboard, Articles, Chat, Trending) and embed them. For a portfolio project, visual proof of the UI is worth more than the README text combined.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README.md "Web Interface Screenshots" section has no actual
screenshots — just text descriptions.

Take 3-4 screenshots of the real running app:
- Dashboard with at least 5 articles fetched
- Articles list page
- Chat conversation
- Trending page

Save them in docs/screenshots/ (create the folder), and embed via
`![Dashboard](docs/screenshots/dashboard.png)` in the README.

Do not generate fake screenshots — these need to be of the actual
app. If the app isn't currently runnable on this machine, leave
this task open and ping the user.
```

- [ ] 🟡 [README.md:29](README.md:29) — claims "Source Comparison View: Side-by-side comparison of how sources cover stories" but [frontend/src/pages/Compare.jsx](frontend/src/pages/Compare.jsx) renders a stacked list, not side-by-side. Either rebuild the UI or rephrase.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README.md line 29 claims "Source Comparison View: Side-by-side
comparison of how sources cover stories" but
frontend/src/pages/Compare.jsx renders a stacked list.

Pick one:
1. Quick: rephrase the README line to "Per-source breakdown of
   coverage on the same story".
2. Better: rewrite Compare.jsx to use CSS grid with each source
   as a column (3 sources side-by-side on desktop, stacked on
   mobile). Show off responsive layout.

If you choose option 2, verify by running the frontend and
checking the Compare page at desktop and mobile widths.
```

- [ ] 🟡 README has no architecture section. Add a small diagram (mermaid works in GitHub markdown) showing CLI/Backend → src/ pipeline modules → Claude/RSS/NewsAPI. Reviewers want to see system thinking, not just feature lists.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README has no architecture section. Add one with a mermaid diagram
(GitHub renders mermaid in markdown natively).

Place after the Features section and before Quick Start. Show:
User → (CLI or React frontend) → FastAPI backend or
NewsSummarizerAgent → src/ pipeline modules (fetcher → summarizer
→ categorizer → tagger → sentiment) → Claude API + RSS/NewsAPI.

Use a ```mermaid``` code fence with a `graph LR` or `flowchart TD`
diagram. Test by viewing the README on github.com after pushing —
confirm it renders.
```

- [ ] 🟡 README has no "Limitations / Known Issues" section. Mention: in-memory state (lost on restart), global state means single-user, no auth, no rate limiting. Being honest about what's not done shows engineering maturity.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README has no "Limitations / Known Issues" section. Add one near
the bottom (before License) listing:
- In-memory state: articles and Q&A history are lost on backend
  restart
- Single-user: backend has a global app_state, multiple users see
  each other's data
- No auth: any client can hit any endpoint
- No rate limiting: /api/fetch fires N Claude calls per request
- Articles are processed sequentially (not concurrently)

Being honest about what's not done signals engineering maturity —
recruiters look for this.
```

- [ ] 🟢 Most docstrings in `src/` are tutorial explanations ("WHAT IS RSS?", "WHY DO WE NEED THIS?"). They were great when learning but read as junior-level in a portfolio. Trim them to short descriptions of args/returns; the WHY belongs in a separate `docs/` if anywhere.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Most docstrings in src/ are tutorial-style ("WHAT IS RSS?",
"WHY DO WE NEED THIS?"). Reads as junior-level in a portfolio.

For each src/*.py file:
- Keep function docstrings but trim to 1-3 lines describing
  args/returns/behavior.
- Delete the giant block-comment headers explaining concepts
  (RSS, LangChain Expression Language, embeddings, etc.).
- Delete the `if __name__ == "__main__":` test blocks at the
  bottom of each file — they're not real tests and they bloat
  the file. The tests/ directory is the real test suite.

After: each file should drop ~30-50% in length. Confirm
pytest tests/ still passes.
```

- [ ] 🟢 No `LICENSE` file in the repo despite README claiming MIT. Add a real `LICENSE` file with the MIT text.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README claims MIT but there is no LICENSE file.

Create LICENSE at the repo root with the standard MIT text. Use
2026 as the year and "Alon Naor" as the copyright holder (matches
the GitHub user AlonNaor22). Standard text:
https://opensource.org/licenses/MIT

One-file task. Commit and push.
```

## 6. DevOps & Production-Readiness

- [ ] 🔴 **Rotate your Anthropic and NewsAPI keys immediately.** The real keys are sitting in plaintext at [.env](.env) on this dev machine. `git log -- .env` confirms it was never committed (good), but the key has been on disk in a portfolio project directory you've likely shared screenshots of and uploaded to backups. Revoke via [Anthropic console](https://console.anthropic.com/) and [NewsAPI dashboard](https://newsapi.org/account), generate new ones, and **never type real keys into a portfolio project's .env again** — use a shell-scoped `export` or a secrets manager.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
The .env file in this repo contains real Anthropic and NewsAPI
keys. Even though .env is in .gitignore and was never committed,
the keys have been on disk in plaintext.

This is a USER task, not an agent task:
1. Go to console.anthropic.com → API Keys → revoke the current
   key, generate a new one.
2. Go to newsapi.org/account → regenerate the API key.
3. Update local .env with the new keys.
4. Confirm `python main.py` and the FastAPI backend still work.

If you're the agent reading this: prompt the user to do the
rotation themselves; do not attempt to revoke keys via any API.
```

- [ ] 🔴 [.github/workflows/ci.yml:5](.github/workflows/ci.yml:5) — workflow triggers on `branches: [main]` but the repo's default branch is `master`. CI literally never runs. Change to `master` (or rename the branch to `main`).

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
.github/workflows/ci.yml line 5 triggers on `branches: [main]`
but the repo's default branch is master. CI never runs.

Fix: change to `branches: [main, master]` (covers either name).
Push and verify the Actions tab on GitHub shows a run for the
next commit.

(Land this in the same commit as the CI install-step fix.)
```

- [ ] 🔴 [.github/workflows/ci.yml:22](.github/workflows/ci.yml:22) — CI only installs `requirements-dev.txt` (just `pytest`). The tests import from `src.categorizer` which imports `langchain_anthropic` — they would fail with `ModuleNotFoundError` if CI actually ran. Add `pip install -r requirements.txt` (and a stub `ANTHROPIC_API_KEY=test` env var so config doesn't blow up).

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
.github/workflows/ci.yml only runs `pip install -r
requirements-dev.txt` (just pytest). Tests import from
src.categorizer which needs langchain-anthropic — they'd fail
with ImportError if CI actually ran.

Fix in ci.yml:
1. Change the install step to:
       pip install -e .[dev]
   (uses the pyproject.toml that already exists; equivalent to
   installing the package + dev extras)
2. Add an env block to the test job:
       env:
         ANTHROPIC_API_KEY: test-key-for-ci
   so config.py's load_dotenv() finds a value even without .env.

Push and verify the next commit's Action run goes green.
```

- [ ] 🔴 No `Dockerfile` or `docker-compose.yml`. For a junior AI/Python role this is now table stakes — a single `docker compose up` to get the whole stack running is the most impressive piece of devops a junior can demonstrate.

```
Prompt for a new chat (model: Opus)
-----------------------------------
No Dockerfile or docker-compose.yml exists. For a junior AI/Python
role, `docker compose up` should bring up the whole stack.

Create:
- backend/Dockerfile — python:3.11-slim base; copies pyproject.toml
  + src/ + backend/; runs `pip install -e .[backend]`; CMD
  `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- frontend/Dockerfile — multi-stage: node:20-alpine to build
  (`npm ci && npm run build`), then nginx:alpine to serve dist/.
- docker-compose.yml at repo root with two services (backend +
  frontend), env_file: ./.env, port mappings 8000 + 5173 (or 80).
- .dockerignore at repo root excluding venv/, node_modules/,
  __pycache__/, .env, *.db, output/.

Add a "Run with Docker" subsection to README's Quick Start.

Verify `docker compose up --build` brings both services up and
the frontend can call the backend.
```

- [ ] 🟡 [requirements.txt:10](requirements.txt:10) — `langchain>=0.1.0` with no upper bound. LangChain had breaking API changes in 0.2 and 0.3. Pin to a range like `langchain>=0.3.0,<0.4.0`. Same issue for `langchain-anthropic>=0.1.0`, `anthropic>=0.18.0`.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
requirements.txt has unpinned upper bounds: langchain>=0.1.0,
langchain-anthropic>=0.1.0, anthropic>=0.18.0. LangChain had
breaking changes in 0.2 and 0.3.

Note: pyproject.toml already pins langchain>=0.3.0,<0.4.0.

Pick one:
1. Delete requirements.txt and update README setup steps to use
   `pip install -e .[backend,dev]` (single source of truth).
2. Update requirements.txt to match pyproject.toml's pins.

Verify a fresh venv install still works.
```

- [ ] 🟡 [backend/main.py:82](backend/main.py:82) — `/api/health` returns `{"status": "healthy"}` unconditionally. It should at least verify `ANTHROPIC_API_KEY` is set and optionally do a cheap upstream check.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
backend/main.py:82 — /api/health returns {"status": "healthy"}
unconditionally. It should verify dependencies are configured.

Fix the handler:
1. Check os.getenv("ANTHROPIC_API_KEY") is set — if not, return
   503 with {"status": "unhealthy", "reason":
   "ANTHROPIC_API_KEY not configured"}.
2. Return {"status": "healthy", "checks": {"anthropic_key":
   "set"}} on success.

Add a test in tests/test_api.py asserting both code paths
(monkey-patch the env var to simulate missing key).
```

- [ ] 🟡 No structured logging. Add `logging` with a JSON formatter in `backend/main.py` and replace `print()` calls in `src/` modules. A senior reviewer will look for this.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
The project uses print() everywhere. Add structured logging.

1. Add python-json-logger to pyproject.toml dependencies.
2. In backend/main.py, configure logging at startup:
       from pythonjsonlogger import jsonlogger
       handler = logging.StreamHandler()
       handler.setFormatter(jsonlogger.JsonFormatter())
       logging.basicConfig(level=logging.INFO, handlers=[handler])
3. Add a middleware that logs each request with method, path,
   status, latency_ms.
4. Replace print() in src/ modules with
   logging.getLogger(__name__).info/warning/error (see the
   print→logging task in section 1).

Verify: backend logs are valid one-line JSON. Bonus: include a
request_id (uuid4) per request in the log records.
```

- [ ] 🟡 No rate limiting on the FastAPI endpoints. The `/api/fetch` endpoint fires off N Claude calls per request — easy to rack up bills. Add `slowapi` or document the limitation.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
No rate limiting on FastAPI endpoints. /api/fetch fires N Claude
calls per request — easy to rack up bills if exposed publicly.

1. Add slowapi to pyproject.toml [backend] extras.
2. In backend/main.py:
       from slowapi import Limiter, _rate_limit_exceeded_handler
       from slowapi.util import get_remote_address
       from slowapi.errors import RateLimitExceeded
       limiter = Limiter(key_func=get_remote_address)
       app.state.limiter = limiter
       app.add_exception_handler(RateLimitExceeded,
                                 _rate_limit_exceeded_handler)
3. Decorate /api/fetch with @limiter.limit("3/minute") and lighter
   endpoints with "30/minute".

Verify with a burst test (4 curls in quick succession to
/api/fetch) — the 4th returns 429.
```

- [ ] 🟡 No frontend `.env.example`. The API base URL is hardcoded to `http://localhost:8000/api` in [frontend/src/services/api.js:3](frontend/src/services/api.js:3) — won't work for any deploy. Use `import.meta.env.VITE_API_URL`.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
frontend/src/services/api.js:3 hardcodes API_BASE_URL =
'http://localhost:8000/api'. Won't work in any deploy.

1. Change to:
   const API_BASE_URL = import.meta.env.VITE_API_URL ||
                        'http://localhost:8000/api';
2. Create frontend/.env.example with:
   VITE_API_URL=http://localhost:8000/api
3. Add VITE_API_URL setup to README's frontend setup step.
4. Add frontend/.env to .gitignore (root .gitignore already
   ignores .env but verify it covers frontend/.env).

Verify the dev server still works without setting the env var
(falls back to localhost).
```

- [ ] 🟢 [.gitignore](.gitignore) is good but consider adding `*.pyc`, `.DS_Store`, `.coverage`, `htmlcov/`, `dist/`, `*.egg-info/` for future-proofing.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
.gitignore is decent but missing some common entries.

Add (one block, well-commented):
- .DS_Store
- .coverage
- htmlcov/
- dist/
- *.egg-info/
- .pytest_cache/

Then if any of these are currently tracked, remove from index:
  git rm -r --cached .pytest_cache  # if tracked
Commit the change.
```

## 7. Impressiveness for Portfolio

- [ ] 🔴 **Add streaming to the Q&A endpoint.** Claude supports server-sent events natively, FastAPI has `StreamingResponse`, and Axios/EventSource handle SSE on the frontend. Watching tokens appear character-by-character is the demo moment that makes a reviewer remember your project. The current setup waits for the entire response then dumps it — feels much slower than it is.

```
Prompt for a new chat (model: Opus)
-----------------------------------
Add server-sent events (SSE) streaming to the Q&A endpoint.
Claude supports streaming natively; FastAPI has StreamingResponse.

Backend (backend/api/routes/qa.py):
- Add POST /api/qa/ask/stream
- Use ChatAnthropic.astream() (or the chain's .astream() equivalent)
- Yield each chunk as `data: {json}\n\n` SSE format
- Wrap in StreamingResponse(media_type="text/event-stream")

Frontend (frontend/src/pages/Chat.jsx):
- For the streaming endpoint, use browser fetch + ReadableStream
  (POST endpoints can't use native EventSource).
- Parse SSE chunks and append each to the latest assistant message
  as it arrives.
- Keep the old non-streaming endpoint as a fallback.

Verify: typing a question shows tokens appearing character-by-
character in the chat UI. Record a screencap for the README.
```

- [ ] 🔴 **Add a real vector-store + RAG flow.** [src/similarity.py:359](src/similarity.py:359) literally contains a comment block titled "ABOUT EMBEDDINGS" that explains the concept but doesn't implement it. Add `langchain-community` + `chromadb` or `faiss-cpu`, embed articles on fetch, do semantic search in `/api/articles/search`. This is the single highest-leverage feature for an AI/Python junior role — it demonstrates you understand the modern RAG stack, not just chat completions.

```
Prompt for a new chat (model: Opus)
-----------------------------------
Add a real RAG (retrieval-augmented generation) flow using
embeddings. This is the highest-leverage portfolio feature for an
AI/Python junior role.

Plan:
1. Add langchain-chroma + chromadb to pyproject.toml dependencies.
2. Create src/rag.py with:
   - embed_articles(articles): converts each article into an
     embedding, stores in a local Chroma collection at ./chroma_db.
   - semantic_search(query, k=5): returns top-k articles by cosine
     similarity.
   - Use HuggingFaceEmbeddings (free, local) or VoyageEmbeddings
     (Anthropic's recommended provider).
3. Wire into backend/api/routes/articles.py: when GET
   /api/articles/search has ?semantic=true, use semantic_search;
   otherwise fall back to the existing keyword search.
4. Wire into src/qa_chain.py: instead of dumping ALL articles into
   the LLM context, do semantic_search(question) and pass only
   top 5. Shrinks token usage and improves answers.

Verify: a question like "What's happening with AI regulation?"
returns articles actually about that topic even when "regulation"
doesn't appear in their summaries.
```

- [ ] 🔴 **Make LLM calls concurrent.** [summarize_articles](src/summarizer.py:205), [categorize_articles](src/categorizer.py:218), [tag_articles](src/tagger.py:276), [analyze_sentiments](src/sentiment.py:339) all loop articles sequentially. With `asyncio.gather` + LangChain's async `.ainvoke`, fetching 15 articles drops from ~30s to ~3s. Reviewers love this.

```
Prompt for a new chat (model: Opus)
-----------------------------------
The four pipeline loops (summarize_articles, categorize_articles,
tag_articles, analyze_sentiments) call Claude sequentially. With
async + asyncio.gather, 15 articles drops from ~30s to ~3s.

Plan for each of the four modules:
1. Add an async sibling:
       async def summarize_article_async(article):
           return await _chain.ainvoke({...})
2. In the batch function, use:
       results = await asyncio.gather(*[
           summarize_article_async(a) for a in articles
       ])
3. Wrap the existing sync batch function to call asyncio.run() on
   the async version, so callers don't change.
4. Add a semaphore (e.g., 5 concurrent) to avoid hitting Anthropic
   rate limits.

Verify pytest tests/ still passes. Fetch 10 articles via CLI and
observe wall-clock time drops 5-10x.

Pair with the "async-ify backend handlers" task in section 3.
```

- [ ] 🟡 Add persistent storage. SQLite via SQLAlchemy is enough — articles, sentiment results, and Q&A history survive restarts. Currently every restart wipes everything (in-memory `app_state`), which makes the app feel like a script.

```
Prompt for a new chat (model: Opus)
-----------------------------------
Add SQLite persistence so articles and Q&A history survive
backend restart. Currently every restart wipes app_state.

Plan:
1. Add SQLAlchemy to pyproject.toml [backend] extras.
2. Create backend/db.py with engine + SessionLocal + Base, using
   DATABASE_URL env var (default sqlite:///./news.db).
3. Define ORM models for Article and ConversationMessage matching
   the Pydantic Article model (pair with section 1's Article task).
4. Update AppState (or replace it) to read/write via SQLAlchemy.
   /api/fetch saves articles; /api/articles reads from DB.
5. Add a startup event in backend/main.py running
   Base.metadata.create_all(engine).
6. Add *.db to .gitignore.

Verify: fetch articles via the UI, kill the backend (Ctrl+C),
restart, GET /api/articles still returns them.
```

- [ ] 🟡 Deploy a live demo. Render/Railway/Fly.io can host the FastAPI backend; Vercel/Netlify the React frontend. A clickable URL in the README is worth more than the rest of the documentation combined.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Deploy a live demo and link it in the README. A clickable URL
beats all other docs combined.

Recommended stack (free tiers exist):
- Backend: Render or Railway. Both auto-deploy on git push.
- Frontend: Vercel or Netlify.

Steps:
1. Add render.yaml or railway.toml at repo root pointing at
   backend/Dockerfile (requires the Docker task from section 6).
2. Set ANTHROPIC_API_KEY + NEWS_API_KEY as platform secrets —
   NEVER commit them.
3. On the frontend deploy, set VITE_API_URL to the deployed
   backend URL.
4. Add a "Live Demo" link + badge near the top of the README.

Optional: add a banner explaining the demo is rate-limited and
single-user.
```

- [ ] 🟡 Convert frontend to TypeScript. `vite` ships with a TS template — straightforward port. For an AI/Python role this is a soft signal that you care about typed APIs end-to-end.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Convert the React frontend from JS to TypeScript.

1. In frontend/, install: typescript, @types/react,
   @types/react-dom, @types/react-router-dom.
2. Add tsconfig.json (use Vite's recommended config: "compilerOptions":
   {"target":"ES2020", "lib":["ES2020","DOM"], "jsx":"react-jsx",
   "strict":true, "esModuleInterop":true}).
3. Rename .jsx → .tsx and .js → .ts in frontend/src/.
4. Define Article + ApiResponse types in src/types.ts mirroring the
   Pydantic Article model.
5. Update src/services/api.js → api.ts with typed axios responses.
6. Fix any type errors `npm run build` surfaces.

Verify npm run build succeeds with zero errors and the app still
runs in npm run dev.
```

- [ ] 🟡 The project is at `C:\Users\alonn\Computer-Projects\Github protfolio\...` — "Github protfolio" is misspelled (should be "portfolio"). Rename the parent folder before screenshots/recordings.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
The project lives at C:\Users\alonn\Computer-Projects\Github
protfolio\... — "protfolio" should be "portfolio". This will show
up in any screencap.

This is a USER task. Rename via Windows Explorer or PowerShell:
   Rename-Item "C:\Users\alonn\Computer-Projects\Github protfolio" `
              "C:\Users\alonn\Computer-Projects\Github portfolio"

Then re-open the project in VS Code / Claude Code from the new
path. Update any tools/IDE configs that pin the path.
```

- [ ] 🟡 No observability — add `logfire` or OpenTelemetry traces around the LangChain calls. Even basic timing logs ("summarize took 2.3s", "categorize took 0.8s") signal you think about latency.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add basic observability. Even simple timing logs ("summarize:
2.3s") signal you think about latency.

Pick one:
1. Cheap: write a @timeit decorator (uses time.monotonic +
   logger.info around start/end). Apply to summarize_article,
   categorize_article, tag_article, analyze_sentiment.
2. Impressive: install logfire (free tier, made by Pydantic team)
   or set up OpenTelemetry with LangChain instrumentation
   (langchain-community has built-in callbacks).

Verify timing logs appear when running the pipeline. If using
logfire/OTel, add the dashboard URL to the README.
```

- [ ] 🟢 Repo name `news-summarizer-agent` is fine but the README hero could lead with a one-line value prop and a screenshot/GIF before the feature list. Recruiters skim — make the first screen sell the project.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
README currently leads with a CI badge and a long feature list.
Recruiters skim — make the first screen sell the project.

Restructure the top of README.md:
1. One-line value prop (h1 + a tagline like "Fetch, summarize,
   and chat with the news using Claude AI").
2. A screenshot or GIF of the running app (use screenshots from
   section 5, or record a short asciinema/Loom).
3. A "Live Demo" link if deployed (section 7 deploy task).
4. THEN the feature list.

Goal: someone scrolls for 3 seconds and gets why this project
exists.
```

- [ ] 🟢 Consider adding a "How it works" section with a request-flow diagram showing Article → Summarize → Categorize → Tag → Sentiment → store, then user Q&A. The pipeline is the most impressive part of the code; show it visually.

```
Prompt for a new chat (model: Sonnet)
-------------------------------------
Add a "How it works" section to README between Features and Quick
Start. The pipeline is the impressive part of the code — show it
visually.

Use two mermaid diagrams:
1. Article processing pipeline:
   Article → Fetcher → Summarizer → Categorizer → Tagger →
   Sentiment → Store
2. Q&A flow:
   User Question → (Semantic Search if RAG done) → Articles
   Context → Claude → Streamed Response (if streaming done)

Use ```mermaid``` code fences. Verify rendering on github.com
after pushing.
```

## Quick Wins

The three under-30-minute tasks with the highest portfolio impact:

1. 🔴 **Rotate the exposed API keys** in [.env](.env) and stop keeping real production keys in dev project directories. ~10 minutes via Anthropic + NewsAPI consoles.
2. 🔴 **Fix the broken CI workflow** — change `branches: [main]` → `branches: [master]` in [ci.yml:5](.github/workflows/ci.yml:5), add `pip install -e .[dev]` to the install step at [ci.yml:22](.github/workflows/ci.yml:22), add `ANTHROPIC_API_KEY: test-key` as a job env var. The badge in README will go green and recruiters skim that first. ~15 minutes.
3. 🔴 **Remove the false feature claims** in [README.md:32-36](README.md:32) — drop "Real-time Updates" and "Interactive Charts" (or downgrade language to match what's actually there). Mismatched README/code is the single fastest credibility loss in a portfolio review. ~5 minutes.
