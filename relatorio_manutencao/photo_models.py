from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class RelatorioManutencaoFoto(Base):
    __tablename__ = "relatorio_manutencao_foto"

    id_relatorio_manutencao_foto = Column(Integer, primary_key=True, autoincrement=True)
    id_relatorio_manutencao = Column(Integer, ForeignKey("relatorio_manutencao.id_relatorio_manutencao", ondelete="CASCADE"), nullable=False, index=True)
    id_ativo = Column(Integer, ForeignKey("ativo.id_ativo", ondelete="SET NULL"), nullable=True, index=True)
    id_plano_item = Column(Integer, ForeignKey("plano_item.id_plano_item", ondelete="SET NULL"), nullable=True, index=True)
    nome_arquivo_zip = Column(String(500), nullable=False)
    valor_medido = Column(String(100), nullable=True)
    status_item = Column(String(10), nullable=False, default="OK")
    observacao = Column(Text, nullable=True)
    incluir = Column(Boolean, nullable=False, default=True)
    confianca = Column(String(20), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)

    ativo = relationship("Ativo")
    plano_item = relationship("PlanoItem")
