from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class SolicitacaoServico(Base):
    __tablename__ = "solicitacao_servico"

    id = Column(Integer, primary_key=True, index=True)

    numero_ss = Column(String(20), unique=True, index=True)

    data_hora_solicitacao = Column(DateTime)
    data_hora_abertura = Column(DateTime)
    data_hora_limite = Column(DateTime)

    solicitante = Column(String(100))
    matricula = Column(String(50))
    funcao = Column(String(100))

    telefone = Column(String(20))
    email = Column(String(100))
    orgao = Column(String(100))

    instalacao = Column(String(100))
    localizacao = Column(String(100))
    complemento = Column(String(100))

    id_ativo = Column(Integer, ForeignKey("ativo.id_ativo"))

    esquema_servico = Column(String(100))
    centro_custo = Column(String(50))

    causa = Column(String(100))
    causa_secundaria = Column(String(100))

    equipe = Column(String(100))

    descricao_problema = Column(Text)

    prioridade = Column(String(20))

    status = Column(String(20), default="ABERTA")

    ativo = relationship("Ativo")