"""Regras de status e permissao das Solicitacoes de Intervencao (SI).

Fluxo novo
----------
::

    RASCUNHO --enviar--> ENVIADA --aprovar--> APROVADA --concluir--> CONCLUIDA
                            |                     |             (final)
                            |                     +--cancelar--> CANCELADA (final)
                            +--rejeitar--> REJEITADA --enviar--> ENVIADA
                            +--cancelar--> CANCELADA (final)

- Somente a Manutencao Local (papel ``mantenedor``) cria, edita e envia.
- O Centro de Operacoes (papeis ``admin`` e ``operador``) aprova, rejeita e
  cancela.
- Concluir e permitido aos dois perfis (Manutencao e Operacao) quando a SI
  esta aprovada e a intervencao foi executada.
- Rascunho nao aparece para a Operacao.
- APROVADA, CANCELADA e CONCLUIDA nunca voltam para RASCUNHO/ENVIADA.

Status herdados do fluxo anterior (``PROGRAMADA``, ``CONCLUIDA``,
``ENCERRADA``) continuam existindo para nao perder o historico. Eles sao
somente leitura, exceto ``PROGRAMADA``, que ainda pode ser editada e enviada
para entrar no fluxo novo.
"""

from __future__ import annotations

RASCUNHO = "RASCUNHO"
ENVIADA = "ENVIADA"
REJEITADA = "REJEITADA"
APROVADA = "APROVADA"
CANCELADA = "CANCELADA"

# Status do fluxo anterior, preservados.
PROGRAMADA = "PROGRAMADA"
CONCLUIDA = "CONCLUIDA"
ENCERRADA = "ENCERRADA"

LEGADOS = (PROGRAMADA, CONCLUIDA, ENCERRADA)

STATUS_VALIDOS = (RASCUNHO, ENVIADA, REJEITADA, APROVADA, CANCELADA) + LEGADOS

ROTULOS = {
    RASCUNHO: "Rascunho",
    ENVIADA: "Enviada / Em analise",
    REJEITADA: "Rejeitada",
    APROVADA: "Aprovada",
    CANCELADA: "Cancelada",
    PROGRAMADA: "Programada",
    CONCLUIDA: "Concluida",
    ENCERRADA: "Encerrada",
}

# Estados em que a Manutencao Local pode alterar o documento.
EDITAVEIS = frozenset({RASCUNHO, REJEITADA, PROGRAMADA})

# Estados em que os campos de liberacao podem ser alterados. Alem da edicao
# normal, a SI aprovada continua aceitando liberacoes enquanto a intervencao
# acontece.
EDITAVEIS_LIBERACAO = frozenset(EDITAVEIS | {APROVADA})

# Transicoes permitidas a partir de cada status.
TRANSICOES = {
    RASCUNHO: (ENVIADA,),
    REJEITADA: (ENVIADA,),
    PROGRAMADA: (ENVIADA,),
    ENVIADA: (APROVADA, REJEITADA, CANCELADA),
    APROVADA: (CONCLUIDA, CANCELADA),
    CANCELADA: (),
    CONCLUIDA: (),
    ENCERRADA: (),
}

ACOES = {
    "enviar": ENVIADA,
    "aprovar": APROVADA,
    "rejeitar": REJEITADA,
    "concluir": CONCLUIDA,
    "cancelar": CANCELADA,
}

ACOES_MANUTENCAO = frozenset({"enviar", "concluir"})
ACOES_OPERACAO = frozenset({"aprovar", "rejeitar", "concluir", "cancelar"})

# Acoes que exigem justificativa.
ACOES_COM_OBSERVACAO = frozenset({"rejeitar", "cancelar"})

ROTULOS_ACAO = {
    "enviar": "Enviar para o Centro de Operacoes",
    "aprovar": "Aprovar",
    "rejeitar": "Rejeitar",
    "concluir": "Concluir SI",
    "cancelar": "Cancelar SI",
}

VERBOS_ACAO = {
    "enviar": "enviar",
    "aprovar": "aprovar",
    "rejeitar": "rejeitar",
    "concluir": "concluir",
    "cancelar": "cancelar",
}

PERFIL_MANUTENCAO = "MANUTENCAO"
PERFIL_OPERACAO = "OPERACAO"


def normalizar(valor) -> str:
    return (valor or "").strip().upper() if isinstance(valor, str) else ""


def status_atual(si) -> str:
    """Status efetivo da SI, com fallback para registros ainda nao migrados."""
    valor = normalizar(getattr(si, "status", None))
    if valor in STATUS_VALIDOS:
        return valor
    for campo in ("status_operacao", "status_manutencao"):
        legado = normalizar(getattr(si, campo, None))
        if legado in (CONCLUIDA, ENCERRADA, PROGRAMADA):
            return legado
    return RASCUNHO


def rotulo(status) -> str:
    valor = normalizar(status) or RASCUNHO
    return ROTULOS.get(valor, valor.replace("_", " ").title())


def perfil(usuario) -> str | None:
    """Traduz o papel do usuario no papel do fluxo de SI.

    ``admin`` e ``operador`` sao o Centro de Operacoes; ``mantenedor`` e a
    Manutencao Local. Exclusao de SI continua sendo restrita ao ``admin``.
    """
    role = normalizar(getattr(usuario, "role", None))
    if role == "MANTENEDOR":
        return PERFIL_MANUTENCAO
    if role in ("ADMIN", "OPERADOR"):
        return PERFIL_OPERACAO
    return None


def pode_editar(si, usuario) -> bool:
    return perfil(usuario) == PERFIL_MANUTENCAO and status_atual(si) in EDITAVEIS


def pode_editar_liberacoes(si, usuario) -> bool:
    """Campos de liberacao: editaveis no rascunho/rejeitada/programada e
    tambem enquanto a SI esta aprovada (a intervencao acontece nesse periodo).
    """
    return perfil(usuario) is not None and status_atual(si) in EDITAVEIS_LIBERACAO


def pode_criar(usuario) -> bool:
    return perfil(usuario) == PERFIL_MANUTENCAO


def pode_excluir(si, usuario) -> bool:
    """Exclusao pelo admin: rascunho, rejeitada ou cancelada.

    Enviada e aprovada fazem parte da trilha de auditoria e nao podem sumir.
    Uma aprovada pode ser cancelada antes (com justificativa) e entao
    excluida. Ao excluir, o numero da SI volta para a fila e o proximo
    cadastro reaproveita o mesmo numero.
    """
    return (
        normalizar(getattr(usuario, "role", None)) == "ADMIN"
        and status_atual(si) in (RASCUNHO, REJEITADA, CANCELADA)
    )


def pode_visualizar(si, usuario) -> bool:
    # A Operacao nao visualiza rascunhos.
    if perfil(usuario) == PERFIL_OPERACAO and status_atual(si) == RASCUNHO:
        return False
    return True


def acoes_disponiveis(si, usuario) -> list[str]:
    """Acoes de status que este usuario pode executar nesta SI."""
    atual = status_atual(si)
    permitidas = TRANSICOES.get(atual, ())
    if not permitidas:
        return []
    perfil_usuario = perfil(usuario)
    if perfil_usuario == PERFIL_MANUTENCAO:
        candidatas = ACOES_MANUTENCAO
    elif perfil_usuario == PERFIL_OPERACAO:
        candidatas = ACOES_OPERACAO
    else:
        return []
    return [
        acao
        for acao in ("enviar", "aprovar", "rejeitar", "concluir", "cancelar")
        if acao in candidatas and ACOES[acao] in permitidas
    ]


def pode_executar(si, usuario, acao: str) -> bool:
    return acao in acoes_disponiveis(si, usuario)


def proximo_status(acao: str) -> str:
    if acao not in ACOES:
        raise KeyError(f"Acao de SI desconhecida: {acao}")
    return ACOES[acao]


def observacao_obrigatoria(acao: str) -> bool:
    return acao in ACOES_COM_OBSERVACAO


def motivo_bloqueio_edicao(si) -> str:
    atual = status_atual(si)
    if atual == ENVIADA:
        return "A SI esta em analise pelo Centro de Operacoes e nao pode ser editada."
    if atual == APROVADA:
        return (
            "A SI foi aprovada: o documento fica somente leitura, mas os campos "
            "de liberacao continuam editaveis. Conclua a SI quando a intervencao terminar."
        )
    if atual == CANCELADA:
        return "A SI foi cancelada e nao pode mais ser editada."
    if atual == CONCLUIDA:
        return "A SI foi concluida e e somente leitura."
    if atual == ENCERRADA:
        return "A SI esta encerrada e e somente leitura."
    return "Seu perfil nao tem permissao para editar esta SI."
