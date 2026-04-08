from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class OrdemServico(Base):
    __tablename__ = "ordem_servico"

    id_os = Column(Integer, primary_key=True, index=True)
    numero_os = Column(String(30), unique=True, nullable=False)
    numero_si = Column(String(30))

    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao"))
    id_ativo = Column(Integer, ForeignKey("ativo.id_ativo"))

    especie = Column(String(50))
    numero_apr = Column(String(50))

    instalacao = Column(String(100))
    localizacao = Column(String(100))
    complemento = Column(String(100))

    origens = Column(Text)
    defeito = Column(Text)
    esquema_servicos = Column(Text)

    prioridade = Column(String(20))
    responsavel = Column(String(100))
    responsavel_manutencao = Column(String(100))
    responsavel_operacao =  Column(String(100))
    substituto = Column(String(100))

    data_inicio_programado = Column(DateTime)
    data_fim_programado = Column(DateTime)

    descricao_servicos = Column(Text)
    observacoes = Column(Text)

    causa_primaria = Column(Text)
    causa_secundaria = Column(Text)
    emissor = Column(Text)

    data_abertura_ss = Column(DateTime)
    data_inicio_execucao = Column(DateTime)
    data_fim_execucao = Column(DateTime)

    centro_custos = Column(String(50))
    status = Column(String(30), default="ABERTA")

    criado_em = Column(DateTime, default=datetime.utcnow)

    subestacao = relationship("Subestacao", back_populates="ordens")
    ativo = relationship("Ativo", back_populates="ordens")
    livro_registro = relationship("LivroRegistro", back_populates="os")
    inspecao = relationship("Inspecao", back_populates="ordem_servico", uselist=False)