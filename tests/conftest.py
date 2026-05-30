import os
import tempfile

# Point the SQLAlchemy engine at a temp file before any backend.* import that
# would otherwise lock onto the real ./news.db. Removing any prior copy keeps
# tests starting from a clean slate.
if "DATABASE_URL" not in os.environ:
    _test_db_path = os.path.join(tempfile.gettempdir(), "news_summarizer_test.db")
    try:
        if os.path.exists(_test_db_path):
            os.remove(_test_db_path)
    except OSError:
        pass
    os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

# Must be non-empty before any module reads config.ANTHROPIC_API_KEY at import time.
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = "test-key-for-ci"

# Create tables once for the test DB so per-test fixtures can DELETE FROM them.
from backend.db import init_db  # noqa: E402

init_db()
