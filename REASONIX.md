# REASONIX.md — Contexto do projeto para o Reasonix

## Identificação

- **Nome do projeto:** PulsoDaLive / LiveScribe  
- **Objetivo:** Coletar chat de lives do YouTube e analisar discurso (frequência de palavras e sentimentos)  
- **Stack:** FastAPI + SQLAlchemy + SQLite + LeIA (léxico) + Extensão Chrome  

## Arquitetura atual

```
app/
├── api/deps.py              -> get_db, get_chat_service (injeta LeiaSentimentAnalyzer)
├── api/routes/chat.py       -> 3 endpoints: POST message, GET word-frequency, GET sentiment
├── services/chat.py         -> ChatService (recebe SentimentAnalyzer por DI)
├── services/sentiment.py    -> SentimentAnalyzer (ABC) + LeiaSentimentAnalyzer (implementação)
├── models/message.py        -> Message ORM
├── repositories/messages.py -> create_message, list_messages_by_live
├── core/config.py           -> Configurações do .env
├── core/stopwords.py        -> stopwords em português
└── infrastructure/          -> database.py
frontend/
└── content.js               -> Extensão Chrome que observa #items e POST em /api/chat/messages
```

## Decisões de design

- **Sentimento desacoplado:** A interface `SentimentAnalyzer` permite trocar o analisador sem mexer no `ChatService` ou rotas.
- **Implementação atual:** `LeiaSentimentAnalyzer` (leve, offline, português).  
- **Migração futura:** Basta criar uma nova classe implementando `SentimentAnalyzer` e alterar a injeção em `deps.py`.
- **Banco:** SQLite em `data/app.db`. Tabela `messages` com colunas: id, live_id, author, message, created_at.
- **Extensão:** Observa o iframe `#chatframe` do YouTube e usa MutationObserver em `#items.yt-live-chat-item-list-renderer`. Posta em `http://127.0.0.1:8000/api/chat/messages`.

## Tarefas concluídas (Fase 1)

1. Rota da extensão alinhada com API.
2. Sentimento funcional com LeIA.
3. Chamada dupla do `word_frequency` removida.
4. Documentação básica criada (README, REASONIX.md).

## Possíveis evoluções

- Linha do tempo de sentimentos (agrupar por intervalos)
- Detecção de picos de engajamento
- Dashboard frontend
- Suporte a Twitch/Facebook Live
- Modelo de tópicos (LDA/BERTopic)

## Comandos úteis

```bash
# Iniciar servidor
uvicorn app.main:app --reload

# Instalar dependências
pip install -r requirements.txt

# Testar endpoints
curl -X POST http://127.0.0.1:8000/api/chat/messages -H "Content-Type: application/json" -d '{"author":"Test","message":"Boa noite","live_id":"test"}'
curl http://127.0.0.1:8000/api/chat/test/sentiment
```