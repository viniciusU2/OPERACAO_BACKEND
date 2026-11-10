"""Schemas Pydantic do modulo Unifilar.

O formato do payload replica a estrutura do editor (nós React Flow:
``id / position / data``) para que o frontend grave o estado tal como
esta no canvas, sem camada de conversao duplicada.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SchemaUnifilar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Posicao(BaseModel):
    x: float = 0
    y: float = 0


class DadosNoEntrada(SchemaUnifilar):
    tipo: str = Field(min_length=1, max_length=40)
    codigo: str | None = Field(default=None, max_length=64)
    nome: str | None = Field(default=None, max_length=160)
    vao: str | None = Field(default=None, max_length=64)
    rotacao: int = 0
    largura: float | None = None
    altura: float | None = None
    id_ativo: int | None = Field(default=None, ge=1)


class NoEntrada(SchemaUnifilar):
    id: str = Field(min_length=1, max_length=160)
    type: str = Field(default="noUnifilar", max_length=40)
    position: Posicao
    data: DadosNoEntrada


class LigacaoEntrada(SchemaUnifilar):
    id: str | None = Field(default=None, max_length=160)
    type: str | None = Field(default="smoothstep", max_length=40)
    source: str = Field(min_length=1, max_length=160)
    sourceHandle: str | None = Field(default=None, max_length=8)
    target: str = Field(min_length=1, max_length=160)
    targetHandle: str | None = Field(default=None, max_length=8)


class DiagramaEntrada(SchemaUnifilar):
    nodes: list[NoEntrada] = Field(default_factory=list)
    edges: list[LigacaoEntrada] = Field(default_factory=list)


class NoSaida(SchemaUnifilar):
    id: str
    type: str = "noUnifilar"
    position: Posicao
    data: DadosNoEntrada


class LigacaoSaida(SchemaUnifilar):
    id: str
    type: str = "smoothstep"
    source: str
    sourceHandle: str | None = None
    target: str
    targetHandle: str | None = None


class DiagramaSaida(SchemaUnifilar):
    id_subestacao: int
    atualizado_em: datetime | None = None
    nodes: list[NoSaida] = Field(default_factory=list)
    edges: list[LigacaoSaida] = Field(default_factory=list)


class TipoComponenteSaida(SchemaUnifilar):
    tipo: str
    nome: str
    categoria: str
    aceita_ativo: bool
    max_por_terminal: int
    largura: float
    altura: float


class ResumoDiagramaSaida(SchemaUnifilar):
    """Linha do indice de diagramas: usado pela rota de navegacao."""

    id_subestacao: int
    nome: str
    total_componentes: int
    total_ligacoes: int
    atualizado_em: datetime | None = None
