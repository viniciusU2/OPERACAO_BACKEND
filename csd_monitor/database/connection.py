"""Configuração de conexão sem credenciais embutidas no código."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class DatabaseSettings:
    host: str = "localhost"
    port: int = 3306
    name: str = "csd_monitor"
    user: str = "root"
    password: str = ""

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        return cls(
            host=os.getenv("DB_HOST", cls.host),
            port=int(os.getenv("DB_PORT", str(cls.port))),
            name=os.getenv("DB_NAME", cls.name),
            user=os.getenv("DB_USER", cls.user),
            password=os.getenv("DB_PASSWORD", cls.password),
        )


def create_database_engine(url: str | None = None, **kwargs) -> Engine:
    """Cria o engine; ``url`` facilita testes locais com SQLite."""
    if url is None:
        settings = DatabaseSettings.from_env()
        url = (
            f"mysql+pymysql://{settings.user}:{settings.password}"
            f"@{settings.host}:{settings.port}/{settings.name}?charset=utf8mb4"
        )
    return create_engine(url, pool_pre_ping=True, future=True, **kwargs)


def get_engine() -> Engine:
    return create_database_engine()



