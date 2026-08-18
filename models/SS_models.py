from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class SolicitacaoServico(Base):
    __tablename__ = "solicitacao_servico"

    id = Column(Integer, primary_key=True, index=True)

    numero_ss = Column(String(20), unique=True, index=True)
    numero_os = Column(String(30))

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
    id_grupo_ativo = Column(Integer, ForeignKey("grupo_ativo.id_grupo_ativo"), nullable=True, index=True)
    id_funcao_operacao = Column(Integer, ForeignKey("funcao_operacao.id_funcao_operacao"), nullable=True, index=True)
    escopo_ativo = Column(String(10), nullable=True)

    esquema_servico = Column(String(100))
    centro_custo = Column(String(50))

    causa = Column(String(100))
    causa_secundaria = Column(String(100))

    equipe = Column(String(100))

    descricao_problema = Column(Text)

    prioridade = Column(String(20))

    status = Column(String(20), default="ABERTA")

    emissor = Column(Text)
    editado_por = Column(Text)

    ativo = relationship("Ativo")
    grupo_ativo = relationship("GrupoAtivo")
    problemas = relationship("SSProblema", back_populates="ss", cascade="all, delete-orphan", lazy="selectin")

    @property
    def tipo_ativo_nome(self):
        if self.ativo and self.ativo.tipo_ativo:
            return self.ativo.tipo_ativo.nome
        if self.grupo_ativo and self.grupo_ativo.tipo_ativo:
            return self.grupo_ativo.tipo_ativo.nome
        return None

    @property
    def fase_ativo(self):
        return self.ativo.fase if self.ativo else None

    @property
    def problemas_titulos(self):
        return "; ".join(item.problema.titulo for item in self.problemas if item.problema)

    @property
    def problemas_criticidades(self):
        valores = []
        for item in self.problemas:
            valor = item.criticidade_identificada or (item.problema.criticidade_padrao if item.problema else None)
            valores.append(valor.value if hasattr(valor, "value") else str(valor or ""))
        return "; ".join(valores)

    @property
    def problemas_observacoes(self):
        return " | ".join((item.observacao or "").strip() for item in self.problemas)

    @property
    def problemas_confirmados(self):
        return "; ".join("SIM" if item.confirmado else "NAO" for item in self.problemas)
    @property
    def id_ss(self):
        return self.id

    @property
    def codigo_ativo(self):
        if self.ativo:
            return self.ativo.codigo_ativo
        return self.grupo_ativo.codigo_ativo if self.grupo_ativo else None

    @property
    def id_subestacao(self):
        if self.ativo:
            return self.ativo.id_subestacao
        return self.grupo_ativo.id_subestacao if self.grupo_ativo else None
