import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ENV = BASE_DIR / ".env"

# Carrega o .env que fica ao lado deste arquivo, independentemente do
# diretorio de trabalho do uvicorn/systemd.
load_dotenv(ARQUIVO_ENV)

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL nao configurada. Crie o arquivo "
        f"{ARQUIVO_ENV} com a linha "
        "DATABASE_URL=mysql+pymysql://usuario:senha@host:3306/manutencao"
    )

SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
