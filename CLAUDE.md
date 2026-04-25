# CLAUDE.md

Guia para Claude Code ao trabalhar neste repositório.

## Running the API

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Run the development server
uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs` after starting.

## Database

The `startup` event that auto-creates tables is **commented out** in [app/main.py](app/main.py). The DB has already been initialized — `data/app.db` exists on disk (16 KB). To re-create from scratch:

```python
from app.infrastructure.database import Base, engine
Base.metadata.create_all(bind=engine)
```

The SQLite file is written to `data/app.db`.

There are also two other SQLite databases from the old prototype:
- `backend/pulso_da_live.db` (16 KB) — from `backend/` prototype
- `pulso_da_live.db` (280 KB) — root-level, likely contains real/test data from the older version

## Repository overview

The repo has **three** distinct components:

### 1. `app/` — FastAPI backend (main codebase)

Strict layered architecture:

| Layer | File | Role |
|---|---|---|
| Entry | `app/main.py` | App factory, CORS middleware, router registration, healthcheck. Startup event (`on_startup`) commented out. |
| Config | `app/core/config.py` | Pydantic `Settings` via `pydantic-settings`, loads from `.env`. Defaults: `Chat Analytics API`, `0.1.0`, `/api`. |
| Config | `app/core/stopwords.py` | `PORTUGUESE_STOPWORDS` — ~200 Portuguese stopwords for word-frequency filtering. |
| Config | `app/core/logging.py` | **Empty file (0 bytes)** — never wired into the app. |
| Infra | `app/infrastructure/database.py` | SQLAlchemy engine + `SessionLocal`. SQLite at `data/app.db`. Uses `check_same_thread=False`. |
| Infra | `app/infrastructure/ml.py` | HuggingFace `pipeline` for `tabularisai/multilingual-sentiment-analysis`, cached via `@lru_cache`. |
| Model | `app/models/message.py` | `Message` ORM: `id`, `live_id` (str, indexed), `author`, `message` (Text), `created_at` (datetime with tz). |
| Repository | `app/repositories/messages.py` | `create_message()`, `list_messages_by_live()` — both straightforward SQLAlchemy queries. |
| Schema | `app/schemas/chat.py` | Pydantic v2 models: `ChatMessage` (input), `MessageResponse` (with `from_attributes=True`), `WordFrequencyItem`/`WordFrequencyResponse`, `SentimentResponse`. |
| DI | `app/api/deps.py` | `get_db()` — yields a `SessionLocal`, closes on teardown; `get_chat_service()` — instantiates `ChatService(db)`. |
| Route | `app/api/routes/chat.py` | Three endpoints under `/api/chat/` (see below). |
| Service | `app/services/chat.py` | `ChatService` — business logic. |

#### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Healthcheck → `{"status": "online"}` |
| `POST` | `/api/chat/messages` | Save a message. Body: `{live_id, author, message}` → `MessageResponse` |
| `GET` | `/api/chat/{live_id}/word-frequency?top_n=10` | Top-N words (stopwords removed) |
| `GET` | `/api/chat/{live_id}/sentiment` | Sentiment analysis summary (currently **broken**, see known issues) |

### 2. `frontend/` — Chrome extension (PulsoDaLive)

Manifest v3 extension that injects into YouTube live pages.

| File | Role |
|---|---|
| `manifest.json` | v3 manifest. Matches `*://www.youtube.com/watch?v=*`. Host permission to `http://127.0.0.1:8000/*`. |
| `content.js` | **Active version (v4)**. Finds `#chatframe` iframe, waits for load, observes `#items.yt-live-chat-item-list-renderer` for new DOM nodes. POSTs author + message + `live_id` (from URL) to `http://127.0.0.1:8000/save-message`. |
| `bb.js` | **Older version (v1)** of content.js. Still present but unused. |

**Note:** The extension POSTs to `/save-message` but the actual API route is `POST /api/chat/messages` — these are **mismatched**. The extension will get a 404.

### 3. `backend/` — Older prototype (inactive)

A monolithic FastAPI prototype with all logic inline (no layered architecture). Files:
- `backend/main.py` — Everything in one file: models, routes, CORS, DB.
- `backend/database.py` — Its own SQLAlchemy engine, writes to `backend/pulso_da_live.db`.
- `backend/models.py` — `Message` ORM with slightly different schema (`timestamp` vs `created_at`, uses `server_default=func.now()`).
- Various `chat_log.txt`, `chat_data.json` files — captured data dumps.

## Known bugs and incomplete areas

### Sentiment analysis is broken (not just stubbed)

In `app/services/chat.py`:
- The ML pipeline import and initialization are **commented out** (`# from app.infrastructure.ml import get_sentiment_pipeline`)
- `results = texts` assigns the raw string list to `results` — the next line `result["label"]` would raise **`TypeError: string indices must be integers`** on any non-empty live
- `summary["resumo"]` would also raise **`KeyError`** — the dict has keys `"Positivo"`, `"Negativo"`, `"Neutro"`, not `"resumo"`
- The model name field is a placeholder: `lct-big-science/bertimbau-base-sentiment-analysis-portuguese` (this model doesn't exist on HuggingFace)

**Result:** The `GET /{live_id}/sentiment` endpoint crashes with an unhandled exception for any live that has messages.

### `word_frequency` calls the service twice

In `app/api/routes/chat.py`:
- Line 17: `freq = service.word_frequency(live_id, top_n)` — result discarded
- Line 20: `freq_tuples = service.word_frequency(live_id, top_n)` — actual result used
- The first call is dead code that duplicates DB work.

### Extension-to-API URL mismatch

The Chrome extension (`content.js`) sends POST to `http://127.0.0.1:8000/save-message`. The actual route is `POST /api/chat/messages` under the `/api` prefix. The payload shape (author, message, live_id) matches the `ChatMessage` schema, so only the URL needs fixing.

### DB auto-creation on startup is disabled

The `@app.on_event("startup")` block in `app/main.py` that calls `Base.metadata.create_all(bind=engine)` and preloads the sentiment pipeline is **fully commented out**.

### `app/core/logging.py` is empty

The file exists but is 0 bytes. No logger is configured anywhere in the app.

### No test suite

No tests exist anywhere in the repo. The README recommends using `TestClient` (FastAPI) for endpoint tests and unit tests for services/repositories.

### `requirements.txt` has torch commented out

```
#pip install torch==2.2.0+cpu --index-url https://download.pytorch.org/whl/cpu
#torch
```
Torch is needed for `transformers` but isn't auto-installed — developer must install manually.

### Model mismatch in ML config

`app/infrastructure/ml.py` lists `tabularisai/multilingual-sentiment-analysis` but `app/services/chat.py` hardcodes `lct-big-science/bertimbau-base-sentiment-analysis-portuguese` in the response. The sentiment service also references a `label_map` mapping `"1 star" → Negativo`, `"3 stars" → Neutro`, `"5 stars" → Positivo` — this mapping corresponds to the **tabularisai** model's output, not the hardcoded one.

## Environment variables

All settings in `app/core/config.py` via Pydantic `BaseSettings`. Override via `.env`:

```
PROJECT_NAME=Chat Analytics API
VERSION=0.1.0
API_PREFIX=/api
```

Full settings with defaults:

| Variable | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `Chat Analytics API` | API title in Swagger |
| `VERSION` | `0.1.0` | API version |
| `API_PREFIX` | `/api` | Prefix for all routes |
| `DOCS_URL` | `/docs` | Swagger UI path |
| `REDOC_URL` | `/redoc` | ReDoc path |
| `OPENAPI_URL` | `/openapi.json` | OpenAPI schema path |
| `CORS_ALLOW_ORIGINS` | `["*"]` | CORS origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | CORS credentials |
| `CORS_ALLOW_METHODS` | `["*"]` | CORS methods |
| `CORS_ALLOW_HEADERS` | `["*"]` | CORS headers |

## Oddities / minor findings

- `app/api/__init__.py` and `app/infrastructure/__init__.py` are **missing** — the packages still work via implicit namespace packages (Python 3.3+), but explicit `__init__.py` files are conventional.
- `app/.github/` is an **empty directory** — likely a leftover from GitHub template generation.
- `app/.continue/agents/new-agent.yaml` is an **example agent config** for the Continue.dev IDE extension (gitignored).
- `.vscode/settings.json` and `app/.vscode/settings.json` both contain only `{"nuxt.isNuxtApp": false}` — unrelated Nuxt.js setting.
- `start-claude.sh` is a commented-out script to run Claude Code CLI with Ollama API — not intended for normal use.
