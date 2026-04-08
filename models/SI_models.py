from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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
    especie = Column(String(50))
    numero_apr = Column(String(50))
    tipo = Column(String(50))
    documentos_referencia = Column(String(100))
    data_inicio_preriodo_total = Column(DateTime)
    data_fim_preriodo_total = Column(DateTime)
    data_inicio_preriodo_manutencao = Column(DateTime)
    data_fim_preriodo_manutencao = Column(DateTime)
    justificativa = Column(String(100))
    responsavel = Column(String(100))
    substituto = Column(String(100))
    aproveitamento = Column(String(30), default="NÃO")
    inclusao_servico = Column(String(30), default="NÃO")
    orgaos = Column(String(100))
    tipo_progrmacao = Column(String(30), default="DIARIO")
    tipo_progrmacao_diario = Column(String(30))
    descricao_servicos = Column(Text)
    observacoes = Column(Text)
    cabo_aterramento = Column(Text)
    risco_desligamento = Column(Text)
    condicoes_climaticas = Column(Text)
    execucao_periodo_noturno = Column(Text)

    responsavel_ons_manutencao = Column(String(100))
    responsavel_cot_manutencao = Column(String(100))
    responsavel_se_manutencao =  Column(String(100))

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
   

    criado_em = Column(DateTime, default=datetime.utcnow)
    emissor = Column(Text)


    subestacao = relationship("Subestacao", back_populates="solicitacao_intervencao")
