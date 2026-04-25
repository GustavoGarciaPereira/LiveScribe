from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define a URL do nosso banco de dados SQLite.
# O arquivo 'pulso_da_live.db' será criado na mesma pasta.
SQLALCHEMY_DATABASE_URL = "sqlite:///./pulso_da_live.db"

# Cria o "motor" do SQLAlchemy. O argumento connect_args é necessário apenas para o SQLite
# para permitir que o mesmo objeto seja usado em múltiplos threads, como o FastAPI faz.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Cria uma fábrica de sessões. Cada instância de SessionLocal será uma sessão de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria uma classe Base. Nossos modelos de banco de dados (tabelas) herdarão desta classe.
Base = declarative_base()