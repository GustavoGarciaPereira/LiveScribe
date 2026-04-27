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
- Prompt: Modernização e Expansão de Testes para API FastAPIVocê é um engenheiro de software experiente em Python, FastAPI e Pydantic. Meu projeto já foi migrado para Pydantic v2 e FastAPI com lifespan, mas ainda usa sintaxe retroativa para type hints (`List`, `Optional`, `Union`) por compatibilidade com Python < 3.9/3.10. Além disso, a suíte de testes precisa ser expandida para maior cobertura.Por favor, realize as seguintes tarefas:## 1. Simplificação de Type Hints (abandono gradual de `List` e `Optional`)- **Assumindo que o projeto agora exige Python 3.10 ou superior** (ou que não há mais restrição de versões antigas):  - Substitua todas as ocorrências de `List[X]` por `list[X]`.  - Substitua `Optional[X]` por `X | None`.  - Substitua `Union[A, B]` por `A | B`.  - Remova as importações de `List`, `Optional`, `Union` do módulo `typing` onde não forem mais usadas.  - Atualize as anotações de tipo em funções, métodos, modelos Pydantic (incluindo `Field(default=None)` → `Field(default=None)` continua igual, mas o tipo deve ser `X | None`).  - Mantenha o código funcional e sem erros de tipo (passe pelo mypy ou pyright se disponível).- **Se ainda houver necessidade de compatibilidade com Python 3.8/3.9**:  - Apenas documente as mudanças necessárias para o futuro, mas não as aplique agora.## 2. Expansão e Refinamento da Suíte de Testes- Analise o código atual e identifique áreas com baixa cobertura (endpoints, modelos de validação, funções auxiliares, erros de negócio).- Adicione testes para os seguintes cenários (se ainda não existirem):  - **Testes unitários**:    - Funções de processamento de texto (ex.: `word_frequency`, `sentiment_summary`).    - Serialização/deserialização de modelos Pydantic (incluindo casos inválidos).    - Lógica de validação personalizada (ex.: `@model_validator`).  - **Testes de integração (com `httpx.AsyncClient`)**:    - Criação, leitura, atualização e remoção de recursos via API.    - Dependências (ex.: banco de dados em memória SQLite) iniciadas e finalizadas corretamente no lifespan.    - Tratamento de erros HTTP (404, 422, 500) com mensagens apropriadas.    - Uso de `pytest` com fixtures para cliente assíncrono, sessão de banco de dados, etc.  - **Testes de regressão**:    - Verifique que as substituições de type hints não quebraram a lógica de negócio.    - Teste a conversão de `datetime` com timezone.- Garanta que a cobertura de código (ex.: usando `pytest-cov`) seja **pelo menos 85%** e que todos os testes passem.- Atualize o arquivo `README.md` ou documentação com instruções para executar os testes: `pytest -v --cov=app`.## 3. Instruções de saída- Forneça o código modificado em formato de patch ou listando os arquivos alterados e as mudanças linha a linha.- Explique brevemente cada alteração relevante e por que ela melhora o projeto.- Inclua um exemplo de execução dos testes mostrando que todos passam com a nova cobertura.**Observação**: Se não tiver acesso ao código fonte completo, peça que eu forneça os arquivos necessários. O foco é manter o projeto moderno, legível e bem testado.
- Prompt: Modernização e Expansão de Testes para API FastAPIVocê é um engenheiro de software experiente em Python, FastAPI e Pydantic. Meu projeto já foi migrado para Pydantic v2 e FastAPI com lifespan, mas ainda usa sintaxe retroativa para type hints (`List`, `Optional`, `Union`) por compatibilidade com Python < 3.9/3.10. Além disso, a suíte de testes precisa ser expandida para maior cobertura.Por favor, realize as seguintes tarefas:## 1. Simplificação de Type Hints (abandono gradual de `List` e `Optional`)- **Assumindo que o projeto agora exige Python 3.10 ou superior** (ou que não há mais restrição de versões antigas):  - Substitua todas as ocorrências de `List[X]` por `list[X]`.  - Substitua `Optional[X]` por `X | None`.  - Substitua `Union[A, B]` por `A | B`.  - Remova as importações de `List`, `Optional`, `Union` do módulo `typing` onde não forem mais usadas.  - Atualize as anotações de tipo em funções, métodos, modelos Pydantic (incluindo `Field(default=None)` → `Field(default=None)` continua igual, mas o tipo deve ser `X | None`).  - Mantenha o código funcional e sem erros de tipo (passe pelo mypy ou pyright se disponível).- **Se ainda houver necessidade de compatibilidade com Python 3.8/3.9**:  - Apenas documente as mudanças necessárias para o futuro, mas não as aplique agora.## 2. Expansão e Refinamento da Suíte de Testes- Analise o código atual e identifique áreas com baixa cobertura (endpoints, modelos de validação, funções auxiliares, erros de negócio).- Adicione testes para os seguintes cenários (se ainda não existirem):  - **Testes unitários**:    - Funções de processamento de texto (ex.: `word_frequency`, `sentiment_summary`).    - Serialização/deserialização de modelos Pydantic (incluindo casos inválidos).    - Lógica de validação personalizada (ex.: `@model_validator`).  - **Testes de integração (com `httpx.AsyncClient`)**:    - Criação, leitura, atualização e remoção de recursos via API.    - Dependências (ex.: banco de dados em memória SQLite) iniciadas e finalizadas corretamente no lifespan.    - Tratamento de erros HTTP (404, 422, 500) com mensagens apropriadas.    - Uso de `pytest` com fixtures para cliente assíncrono, sessão de banco de dados, etc.  - **Testes de regressão**:    - Verifique que as substituições de type hints não quebraram a lógica de negócio.    - Teste a conversão de `datetime` com timezone.- Garanta que a cobertura de código (ex.: usando `pytest-cov`) seja **pelo menos 85%** e que todos os testes passem.- Atualize o arquivo `README.md` ou documentação com instruções para executar os testes: `pytest -v --cov=app`.## 3. Instruções de saída- Forneça o código modificado em formato de patch ou listando os arquivos alterados e as mudanças linha a linha.- Explique brevemente cada alteração relevante e por que ela melhora o projeto.- Inclua um exemplo de execução dos testes mostrando que todos passam com a nova cobertura.**Observação**: Se não tiver acesso ao código fonte completo, peça que eu forneça os arquivos necessários. O foco é manter o projeto moderno, legível e bem testado. valise se isso na foi feito
- Prompt: Modernização e Expansão de Testes para API FastAPIVocê é um engenheiro de software experiente em Python, FastAPI e Pydantic. Meu projeto já foi migrado para Pydantic v2 e FastAPI com lifespan, mas ainda usa sintaxe retroativa para type hints (`List`, `Optional`, `Union`) por compatibilidade com Python < 3.9/3.10. Além disso, a suíte de testes precisa ser expandida para maior cobertura.Por favor, realize as seguintes tarefas:## 1. Simplificação de Type Hints (abandono gradual de `List` e `Optional`)- **Assumindo que o projeto agora exige Python 3.10 ou superior** (ou que não há mais restrição de versões antigas):  - Substitua todas as ocorrências de `List[X]` por `list[X]`.  - Substitua `Optional[X]` por `X | None`.  - Substitua `Union[A, B]` por `A | B`.  - Remova as importações de `List`, `Optional`, `Union` do módulo `typing` onde não forem mais usadas.  - Atualize as anotações de tipo em funções, métodos, modelos Pydantic (incluindo `Field(default=None)` → `Field(default=None)` continua igual, mas o tipo deve ser `X | None`).  - Mantenha o código funcional e sem erros de tipo (passe pelo mypy ou pyright se disponível).- **Se ainda houver necessidade de compatibilidade com Python 3.8/3.9**:  - Apenas documente as mudanças necessárias para o futuro, mas não as aplique agora.## 2. Expansão e Refinamento da Suíte de Testes- Analise o código atual e identifique áreas com baixa cobertura (endpoints, modelos de validação, funções auxiliares, erros de negócio).- Adicione testes para os seguintes cenários (se ainda não existirem):  - **Testes unitários**:    - Funções de processamento de texto (ex.: `word_frequency`, `sentiment_summary`).    - Serialização/deserialização de modelos Pydantic (incluindo casos inválidos).    - Lógica de validação personalizada (ex.: `@model_validator`).  - **Testes de integração (com `httpx.AsyncClient`)**:    - Criação, leitura, atualização e remoção de recursos via API.    - Dependências (ex.: banco de dados em memória SQLite) iniciadas e finalizadas corretamente no lifespan.    - Tratamento de erros HTTP (404, 422, 500) com mensagens apropriadas.    - Uso de `pytest` com fixtures para cliente assíncrono, sessão de banco de dados, etc.  - **Testes de regressão**:    - Verifique que as substituições de type hints não quebraram a lógica de negócio.    - Teste a conversão de `datetime` com timezone.- Garanta que a cobertura de código (ex.: usando `pytest-cov`) seja **pelo menos 85%** e que todos os testes passem.- Atualize o arquivo `README.md` ou documentação com instruções para executar os testes: `pytest -v --cov=app`.## 3. Instruções de saída- Forneça o código modificado em formato de patch ou listando os arquivos alterados e as mudanças linha a linha.- Explique brevemente cada alteração relevante e por que ela melhora o projeto.- Inclua um exemplo de execução dos testes mostrando que todos passam com a nova cobertura.**Observação**: Se não tiver acesso ao código fonte completo, peça que eu forneça os arquivos necessários. O foco é manter o projeto moderno, legível e bem testado.
