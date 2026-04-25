# CLAUDE.md

Guia para Claude Code ao trabalhar neste repositório.

## Running the API

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (tabelas são criadas automaticamente na inicialização)
uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs` after starting.

## Database

As tabelas são **criadas automaticamente** na inicialização via `@app.on_event("startup")` em [app/main.py](app/main.py) — não é mais necessário rodar comandos manuais.

O SQLite fica em `data/app.db`. Para recriar do zero, pare o servidor, delete o arquivo e reinicie:

```bash
rm data/app.db
uvicorn app.main:app --reload
```

Há também outros bancos SQLite de versões antigas:
- `backend/pulso_da_live.db` (16 KB) — do protótipo em `backend/`
- `pulso_da_live.db` (280 KB) — raiz, pode conter dados de teste

## Repository overview

O repo tem **três** componentes distintos:

### 1. `app/` — FastAPI backend (main codebase)

Arquitetura em camadas com injeção de dependência para o analisador de sentimento:

| Layer | File | Role |
|---|---|---|
| Entry | `app/main.py` | App factory, CORS, router, healthcheck. Startup cria as tabelas do DB automaticamente. |
| Config | `app/core/config.py` | Pydantic `Settings` via `pydantic-settings`, carrega de `.env`. |
| Config | `app/core/stopwords.py` | `PORTUGUESE_STOPWORDS` — ~200 stopwords para filtragem de frequência. |
| Config | `app/core/logging.py` | **Vazio (0 bytes)** — nunca configurado. |
| Infra | `app/infrastructure/database.py` | SQLAlchemy engine + `SessionLocal`. SQLite em `data/app.db`. |
| Model | `app/models/message.py` | `Message` ORM: `id`, `live_id`, `author`, `message`, `created_at`. |
| Repository | `app/repositories/messages.py` | `create_message()`, `list_messages_by_live()`. |
| Schema | `app/schemas/chat.py` | Pydantic v2: `ChatMessage`, `MessageResponse`, `WordFrequencyItem/Response`, `SentimentResponse`. |
| Service | `app/services/sentiment.py` | **Interface** `SentimentAnalyzer` (ABC) + implementação `LeiaSentimentAnalyzer` (léxico LeIA). |
| Service | `app/services/chat.py` | `ChatService` — recebe um `SentimentAnalyzer` por injeção de dependência. |
| DI | `app/api/deps.py` | `get_db()` + `get_chat_service()` — instancia `LeiaSentimentAnalyzer` e injeta no `ChatService`. |
| Route | `app/api/routes/chat.py` | Três endpoints sob `/api/chat/` (ver abaixo). |

#### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Healthcheck → `{"status": "online"}` |
| `POST` | `/api/chat/messages` | Salva mensagem. Body: `{live_id, author, message}` |
| `GET` | `/api/chat/{live_id}/word-frequency?top_n=10` | Top-N palavras (stopwords removidas) |
| `GET` | `/api/chat/{live_id}/sentiment` | Análise de sentimento via LeIA (VADER pt-BR) — **funcional** |

### 2. `frontend/` — Chrome extension (PulsoDaLive)

Manifest v3 que injeta em páginas de live do YouTube.

| File | Role |
|---|---|
| `manifest.json` | v3. Match `*://www.youtube.com/watch?v=*`. Host permission `http://127.0.0.1:8000/*`. |
| `content.js` | **Versão ativa (v4)**. Extrai `liveId` da URL (`window.top.location`), observa `#chatframe` via MutationObserver, POST para `/api/chat/messages`. |
| `bb.js` | Versão antiga (v1) — não utilizada. |

### 3. `backend/` — Protótipo antigo (inativo)

FastAPI monolithic com tudo inline. Contém seu próprio `database.py`, `models.py` e dados dumpados em arquivos `.txt`/`.json`.

## Histórico de mudanças recentes

### Tarefa 1 — Corrigir extensão Chrome
- **URL corrigida**: `/save-message` → `/api/chat/messages` no `content.js`
- **Escopo do `liveId`**: movido para dentro de `startMonitoring()` com `window.top.location` + fallback, eliminando `ReferenceError`
- **Debug logs removidos**: consoles poluentes deletados

### Tarefa 2 — Análise de sentimento com LeIA
- **`app/services/sentiment.py`** (novo): interface `SentimentAnalyzer` (ABC) + `LeiaSentimentAnalyzer`
- **`app/services/chat.py`**: reescrito para usar `SentimentAnalyzer` via DI, sem dependência de HuggingFace
- **`app/api/deps.py`**: injeta `LeiaSentimentAnalyzer()` no `ChatService`
- **`app/api/routes/chat.py`**: consome novo formato de retorno (`total_messages`, `sentiments`)
- **`app/infrastructure/ml.py`**: removido (não usado)
- **`app/main.py`**: import do `ml.py` removido; **startup event ativado** para criar tabelas automaticamente
- **`requirements.txt`**: adicionado `leia-br`

## Known bugs

### `word_frequency` chama o service duas vezes

Em `app/api/routes/chat.py`:
- Linha 17: `freq = service.word_frequency(live_id, top_n)` — resultado descartado
- Linha 20: `freq_tuples = service.word_frequency(live_id, top_n)` — resultado usado
- A primeira chamada é dead code que duplica trabalho no DB.

### `app/core/logging.py` está vazio

0 bytes. Nenhum logger configurado.

### Sem suíte de testes

Nenhum teste no repositório.

## Arquitetura: Análise de Sentimento (desacoplada)

O sistema segue **Interface + Injeção de Dependência**:

```
┌─────────────────────┐
│  SentimentAnalyzer  │  ← ABC (abstract method `analyze`)
│  (services/sentiment│
│   .py)              │
└─────────┬───────────┘
          │ implementa
┌─────────▼───────────┐
│ LeiaSentimentAnalyzer│  ← LeIA (VADER pt-BR), leve, sem GPU
└─────────┬───────────┘
          │ injetado em
┌─────────▼───────────┐
│    ChatService       │  ← acoplado à interface, não à implementação
└─────────────────────┘
```

Para trocar de analisador no futuro:
1. Crie uma nova classe que implemente `SentimentAnalyzer`
2. Em `app/api/deps.py`, troque `LeiaSentimentAnalyzer()` pela nova classe
3. O `ChatService` e os endpoints não precisam ser alterados

## Environment variables

All settings in `app/core/config.py` via Pydantic `BaseSettings`. Override via `.env`:

```
PROJECT_NAME=Chat Analytics API
VERSION=0.1.0
API_PREFIX=/api
```

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

## Oddities

- `app/api/__init__.py` e `app/infrastructure/__init__.py` estão faltando (namespace packages implícitos desde Python 3.3)
- `app/.github/` é um diretório vazio
- `app/.continue/agents/new-agent.yaml` é config exemplo do Continue.dev (gitignored)
- Arquivos `.vscode/settings.json` contêm `{"nuxt.isNuxtApp": false}` — config irrelevante
- `start-claude.sh` é um script comentado para rodar Claude Code via Ollama
