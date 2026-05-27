# Backend image: FastAPI app served by uvicorn.
# Build context must be the repo root so we can copy pyproject.toml + src/ + backend/.
#   docker build -f backend/Dockerfile -t news-summarizer-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Files required by the editable install. pyproject.toml declares main/config as
# top-level py-modules and reads README.md for the package description, so all
# four must be present for `pip install -e .` to succeed.
COPY pyproject.toml README.md main.py config.py ./
COPY src/ ./src/
COPY backend/ ./backend/

RUN pip install -e .[backend]

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
