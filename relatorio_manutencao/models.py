from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class RelatorioManutencao(Base):
    __tablename__ = "relatorio_manutencao"

    id_relatorio_manutencao = Column(Integer, primary_key=True, autoincrement=True)
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    id_tipo_ativo = Column(Integer, ForeignKey("tipo_ativo.id_tipo_ativo", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    periodicidade = Column(String(20), nullable=False, index=True)
    data_referencia = Column(Date, nullable=False, index=True)
    observacao = Column(Text, nullable=True)
    texto_introducao = Column(Text, nullable=False)
    corpo_tecnico_json = Column(Text, nullable=False)
    numero_os = Column(String(100), nullable=True)
    numero_apr = Column(String(100), nullable=True)
    periodo_capa = Column(String(100), nullable=False)
    concessao = Column(String(255), nullable=False)
    hora_inicio = Column(String(10), nullable=False)
    hora_fim = Column(String(10), nullable=False)
    temperatura_inicio = Column(String(20), nullable=False)
    temperatura_fim = Column(String(20), nullable=False)
    frequencia_inicio = Column(String(20), nullable=False)
    frequencia_fim = Column(String(20), nullable=False)
    tensao_inicio = Column(String(20), nullable=False)
    tensao_fim = Column(String(20), nullable=False)
    nome_arquivo_original = Column(String(255), nullable=False)
    nome_arquivo_armazenado = Column(String(255), nullable=False, unique=True)
    caminho_arquivo = Column(String(500), nullable=False)
    tamanho_bytes = Column(BigInteger, nullable=False)
    quantidade_fotos = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="RECEBIDO", index=True)
    erro_processamento = Column(Text, nullable=True)
    id_usuario_envio = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    id_usuario_edicao = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subestacao = relationship("Subestacao")
    tipo_ativo = relationship("TipoAtivo")
    usuario_envio = relationship("Usuario", foreign_keys=[id_usuario_envio])
    usuario_edicao = relationship("Usuario", foreign_keys=[id_usuario_edicao])

    @property
    def emissor(self):
        return self.usuario_envio.nome if self.usuario_envio else None

    @property
    def editado_por(self):
        return self.usuario_edicao.nome if self.usuario_edicao else None




