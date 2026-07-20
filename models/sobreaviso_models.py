from datetime import datetime

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class SobreavisoEquipe(Base):
    __tablename__ = "sobreaviso_equipe"

    id_equipe = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Integer, default=1, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    colaboradores = relationship("SobreavisoColaborador", back_populates="equipe")


class SobreavisoColaborador(Base):
    __tablename__ = "sobreaviso_colaborador"

    id_colaborador = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    id_equipe = Column(Integer, ForeignKey("sobreaviso_equipe.id_equipe"), nullable=False)
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao"), nullable=True)
    nome = Column(String(200), nullable=False)
    matricula = Column(String(50), nullable=False, unique=True)
    email = Column(String(200), nullable=False)
    cargo = Column(String(150), nullable=True)
    telefone = Column(String(50), nullable=True)
    ativo = Column(Integer, default=1, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=True)

    equipe = relationship("SobreavisoEquipe", back_populates="colaboradores")
    periodos = relationship("SobreavisoPeriodo", back_populates="colaborador")


class SobreavisoPeriodo(Base):
    __tablename__ = "sobreaviso_periodo"

    id_sobreaviso = Column(Integer, primary_key=True, index=True)
    id_colaborador = Column(
        Integer,
        ForeignKey("sobreaviso_colaborador.id_colaborador"),
        nullable=False,
        index=True,
    )
    inicio = Column(DateTime, nullable=False, index=True)
    fim = Column(DateTime, nullable=False, index=True)
    total_horas = Column(DECIMAL(10, 2), nullable=False, default=0)
    status = Column(String(30), nullable=False, default="PENDENTE")
    origem = Column(String(30), nullable=False, default="GESTOR")
    justificativa = Column(Text, nullable=True)
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    atualizado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=True)

    colaborador = relationship("SobreavisoColaborador", back_populates="periodos")
    solicitacoes = relationship(
        "SobreavisoSolicitacaoAjuste",
        back_populates="sobreaviso",
        cascade="all, delete-orphan",
    )


class SobreavisoSolicitacaoAjuste(Base):
    __tablename__ = "sobreaviso_solicitacao_ajuste"

    id_solicitacao = Column(Integer, primary_key=True, index=True)
    id_sobreaviso = Column(
        Integer,
        ForeignKey("sobreaviso_periodo.id_sobreaviso", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    solicitado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    inicio_solicitado = Column(DateTime, nullable=False)
    fim_solicitado = Column(DateTime, nullable=False)
    justificativa = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="PENDENTE")
    avaliado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    avaliado_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    sobreaviso = relationship("SobreavisoPeriodo", back_populates="solicitacoes")


class SobreavisoHistorico(Base):
    __tablename__ = "sobreaviso_historico"

    id_historico = Column(Integer, primary_key=True, index=True)
    entidade = Column(String(50), nullable=False)
    entidade_id = Column(Integer, nullable=False, index=True)
    acao = Column(String(50), nullable=False)
    dados_anteriores = Column(Text, nullable=True)
    dados_novos = Column(Text, nullable=True)
    justificativa = Column(Text, nullable=True)
    alterado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
