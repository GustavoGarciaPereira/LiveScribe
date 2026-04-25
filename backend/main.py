# Importações existentes
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal, engine

# Novas importações para a Fase 2 (COM A CORREÇÃO)
import re
from collections import Counter

# --- CARREGANDO O MODELO DE IA (FAÇA ISSO APENAS UMA VEZ) ---
# Carregamos o pipeline de análise de sentimento para português.
# Isso pode levar alguns segundos na primeira vez que o servidor iniciar.

print("Modelo carregado com sucesso!")

# Cria todas as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuração do CORS (sem alterações)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependência para obter a sessão do banco de dados ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelo Pydantic (sem alterações)
class ChatMessage(BaseModel):
    author: str
    message: str
    live_id: str

# Endpoint para salvar mensagens (sem alterações)
@app.post("/save-message")
def save_message(chat_message: ChatMessage, db: Session = Depends(get_db)):
    db_message = models.Message(
        live_id=chat_message.live_id,
        author=chat_message.author,
        message=chat_message.message
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    print(f"Salvo no DB: [Live: {db_message.live_id}] [{db_message.author}] - {db_message.message}")
    return {"status": "success", "data_saved": db_message}

@app.get('/')
def activo():
    return {"Status": 'online'}

# --- FASE 2: ENDPOINTS DE INTELIGÊNCIA ---

###
### Endpoint de Frequência de Palavras
###
@app.get("/word-frequency/{live_id}")
def get_word_frequency(live_id: str, top_n: int = 10, db: Session = Depends(get_db)):
    # Busca todas as mensagens para o live_id fornecido
    messages = db.query(models.Message).filter(models.Message.live_id == live_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail=f"Nenhuma mensagem encontrada para a live_id: {live_id}")

    # Concatena todas as mensagens em um único bloco de texto
    full_text = " ".join([msg.message for msg in messages])

    # Lista de stopwords em português (pode ser expandida)
    stopwords = set([
        'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma',
        'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao',
        'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há',
        'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela',
        'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas',
        'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem',
        'suas', 'meu', 'às', 'minha', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual',
        'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'fosse',
        'dele', 'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus',
        'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela', 'delas', 'esta', 'estes',
        'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo', 'estou', 'está',
        'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram', 'estava', 'estávamos',
        'estavam', 'estivera', 'estivéramos', 'esteja', 'estejamos', 'estejam', 'estivesse',
        'estivéssemos', 'estivessem', 'estiver', 'estivermos', 'estiverem', 'hei', 'há',
        'havemos', 'hão', 'houve', 'houvemos', 'houveram', 'houvera', 'houvéramos', 'haja',
        'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem', 'houver', 'houvermos',
        'houverem', 'houverei', 'houverá', 'houveremos', 'houverão', 'houveria', 'houveríamos',
        'houveriam', 'sou', 'somos', 'são', 'era', 'éramos', 'eram', 'fui', 'foi', 'fomos',
        'foram', 'fora', 'fôramos', 'seja', 'sejamos', 'sejam', 'fosse', 'fôssemos', 'fossem',
        'for', 'formos', 'forem', 'serei', 'será', 'seremos', 'serão', 'seria', 'seríamos',
        'seriam', 'tenho', 'tem', 'temos', 'tém', 'tinha', 'tínhamos', 'tinham', 'tive',
        'teve', 'tivemos', 'tiveram', 'tivera', 'tivéramos', 'tenha', 'tenhamos', 'tenham',
        'tivesse', 'tivéssemos', 'tivessem', 'tiver', 'tivermos', 'tiverem', 'terei', 'terá',
        'teremos', 'terão', 'teria', 'teríamos', 'teriam', 'kkk', 'rs', 'kk', 'k'
    ])

    # Limpa o texto: minúsculas, encontra palavras, remove stopwords e palavras curtas
    words = re.findall(r'\b\w+\b', full_text.lower())
    filtered_words = [word for word in words if word not in stopwords and not word.isdigit()]

    # Conta a frequência e pega as 'top_n' mais comuns
    word_counts = Counter(filtered_words)
    most_common_words = word_counts.most_common(top_n)

    return {"live_id": live_id, "word_frequency": most_common_words}

@app.get("/sentiment-analysis/{live_id}")
def get_sentiment_analysis_transformers(live_id: str, db: Session = Depends(get_db)):
    messages = db.query(models.Message).filter(models.Message.live_id == live_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail=f"Nenhuma mensagem encontrada para a live_id: {live_id}")

    # Pega apenas o texto das mensagens para processar em lote
    message_texts = [msg.message for msg in messages]

    # Processa TODAS as mensagens de uma vez (muito mais eficiente!)
    # O truncation=True garante que mensagens muito longas não causem erro.
    sentiment_results = sentiment_analyzer_pipeline(message_texts, truncation=True)

    # Contabiliza os resultados
    results_summary = {"Positivo": 0, "Negativo": 0, "Neutro": 0}
    
    # O modelo usado retorna '1 star' (negativo), '3 stars' (neutro), '5 stars' (positivo)
    # Vamos mapear isso para nomes mais amigáveis.
    label_map = {
        "1 star": "Negativo",
        "3 stars": "Neutro",
        "5 stars": "Positivo"
    }

    for result in sentiment_results:
        friendly_label = label_map.get(result['label'], "Neutro") # Mapeia o rótulo
        results_summary[friendly_label] += 1

    return {
        "live_id": live_id,
        "total_messages_analyzed": len(messages),
        "sentiment_summary": results_summary,
        "library_used": "Hugging Face Transformers",
        "model": "lct-big-science/bertimbau-base-sentiment-analysis-portuguese"
    }