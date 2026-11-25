"""Corrige a topologia do unifilar da SE GOR para a simulacao SAGE.

Ajustes aplicados (idempotentes):

1. Fecha o elo que faltava no vao G: ``35C2-5.T2 -> 95C2.T1``. Sem ele o
   caminho alternativo pelo barramento B nao existe e abrir 15E7/15E9
   desenergizava o restante da linha.
2. Reposiciona os ramos dos reatores 05E6/05E8 para a base do barramento
   B (``BAR500B.B4``), como no arranjo original. Assim os reatores so
   ficam desenergizados quando os dois disjuntores 15C2 e 15C4 abrem e o
   barramento B inteiro cai, e nao por causa de 15E7/15E9/15D7/15D8.

Uso:

    python scripts/corrigir_unifilar_sage_gor.py --dry-run
    python scripts/corrigir_unifilar_sage_gor.py

O script le o diagrama salvo pelo proprio servico (mesmas validacoes da
API), troca as ligacoes necessarias e regrava o diagrama completo.
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bootstrap import RAIZ  # noqa: E402,F401

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402
from UNIFILAR import schemas, service  # noqa: E402

SUBESTACAO_PADRAO = "SE GOR"

# Terminais que precisam ser religados.
ELO_VAO_G = ("35C2-5", "T2", "95C2", "T1")
RAMOS_REATOR_BARRA = (
    ("35C2-7", "T1", "BAR500B", "B4"),
    ("35C4-7", "T1", "BAR500B", "B4"),
)


def _por_codigo(nodes: list[schemas.NoSaida]) -> dict[str, schemas.NoSaida]:
    mapa: dict[str, schemas.NoSaida] = {}
    for no in nodes:
        codigo = (no.data.codigo or "").strip().upper()
        if codigo:
            mapa[codigo] = no
    return mapa


def _chave(lig: schemas.LigacaoSaida) -> tuple[str, str | None, str, str | None]:
    return (lig.source, lig.sourceHandle, lig.target, lig.targetHandle)


def _ligacao_existe(
    edges: list[schemas.LigacaoSaida], a: str, ta: str, b: str, tb: str
) -> bool:
    alvo = {(a, ta, b, tb), (b, tb, a, ta)}
    return any(_chave(e) in alvo for e in edges)


def _remove_ligacoes(
    edges: list[schemas.LigacaoSaida],
    no_id: str,
    terminal: str,
) -> list[str]:
    """Remove as ligacoes que chegam em um terminal especifico do no."""
    removidas = []
    mantidas = []
    for lig in edges:
        toca_origem = lig.source == no_id and lig.sourceHandle == terminal
        toca_destino = lig.target == no_id and lig.targetHandle == terminal
        if toca_origem or toca_destino:
            removidas.append(
                f"{lig.source}.{lig.sourceHandle} -> {lig.target}.{lig.targetHandle}"
            )
            continue
        mantidas.append(lig)
    edges[:] = mantidas
    return removidas


def _aplicar(
    nodes: list[schemas.NoSaida], edges: list[schemas.LigacaoSaida]
) -> list[str]:
    codigos = _por_codigo(nodes)
    avisos: list[str] = []
    for codigo in ("35C2-5", "95C2", "35C2-7", "35C4-7", "BAR500B"):
        if codigo not in codigos:
            avisos.append(f"componente {codigo} nao encontrado; nada alterado")
    if avisos:
        return avisos

    ids = {
        "35C2-5": codigos["35C2-5"].id,
        "95C2": codigos["95C2"].id,
        "35C2-7": codigos["35C2-7"].id,
        "35C4-7": codigos["35C4-7"].id,
        "BAR500B": codigos["BAR500B"].id,
    }

    # 1) elo do vao G
    a, ta, b, tb = ELO_VAO_G
    if not _ligacao_existe(edges, ids[a], ta, ids[b], tb):
        edges.append(
            schemas.LigacaoSaida(
                id=f"l-{ids[a]}-{ta}-{ids[b]}-{tb}",
                source=ids[a],
                sourceHandle=ta,
                target=ids[b],
                targetHandle=tb,
            )
        )
        print(f"+ ligacao {a}.{ta} -> {b}.{tb}")

    # 2) ramos dos reatores na base do barramento B
    for origem, terminal, barra, terminal_barra in RAMOS_REATOR_BARRA:
        removidas = _remove_ligacoes(edges, ids[origem], terminal)
        for lig in removidas:
            print(f"- ligacao {lig} (terminal {origem}.{terminal})")
        edges.append(
            schemas.LigacaoSaida(
                id=f"l-{ids[barra]}-{terminal_barra}-{ids[origem]}-{terminal}",
                source=ids[barra],
                sourceHandle=terminal_barra,
                target=ids[origem],
                targetHandle=terminal,
            )
        )
        print(f"+ ligacao {barra}.{terminal_barra} -> {origem}.{terminal}")

    return avisos


def _adjacencia(edges: list[schemas.LigacaoSaida]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for lig in edges:
        adj.setdefault(lig.source, set()).add(lig.target)
        adj.setdefault(lig.target, set()).add(lig.source)
    return adj


def _alcancaveis(
    inicio: list[str], adj: dict[str, set[str]], bloqueados: set[str]
) -> set[str]:
    vistos = set(inicio)
    fila = deque(inicio)
    while fila:
        atual = fila.popleft()
        for vizinho in adj.get(atual, ()):
            if vizinho in vistos or vizinho in bloqueados:
                continue
            vistos.add(vizinho)
            fila.append(vizinho)
    return vistos


def _simular(
    nodes: list[schemas.NoSaida], edges: list[schemas.LigacaoSaida]
) -> None:
    codigos = _por_codigo(nodes)
    barras = [n for n in nodes if n.data.tipo == "BARRAMENTO"]
    if not barras:
        print("Sem barramento para simular.")
        return
    fonte = min(barras, key=lambda n: n.position.y)
    adj = _adjacencia(edges)
    base = _alcancaveis([fonte.id], adj, set())
    por_id = {n.id: n for n in nodes}

    print(f"\nFonte SAGE: {(fonte.data.codigo or fonte.id)} (y={fonte.position.y:.0f})")
    print(f"Energizados com tudo fechado: {len(base)} de {len(nodes)}")

    alvos = [
        "15E7",
        "15E9",
        "15D7",
        "15D8",
        "15C2",
        "15C4",
        "15C2+15C4",
        "05E6",
        "05E8",
        "BAR500B",
    ]
    for alvo in alvos:
        if alvo == "15C2+15C4":
            abertos = {codigos[c].id for c in ("15C2", "15C4") if c in codigos}
        elif alvo in codigos:
            abertos = {codigos[alvo].id}
        else:
            continue
        depois = _alcancaveis([fonte.id], adj, abertos)
        perderam = sorted(
            (por_id[i] for i in base - depois),
            key=lambda n: (n.position.y, n.position.x),
        )
        nomes = ", ".join(
            (n.data.codigo or n.data.tipo) for n in perderam
        ) or "nenhum"
        print(f"  abrir {alvo:<10} -> perdem energizacao: {len(perderam)} [{nomes}]")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrige a topologia SAGE do unifilar da SE GOR."
    )
    parser.add_argument("--subestacao", default=SUBESTACAO_PADRAO)
    parser.add_argument("--id-subestacao", type=int)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra as alteracoes e a simulacao sem gravar",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.id_subestacao:
            linha = db.execute(
                text("SELECT id_subestacao, nome FROM subestacao WHERE id_subestacao = :i"),
                {"i": args.id_subestacao},
            ).first()
        else:
            linha = db.execute(
                text(
                    "SELECT id_subestacao, nome FROM subestacao "
                    "WHERE UPPER(TRIM(nome)) = UPPER(TRIM(:n))"
                ),
                {"n": args.subestacao},
            ).first()
        if not linha:
            raise SystemExit("Subestacao nao encontrada.")

        id_subestacao = int(linha.id_subestacao)
        diagrama = service.carregar_diagrama(db, id_subestacao)
        print(
            f"{linha.nome} (id {id_subestacao}): "
            f"{len(diagrama.nodes)} componentes, {len(diagrama.edges)} ligacoes"
        )

        print("\n--- antes ---")
        _simular(diagrama.nodes, diagrama.edges)

        avisos = _aplicar(diagrama.nodes, diagrama.edges)
        for aviso in avisos:
            print(f"AVISO: {aviso}")
        if avisos:
            return 1

        print("\n--- depois ---")
        _simular(diagrama.nodes, diagrama.edges)

        if args.dry_run:
            print("\nDRY-RUN: nada foi gravado.")
            return 0

        payload = schemas.DiagramaEntrada(
            nodes=[
                schemas.NoEntrada(
                    id=n.id,
                    type="noUnifilar",
                    position=n.position,
                    data=n.data,
                )
                for n in diagrama.nodes
            ],
            edges=[
                schemas.LigacaoEntrada(
                    id=e.id,
                    type=e.type or "smoothstep",
                    source=e.source,
                    sourceHandle=e.sourceHandle,
                    target=e.target,
                    targetHandle=e.targetHandle,
                )
                for e in diagrama.edges
            ],
        )
        salvo = service.salvar_diagrama(db, id_subestacao, payload, None)
        print(
            f"\nDiagrama salvo: {len(salvo.nodes)} componentes, "
            f"{len(salvo.edges)} ligacoes."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
