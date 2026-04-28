# PulsoDaLive / LiveScribe

Captura e análise de discurso em tempo real de chats de lives do YouTube.

## Funcionalidades

- Extensão Chrome com autenticação JWT integrada
- API FastAPI para armazenar e analisar mensagens
- Autenticação local (email/senha) e Google OAuth2
- Frequência de palavras com stopwords em português
- Análise de sentimentos com LeIA (VADER adaptado)
- Linha do tempo de sentimentos por intervalos
- Picos de engajamento por janela de tempo
- Tópicos emergentes via TF-IDF (scikit-learn)
- Exportação de dados (JSON, CSV, XLSX)
- Sistema de webhooks (new_message, peak_engagement)
- Dashboard HTML interativo com Chart.js e login/logout
- Isolamento de dados por usuário (JWT)
- Suporte a múltiplas plataformas (campo `platform`)

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Autenticação:** JWT (python-jose) + bcrypt + Google OAuth2 (httpx-oauth)
- **ML/NLP:** LeIA (sentimento), scikit-learn (TF-IDF)
- **Frontend:** Extensão Chrome Manifest v3 + Dashboard HTML (Chart.js)
- **Testes:** pytest + pytest-cov (70 testes, 89% cobertura)

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse: http://127.0.0.1:8000/docs | Dashboard: http://127.0.0.1:8000/dashboard

## Extensão Chrome

1. Vá em `chrome://extensions/`, ative "Modo do desenvolvedor"
2. "Carregar sem compactação" → selecione a pasta `frontend/`
3. Clique no ícone da extensão → faça login
4. Abra uma live do YouTube com chat ativo
5. As mensagens serão enviadas automaticamente com token JWT

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|:----:|-----------|
| `GET` | `/` | ❌ | Healthcheck |
| `GET` | `/dashboard` | ❌ | Dashboard HTML |
| `POST` | `/api/auth/register` | ❌ | Cadastro local |
| `POST` | `/api/auth/login` | ❌ | Login local |
| `GET` | `/api/auth/login/google` | ❌ | URL Google OAuth |
| `GET` | `/api/auth/callback/google` | ❌ | Callback Google |
| `GET` | `/api/auth/me` | ✅ | Dados do usuário |
| `POST` | `/api/chat/messages` | Opcional | Salvar mensagem |
| `GET` | `/api/chat/lives` | ✅ | Listar lives |
| `GET` | `/api/chat/{id}/word-frequency` | ✅ | Top palavras |
| `GET` | `/api/chat/{id}/sentiment` | ✅ | Sentimentos |
| `GET` | `/api/chat/{id}/sentiment-timeline` | ✅ | Timeline |
| `GET` | `/api/chat/{id}/engagement-peaks` | ✅ | Picos |
| `GET` | `/api/chat/{id}/topics` | ✅ | Tópicos |
| `GET` | `/api/chat/{id}/export` | ✅ | Exportar JSON/CSV/XLSX |
| `POST` | `/api/webhooks` | ✅ | Criar webhook |
| `GET` | `/api/webhooks` | ✅ | Listar webhooks |
| `DELETE` | `/api/webhooks/{id}` | ✅ | Deletar webhook |

## Testes

```bash
pytest -v --cov=app --cov-report=term-missing
```

**70 testes, 89% cobertura.**

## Arquivos de teste

| Arquivo | O que testa |
|---------|------------|
| `tests/test_auth.py` | JWT, login local, registro, /me |
| `tests/test_routes.py` | Todos os endpoints (protegidos com `auth_client`) |
| `tests/test_services.py` | ChatService, LeiaAnalyzer real, platform |
| `tests/test_export.py` | Exportação JSON, CSV, XLSX |
| `tests/test_schemas.py` | Schemas Pydantic |
| `tests/test_repositories.py` | CRUD mensagens, list_lives |
| `tests/test_models.py` | Modelo Message (created_at) |
| `tests/test_deps.py` | Injeção de dependências |
| `tests/test_dashboard.py` | Dashboard HTML |
| `tests/test_webhooks.py` | Webhooks CRUD + trigger |
| `tests/conftest.py` | Fixtures (DB memória, mocks, auth_client) |

## Autenticação

- **Google OAuth2**: `GET /api/auth/login/google` → `GET /api/auth/callback/google`
- **Login local**: `POST /api/auth/register` → `POST /api/auth/login`
- **JWT**: `python-jose` HS256, expira em 24h
- **Hash**: `bcrypt` para senhas locais
- **Provider**: campo `provider` no User (`local` / `google`)
- **Extensão Chrome**: popup de login, token em `chrome.storage.local`, enviado no header `Authorization`

## Arquitetura de serviços

```
SentimentAnalyzer (ABC)  ← LeiaSentimentAnalyzer (LeIA)
TopicExtractor (ABC)     ← TfidfTopicExtractor (sklearn)
ExportService            → export_json / export_csv / export_xlsx
WebhookService           → trigger_webhooks (new_message, peak_engagement)
                              ↓ injetados em
                         ChatService / rotas
```

## Migração de banco

Colunas/tabelas adicionadas automaticamente no `lifespan` (ALTER TABLE):
- `platform` (Fase 2)
- `user_id` (Fase 3)
- `password_hash`, `provider`, `is_active` (Feature 1.5)

Para recriar do zero: `rm data/app.db` e reiniciar o servidor.

## Histórico de features

| Feature | O que |
|---------|-------|
| Pydantic v2 + testes | Migração para lifespan, type hints modernos, 28 testes |
| Fase 2 | 4 endpoints analíticos + dashboard + platform |
| Fase 3 | Auth JWT + Google OAuth2 + multi-usuário |
| Feature 1.5 | Login local email/senha + bcrypt |
| Feature 2 | Proteção de rotas + extensão Chrome com auth |
| Feature 3 | Exportação JSON/CSV/XLSX |
| Feature 4 | Sistema de webhooks |
