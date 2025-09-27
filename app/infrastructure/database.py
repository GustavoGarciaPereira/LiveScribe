from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path("./data")
DB_PATH.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH / 'app.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necessário para SQLite com FastAPI
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()