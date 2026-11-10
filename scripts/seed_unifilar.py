"""Carrega o seed portatil dos diagramas unifilares no banco atual.

Uso na VPS (depois de subir o codigo, com o .env configurado):

    python scripts/seed_unifilar.py --dry-run
    python scripts/seed_unifilar.py --substituir

O arquivo guarda a instalacao pelo nome e o ativo pelo codigo/fase; o seed
resolve o id correto no cadastro da VPS. Se um ativo nao existir, o vinculo
fica nulo e o codigo e listado como aviso (o desenho continua sendo criado).

As migracoes do Unifilar sao aplicadas/registradas na tabela
``unifilar_migracao`` antes da carga.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bootstrap import RAIZ  # noqa: E402,F401

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402
from UNIFILAR import migracoes, schemas, service  # noqa: E402

ARQUIVO_PADRAO = RAIZ / "scripts" / "seeds" / "unifilar_seed.json"


def mapa_ativos(db, id_subestacao: int) -> dict[str, dict[str, int]]:
    mapa: dict[str, dict[str, int]] = {}
    for linha in db.execute(
        text(
            "SELECT id_ativo, codigo_ativo, fase FROM ativo "
            "WHERE id_subestacao = :s"
        ),
        {"s": id_subestacao},
    ):
        codigo = (linha.codigo_ativo or "").strip().upper()
        if not codigo:
            continue
        fase = (linha.fase or "").strip().upper()
        mapa.setdefault(codigo, {})[fase] = int(linha.id_ativo)
    return mapa


def escolher_ativo(
    mapa: dict[str, dict[str, int]],
    codigo: str | None,
    fase: str | None,
) -> int | None:
    if not codigo:
        return None
    fases = mapa.get(codigo.strip().upper())
    if not fases:
        return None
    if fase:
        achado = fases.get(fase.strip().upper())
        if achado:
            return achado
    if "AZ" in fases:
        return fases["AZ"]
    return next(iter(fases.values()))


def montar_payload(
    diagrama: dict,
    ativos: dict[str, dict[str, int]],
) -> tuple[schemas.DiagramaEntrada, list[str]]:
    faltantes: list[str] = []
    nodes = []
    for no in diagrama.get("nodes") or []:
        dados = dict(no.get("data") or {})
        codigo = dados.pop("ativo_codigo", None)
        fase = dados.pop("ativo_fase", None)
        if codigo:
            id_ativo = escolher_ativo(ativos, codigo, fase)
            if id_ativo is None:
                faltantes.append(f"{codigo} ({fase or 'sem fase'})")
        else:
            id_ativo = None
        dados["id_ativo"] = id_ativo
        nodes.append(
            {
                "id": no["id"],
                "type": "noUnifilar",
                "position": no.get("position") or {"x": 0, "y": 0},
                "data": dados,
            }
        )

    edges = []
    for lig in diagrama.get("edges") or []:
        edges.append(
            {
                "id": lig.get("id"),
                "type": lig.get("type") or "smoothstep",
                "source": lig["source"],
                "sourceHandle": lig.get("sourceHandle"),
                "target": lig["target"],
                "targetHandle": lig.get("targetHandle"),
            }
        )

    payload = schemas.DiagramaEntrada.model_validate({"nodes": nodes, "edges": edges})
    return payload, faltantes


def resolver_subestacao(
    db,
    nome: str,
    id_override: int | None,
) -> tuple[int, str]:
    if id_override:
        linha = db.execute(
            text("SELECT id_subestacao, nome FROM subestacao WHERE id_subestacao = :i"),
            {"i": id_override},
        ).first()
        if not linha:
            raise SystemExit(f"Subestacao id {id_override} nao encontrada.")
        return int(linha.id_subestacao), linha.nome

    linhas = db.execute(
        text(
            "SELECT id_subestacao, nome FROM subestacao "
            "WHERE UPPER(TRIM(nome)) = UPPER(TRIM(:n))"
        ),
        {"n": nome},
    ).all()
    if not linhas:
        raise SystemExit(f"Subestacao '{nome}' nao existe neste banco.")
    if len(linhas) > 1:
        ids = ", ".join(str(linha.id_subestacao) for linha in linhas)
        raise SystemExit(
            f"Mais de uma subestacao chamada '{nome}' (ids {ids}); use --id-subestacao."
        )
    return int(linhas[0].id_subestacao), linhas[0].nome


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carrega o seed portatil dos diagramas unifilares."
    )
    parser.add_argument(
        "--arquivo",
        default=str(ARQUIVO_PADRAO),
        help="Arquivo JSON gerado por scripts/exportar_unifilar_seed.py",
    )
    parser.add_argument(
        "--subestacao",
        help="Carrega apenas o diagrama desta instalacao (nome exato)",
    )
    parser.add_argument(
        "--id-subestacao",
        type=int,
        help="Forca o id da instalacao no banco de destino",
    )
    parser.add_argument(
        "--substituir",
        action="store_true",
        help="Sobrescreve um diagrama que ja exista",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida e mostra o resumo sem gravar",
    )
    args = parser.parse_args()

    arquivo = Path(args.arquivo)
    if not arquivo.is_file():
        raise SystemExit(f"Arquivo nao encontrado: {arquivo}")

    payload_json = json.loads(arquivo.read_text(encoding="utf-8"))
    diagramas = payload_json.get("diagramas") or []
    if not diagramas:
        raise SystemExit("O arquivo nao contem diagramas.")

    if args.id_subestacao and len(diagramas) > 1:
        raise SystemExit("Use --id-subestacao apenas com um diagrama no arquivo.")

    db = SessionLocal()
    falhas = 0
    try:
        aplicadas = migracoes.aplicar_migracoes(db)
        print(
            "Migracoes aplicadas agora:",
            ", ".join(aplicadas) if aplicadas else "nenhuma (ja registradas)",
        )
        registradas = [
            linha[0]
            for linha in db.execute(
                text("SELECT nome FROM unifilar_migracao ORDER BY nome")
            )
        ]
        print("Migracoes registradas:", ", ".join(registradas) or "nenhuma")

        for diagrama in diagramas:
            nome_arquivo = str(diagrama.get("subestacao") or "").strip()
            if args.subestacao and nome_arquivo.casefold() != args.subestacao.strip().casefold():
                continue
            try:
                id_subestacao, nome = resolver_subestacao(
                    db, nome_arquivo, args.id_subestacao
                )
            except SystemExit as exc:
                print(f"AVISO: {exc}")
                falhas += 1
                continue

            atual = service.carregar_diagrama(db, id_subestacao)
            if atual.nodes and not args.substituir:
                print(
                    f"{nome}: ja possui {len(atual.nodes)} componentes. "
                    "Use --substituir para sobrescrever."
                )
                continue

            ativos = mapa_ativos(db, id_subestacao)
            payload, faltantes = montar_payload(diagrama, ativos)

            if faltantes:
                print(
                    f"{nome}: {len(faltantes)} ativo(s) sem correspondencia "
                    f"(vinculo sera nulo): {', '.join(sorted(set(faltantes)))}"
                )

            if args.dry_run:
                print(
                    f"{nome} (id {id_subestacao}): DRY-RUN ok — "
                    f"{len(payload.nodes)} componentes, {len(payload.edges)} ligacoes"
                )
                continue

            salvo = service.salvar_diagrama(db, id_subestacao, payload, None)
            print(
                f"{nome} (id {id_subestacao}): salvo — "
                f"{len(salvo.nodes)} componentes, {len(salvo.edges)} ligacoes"
            )
    except HTTPException as exc:
        db.rollback()
        print(f"ERRO de validacao: {exc.detail}")
        falhas += 1
    finally:
        db.close()

    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
