# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json

# Cria a aplicação FastAPI
app = FastAPI()

# Configuração do CORS
# Isso permite que a sua extensão (rodando no youtube.com) se comunique com o seu backend (rodando em localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens, para teste. Em produção, restrinja.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de dados usando Pydantic. Garante que os dados recebidos terão esse formato.
class ChatMessage(BaseModel):
    author: str
    message: str

# O endpoint que vai receber as mensagens
@app.post("/save-message")
def save_message(chat_message: ChatMessage):
    print(f"Recebido: [{chat_message.author}] - {chat_message.message}")

    # Lógica para salvar os dados
    # Exemplo: salvando em um arquivo de texto (um "log")
    with open("chat_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{chat_message.author}] {chat_message.message}\n")
    
    # Exemplo 2: salvando em um arquivo JSON
    # (uma abordagem mais estruturada)
    try:
        with open("chat_data.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
            data.append(chat_message.dict())
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("chat_data.json", "w", encoding="utf-8") as f:
            json.dump([chat_message.dict()], f, ensure_ascii=False, indent=4)


    return {"status": "success", "message_received": chat_message.dict()}

@app.get('/')
def activo():
    return{
        "Status": 'online'
    }

# Para rodar o servidor: uvicorn main:app --reload