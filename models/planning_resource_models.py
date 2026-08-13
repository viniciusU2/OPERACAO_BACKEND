from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from database import Base


MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci",
}


class Recurso(Base):
    __tablename__ = "recurso"
    __table_args__ = (
        CheckConstraint(
            "categoria IN ('MAO_DE_OBRA','INSTRUMENTO','VEICULO','EQUIPAMENTO','MATERIAL','EPI','EPC')",
            name="ck_recurso_categoria",
        ),
        CheckConstraint(
            "quantidade_disponivel IS NULL OR quantidade_disponivel >= 0",
            name="ck_recurso_quantidade",
        ),
        UniqueConstraint("categoria", "nome", name="uq_recurso_categoria_nome"),
        MYSQL_ARGS,
    )

    id_recurso = Column(Integer, primary_key=True)
    nome = Column(String(160), nullable=False)
    categoria = Column(String(30), nullable=False, index=True)
    unidade = Column(String(30), nullable=False)
    quantidade_disponivel = Column(DECIMAL(12, 3), nullable=True)
    controla_disponibilidade = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanoEstimativa(Base):
    __tablename__ = "plano_estimativa"
    __table_args__ = (
        CheckConstraint(
            "duracao_estimada_horas IS NULL OR duracao_estimada_horas > 0",
            name="ck_plano_estimativa_duracao",
        ),
        MYSQL_ARGS,
    )

    id_plano_manutencao = Column(
        Integer,
        ForeignKey("plano_manutencao.id_plano_manutencao", ondelete="CASCADE"),
        primary_key=True,
    )
    duracao_estimada_horas = Column(DECIMAL(8, 2), nullable=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanoRecurso(Base):
    __tablename__ = "plano_recurso"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_plano_recurso_quantidade"),
        CheckConstraint(
            "horas_por_recurso IS NULL OR horas_por_recurso > 0",
            name="ck_plano_recurso_horas",
        ),
        UniqueConstraint("id_plano_manutencao", "id_recurso", name="uq_plano_recurso"),
        Index("ix_plano_recurso_plano", "id_plano_manutencao"),
        Index("ix_plano_recurso_recurso", "id_recurso"),
        MYSQL_ARGS,
    )

    id_plano_recurso = Column(Integer, primary_key=True)
    id_plano_manutencao = Column(
        Integer,
        ForeignKey("plano_manutencao.id_plano_manutencao", ondelete="CASCADE"),
        nullable=False,
    )
    id_recurso = Column(Integer, ForeignKey("recurso.id_recurso"), nullable=False)
    quantidade = Column(DECIMAL(12, 3), nullable=False)
    horas_por_recurso = Column(DECIMAL(8, 2), nullable=True)
    consumivel = Column(Boolean, nullable=False, default=False)
    obrigatorio = Column(Boolean, nullable=False, default=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanoEquipe(Base):
    __tablename__ = "plano_equipe"
    __table_args__ = (
        CheckConstraint("prioridade > 0", name="ck_plano_equipe_prioridade"),
        UniqueConstraint("id_plano_manutencao", "id_equipe", name="uq_plano_equipe"),
        Index("ix_plano_equipe_plano", "id_plano_manutencao"),
        Index("ix_plano_equipe_equipe", "id_equipe"),
        MYSQL_ARGS,
    )

    id_plano_equipe = Column(Integer, primary_key=True)
    id_plano_manutencao = Column(
        Integer,
        ForeignKey("plano_manutencao.id_plano_manutencao", ondelete="CASCADE"),
        nullable=False,
    )
    id_equipe = Column(Integer, ForeignKey("sobreaviso_equipe.id_equipe"), nullable=False)
    prioridade = Column(Integer, nullable=False, default=1)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)


class EquipeCapacidade(Base):
    __tablename__ = "equipe_capacidade"
    __table_args__ = (
        CheckConstraint("data_fim >= data_inicio", name="ck_equipe_capacidade_periodo"),
        CheckConstraint("horas_disponiveis >= 0", name="ck_equipe_capacidade_horas"),
        UniqueConstraint("id_equipe", "data_inicio", "data_fim", name="uq_equipe_capacidade_periodo"),
        Index("ix_equipe_capacidade_periodo", "data_inicio", "data_fim"),
        MYSQL_ARGS,
    )

    id_equipe_capacidade = Column(Integer, primary_key=True)
    id_equipe = Column(
        Integer,
        ForeignKey("sobreaviso_equipe.id_equipe", ondelete="CASCADE"),
        nullable=False,
    )
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    horas_disponiveis = Column(DECIMAL(10, 2), nullable=False)
    fonte = Column(String(80), nullable=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
