from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class solicitacao_intervencao(Base):
    __tablename__ = "solicitacao_intervencao"

    id_si = Column(Integer, primary_key=True, index=True)
    numero_si = Column(String(30), unique=True, nullable=False)
    numero_sgi = Column(String(30))
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao"))
    id_ativo = Column(Integer, ForeignKey("ativo.id_ativo"))
    id_grupo_ativo = Column(Integer, ForeignKey("grupo_ativo.id_grupo_ativo"), nullable=True, index=True)
    id_funcao_operacao = Column(Integer, ForeignKey("funcao_operacao.id_funcao_operacao"), nullable=True, index=True)
    escopo_ativo = Column(String(10), nullable=True)
    especie = Column(String(50))
    numero_os = Column(String(30))
    numero_apr = Column(String(50))
    prioridade = Column(String(20), default="NIVEL_3")
    natureza = Column(String(255))
    caracteristica_intervencao = Column(String(100))
    tipo = Column(String(50))
    documentos_referencia = Column(String(100))
    data_inicio_preriodo_total = Column(DateTime)
    data_fim_preriodo_total = Column(DateTime)
    data_inicio_preriodo_manutencao = Column(DateTime)
    data_fim_preriodo_manutencao = Column(DateTime)
    justificativa = Column(String(100))
    responsavel = Column(String(100))
    substituto = Column(String(100))
    aproveitamento = Column(String(30), default="NÃƒO")
    inclusao_servico = Column(String(30), default="NÃƒO")
    acarreta_risco_perdas_multiplas = Column(String(30), default="NAO")
    orgaos = Column(String(100))
    tipo_progrmacao = Column(String(30), default="DIARIO")
    tipo_progrmacao_diario = Column(String(30))
    descricao_servicos = Column(Text)
    observacoes = Column(Text)
    cabo_aterramento = Column(Text)
    risco_desligamento = Column(Text)
    condicoes_climaticas = Column(Text)
    execucao_periodo_noturno = Column(Text)
    postergacao_traz_risco = Column(String(30), default="NAO")
    quais_risco_desligamento = Column(Text)
    quais_condicoes_climaticas = Column(Text)
    quais_execucao_periodo_noturno = Column(Text)

    responsavel_ons_manutencao = Column(String(100))
    responsavel_cot_manutencao = Column(String(100))
    responsavel_se_manutencao =  Column(String(100))

    tipo_programacao=  Column(String(100))
    dias_excecao =  Column(String(100))
    tempo_retorno =  Column(String(100))
    disponivel =  Column(String(100))

    responsavel_data_ons_manutencao = Column(DateTime)
    responsavel_data_cot_manutencao = Column(DateTime)
    responsavel_data_se_manutencao = Column(DateTime)

    status_manutencao = Column(String(30), default="ABERTA")

    responsavel_ons_operacao = Column(String(100))
    responsavel_cot_operacao = Column(String(100))
    responsavel_se_operacao =  Column(String(100))
    
    responsavel_data_ons_operacao = Column(DateTime)
    responsavel_data_cot_operacao = Column(DateTime)
    responsavel_data_se_operacao = Column(DateTime)

    status_operacao = Column(String(30), default="ABERTA")

    # Status do fluxo novo (RASCUNHO, ENVIADA, REJEITADA, APROVADA, CANCELADA)
    # ou herdado (PROGRAMADA, CONCLUIDA, ENCERRADA). Ver SI/workflow.py.
    status = Column(String(30), nullable=True, default="RASCUNHO", index=True)

    criado_em = Column(DateTime, default=datetime.utcnow)
    emissor = Column(Text)
    editado_por = Column(Text)


    subestacao = relationship("Subestacao", back_populates="solicitacao_intervencao")
    ativo = relationship("Ativo")
    liberacoes = relationship("SILiberacao", back_populates="si", cascade="all, delete-orphan")
    historico = relationship(
        "SIHistorico",
        back_populates="si",
        cascade="all, delete-orphan",
        order_by="SIHistorico.id_historico",
    )

    @property
    def codigo_ativo(self):
        return self.ativo.codigo_ativo if self.ativo else None


class SILiberacao(Base):
    __tablename__ = "si_liberacao"

    id_liberacao = Column(Integer, primary_key=True, index=True)
    id_si = Column(Integer, ForeignKey("solicitacao_intervencao.id_si"), nullable=False, index=True)

    data_utilizacao = Column(Date, nullable=False)
    data_hora_liberacao = Column(DateTime, nullable=False)
    usuario_solicitou_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_solicitou = Column(String(200), nullable=False)
    operador_liberou = Column(String(200))

    data_hora_devolucao = Column(DateTime)
    usuario_devolveu_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_devolveu = Column(String(200))
    operador_recebeu_devolucao = Column(String(200))

    observacoes = Column(Text)
    status = Column(String(30), default="EM_EXECUCAO", nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    si = relationship("solicitacao_intervencao", back_populates="liberacoes")
    usuario_solicitou_rel = relationship("Usuario", foreign_keys=[usuario_solicitou_id])
    usuario_devolveu_rel = relationship("Usuario", foreign_keys=[usuario_devolveu_id])


class SIHistorico(Base):
    """Trilha de auditoria das mudancas de status da SI."""

    __tablename__ = "si_historico"

    id_historico = Column(Integer, primary_key=True, index=True)
    id_si = Column(
        Integer,
        ForeignKey("solicitacao_intervencao.id_si", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acao = Column(String(30), nullable=False)
    status_anterior = Column(String(30), nullable=True)
    status_novo = Column(String(30), nullable=False)
    observacao = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_nome = Column(String(200), nullable=False)
    usuario_perfil = Column(String(30), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    si = relationship("solicitacao_intervencao", back_populates="historico")

