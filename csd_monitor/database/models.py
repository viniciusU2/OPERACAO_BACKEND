"""Modelo SQLAlchemy correspondente ao schema dimensional do MVP."""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DimEquipamento(Base):
    __tablename__ = "dim_equipamento"
    id_equipamento: Mapped[int] = mapped_column(primary_key=True)
    project_reference: Mapped[str | None] = mapped_column(String(100))
    order_reference: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100))
    end_user: Mapped[str | None] = mapped_column(String(100))
    substation: Mapped[str | None] = mapped_column(String(150))
    voltage_level_kv: Mapped[float | None] = mapped_column(Float)
    frequency_hz: Mapped[float | None] = mapped_column(Float)
    bay_number: Mapped[str | None] = mapped_column(String(100))
    feeder_name: Mapped[str | None] = mapped_column(String(100))
    cb_model: Mapped[str | None] = mapped_column(String(100))
    cb1_sn: Mapped[str | None] = mapped_column(String(100))
    cb2_sn: Mapped[str | None] = mapped_column(String(100))
    csd_serial_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    csd_hostname: Mapped[str | None] = mapped_column(String(100))
    csd_ied_name: Mapped[str | None] = mapped_column(String(100))
    csd_software_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[object | None] = mapped_column(DateTime)


class DimCanal(Base):
    __tablename__ = "dim_canal"
    id_canal: Mapped[int] = mapped_column(primary_key=True)
    indice_canal: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    nome_canal: Mapped[str | None] = mapped_column(String(100))
    fase: Mapped[str | None] = mapped_column(String(20))
    disjuntor: Mapped[str | None] = mapped_column(String(50))
    descricao: Mapped[str | None] = mapped_column(String(255))


class DimGrandeza(Base):
    __tablename__ = "dim_grandeza"
    id_grandeza: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(200), nullable=False)
    nome: Mapped[str | None] = mapped_column(String(255))
    categoria: Mapped[str | None] = mapped_column(String(100))
    subcategoria: Mapped[str | None] = mapped_column(String(100))
    unidade: Mapped[str | None] = mapped_column(String(50))
    __table_args__ = (UniqueConstraint("codigo", "unidade", name="uk_grandeza"),)


class DimTipoAlarme(Base):
    __tablename__ = "dim_tipo_alarme"
    id_tipo_alarme: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    nome: Mapped[str | None] = mapped_column(String(255))
    categoria: Mapped[str | None] = mapped_column(String(100))
    severidade: Mapped[str | None] = mapped_column(String(50))


class DimConfiguracao(Base):
    __tablename__ = "dim_configuracao"
    id_configuracao: Mapped[int] = mapped_column(primary_key=True)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    parametro: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100))
    valor_original: Mapped[str | None] = mapped_column(Text)
    valor_numerico: Mapped[float | None] = mapped_column(Float)
    unidade: Mapped[str | None] = mapped_column(String(50))
    source_file: Mapped[str | None] = mapped_column(String(255))
    data_importacao: Mapped[object | None] = mapped_column(DateTime)


class FatoEvento(Base):
    __tablename__ = "fato_evento"
    id_evento: Mapped[int] = mapped_column(primary_key=True)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    nome_arquivo: Mapped[str | None] = mapped_column(String(255))
    hash_arquivo: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    archive_type: Mapped[str | None] = mapped_column(String(50))
    archive_creation_date_utc: Mapped[object | None] = mapped_column(DateTime)
    archive_creation_date_local: Mapped[object | None] = mapped_column(DateTime)
    switching_program: Mapped[str | None] = mapped_column(String(100))
    phase_ref_open: Mapped[str | None] = mapped_column(String(50))
    phase_ref_close: Mapped[str | None] = mapped_column(String(50))
    timestamp_open_order: Mapped[object | None] = mapped_column(DateTime)
    timestamp_close_order: Mapped[object | None] = mapped_column(DateTime)
    data_importacao: Mapped[object | None] = mapped_column(DateTime)


class FatoMedicao(Base):
    __tablename__ = "fato_medicao"
    id_medicao: Mapped[int] = mapped_column(primary_key=True)
    id_evento: Mapped[int] = mapped_column(ForeignKey("fato_evento.id_evento"), nullable=False)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    id_grandeza: Mapped[int] = mapped_column(ForeignKey("dim_grandeza.id_grandeza"), nullable=False)
    id_canal: Mapped[int | None] = mapped_column(ForeignKey("dim_canal.id_canal"))
    valor: Mapped[float | None] = mapped_column(Float)
    source_parameter: Mapped[str | None] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("id_evento", "id_grandeza", "id_canal", "source_parameter", name="uk_medicao"),)


class FatoAlarme(Base):
    __tablename__ = "fato_alarme"
    id_alarme: Mapped[int] = mapped_column(primary_key=True)
    id_evento: Mapped[int] = mapped_column(ForeignKey("fato_evento.id_evento"), nullable=False)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    id_tipo_alarme: Mapped[int] = mapped_column(ForeignKey("dim_tipo_alarme.id_tipo_alarme"), nullable=False)
    id_canal: Mapped[int | None] = mapped_column(ForeignKey("dim_canal.id_canal"))
    estado_alarme: Mapped[bool | None] = mapped_column(Boolean)
    timestamp_on: Mapped[object | None] = mapped_column(DateTime)
    timestamp_off: Mapped[object | None] = mapped_column(DateTime)
    duracao_segundos: Mapped[float | None] = mapped_column(Float)
    source_parameter: Mapped[str | None] = mapped_column(String(255))


class FatoEstado(Base):
    __tablename__ = "fato_estado"
    id_estado: Mapped[int] = mapped_column(primary_key=True)
    id_evento: Mapped[int] = mapped_column(ForeignKey("fato_evento.id_evento"), nullable=False)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    id_canal: Mapped[int | None] = mapped_column(ForeignKey("dim_canal.id_canal"))
    codigo_estado: Mapped[str | None] = mapped_column(String(200))
    valor_estado: Mapped[str | None] = mapped_column(String(255))


class FatoContador(Base):
    __tablename__ = "fato_contador"
    id_contador: Mapped[int] = mapped_column(primary_key=True)
    id_evento: Mapped[int] = mapped_column(ForeignKey("fato_evento.id_evento"), nullable=False)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    id_grandeza: Mapped[int] = mapped_column(ForeignKey("dim_grandeza.id_grandeza"), nullable=False)
    id_canal: Mapped[int | None] = mapped_column(ForeignKey("dim_canal.id_canal"))
    valor: Mapped[float | None] = mapped_column(Float)


class FatoTimestamp(Base):
    __tablename__ = "fato_timestamp"
    id_timestamp: Mapped[int] = mapped_column(primary_key=True)
    id_evento: Mapped[int] = mapped_column(ForeignKey("fato_evento.id_evento"), nullable=False)
    id_equipamento: Mapped[int] = mapped_column(ForeignKey("dim_equipamento.id_equipamento"), nullable=False)
    id_canal: Mapped[int | None] = mapped_column(ForeignKey("dim_canal.id_canal"))
    tipo_timestamp: Mapped[str | None] = mapped_column(String(200))
    timestamp_valor: Mapped[object | None] = mapped_column(DateTime)
    source_parameter: Mapped[str | None] = mapped_column(String(255))


class EtlImportacao(Base):
    __tablename__ = "etl_importacao"
    id_importacao: Mapped[int] = mapped_column(primary_key=True)
    nome_arquivo: Mapped[str | None] = mapped_column(String(255))
    hash_arquivo: Mapped[str | None] = mapped_column(String(64))
    data_inicio: Mapped[object | None] = mapped_column(DateTime)
    data_fim: Mapped[object | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String(20))
    linhas_xml: Mapped[int | None] = mapped_column(Integer)
    medicoes_inseridas: Mapped[int | None] = mapped_column(Integer)
    alarmes_inseridos: Mapped[int | None] = mapped_column(Integer)
    estados_inseridos: Mapped[int | None] = mapped_column(Integer)
    contadores_inseridos: Mapped[int | None] = mapped_column(Integer)
    timestamps_inseridos: Mapped[int | None] = mapped_column(Integer)
    mensagem_erro: Mapped[str | None] = mapped_column(Text)


class EtlParametroNaoClassificado(Base):
    __tablename__ = "etl_parametro_nao_classificado"
    id: Mapped[int] = mapped_column(primary_key=True)
    id_importacao: Mapped[int] = mapped_column(ForeignKey("etl_importacao.id_importacao"), nullable=False)
    parametro: Mapped[str] = mapped_column(String(255), nullable=False)
    valor_original: Mapped[str | None] = mapped_column(Text)
    unidade: Mapped[str | None] = mapped_column(String(50))

