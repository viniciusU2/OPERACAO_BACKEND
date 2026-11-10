"""Exporta os diagramas unifilares salvos para um arquivo de seed portatil.

O arquivo nao guarda ids de ativo (que mudam entre bancos). Cada componente
leva o codigo e a fase do ativo associado, e o seed na VPS resolve o id
correspondente no cadastro local.

Uso:
    python scripts/exportar_unifilar_seed.py [arquivo_saida]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bootstrap import RAIZ  # noqa: E402,F401

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402
from UNIFILAR import service  # noqa: E402

SAIDA_PADRAO = RAIZ / "scripts" / "seeds" / "unifilar_seed.json"


def exportar(saida: Path) -> None:
    db = SessionLocal()
    try:
        diagramas = []
        for resumo in service.listar_diagramas(db):
            diagrama = service.carregar_diagrama(db, resumo.id_subestacao)
            ativos = {
                int(linha.id_ativo): {
                    "codigo": linha.codigo_ativo,
                    "fase": linha.fase,
                }
                for linha in db.execute(
                    text(
                        "SELECT id_ativo, codigo_ativo, fase FROM ativo "
                        "WHERE id_subestacao = :s"
                    ),
                    {"s": resumo.id_subestacao},
                )
            }

            nodes = []
            associacoes = 0
            for no in diagrama.nodes:
                dados = no.data.model_dump()
                ativo = ativos.get(int(no.data.id_ativo)) if no.data.id_ativo else None
                dados.pop("id_ativo", None)
                dados["ativo_codigo"] = ativo["codigo"] if ativo else None
                dados["ativo_fase"] = ativo["fase"] if ativo else None
                if ativo:
                    associacoes += 1
                nodes.append(
                    {
                        "id": no.id,
                        "type": "noUnifilar",
                        "position": {"x": no.position.x, "y": no.position.y},
                        "data": dados,
                    }
                )

            edges = [
                {
                    "id": lig.id,
                    "type": lig.type or "smoothstep",
                    "source": lig.source,
                    "sourceHandle": lig.sourceHandle,
                    "target": lig.target,
                    "targetHandle": lig.targetHandle,
                }
                for lig in diagrama.edges
            ]

            diagramas.append(
                {
                    "subestacao": resumo.nome,
                    "tipo_instalacao": resumo.tipo_instalacao,
                    "atualizado_em": (
                        diagrama.atualizado_em.isoformat()
                        if diagrama.atualizado_em
                        else None
                    ),
                    "nodes": nodes,
                    "edges": edges,
                }
            )
            print(
                f"{resumo.nome}: {len(nodes)} componentes, {len(edges)} ligacoes, "
                f"{associacoes} associacoes de ativo"
            )

        payload = {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "diagramas": diagramas,
        }
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Arquivo gerado: {saida}")
    finally:
        db.close()


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA_PADRAO
    exportar(destino)
