from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)

    senha_hash = Column(String(255), nullable=False)

    foto = Column(String(500), nullable=True)

    ativo = Column(Boolean, default=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String(200), default="usuario")




