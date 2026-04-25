# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the API

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings transformers
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run the development server
uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs` after starting.

## Database

The `startup` event that auto-creates tables is commented out in [app/main.py](app/main.py). The DB has already been initialized — `data/app.db` exists on disk with tables created. To re-create from scratch:

```python
from app.infrastructure.database import Base, engine
Base.metadata.create_all(bind=engine)
```

The SQLite file is written to `data/app.db`.

## Architecture

The project has two independent components:

**`app/` — FastAPI backend (main codebase)**

Follows a strict layered architecture:
- `app/main.py` — App factory, CORS middleware, router registration
- `app/core/config.py` — Pydantic `Settings` loaded from `.env` (defaults: `Chat Analytics API`, `0.1.0`, `/api`)
- `app/core/stopwords.py` — Portuguese stopword list for word-frequency filtering
- `app/core/logging.py` — Empty file (0 bytes), not yet configured
- `app/infrastructure/database.py` — SQLAlchemy engine + session (`SessionLocal`)
- `app/infrastructure/ml.py` — HuggingFace sentiment pipeline (`tabularisai/multilingual-sentiment-analysis`), cached with `lru_cache`
- `app/models/message.py` — `Message` SQLAlchemy ORM model
- `app/repositories/messages.py` — DB query functions (`create_message`, `list_messages_by_live`)
- `app/services/chat.py` — `ChatService`: business logic for `save_message`, `word_frequency`, `sentiment_summary`
- `app/schemas/chat.py` — Pydantic v2 request/response schemas
- `app/api/deps.py` — FastAPI dependency injection: `get_db` (DB session) and `get_chat_service` (instantiates `ChatService`)
- `app/api/routes/chat.py` — Three endpoints under `/api/chat/`

**`frontend/` — Chrome extension (PulsoDaLive)**

Manifest v3 extension that injects `content.js` into YouTube live pages. It observes the YouTube chat iframe (`#chatframe`) for new DOM nodes and POSTs each message to `http://127.0.0.1:8000/save-message`. Load via Chrome's "Load unpacked" from the `frontend/` folder.

**Note:** The extension posts to `/save-message` but the current API route is `POST /api/chat/messages` — these are mismatched.

## Known incomplete areas

- **Sentiment analysis is stubbed**: The ML pipeline import and call are commented out in `app/services/chat.py`. `sentiment_summary` bypasses the model (`results = texts`) and returns hardcoded values — `resumo` is the string `"test"`, and the model name is a placeholder (`lct-big-science/bertimbau-base-sentiment-analysis-portuguese`).
- **`word_frequency` calls the service twice** in `app/api/routes/chat.py` (line 17 result is discarded, line 20 calls it again — bug).
- **`backend/`** contains an older prototype version of the app — not the active codebase.
- **No test suite** exists. The README recommends `TestClient` (FastAPI) for endpoint tests and unit tests for services/repositories.
- **`app/core/logging.py`** is an empty file — never wired into the app.

## Environment variables

All settings are in `app/core/config.py` via Pydantic `BaseSettings`. Override via `.env`:

```
PROJECT_NAME=Chat Analytics API
VERSION=0.1.0
API_PREFIX=/api
```
