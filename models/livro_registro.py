from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class LivroRegistro(Base):
    __tablename__ = "livro_registro"

    id = Column(Integer, primary_key=True, index=True)

    # Datas
    data_registro_inicio = Column(DateTime, default=datetime.utcnow)
    data_registro_fim = Column(DateTime, nullable=True)

    # Tipo
    # inicio_os | termino_os | atividade | foto | observacao
    tipo = Column(String(50), nullable=False)

    descricao = Column(Text, nullable=False)

    # Relacionamentos
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os"), nullable=True)
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao"), nullable=True)

    # Foto
    foto = Column(String(255), nullable=True)

    # Usuário
    usuario = Column(String(100), nullable=False)

    # Relationships
    os = relationship("OrdemServico", back_populates="livro_registro")
    subestacao = relationship("Subestacao")