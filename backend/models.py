from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

# Define o modelo da tabela 'messages' que o SQLAlchemy usará
class Message(Base):
    __tablename__ = "messages"

    # Colunas da nossa tabela
    id = Column(Integer, primary_key=True, index=True)
    live_id = Column(String, index=True)
    author = Column(String)
    message = Column(String)
    # O timestamp será gerado automaticamente pelo banco de dados no momento da criação
    timestamp = Column(DateTime(timezone=True), server_default=func.now())