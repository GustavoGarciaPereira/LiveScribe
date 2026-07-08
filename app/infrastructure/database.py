from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path("./data")
DB_PATH.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH / 'app.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,             # SQLite espera até 30s pelo lock
    },
    pool_size=10,                  # Aumenta o pool
    max_overflow=20,               # Permite até 20 conexões extras
    future=True,
)

# Ativa WAL mode para permitir leituras e escritas concorrentes
@event.listens_for(engine, "connect")
def _set_wal(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL;")
    dbapi_connection.execute("PRAGMA busy_timeout=5000;")

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()