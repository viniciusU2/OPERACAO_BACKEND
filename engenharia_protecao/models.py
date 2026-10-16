from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci",
}


class ModeloIED(Base):
    __tablename__ = "modelo_ied"
    __table_args__ = (
        UniqueConstraint("fabricante", "modelo", name="uq_modelo_ied_fabricante_modelo"),
        MYSQL_ARGS,
    )

    id_modelo_ied = Column(Integer, primary_key=True, autoincrement=True)
    fabricante = Column(String(100), nullable=False, index=True)
    familia = Column(String(100), nullable=True, index=True)
    modelo = Column(String(100), nullable=False, index=True)
    aplicacao = Column(String(300), nullable=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ieds = relationship("IED", back_populates="modelo")


class IED(Base):
    __tablename__ = "ied"
    __table_args__ = (
        UniqueConstraint("codigo_uuid", name="uq_ied_codigo_uuid"),
        UniqueConstraint("tag_operacional", name="uq_ied_tag_operacional"),
        UniqueConstraint("numero_serie", name="uq_ied_numero_serie"),
        CheckConstraint(
            "status_operacional IN ('EM_OPERACAO','SOBRESSALENTE','EM_MANUTENCAO','RETIRADO','DESCARTADO')",
            name="ck_ied_status_operacional",
        ),
        Index("ix_ied_localizacao", "id_subestacao", "id_funcao_operacao"),
        MYSQL_ARGS,
    )

    id_ied = Column(Integer, primary_key=True, autoincrement=True)
    codigo_uuid = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    tag_operacional = Column(String(100), nullable=False, index=True)
    id_ativo = Column(
        Integer,
        ForeignKey("ativo.id_ativo", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    id_modelo_ied = Column(
        Integer,
        ForeignKey("modelo_ied.id_modelo_ied", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    id_subestacao = Column(
        Integer,
        ForeignKey("subestacao.id_subestacao", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    id_funcao_operacao = Column(
        Integer,
        ForeignKey("funcao_operacao.id_funcao_operacao", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    painel_instalacao = Column(String(150), nullable=False)
    numero_serie = Column(String(150), nullable=True)
    codigo_produto = Column(String(150), nullable=True)
    versao_hardware = Column(String(100), nullable=True)
    versao_firmware = Column(String(100), nullable=True, index=True)
    data_instalacao = Column(Date, nullable=False)
    status_operacional = Column(String(30), nullable=False, default="EM_OPERACAO", server_default="EM_OPERACAO", index=True)
    observacoes_tecnicas = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    modelo = relationship("ModeloIED", back_populates="ieds")
    ativo_inventario = relationship("Ativo", foreign_keys=[id_ativo])
    instalacoes = relationship("IEDInstalacao", back_populates="ied", cascade="all, delete-orphan")
    modulos = relationship("IEDModulo", back_populates="ied", cascade="all, delete-orphan")
    firmwares = relationship("IEDFirmwareHistorico", back_populates="ied", cascade="all, delete-orphan")
    equipamentos = relationship("IEDEquipamento", back_populates="ied", cascade="all, delete-orphan")
    funcoes = relationship("IEDFuncao", back_populates="ied", cascade="all, delete-orphan")
    grupos_ajuste = relationship("IEDGrupoAjuste", back_populates="ied", cascade="all, delete-orphan")
    configuracoes = relationship("IEDConfiguracao", back_populates="ied", cascade="all, delete-orphan")
    alteracoes = relationship("SolicitacaoAlteracao", back_populates="ied", cascade="all, delete-orphan")
    interfaces_comunicacao = relationship(
        "IEDInterfaceComunicacao", back_populates="ied", cascade="all, delete-orphan"
    )
    goose_controles = relationship("IEDGooseControle", back_populates="ied", cascade="all, delete-orphan")
    circuitos = relationship("IEDCircuito", back_populates="ied", cascade="all, delete-orphan")
    sinais = relationship("IEDSinal", back_populates="ied", cascade="all, delete-orphan")
    ensaios = relationship("IEDEnsaio", back_populates="ied", cascade="all, delete-orphan")
    ocorrencias = relationship("IEDOcorrencia", back_populates="ied", cascade="all, delete-orphan")
    oscilografias = relationship("IEDOscilografia", back_populates="ied", cascade="all, delete-orphan")
    relatorios = relationship("IEDRelatorio", back_populates="ied", cascade="all, delete-orphan")


class IEDInstalacao(Base):
    __tablename__ = "ied_instalacao"
    __table_args__ = (
        CheckConstraint(
            "tipo_movimentacao IN ('INSTALACAO','TRANSFERENCIA','SUBSTITUICAO','RETIRADA')",
            name="ck_ied_instalacao_tipo_movimentacao",
        ),
        Index("ix_ied_instalacao_periodo", "id_ied", "data_inicio", "data_fim"),
        MYSQL_ARGS,
    )

    id_ied_instalacao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao", ondelete="RESTRICT"), nullable=False, index=True)
    id_funcao_operacao = Column(Integer, ForeignKey("funcao_operacao.id_funcao_operacao", ondelete="RESTRICT"), nullable=True, index=True)
    painel_instalacao = Column(String(150), nullable=False)
    tipo_movimentacao = Column(String(30), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)
    motivo = Column(String(300), nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ied = relationship("IED", back_populates="instalacoes")


class IEDModulo(Base):
    __tablename__ = "ied_modulo"
    __table_args__ = (
        Index("ix_ied_modulo_ied_slot", "id_ied", "slot"),
        MYSQL_ARGS,
    )

    id_ied_modulo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    tipo_modulo = Column(String(100), nullable=False)
    slot = Column(String(50), nullable=True)
    codigo_produto = Column(String(150), nullable=True)
    numero_serie = Column(String(150), nullable=True, index=True)
    versao_hardware = Column(String(100), nullable=True)
    status_operacional = Column(String(30), nullable=False, default="INSTALADO", server_default="INSTALADO")
    data_instalacao = Column(Date, nullable=True)
    data_retirada = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ied = relationship("IED", back_populates="modulos")


class IEDFirmwareHistorico(Base):
    __tablename__ = "ied_firmware_historico"
    __table_args__ = (
        Index("ix_ied_firmware_periodo", "id_ied", "data_inicio", "data_fim"),
        MYSQL_ARGS,
    )

    id_ied_firmware_historico = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    versao_firmware = Column(String(100), nullable=False, index=True)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)
    motivo = Column(String(300), nullable=True)
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os", ondelete="SET NULL"), nullable=True, index=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ied = relationship("IED", back_populates="firmwares")


class IEDEquipamento(Base):
    __tablename__ = "ied_equipamento"
    __table_args__ = (
        UniqueConstraint("id_ied", "id_ativo", "data_inicio", name="uq_ied_equipamento_periodo"),
        Index("ix_ied_equipamento_ativo_periodo", "id_ativo", "data_inicio", "data_fim"),
        MYSQL_ARGS,
    )

    id_ied_equipamento = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_ativo = Column(Integer, ForeignKey("ativo.id_ativo", ondelete="RESTRICT"), nullable=False, index=True)
    principal = Column(Boolean, nullable=False, default=False, server_default="0")
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ied = relationship("IED", back_populates="equipamentos")


# --------------------------------------------------------------------------- #
# Fase 2 - Funcoes de protecao, ajustes, configuracoes e backups
# --------------------------------------------------------------------------- #


class FuncaoANSI(Base):
    __tablename__ = "funcao_ansi"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_funcao_ansi_codigo"),
        Index("ix_funcao_ansi_categoria", "categoria"),
        MYSQL_ARGS,
    )

    id_funcao_ansi = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(20), nullable=False, index=True)
    nome = Column(String(150), nullable=False)
    categoria = Column(String(60), nullable=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    parametros = relationship("ParametroDefinicao", back_populates="funcao", cascade="all, delete-orphan")
    ied_funcoes = relationship("IEDFuncao", back_populates="funcao")


class ParametroDefinicao(Base):
    __tablename__ = "parametro_definicao"
    __table_args__ = (
        UniqueConstraint("id_funcao_ansi", "codigo", name="uq_parametro_definicao_funcao_codigo"),
        CheckConstraint(
            "tipo_dado IN ('NUMERICO','TEMPO','BOOLEANO','TEXTO')",
            name="ck_parametro_definicao_tipo_dado",
        ),
        MYSQL_ARGS,
    )

    id_parametro_definicao = Column(Integer, primary_key=True, autoincrement=True)
    id_funcao_ansi = Column(
        Integer,
        ForeignKey("funcao_ansi.id_funcao_ansi", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo = Column(String(60), nullable=False)
    nome = Column(String(150), nullable=False)
    unidade = Column(String(30), nullable=True)
    tipo_dado = Column(String(20), nullable=False, default="NUMERICO", server_default="NUMERICO")
    identificador_fabricante = Column(String(100), nullable=True)
    valor_minimo = Column(String(60), nullable=True)
    valor_maximo = Column(String(60), nullable=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    funcao = relationship("FuncaoANSI", back_populates="parametros")
    configs = relationship("ConfigParametro", back_populates="parametro", cascade="all, delete-orphan")


class IEDFuncao(Base):
    __tablename__ = "ied_funcao"
    __table_args__ = (
        UniqueConstraint("id_ied", "id_funcao_ansi", "instancia", name="uq_ied_funcao_instancia"),
        MYSQL_ARGS,
    )

    id_ied_funcao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_funcao_ansi = Column(
        Integer,
        ForeignKey("funcao_ansi.id_funcao_ansi", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    instancia = Column(Integer, nullable=False, default=1, server_default="1")
    habilitada = Column(Boolean, nullable=False, default=True, server_default="1")
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="funcoes")
    funcao = relationship("FuncaoANSI", back_populates="ied_funcoes")


class IEDGrupoAjuste(Base):
    __tablename__ = "ied_grupo_ajuste"
    __table_args__ = (
        UniqueConstraint("id_ied", "numero", name="uq_ied_grupo_ajuste_numero"),
        MYSQL_ARGS,
    )

    id_ied_grupo_ajuste = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    nome = Column(String(100), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1")
    descricao = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="grupos_ajuste")
    parametros = relationship("ConfigParametro", back_populates="grupo", cascade="all, delete-orphan")


class ConfigParametro(Base):
    __tablename__ = "config_parametro"
    __table_args__ = (
        UniqueConstraint(
            "id_ied_grupo_ajuste",
            "id_parametro_definicao",
            name="uq_config_parametro_grupo_parametro",
        ),
        MYSQL_ARGS,
    )

    id_config_parametro = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_grupo_ajuste = Column(
        Integer,
        ForeignKey("ied_grupo_ajuste.id_ied_grupo_ajuste", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_parametro_definicao = Column(
        Integer,
        ForeignKey("parametro_definicao.id_parametro_definicao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valor = Column(String(255), nullable=False)
    ajustado_em = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    grupo = relationship("IEDGrupoAjuste", back_populates="parametros")
    parametro = relationship("ParametroDefinicao", back_populates="configs")


class Arquivo(Base):
    __tablename__ = "arquivo"
    __table_args__ = (
        Index("ix_arquivo_sha256", "sha256"),
        Index("ix_arquivo_categoria", "categoria"),
        MYSQL_ARGS,
    )

    id_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    nome_original = Column(String(255), nullable=False)
    nome_armazenado = Column(String(255), nullable=False, unique=True)
    caminho = Column(String(500), nullable=False)
    tamanho_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(150), nullable=True)
    extensao = Column(String(20), nullable=True)
    sha256 = Column(String(64), nullable=False)
    categoria = Column(String(40), nullable=False, default="OUTRO", server_default="OUTRO")
    descricao = Column(Text, nullable=True)
    id_usuario_upload = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())


class IEDConfiguracao(Base):
    __tablename__ = "ied_configuracao"
    __table_args__ = (
        UniqueConstraint("id_ied", "versao", name="uq_ied_configuracao_versao"),
        CheckConstraint(
            "motivo IN ('BACKUP_PERIODICO','ALTERACAO_AJUSTE','PRE_MANUTENCAO','POS_MANUTENCAO','POS_FIRMWARE','OUTRO')",
            name="ck_ied_configuracao_motivo",
        ),
        CheckConstraint(
            "status_validacao IN ('PENDENTE','VALIDADA','REJEITADA')",
            name="ck_ied_configuracao_status_validacao",
        ),
        Index("ix_ied_configuracao_ied_data", "id_ied", "data_coleta"),
        MYSQL_ARGS,
    )

    id_ied_configuracao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    versao = Column(Integer, nullable=False)
    rotulo = Column(String(150), nullable=False)
    motivo = Column(String(40), nullable=False, default="OUTRO", server_default="OUTRO")
    status_validacao = Column(String(20), nullable=False, default="PENDENTE", server_default="PENDENTE", index=True)
    versao_digsi = Column(String(60), nullable=True)
    versao_firmware = Column(String(100), nullable=True)
    data_coleta = Column(Date, nullable=False)
    id_grupo_ajuste = Column(
        Integer,
        ForeignKey("ied_grupo_ajuste.id_ied_grupo_ajuste", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os", ondelete="SET NULL"), nullable=True, index=True)
    hash_configuracao = Column(String(64), nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    id_usuario_coleta = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="configuracoes")
    arquivos = relationship("ConfiguracaoArquivo", back_populates="configuracao", cascade="all, delete-orphan")
    validacoes = relationship("IEDBackupValidacao", back_populates="configuracao", cascade="all, delete-orphan")


class ConfiguracaoArquivo(Base):
    __tablename__ = "configuracao_arquivo"
    __table_args__ = (
        UniqueConstraint("id_ied_configuracao", "id_arquivo", name="uq_configuracao_arquivo"),
        CheckConstraint(
            "papel IN ('PRINCIPAL','EXPORT_PARAMETROS','SCL','DOCUMENTO','COMPLEMENTAR')",
            name="ck_configuracao_arquivo_papel",
        ),
        MYSQL_ARGS,
    )

    id_configuracao_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_configuracao = Column(
        Integer,
        ForeignKey("ied_configuracao.id_ied_configuracao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_arquivo = Column(Integer, ForeignKey("arquivo.id_arquivo", ondelete="CASCADE"), nullable=False, index=True)
    papel = Column(String(30), nullable=False, default="PRINCIPAL", server_default="PRINCIPAL")
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    configuracao = relationship("IEDConfiguracao", back_populates="arquivos")
    arquivo = relationship("Arquivo")


class IEDBackupValidacao(Base):
    __tablename__ = "ied_backup_validacao"
    __table_args__ = (
        CheckConstraint(
            "resultado IN ('APROVADO','REPROVADO')",
            name="ck_ied_backup_validacao_resultado",
        ),
        MYSQL_ARGS,
    )

    id_ied_backup_validacao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_configuracao = Column(
        Integer,
        ForeignKey("ied_configuracao.id_ied_configuracao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resultado = Column(String(20), nullable=False)
    observacoes = Column(Text, nullable=True)
    id_usuario_validacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    data_validacao = Column(Date, nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    configuracao = relationship("IEDConfiguracao", back_populates="validacoes")


# --------------------------------------------------------------------------- #
# Fase 3 - Gestao de alteracoes (solicitacao -> aprovacao -> implantacao -> validacao)
# --------------------------------------------------------------------------- #


class SolicitacaoAlteracao(Base):
    __tablename__ = "solicitacao_alteracao"
    __table_args__ = (
        UniqueConstraint("numero", name="uq_solicitacao_alteracao_numero"),
        CheckConstraint(
            "tipo IN ('AJUSTE','FIRMWARE','HARDWARE','COMUNICACAO','CORRECAO','OUTRO')",
            name="ck_solicitacao_alteracao_tipo",
        ),
        CheckConstraint(
            "prioridade IN ('BAIXA','MEDIA','ALTA','CRITICA')",
            name="ck_solicitacao_alteracao_prioridade",
        ),
        CheckConstraint(
            "status IN ('RASCUNHO','SUBMETIDA','EM_ANALISE','APROVADA','REJEITADA','IMPLANTADA',"
            "'EM_VALIDACAO','VALIDADA','NAO_VALIDADA','CONCLUIDA','CANCELADA','REVERTIDA')",
            name="ck_solicitacao_alteracao_status",
        ),
        CheckConstraint(
            "resultado_validacao IS NULL OR resultado_validacao IN ('APROVADO','REPROVADO')",
            name="ck_solicitacao_alteracao_resultado",
        ),
        Index("ix_solicitacao_alteracao_ied_status", "id_ied", "status"),
        MYSQL_ARGS,
    )

    id_solicitacao_alteracao = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(Integer, nullable=False, index=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(30), nullable=False, default="AJUSTE", server_default="AJUSTE", index=True)
    prioridade = Column(String(20), nullable=False, default="MEDIA", server_default="MEDIA", index=True)
    status = Column(String(30), nullable=False, default="RASCUNHO", server_default="RASCUNHO", index=True)
    id_configuracao_origem = Column(
        Integer,
        ForeignKey("ied_configuracao.id_ied_configuracao", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_configuracao_resultante = Column(
        Integer,
        ForeignKey("ied_configuracao.id_ied_configuracao", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_grupo_ajuste = Column(
        Integer,
        ForeignKey("ied_grupo_ajuste.id_ied_grupo_ajuste", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os", ondelete="SET NULL"), nullable=True, index=True)
    justificativa = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    data_necessidade = Column(Date, nullable=True)
    data_implantacao = Column(Date, nullable=True)
    data_validacao = Column(Date, nullable=True)
    resultado_validacao = Column(String(20), nullable=True)
    id_usuario_solicitante = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    id_usuario_aprovador = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    id_usuario_implantador = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    id_usuario_validador = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    id_usuario_reversao = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    id_configuracao_rollback = Column(
        Integer,
        ForeignKey("ied_configuracao.id_ied_configuracao", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_reversao = Column(Date, nullable=True)
    evidencia_implantacao = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="alteracoes")
    itens = relationship("AlteracaoItem", back_populates="solicitacao", cascade="all, delete-orphan")
    historico = relationship(
        "AlteracaoHistorico",
        back_populates="solicitacao",
        cascade="all, delete-orphan",
        order_by="AlteracaoHistorico.id_alteracao_historico",
    )


class AlteracaoItem(Base):
    __tablename__ = "alteracao_item"
    __table_args__ = (
        UniqueConstraint(
            "id_solicitacao_alteracao",
            "id_parametro_definicao",
            name="uq_alteracao_item_parametro",
        ),
        MYSQL_ARGS,
    )

    id_alteracao_item = Column(Integer, primary_key=True, autoincrement=True)
    id_solicitacao_alteracao = Column(
        Integer,
        ForeignKey("solicitacao_alteracao.id_solicitacao_alteracao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_parametro_definicao = Column(
        Integer,
        ForeignKey("parametro_definicao.id_parametro_definicao", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    valor_atual = Column(String(255), nullable=True)
    valor_proposto = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    solicitacao = relationship("SolicitacaoAlteracao", back_populates="itens")
    parametro = relationship("ParametroDefinicao")


class AlteracaoHistorico(Base):
    __tablename__ = "alteracao_historico"
    __table_args__ = (
        CheckConstraint(
            "acao IN ('CRIACAO','ATUALIZACAO','SUBMISSAO','ANALISE','APROVACAO','REJEICAO',"
            "'IMPLANTACAO','INICIO_VALIDACAO','VALIDACAO','CONCLUSAO','REJEICAO_VALIDACAO',"
            "'CANCELAMENTO','REVERSAO')",
            name="ck_alteracao_historico_acao",
        ),
        MYSQL_ARGS,
    )

    id_alteracao_historico = Column(Integer, primary_key=True, autoincrement=True)
    id_solicitacao_alteracao = Column(
        Integer,
        ForeignKey("solicitacao_alteracao.id_solicitacao_alteracao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acao = Column(String(30), nullable=False)
    status_anterior = Column(String(30), nullable=True)
    status_novo = Column(String(30), nullable=True)
    comentario = Column(Text, nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    solicitacao = relationship("SolicitacaoAlteracao", back_populates="historico")


# --------------------------------------------------------------------------- #
# Fase 4 - Engenharia de protecao: comunicacao, circuitos/sinais e ensaios
# --------------------------------------------------------------------------- #


class IEDInterfaceComunicacao(Base):
    __tablename__ = "ied_interface_comunicacao"
    __table_args__ = (
        UniqueConstraint("id_ied", "nome", name="uq_ied_interface_comunicacao_nome"),
        CheckConstraint(
            "tipo IN ('ETHERNET','SERIAL','FIBRA_OPTICA','PROCESS_BUS','WIRELESS')",
            name="ck_ied_interface_comunicacao_tipo",
        ),
        MYSQL_ARGS,
    )

    id_ied_interface_comunicacao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(60), nullable=False)
    tipo = Column(String(30), nullable=False, default="ETHERNET", server_default="ETHERNET", index=True)
    meio = Column(String(30), nullable=True)
    mac_address = Column(String(32), nullable=True)
    endereco_ip = Column(String(45), nullable=True)
    mascara = Column(String(45), nullable=True)
    gateway = Column(String(45), nullable=True)
    vlan = Column(String(30), nullable=True)
    velocidade = Column(String(20), nullable=True)
    conectada = Column(Boolean, nullable=False, default=True, server_default="1")
    descricao = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="interfaces_comunicacao")
    protocolos = relationship(
        "IEDProtocoloComunicacao", back_populates="interface", cascade="all, delete-orphan"
    )


class IEDProtocoloComunicacao(Base):
    __tablename__ = "ied_protocolo_comunicacao"
    __table_args__ = (
        UniqueConstraint(
            "id_ied_interface_comunicacao", "protocolo", "papel", name="uq_ied_protocolo_comunicacao"
        ),
        CheckConstraint(
            "protocolo IN ('IEC61850_MMS','IEC61850_GOOSE','IEC61850_SV','DNP3','MODBUS_RTU','MODBUS_TCP',"
            "'IEC60870_5_101','IEC60870_5_104','PROFIBUS','SNTP','NTP','PRP','HSR','OUTRO')",
            name="ck_ied_protocolo_comunicacao_protocolo",
        ),
        CheckConstraint(
            "papel IN ('SERVIDOR','CLIENTE','PUBLICADOR','ASSINANTE','AMBOS')",
            name="ck_ied_protocolo_comunicacao_papel",
        ),
        MYSQL_ARGS,
    )

    id_ied_protocolo_comunicacao = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_interface_comunicacao = Column(
        Integer,
        ForeignKey("ied_interface_comunicacao.id_ied_interface_comunicacao", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    protocolo = Column(String(40), nullable=False, index=True)
    papel = Column(String(20), nullable=False, default="SERVIDOR", server_default="SERVIDOR")
    porta = Column(String(20), nullable=True)
    endereco_destino = Column(String(60), nullable=True)
    habilitado = Column(Boolean, nullable=False, default=True, server_default="1")
    observacoes = Column(Text, nullable=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    interface = relationship("IEDInterfaceComunicacao", back_populates="protocolos")


class IEDGooseControle(Base):
    __tablename__ = "ied_goose_controle"
    __table_args__ = (
        UniqueConstraint("id_ied", "tipo", "direcao", "nome_controle", name="uq_ied_goose_controle"),
        CheckConstraint("tipo IN ('GOOSE','SV')", name="ck_ied_goose_controle_tipo"),
        CheckConstraint("direcao IN ('PUBLICADO','ASSINADO')", name="ck_ied_goose_controle_direcao"),
        MYSQL_ARGS,
    )

    id_ied_goose_controle = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_ied_interface_comunicacao = Column(
        Integer,
        ForeignKey("ied_interface_comunicacao.id_ied_interface_comunicacao", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo = Column(String(20), nullable=False, default="GOOSE", server_default="GOOSE", index=True)
    direcao = Column(String(20), nullable=False, default="PUBLICADO", server_default="PUBLICADO", index=True)
    nome_controle = Column(String(150), nullable=False)
    dataset = Column(String(150), nullable=True)
    appid = Column(String(20), nullable=True)
    mac_destino = Column(String(32), nullable=True)
    vlan = Column(String(30), nullable=True)
    conf_rev = Column(Integer, nullable=True)
    tempo_retransmissao_ms = Column(Integer, nullable=True)
    habilitado = Column(Boolean, nullable=False, default=True, server_default="1")
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="goose_controles")
    interface = relationship("IEDInterfaceComunicacao")


class IEDCircuito(Base):
    __tablename__ = "ied_circuito"
    __table_args__ = (
        UniqueConstraint("id_ied", "codigo", name="uq_ied_circuito_codigo"),
        CheckConstraint(
            "tipo IN ('TRIP','FECHAMENTO','BLOQUEIO','SINALIZACAO','MEDICAO','ALARME','SUPERVISAO','OUTRO')",
            name="ck_ied_circuito_tipo",
        ),
        MYSQL_ARGS,
    )

    id_ied_circuito = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(60), nullable=False)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(30), nullable=False, default="SINALIZACAO", server_default="SINALIZACAO", index=True)
    id_funcao_ansi = Column(
        Integer, ForeignKey("funcao_ansi.id_funcao_ansi", ondelete="SET NULL"), nullable=True, index=True
    )
    id_ied_equipamento = Column(
        Integer, ForeignKey("ied_equipamento.id_ied_equipamento", ondelete="SET NULL"), nullable=True, index=True
    )
    descricao = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1", index=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="circuitos")
    funcao = relationship("FuncaoANSI")
    sinais = relationship("IEDSinal", back_populates="circuito")


class IEDSinal(Base):
    __tablename__ = "ied_sinal"
    __table_args__ = (
        UniqueConstraint("id_ied", "mnemonico", name="uq_ied_sinal_mnemonico"),
        CheckConstraint(
            "tipo IN ('DIGITAL_ENTRADA','DIGITAL_SAIDA','ANALOGICA_ENTRADA','ANALOGICA_SAIDA')",
            name="ck_ied_sinal_tipo",
        ),
        CheckConstraint(
            "estado IN ('PENDENTE','COMISSIONADO','INATIVO','DESATIVADO')", name="ck_ied_sinal_estado"
        ),
        MYSQL_ARGS,
    )

    id_ied_sinal = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_ied_circuito = Column(
        Integer, ForeignKey("ied_circuito.id_ied_circuito", ondelete="SET NULL"), nullable=True, index=True
    )
    id_funcao_ansi = Column(
        Integer, ForeignKey("funcao_ansi.id_funcao_ansi", ondelete="SET NULL"), nullable=True, index=True
    )
    id_ied_equipamento = Column(
        Integer, ForeignKey("ied_equipamento.id_ied_equipamento", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo = Column(String(30), nullable=False, default="DIGITAL_ENTRADA", server_default="DIGITAL_ENTRADA", index=True)
    mnemonico = Column(String(60), nullable=False)
    descricao = Column(String(300), nullable=False)
    numero_terminal = Column(String(40), nullable=True)
    unidade = Column(String(30), nullable=True)
    valor_nominal = Column(String(60), nullable=True)
    estado = Column(String(20), nullable=False, default="PENDENTE", server_default="PENDENTE", index=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="sinais")
    circuito = relationship("IEDCircuito", back_populates="sinais")
    funcao = relationship("FuncaoANSI")


class IEDEnsaio(Base):
    __tablename__ = "ied_ensaio"
    __table_args__ = (
        UniqueConstraint("id_ied", "numero", name="uq_ied_ensaio_numero"),
        CheckConstraint(
            "tipo IN ('COMISSIONAMENTO','ACEITACAO','ROTINA','PERIODICO','POS_EVENTO','POS_REPARO','OUTRO')",
            name="ck_ied_ensaio_tipo",
        ),
        CheckConstraint(
            "status IN ('PLANEJADO','EM_ANDAMENTO','APROVADO','REPROVADO','CANCELADO')",
            name="ck_ied_ensaio_status",
        ),
        MYSQL_ARGS,
    )

    id_ied_ensaio = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(30), nullable=False, default="ROTINA", server_default="ROTINA", index=True)
    status = Column(String(20), nullable=False, default="PLANEJADO", server_default="PLANEJADO", index=True)
    descricao = Column(Text, nullable=True)
    data_prevista = Column(Date, nullable=True)
    data_execucao = Column(Date, nullable=True)
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os", ondelete="SET NULL"), nullable=True, index=True)
    id_usuario_executor = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    instrumentos = Column(Text, nullable=True)
    resultado = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="ensaios")
    itens = relationship(
        "IEDEnsaioItem",
        back_populates="ensaio",
        cascade="all, delete-orphan",
        order_by="IEDEnsaioItem.ordem",
    )
    arquivos = relationship("IEDEnsaioArquivo", back_populates="ensaio", cascade="all, delete-orphan")


class IEDEnsaioItem(Base):
    __tablename__ = "ied_ensaio_item"
    __table_args__ = (
        CheckConstraint(
            "resultado IS NULL OR resultado IN ('APROVADO','REPROVADO','NAO_APLICAVEL')",
            name="ck_ied_ensaio_item_resultado",
        ),
        MYSQL_ARGS,
    )

    id_ied_ensaio_item = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_ensaio = Column(
        Integer, ForeignKey("ied_ensaio.id_ied_ensaio", ondelete="CASCADE"), nullable=False, index=True
    )
    id_funcao_ansi = Column(
        Integer, ForeignKey("funcao_ansi.id_funcao_ansi", ondelete="SET NULL"), nullable=True, index=True
    )
    id_ied_sinal = Column(
        Integer, ForeignKey("ied_sinal.id_ied_sinal", ondelete="SET NULL"), nullable=True, index=True
    )
    ordem = Column(Integer, nullable=False, default=0, server_default="0")
    descricao = Column(String(300), nullable=False)
    valor_esperado = Column(String(120), nullable=True)
    valor_medido = Column(String(120), nullable=True)
    unidade = Column(String(30), nullable=True)
    resultado = Column(String(20), nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ensaio = relationship("IEDEnsaio", back_populates="itens")
    funcao = relationship("FuncaoANSI")
    sinal = relationship("IEDSinal")


class IEDEnsaioArquivo(Base):
    __tablename__ = "ied_ensaio_arquivo"
    __table_args__ = (
        UniqueConstraint("id_ied_ensaio", "id_arquivo", name="uq_ied_ensaio_arquivo"),
        MYSQL_ARGS,
    )

    id_ied_ensaio_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_ensaio = Column(
        Integer, ForeignKey("ied_ensaio.id_ied_ensaio", ondelete="CASCADE"), nullable=False, index=True
    )
    id_arquivo = Column(Integer, ForeignKey("arquivo.id_arquivo", ondelete="CASCADE"), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    id_usuario_upload = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ensaio = relationship("IEDEnsaio", back_populates="arquivos")
    arquivo = relationship("Arquivo")


# --------------------------------------------------------------------------- #
# Fase 5 - Ocorrencias e indicadores: eventos, oscilografias, relatorios, auditoria
# --------------------------------------------------------------------------- #


class IEDOcorrencia(Base):
    __tablename__ = "ied_ocorrencia"
    __table_args__ = (
        UniqueConstraint("id_ied", "numero", name="uq_ied_ocorrencia_numero"),
        CheckConstraint(
            "tipo IN ('DISPARO','REARME','ATUACAO_PROTECAO','ALARME','FALHA_COMUNICACAO',"
            "'SOBRECORRENTE','SOBRETENSAO','SUBTENSAO','FALTA_ENERGIA','OSCILACAO','OUTRO')",
            name="ck_ied_ocorrencia_tipo",
        ),
        CheckConstraint(
            "severidade IN ('BAIXA','MEDIA','ALTA','CRITICA')", name="ck_ied_ocorrencia_severidade"
        ),
        CheckConstraint(
            "status IN ('ABERTA','EM_ANALISE','ENCERRADA','CANCELADA')", name="ck_ied_ocorrencia_status"
        ),
        MYSQL_ARGS,
    )

    id_ied_ocorrencia = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(30), nullable=False, default="ALARME", server_default="ALARME", index=True)
    severidade = Column(String(20), nullable=False, default="MEDIA", server_default="MEDIA", index=True)
    status = Column(String(20), nullable=False, default="ABERTA", server_default="ABERTA", index=True)
    data_hora = Column(DateTime, nullable=False, server_default=func.now())
    descricao = Column(Text, nullable=True)
    causa_provavel = Column(Text, nullable=True)
    acao_tomada = Column(Text, nullable=True)
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os", ondelete="SET NULL"), nullable=True, index=True)
    id_usuario_registro = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    id_usuario_encerramento = Column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    data_encerramento = Column(DateTime, nullable=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="ocorrencias")
    arquivos = relationship("IEDOcorrenciaArquivo", back_populates="ocorrencia", cascade="all, delete-orphan")
    historico = relationship(
        "IEDOcorrenciaHistorico",
        back_populates="ocorrencia",
        cascade="all, delete-orphan",
        order_by="IEDOcorrenciaHistorico.id_ied_ocorrencia_historico",
    )
    oscilografias = relationship("IEDOscilografia", back_populates="ocorrencia")


class IEDOcorrenciaArquivo(Base):
    __tablename__ = "ied_ocorrencia_arquivo"
    __table_args__ = (
        UniqueConstraint("id_ied_ocorrencia", "id_arquivo", name="uq_ied_ocorrencia_arquivo"),
        MYSQL_ARGS,
    )

    id_ied_ocorrencia_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_ocorrencia = Column(
        Integer, ForeignKey("ied_ocorrencia.id_ied_ocorrencia", ondelete="CASCADE"), nullable=False, index=True
    )
    id_arquivo = Column(Integer, ForeignKey("arquivo.id_arquivo", ondelete="CASCADE"), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    id_usuario_upload = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ocorrencia = relationship("IEDOcorrencia", back_populates="arquivos")
    arquivo = relationship("Arquivo")


class IEDOcorrenciaHistorico(Base):
    __tablename__ = "ied_ocorrencia_historico"
    __table_args__ = (
        CheckConstraint(
            "acao IN ('CRIACAO','ATUALIZACAO','ANEXO','REMOCAO_ARQUIVO','ENCERRAMENTO','CANCELAMENTO',"
            "'REABERTURA','OSCILOGRAFIA','RELATORIO')",
            name="ck_ied_ocorrencia_historico_acao",
        ),
        MYSQL_ARGS,
    )

    id_ied_ocorrencia_historico = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_ocorrencia = Column(
        Integer, ForeignKey("ied_ocorrencia.id_ied_ocorrencia", ondelete="CASCADE"), nullable=False, index=True
    )
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    acao = Column(String(30), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    ocorrencia = relationship("IEDOcorrencia", back_populates="historico")


class IEDOscilografia(Base):
    __tablename__ = "ied_oscilografia"
    __table_args__ = (
        UniqueConstraint("id_ied", "numero", name="uq_ied_oscilografia_numero"),
        CheckConstraint(
            "tipo IN ('OSCILOGRAFIA','PERTURBACAO','RELIGAMENTO','FALTA','OUTRO')",
            name="ck_ied_oscilografia_tipo",
        ),
        MYSQL_ARGS,
    )

    id_ied_oscilografia = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_ocorrencia = Column(
        Integer, ForeignKey("ied_ocorrencia.id_ied_ocorrencia", ondelete="SET NULL"), nullable=True, index=True
    )
    numero = Column(Integer, nullable=False)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(30), nullable=False, default="OSCILOGRAFIA", server_default="OSCILOGRAFIA", index=True)
    data_hora = Column(DateTime, nullable=False, server_default=func.now())
    duracao_ms = Column(Integer, nullable=True)
    frequencia_amostragem_hz = Column(Integer, nullable=True)
    numero_canais = Column(Integer, nullable=True)
    origem = Column(String(150), nullable=True)
    observacoes = Column(Text, nullable=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="oscilografias")
    ocorrencia = relationship("IEDOcorrencia", back_populates="oscilografias")
    arquivos = relationship(
        "IEDOscilografiaArquivo", back_populates="oscilografia", cascade="all, delete-orphan"
    )


class IEDOscilografiaArquivo(Base):
    __tablename__ = "ied_oscilografia_arquivo"
    __table_args__ = (
        UniqueConstraint("id_ied_oscilografia", "id_arquivo", name="uq_ied_oscilografia_arquivo"),
        MYSQL_ARGS,
    )

    id_ied_oscilografia_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_oscilografia = Column(
        Integer,
        ForeignKey("ied_oscilografia.id_ied_oscilografia", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    id_arquivo = Column(Integer, ForeignKey("arquivo.id_arquivo", ondelete="CASCADE"), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    id_usuario_upload = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    oscilografia = relationship("IEDOscilografia", back_populates="arquivos")
    arquivo = relationship("Arquivo")


class IEDRelatorio(Base):
    __tablename__ = "ied_relatorio"
    __table_args__ = (
        UniqueConstraint("id_ied", "numero", name="uq_ied_relatorio_numero"),
        CheckConstraint(
            "tipo IN ('OCORRENCIA','INSPECAO','ENSAIO','MANUTENCAO','ANALISE','PERIODICO','OUTRO')",
            name="ck_ied_relatorio_tipo",
        ),
        CheckConstraint(
            "status IN ('RASCUNHO','EMITIDO','APROVADO','CANCELADO')", name="ck_ied_relatorio_status"
        ),
        MYSQL_ARGS,
    )

    id_ied_relatorio = Column(Integer, primary_key=True, autoincrement=True)
    id_ied = Column(Integer, ForeignKey("ied.id_ied", ondelete="CASCADE"), nullable=False, index=True)
    id_ocorrencia = Column(
        Integer, ForeignKey("ied_ocorrencia.id_ied_ocorrencia", ondelete="SET NULL"), nullable=True, index=True
    )
    numero = Column(Integer, nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(30), nullable=False, default="OCORRENCIA", server_default="OCORRENCIA", index=True)
    status = Column(String(20), nullable=False, default="RASCUNHO", server_default="RASCUNHO", index=True)
    data_emissao = Column(Date, nullable=True)
    periodo_inicio = Column(Date, nullable=True)
    periodo_fim = Column(Date, nullable=True)
    resumo = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    id_usuario_emissao = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    versao = Column(Integer, nullable=False, default=1, server_default="1")
    id_usuario_criacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    id_usuario_atualizacao = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ied = relationship("IED", back_populates="relatorios")
    ocorrencia = relationship("IEDOcorrencia")
    arquivos = relationship("IEDRelatorioArquivo", back_populates="relatorio", cascade="all, delete-orphan")


class IEDRelatorioArquivo(Base):
    __tablename__ = "ied_relatorio_arquivo"
    __table_args__ = (
        UniqueConstraint("id_ied_relatorio", "id_arquivo", name="uq_ied_relatorio_arquivo"),
        MYSQL_ARGS,
    )

    id_ied_relatorio_arquivo = Column(Integer, primary_key=True, autoincrement=True)
    id_ied_relatorio = Column(
        Integer, ForeignKey("ied_relatorio.id_ied_relatorio", ondelete="CASCADE"), nullable=False, index=True
    )
    id_arquivo = Column(Integer, ForeignKey("arquivo.id_arquivo", ondelete="CASCADE"), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    id_usuario_upload = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())

    relatorio = relationship("IEDRelatorio", back_populates="arquivos")
    arquivo = relationship("Arquivo")


class EngenhariaProtecaoAuditoria(Base):
    """Trilha imutável das operações sensíveis do módulo."""

    __tablename__ = "engenharia_protecao_auditoria"
    __table_args__ = (
        Index("ix_eng_protecao_auditoria_data", "criado_em"),
        Index("ix_eng_protecao_auditoria_usuario_data", "id_usuario", "criado_em"),
        Index("ix_eng_protecao_auditoria_recurso", "recurso", "id_recurso"),
        MYSQL_ARGS,
    )

    id_engenharia_protecao_auditoria = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    acao = Column(String(30), nullable=False, index=True)
    metodo = Column(String(10), nullable=False)
    caminho = Column(String(500), nullable=False)
    recurso = Column(String(100), nullable=True, index=True)
    id_recurso = Column(String(100), nullable=True)
    status_http = Column(Integer, nullable=False, index=True)
    endereco_ip = Column(String(64), nullable=True)
    user_agent = Column(String(300), nullable=True)
    detalhes = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
