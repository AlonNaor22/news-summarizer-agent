"""Entry point shim — the real CLI lives in the :mod:`cli` package.

Kept at the repo root so ``python main.py`` and the ``news-summarizer``
console script (see ``pyproject.toml``) both continue to work.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from cli.main import main

if __name__ == "__main__":
    main()
