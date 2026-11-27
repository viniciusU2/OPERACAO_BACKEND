"""Replica os ativos de supervisório do "Módulo Geral" e sincroniza os grupos.

Os ativos abaixo foram cadastrados direto no banco da VPS (INSERT manual), o
que deixa ``ativo.id_grupo_ativo`` nulo. Sem grupo, o seletor hierárquico de
OS/SS/SI não os exibe depois de escolher a subestação e a função de
transmissão.

O script faz, de forma idempotente:

1. Insere (ou atualiza) os ativos 3208..3231.
2. Chama ``sincronizar_grupos_ativos``, que cria os registros de
   ``grupo_ativo`` e vincula ``ativo.id_grupo_ativo``.

Uso:

    python scripts/replicar_ativos_modulo_geral.py --dry-run
    python scripts/replicar_ativos_modulo_geral.py
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bootstrap import RAIZ  # noqa: E402,F401

from sqlalchemy import text  # noqa: E402

from ATIVO.grupos_ativos import sincronizar_grupos_ativos  # noqa: E402
from database import SessionLocal  # noqa: E402
from models.Ativo import Ativo, GrupoAtivo  # noqa: E402

TIPO_SUPERVISORIO = 32

# (id_ativo, id_subestacao, id_funcao_operacao, codigo, fabricante, modelo, fase)
ATIVOS = [
    # SE JAB (3) - MG-JAB (29)
    (3223, 3, 29, "SERV1", "SDC", None, "SAGE 1"),
    (3224, 3, 29, "SERV2", "SDC", None, "SAGE 2"),
    (3225, 3, 29, "SERV3", "SDC", None, "CA"),
    (3226, 3, 29, "MONITOR 1", "LG", "24MP400-BB.AWZJMVZ", "SAGE 1"),
    (3227, 3, 29, "MONITOR 2", "LG", "24MP400-BB.AWZJMVZ", "SAGE 2"),
    (3228, 3, 29, "MONITOR 3", "LG", "24MP400-BB.AWZJMVZ", "CA"),
    (3229, 3, 29, "THIN CLIENT 1", None, "HBJC313U691SKD", "SAGE 1"),
    (3230, 3, 29, "THIN CLIENT 2", None, "HBJC313U691SKD", "SAGE 2"),
    (3231, 3, 29, "THIN CLIENT 3", None, "HBJC313U691-SKD", "CA"),
    # SE BJD (1) - MG-BJD (12)
    (3208, 1, 12, "SERV1", "SDC", None, "SAGE 1"),
    (3209, 1, 12, "SERV2", "SDC", None, "SAGE 2"),
    (3210, 1, 12, "SERV3", "SDC", None, "CA"),
    (3211, 1, 12, "MONITOR 1", "LG", "24MP400-BB.AWZJMVZ", "SAGE 1"),
    (3212, 1, 12, "MONITOR 2", "LG", "24MP400-BB.AWZJMVZ", "SAGE 2"),
    (3213, 1, 12, "MONITOR 3", "LG", "24MP400-BB.AWZJMVZ", "CA"),
    (3214, 1, 12, "THIN CLIENT 1", None, "HBJC313U691SKD", "SAGE 1"),
    (3215, 1, 12, "THIN CLIENT 2", None, "HBJC313U691SKD", "SAGE 2"),
    (3216, 1, 12, "THIN CLIENT 3", None, "HBJC313U691-SKD", "CA"),
]

STATUS = "Em Operação"
BAY = "SACA"
TENSAO = Decimal("0.12")


def _resumo_grupos(db, id_funcao_operacao: int) -> list[tuple[int, str, str | None, int]]:
    return [
        (g.id_grupo_ativo, g.codigo_ativo, g.bay, g.id_tipo_ativo)
        for g in db.query(GrupoAtivo)
        .filter(GrupoAtivo.id_funcao_operacao == id_funcao_operacao)
        .order_by(GrupoAtivo.codigo_ativo)
        .all()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito sem gravar no banco.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existentes = {
            row[0]
            for row in db.query(Ativo.id_ativo)
            .filter(Ativo.id_ativo.in_([item[0] for item in ATIVOS]))
            .all()
        }
        faltantes = [item for item in ATIVOS if item[0] not in existentes]

        print(f"Ativos no lote: {len(ATIVOS)} | já existentes: {len(existentes)} | novos: {len(faltantes)}")
        for item in faltantes:
            print(f"  + {item[0]} {item[3]} (SE {item[1]} / FO {item[2]})")

        if args.dry_run:
            print("\n[dry-run] Nada foi gravado.")
            return 0

        for id_ativo, id_subestacao, id_fo, codigo, fabricante, modelo, fase in ATIVOS:
            db.execute(
                text(
                    """
                    INSERT INTO ativo (
                        id_ativo, id_subestacao, id_tipo_ativo, codigo_ativo,
                        fabricante, modelo, tensao_nominal_kv, status, bay, fase,
                        id_funcao_operacao
                    ) VALUES (
                        :id_ativo, :id_subestacao, :id_tipo_ativo, :codigo_ativo,
                        :fabricante, :modelo, :tensao, :status, :bay, :fase,
                        :id_funcao_operacao
                    )
                    ON DUPLICATE KEY UPDATE
                        id_subestacao = VALUES(id_subestacao),
                        id_tipo_ativo = VALUES(id_tipo_ativo),
                        codigo_ativo = VALUES(codigo_ativo),
                        fabricante = VALUES(fabricante),
                        modelo = VALUES(modelo),
                        tensao_nominal_kv = VALUES(tensao_nominal_kv),
                        status = VALUES(status),
                        bay = VALUES(bay),
                        fase = VALUES(fase),
                        id_funcao_operacao = VALUES(id_funcao_operacao)
                    """
                ),
                {
                    "id_ativo": id_ativo,
                    "id_subestacao": id_subestacao,
                    "id_tipo_ativo": TIPO_SUPERVISORIO,
                    "codigo_ativo": codigo,
                    "fabricante": fabricante,
                    "modelo": modelo,
                    "tensao": TENSAO,
                    "status": STATUS,
                    "bay": BAY,
                    "fase": fase,
                    "id_funcao_operacao": id_fo,
                },
            )

        db.flush()
        sincronizar_grupos_ativos(db)
        db.commit()

        print("\nGrupos sincronizados:")
        for id_fo in (12, 29):
            grupos = _resumo_grupos(db, id_fo)
            print(f"  FO {id_fo}: {len(grupos)} grupos")
            for id_grupo, codigo, bay, id_tipo in grupos:
                if codigo.upper() in {
                    item[3].upper() for item in ATIVOS if item[2] == id_fo
                }:
                    print(f"    - {id_grupo} {codigo} ({bay}) tipo {id_tipo}")

        vinculados = (
            db.query(Ativo)
            .filter(Ativo.id_ativo.in_([item[0] for item in ATIVOS]))
            .order_by(Ativo.id_ativo)
            .all()
        )
        sem_grupo = [a.id_ativo for a in vinculados if not a.id_grupo_ativo]
        print(f"\nAtivos vinculados a grupo: {len(vinculados) - len(sem_grupo)}/{len(vinculados)}")
        if sem_grupo:
            print(f"  ATENÇÃO: sem grupo -> {sem_grupo}")
            return 1
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
