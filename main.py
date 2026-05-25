"""Entry point shim — the real CLI lives in the :mod:`cli` package.

Kept at the repo root so ``python main.py`` and the ``news-summarizer``
console script (see ``pyproject.toml``) both continue to work.
"""

from cli.main import main

if __name__ == "__main__":
    main()
