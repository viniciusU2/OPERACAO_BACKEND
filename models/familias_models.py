import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text
)
from sqlalchemy.orm import relationship

from database import Base


# =========================================================
# CONFIG MYSQL (PADRÃO DO PROJETO)
# =========================================================
MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci"
}


# =========================================================
# TIPO ATIVO
# =========================================================
class TipoAtivo(Base):
    __tablename__ = "tipo_ativo"
    __table_args__ = MYSQL_ARGS

    id_tipo_ativo = Column(Integer, primary_key=True, autoincrement=True)

    nome = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(300), nullable=True)

    
    # ================= RELATIONSHIPS =================
    ativos = relationship(
        "Ativo",
        back_populates="tipo_ativo",
        cascade="all, delete"
    )

    planos_manutencao = relationship(
        "PlanoManutencao",
        back_populates="tipo_ativo",
        cascade="all, delete-orphan"
    )