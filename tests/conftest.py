import os

# Must be non-empty before any module reads config.ANTHROPIC_API_KEY at import time.
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = "test-key-for-ci"
