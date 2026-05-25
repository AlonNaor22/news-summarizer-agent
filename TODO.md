# TODO — News Summarizer Agent

> Audit date: 2026-05-25

**Summary:** Strong feature breadth (CLI + FastAPI + React all wired to a real Claude/LangChain pipeline with sentiment, trending, similarity, and multi-source comparison) is undermined by a 1571-line god-class CLI, an LLM that gets re-instantiated for every single article, broken CI, and a real Anthropic API key sitting in plaintext on disk — the kind of issues a senior reviewer would flag in the first ten minutes.

## 1. Code Quality

- [ ] 🔴 Split [main.py](main.py) (1571 lines, `NewsSummarizerAgent` class) into focused modules — at minimum `cli/commands.py`, `cli/display.py`, `cli/state.py`, `cli/main.py`. A single-file CLI of this size is the first thing a reviewer will mention.
- [x] 🔴 ~~Stop re-creating the `ChatAnthropic` LLM inside every per-article call~~ — each `src/` module now has a lazy `_chain` singleton (e.g. [summarizer.py:121](src/summarizer.py:121)), so the LLM client is built once per process instead of once per article.
- [x] 🔴 ~~Remove the duplicated `sys.path.append(...)` hack~~ — added [pyproject.toml](pyproject.toml) (installable with `pip install -e .`) and stripped the path hack from all 9 `src/` files and all 7 `backend/api/` files. The single remaining hack lives in [backend/main.py](backend/main.py) so `uvicorn backend.main:app` keeps working without an install step.
- [ ] 🔴 Replace the `list[dict]` article representation with a Pydantic `Article` model. Every module accesses fields via `.get("summary", article.get("description", ""))` which is fragile and untyped. Define it once in `src/models.py`.
- [x] 🟡 ~~[main.py:1559](main.py:1559) — bare-ish `except Exception as e` in the main loop~~ — now catches `KeyboardInterrupt`, `EOFError`, and `(ValueError, KeyError, IndexError)` explicitly so unexpected exceptions propagate with a real traceback.
- [ ] 🟡 Replace manual LLM output parsing in [src/sentiment.py:201](src/sentiment.py:201), [src/tagger.py:121](src/tagger.py:121), [src/categorizer.py:283](src/categorizer.py:283), [src/trending.py:325](src/trending.py:325), [src/similarity.py:517](src/similarity.py:517), [src/comparator.py:338](src/comparator.py:338) with structured outputs (LangChain `with_structured_output()` or Anthropic tool-use). The current `line.split(":")` parsing is fragile and breaks silently when Claude varies its format. **This is a major portfolio talking point** — junior candidates almost never know this.
- [x] 🟡 ~~Unused imports in [main.py:33](main.py:33)~~ — trimmed to just `fetch_news`.
- [x] 🟡 ~~Magic numbers scattered across the codebase~~ — added `SIMILARITY_THRESHOLDS` and `WORDS_PER_MINUTE` to [config.py](config.py); removed the hardcoded `max_per_source=3` override in `main.py` so it now uses `MAX_ARTICLES_PER_SOURCE` from config.
- [x] 🟡 ~~`MAX_TOKENS = 500` overridden in every module~~ — added a single `LLM_SETTINGS` dict in [config.py](config.py) keyed by task (`summarize`, `categorize`, `tag`, `sentiment`, `trending`, `similarity`, `comparison`, `qa`); every `create_llm()` now reads its temperature and max_tokens from that one place.
- [x] 🟡 ~~Most CLI methods in [main.py](main.py) have no return type hints~~ — added `-> None` (or appropriate `int | None` for optional args) to all 22 public/private methods of `NewsSummarizerAgent`.
- [x] 🟢 ~~[src/__init__.py](src/__init__.py) is a tutorial comment with no code~~ — replaced with a one-line docstring.
- [ ] 🟢 Print statements are used as logging throughout `src/` ([summarizer.py:190](src/summarizer.py:190), [news_fetcher.py:80](src/news_fetcher.py:80), etc.). Replace with `logging.getLogger(__name__)` — library code shouldn't print.

## 2. Error Handling

- [ ] 🔴 [src/news_fetcher.py:81](src/news_fetcher.py:81) — `feedparser.parse(feed_url)` has **no timeout**. A slow RSS feed will hang the entire fetch. Wrap with `requests.get(url, timeout=10)` and pass bytes to feedparser.
- [ ] 🔴 [backend/api/routes/articles.py:87](backend/api/routes/articles.py:87), [qa.py:66](backend/api/routes/qa.py:66) — `raise HTTPException(status_code=500, detail=str(e))` leaks raw Python exception messages (including potential stack-trace info and API keys in some LangChain errors) to HTTP clients. Log the exception server-side and return a sanitized message.
- [ ] 🟡 No retry/backoff on Anthropic API calls. A transient 529 rate-limit kills the whole fetch pipeline. Use `tenacity` for exponential backoff on `summarize_articles`, `categorize_articles`, `tag_articles`, `analyze_sentiments` — these are the four loops that hit Claude N times.
- [ ] 🟡 [src/news_fetcher.py:313](src/news_fetcher.py:313) — NewsAPI request has `timeout=10` but the except block swallows the error with a print and returns `[]`. The caller can't distinguish "no articles" from "network down" from "bad API key". Return a `Result` type or raise a custom exception.
- [ ] 🟡 [backend/api/routes/qa.py:36](backend/api/routes/qa.py:36) — `request.question` has no validation. A 100KB question or empty string both reach the LLM. Add `Field(..., min_length=1, max_length=2000)` to the Pydantic model.
- [ ] 🟡 [main.py:653](main.py:653) — `os.makedirs(output_dir)` will silently re-raise on race condition. Use `os.makedirs(output_dir, exist_ok=True)`.
- [ ] 🟡 Empty `except (ValueError, IndexError)` in [src/trending.py:415](src/trending.py:415) and [src/similarity.py:579](src/similarity.py:579) silently swallows parse errors and leaves fields at default values. At minimum, log a warning.

## 3. Architecture & Structure

- [ ] 🔴 [backend/api/dependencies.py:37](backend/api/dependencies.py:37) — `app_state = AppState()` is a module-level global mutable singleton. Every user shares the same articles and Q&A history. Acceptable for a demo, but you need to either acknowledge this in the README or move to a per-session store (Redis, in-memory dict keyed by session ID). At minimum, document the limitation.
- [ ] 🔴 [main.py](main.py) `NewsSummarizerAgent` mixes business logic, display rendering, command parsing, and state management. Extract `Display` (all the `print` calls and box-drawing), `CommandRouter` (the giant `process_command` if/elif chain), and `AgentState` (articles + caches + qa_chain).
- [ ] 🔴 The backend duplicates the orchestration logic from `main.py`'s `fetch_news`. Both call `summarize_articles → categorize_articles → tag_articles → analyze_sentiments` in sequence. Extract this to `src/pipeline.py` and call it from both entry points.
- [ ] 🟡 FastAPI route handlers are `async def` but call **synchronous** LangChain code that blocks the event loop ([backend/api/routes/articles.py:64](backend/api/routes/articles.py:64), [qa.py:57](backend/api/routes/qa.py:57)). Either make them `def` (let FastAPI run them in a threadpool) or use `await asyncio.to_thread(...)` for the LLM calls. As-is, the server serves one request at a time during a fetch.
- [ ] 🟡 [config.py:118](config.py:118) defines `CORS_ORIGINS` but [backend/main.py:52](backend/main.py:52) hardcodes the same list instead of importing from config. Either source from config or delete the dead constant in config.
- [ ] 🟡 [src/comparator.py:51](src/comparator.py:51) imports `from src.similarity import calculate_combined_similarity` while all other src/ modules import via the sys.path hack. Inconsistent — a sign the package boundary isn't well-defined.
- [ ] 🟢 [src/qa_chain.py:115](src/qa_chain.py:115) — `_create_chain` is called once in `__init__` but `_format_articles_for_context` is recomputed on every `ask()`. For a long conversation with 30 articles, this re-formats the context 30 times. Cache it when articles are loaded.

## 4. Tests

- [ ] 🔴 No tests cover any module that calls Claude — [src/summarizer.py](src/summarizer.py), [src/sentiment.py](src/sentiment.py), [src/trending.py](src/trending.py), [src/comparator.py](src/comparator.py), [src/qa_chain.py](src/qa_chain.py). Add tests that mock `ChatAnthropic` (use `unittest.mock.patch`) — being able to test LLM code without hitting the API is a top-tier portfolio skill.
- [ ] 🔴 No tests for any FastAPI endpoint. Add `tests/test_api.py` using `fastapi.testclient.TestClient` — covers articles, sentiment, trending, qa routes at minimum. A reviewer can run this in 10 seconds to verify the API contract.
- [ ] 🟡 [tests/conftest.py:5](tests/conftest.py:5) — `sample_article` fixture is defined but never used by any test. Either use it or delete it.
- [ ] 🟡 [tests/test_categorizer.py](tests/test_categorizer.py) only tests pure-Python helpers (`clean_category`, `parse_multi_category_response`, `group_by_category`) — these are the easy bits. Tests don't cover the full `categorize_article` pipeline because there's no LLM mocking infrastructure. Add it.
- [ ] 🟡 No edge-case tests for empty input, malformed Claude responses, or NewsAPI 401/429 errors. Add tests asserting that `parse_sentiment_response("garbage")` returns the documented default rather than crashing.
- [ ] 🟡 No tests for [src/news_fetcher.py](src/news_fetcher.py). Mock `feedparser.parse` and `requests.get` and assert article structure.
- [ ] 🟢 No frontend tests at all — add at least one Vitest test for `SentimentBadge` rendering and one for the `api.js` client (mock axios).

## 5. Documentation

- [ ] 🔴 [README.md:1](README.md:1) — CI badge points to a workflow on the `main` branch but the repo is on `master`. The badge will perpetually show "no status" or red. Fix the workflow branch (see DevOps below) — the badge will then work.
- [ ] 🔴 [README.md:33](README.md:33) — claims "Real-time Updates: See articles as they're fetched and processed". There is no streaming, SSE, or websockets in the codebase — the frontend polls after the request completes. Either remove the claim or implement streaming (which would be impressive — see section 7).
- [ ] 🔴 [README.md:34](README.md:34) — claims "Interactive Charts: Visualize sentiment distribution and category breakdowns". The dashboard renders CSS bars, not charts. Either install `recharts`/`chart.js` and use it, or rewrite the claim as "visual sentiment bars".
- [ ] 🟡 [README.md:114-149](README.md:114) — "Web Interface Screenshots" section has no actual screenshots. Take 3–4 screenshots (Dashboard, Articles, Chat, Trending) and embed them. For a portfolio project, visual proof of the UI is worth more than the README text combined.
- [ ] 🟡 [README.md:29](README.md:29) — claims "Source Comparison View: Side-by-side comparison of how sources cover stories" but [frontend/src/pages/Compare.jsx](frontend/src/pages/Compare.jsx) renders a stacked list, not side-by-side. Either rebuild the UI or rephrase.
- [ ] 🟡 README has no architecture section. Add a small diagram (mermaid works in GitHub markdown) showing CLI/Backend → src/ pipeline modules → Claude/RSS/NewsAPI. Reviewers want to see system thinking, not just feature lists.
- [ ] 🟡 README has no "Limitations / Known Issues" section. Mention: in-memory state (lost on restart), global state means single-user, no auth, no rate limiting. Being honest about what's not done shows engineering maturity.
- [ ] 🟢 Most docstrings in `src/` are tutorial explanations ("WHAT IS RSS?", "WHY DO WE NEED THIS?"). They were great when learning but read as junior-level in a portfolio. Trim them to short descriptions of args/returns; the WHY belongs in a separate `docs/` if anywhere.
- [ ] 🟢 No `LICENSE` file in the repo despite README claiming MIT. Add a real `LICENSE` file with the MIT text.

## 6. DevOps & Production-Readiness

- [ ] 🔴 **Rotate your Anthropic and NewsAPI keys immediately.** The real keys are sitting in plaintext at [.env](.env) on this dev machine. `git log -- .env` confirms it was never committed (good), but the key has been on disk in a portfolio project directory you've likely shared screenshots of and uploaded to backups. Revoke via [Anthropic console](https://console.anthropic.com/) and [NewsAPI dashboard](https://newsapi.org/account), generate new ones, and **never type real keys into a portfolio project's .env again** — use a shell-scoped `export` or a secrets manager.
- [ ] 🔴 [.github/workflows/ci.yml:5](.github/workflows/ci.yml:5) — workflow triggers on `branches: [main]` but the repo's default branch is `master`. CI literally never runs. Change to `master` (or rename the branch to `main`).
- [ ] 🔴 [.github/workflows/ci.yml:22](.github/workflows/ci.yml:22) — CI only installs `requirements-dev.txt` (just `pytest`). The tests import from `src.categorizer` which imports `langchain_anthropic` — they would fail with `ModuleNotFoundError` if CI actually ran. Add `pip install -r requirements.txt` (and a stub `ANTHROPIC_API_KEY=test` env var so config doesn't blow up).
- [ ] 🔴 No `Dockerfile` or `docker-compose.yml`. For a junior AI/Python role this is now table stakes — a single `docker compose up` to get the whole stack running is the most impressive piece of devops a junior can demonstrate.
- [ ] 🟡 [requirements.txt:10](requirements.txt:10) — `langchain>=0.1.0` with no upper bound. LangChain had breaking API changes in 0.2 and 0.3. Pin to a range like `langchain>=0.3.0,<0.4.0`. Same issue for `langchain-anthropic>=0.1.0`, `anthropic>=0.18.0`.
- [ ] 🟡 [backend/main.py:82](backend/main.py:82) — `/api/health` returns `{"status": "healthy"}` unconditionally. It should at least verify `ANTHROPIC_API_KEY` is set and optionally do a cheap upstream check.
- [ ] 🟡 No structured logging. Add `logging` with a JSON formatter in `backend/main.py` and replace `print()` calls in `src/` modules. A senior reviewer will look for this.
- [ ] 🟡 No rate limiting on the FastAPI endpoints. The `/api/fetch` endpoint fires off N Claude calls per request — easy to rack up bills. Add `slowapi` or document the limitation.
- [ ] 🟡 No frontend `.env.example`. The API base URL is hardcoded to `http://localhost:8000/api` in [frontend/src/services/api.js:3](frontend/src/services/api.js:3) — won't work for any deploy. Use `import.meta.env.VITE_API_URL`.
- [ ] 🟢 [.gitignore](.gitignore) is good but consider adding `*.pyc`, `.DS_Store`, `.coverage`, `htmlcov/`, `dist/`, `*.egg-info/` for future-proofing.

## 7. Impressiveness for Portfolio

- [ ] 🔴 **Add streaming to the Q&A endpoint.** Claude supports server-sent events natively, FastAPI has `StreamingResponse`, and Axios/EventSource handle SSE on the frontend. Watching tokens appear character-by-character is the demo moment that makes a reviewer remember your project. The current setup waits for the entire response then dumps it — feels much slower than it is.
- [ ] 🔴 **Add a real vector-store + RAG flow.** [src/similarity.py:359](src/similarity.py:359) literally contains a comment block titled "ABOUT EMBEDDINGS" that explains the concept but doesn't implement it. Add `langchain-community` + `chromadb` or `faiss-cpu`, embed articles on fetch, do semantic search in `/api/articles/search`. This is the single highest-leverage feature for an AI/Python junior role — it demonstrates you understand the modern RAG stack, not just chat completions.
- [ ] 🔴 **Make LLM calls concurrent.** [summarize_articles](src/summarizer.py:205), [categorize_articles](src/categorizer.py:218), [tag_articles](src/tagger.py:276), [analyze_sentiments](src/sentiment.py:339) all loop articles sequentially. With `asyncio.gather` + LangChain's async `.ainvoke`, fetching 15 articles drops from ~30s to ~3s. Reviewers love this.
- [ ] 🟡 Add persistent storage. SQLite via SQLAlchemy is enough — articles, sentiment results, and Q&A history survive restarts. Currently every restart wipes everything (in-memory `app_state`), which makes the app feel like a script.
- [ ] 🟡 Deploy a live demo. Render/Railway/Fly.io can host the FastAPI backend; Vercel/Netlify the React frontend. A clickable URL in the README is worth more than the rest of the documentation combined.
- [ ] 🟡 Convert frontend to TypeScript. `vite` ships with a TS template — straightforward port. For an AI/Python role this is a soft signal that you care about typed APIs end-to-end.
- [ ] 🟡 The project is at `C:\Users\alonn\Computer-Projects\Github protfolio\...` — "Github protfolio" is misspelled (should be "portfolio"). Rename the parent folder before screenshots/recordings.
- [ ] 🟡 No observability — add `logfire` or OpenTelemetry traces around the LangChain calls. Even basic timing logs ("summarize took 2.3s", "categorize took 0.8s") signal you think about latency.
- [ ] 🟢 Repo name `news-summarizer-agent` is fine but the README hero could lead with a one-line value prop and a screenshot/GIF before the feature list. Recruiters skim — make the first screen sell the project.
- [ ] 🟢 Consider adding a "How it works" section with a request-flow diagram showing Article → Summarize → Categorize → Tag → Sentiment → store, then user Q&A. The pipeline is the most impressive part of the code; show it visually.

## Quick Wins

The three under-30-minute tasks with the highest portfolio impact:

1. 🔴 **Rotate the exposed API keys** in [.env](.env) and stop keeping real production keys in dev project directories. ~10 minutes via Anthropic + NewsAPI consoles.
2. 🔴 **Fix the broken CI workflow** — change `branches: [main]` → `branches: [master]` in [ci.yml:5](.github/workflows/ci.yml:5), add `pip install -r requirements.txt` to the install step at [ci.yml:22](.github/workflows/ci.yml:22), add `ANTHROPIC_API_KEY: test-key` as a job env var. The badge in README will go green and recruiters skim that first. ~15 minutes.
3. 🔴 **Remove the false feature claims** in [README.md:32-36](README.md:32) — drop "Real-time Updates" and "Interactive Charts" (or downgrade language to match what's actually there). Mismatched README/code is the single fastest credibility loss in a portfolio review. ~5 minutes.
