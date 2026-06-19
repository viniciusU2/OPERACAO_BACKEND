from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Rdo(Base):
    __tablename__ = "rdo"
    __table_args__ = (
        UniqueConstraint("data_rdo", "sistema", name="uq_rdo_data_sistema"),
    )

    id_rdo = Column(Integer, primary_key=True, index=True)

    data_rdo = Column(Date, nullable=False, index=True)
    titulo = Column(String(150), default="RDO - RELATORIO DIARIO DA OPERACAO")
    codigo_procedimento = Column(String(50), default="PR-OP.COS.002")
    revisao = Column(String(10), default="00")
    sistema = Column(String(100), default="RIALMA V", nullable=False)
    emissor = Column(String(150), nullable=False)
    arquivo_pdf = Column(String(255), nullable=True)
    status = Column(String(30), default="RASCUNHO", nullable=False)

    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    editado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    validado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    validado_em = Column(DateTime, nullable=True)

    configuracoes = relationship(
        "RdoConfiguracaoSistema",
        back_populates="rdo",
        cascade="all, delete-orphan",
    )
    eventos = relationship(
        "RdoEvento",
        back_populates="rdo",
        cascade="all, delete-orphan",
    )
    importacoes = relationship(
        "RdoImportacaoPdf",
        back_populates="rdo",
        cascade="all, delete-orphan",
    )
    historico = relationship(
        "RdoHistoricoEdicao",
        back_populates="rdo",
        cascade="all, delete-orphan",
    )


class RdoConfiguracaoSistema(Base):
    __tablename__ = "rdo_configuracao_sistema"

    id_configuracao = Column(Integer, primary_key=True, index=True)
    id_rdo = Column(Integer, ForeignKey("rdo.id_rdo", ondelete="CASCADE"), nullable=False)

    periodo_inicio = Column(Time, nullable=False)
    periodo_fim = Column(Time, nullable=False)
    subestacao = Column(String(50), nullable=True)
    equipamento = Column(String(100), nullable=False)
    estado = Column(String(50), nullable=False)
    ordem = Column(Integer, default=0)

    rdo = relationship("Rdo", back_populates="configuracoes")


class RdoEvento(Base):
    __tablename__ = "rdo_evento"

    id_evento = Column(Integer, primary_key=True, index=True)
    id_rdo = Column(Integer, ForeignKey("rdo.id_rdo", ondelete="CASCADE"), nullable=False)

    categoria = Column(String(50), nullable=False)
    sistema = Column(String(100), nullable=True)
    subestacao = Column(String(50), nullable=True)
    hora_inicio = Column(Time, nullable=True)
    hora_fim = Column(Time, nullable=True)
    titulo = Column(String(255), nullable=True)
    descricao = Column(Text, nullable=False)
    status_evento = Column(String(30), default="INFORMATIVO", nullable=False)
    ordem = Column(Integer, default=0)

    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    editado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rdo = relationship("Rdo", back_populates="eventos")
    vinculos = relationship(
        "RdoEventoVinculo",
        back_populates="evento",
        cascade="all, delete-orphan",
    )


class RdoEventoVinculo(Base):
    __tablename__ = "rdo_evento_vinculo"

    id_vinculo = Column(Integer, primary_key=True, index=True)
    id_evento = Column(Integer, ForeignKey("rdo_evento.id_evento", ondelete="CASCADE"), nullable=False)

    tipo_vinculo = Column(String(30), nullable=False)
    id_referencia = Column(Integer, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    evento = relationship("RdoEvento", back_populates="vinculos")


class RdoImportacaoPdf(Base):
    __tablename__ = "rdo_importacao_pdf"

    id_importacao = Column(Integer, primary_key=True, index=True)
    id_rdo = Column(Integer, ForeignKey("rdo.id_rdo", ondelete="CASCADE"), nullable=False)

    nome_arquivo = Column(String(255), nullable=False)
    texto_extraido = Column(Text, nullable=True)
    dados_extraidos_json = Column(Text, nullable=True)
    status = Column(String(30), default="PENDENTE_REVISAO", nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    rdo = relationship("Rdo", back_populates="importacoes")


class RdoHistoricoEdicao(Base):
    __tablename__ = "rdo_historico_edicao"

    id_historico = Column(Integer, primary_key=True, index=True)
    id_rdo = Column(Integer, ForeignKey("rdo.id_rdo", ondelete="CASCADE"), nullable=False)

    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(50), nullable=False)
    campo_alterado = Column(String(100), nullable=True)
    valor_anterior = Column(Text, nullable=True)
    valor_novo = Column(Text, nullable=True)
    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    rdo = relationship("Rdo", back_populates="historico")
