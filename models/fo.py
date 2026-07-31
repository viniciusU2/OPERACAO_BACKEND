from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci",
}


class FuncaoOperacao(Base):
    __tablename__ = "funcao_operacao"
    __table_args__ = (
        UniqueConstraint(
            "id_subestacao",
            "codigo",
            name="uq_funcao_operacao_subestacao_codigo",
        ),
        MYSQL_ARGS,
    )

    id_funcao_operacao = Column(Integer, primary_key=True, autoincrement=True)
    id_subestacao = Column(
        Integer,
        ForeignKey("subestacao.id_subestacao", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo = Column(String(100), nullable=False)
    descricao = Column(String(300), nullable=True)

    subestacao = relationship("Subestacao", back_populates="funcoes_operacao")
    ativos = relationship("Ativo", back_populates="funcao_operacao")
