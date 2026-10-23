"""Verificação, somente leitura, da base de conhecimento de problemas típicos.

Uso:
    python -m scripts.verificar_problemas_tipicos

Consulta o MariaDB configurado em ``DATABASE_URL`` e imprime:
- totais por categoria, criticidade, risco e status de validação;
- quantidade de itens nas listas estruturadas;
- integridade referencial (registros órfãos);
- tipos de ativo utilizados e o registro legado preservado.

Não altera nenhum dado.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from database import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

PREFIXO_SEED = "BDC-%"
TABELAS_FILHAS = (
    "sintoma_problema",
    "causa_problema",
    "metodo_deteccao_problema",
    "alarme_problema",
    "palavra_chave_problema",
    "instrumento_problema",
    "acao_recomendada",
)


def linhas(conexao, sql, **params):
    return conexao.execute(text(sql), params).fetchall()


def main() -> int:
    with engine.connect() as conexao:
        total = linhas(conexao, "SELECT COUNT(*) FROM problema_tipico WHERE codigo LIKE :p", p=PREFIXO_SEED)[0][0]
        print(f"Total de problemas da seed (codigo LIKE '{PREFIXO_SEED}'): {total}")
        if not total:
            print("Nenhum registro da seed encontrado. Execute scripts.seed_problemas_tipicos.")
            return 0

        print("\n== Por categoria ==")
        for categoria, quantidade in linhas(
            conexao,
            "SELECT categoria, COUNT(*) AS total FROM problema_tipico WHERE codigo LIKE :p "
            "GROUP BY categoria ORDER BY total DESC, categoria",
            p=PREFIXO_SEED,
        ):
            print(f"  {quantidade:3d}  {categoria}")

        for rotulo, coluna in (("criticidade", "criticidade_padrao"), ("risco operacional", "risco_operacional"),
                               ("status de validação", "status_validacao"), ("origem", "origem_registro")):
            dados = linhas(
                conexao,
                f"SELECT {coluna}, COUNT(*) FROM problema_tipico WHERE codigo LIKE :p GROUP BY {coluna} ORDER BY 1",
                p=PREFIXO_SEED,
            )
            print(f"\n== Por {rotulo} ==")
            for valor, quantidade in dados:
                print(f"  {quantidade:3d}  {valor}")

        print("\n== Listas estruturadas ==")
        for tabela in TABELAS_FILHAS:
            quantidade = linhas(
                conexao,
                f"SELECT COUNT(*) FROM {tabela} t JOIN problema_tipico p ON p.id_problema = t.id_problema "
                "WHERE p.codigo LIKE :p",
                p=PREFIXO_SEED,
            )[0][0]
            print(f"  {quantidade:4d}  {tabela}")

        print("\n== Ações por tipo ==")
        for tipo_acao, quantidade in linhas(
            conexao,
            "SELECT a.tipo_acao, COUNT(*) FROM acao_recomendada a "
            "JOIN problema_tipico p ON p.id_problema = a.id_problema WHERE p.codigo LIKE :p "
            "GROUP BY a.tipo_acao ORDER BY 2 DESC",
            p=PREFIXO_SEED,
        ):
            print(f"  {quantidade:4d}  {tipo_acao}")

        print("\n== Integridade referencial (esperado: todos 0) ==")
        problemas = 0
        for tabela in TABELAS_FILHAS:
            orfaos = linhas(
                conexao,
                f"SELECT COUNT(*) FROM {tabela} x LEFT JOIN problema_tipico p ON p.id_problema = x.id_problema "
                "WHERE p.id_problema IS NULL",
            )[0][0]
            problemas += orfaos
            marcador = "OK" if orfaos == 0 else "FALHA"
            print(f"  {marcador:5s} {tabela}: {orfaos}")

        sem_sintoma = linhas(
            conexao,
            "SELECT COUNT(*) FROM problema_tipico p WHERE p.codigo LIKE :p AND NOT EXISTS "
            "(SELECT 1 FROM sintoma_problema s WHERE s.id_problema = p.id_problema)",
            p=PREFIXO_SEED,
        )[0][0]
        problemas += sem_sintoma
        print(f"  {'OK' if sem_sintoma == 0 else 'FALHA':5s} problemas sem sintoma: {sem_sintoma}")

        print("\n== Tipos de ativo utilizados pela seed ==")
        for nome, quantidade in linhas(
            conexao,
            "SELECT ta.nome, COUNT(*) FROM problema_tipico p JOIN tipo_ativo ta ON ta.id_tipo_ativo = p.id_tipo_ativo "
            "WHERE p.codigo LIKE :p GROUP BY ta.nome ORDER BY ta.nome",
            p=PREFIXO_SEED,
        ):
            print(f"  {quantidade:3d}  {nome}")

        print("\n== Registro legado anterior à base de conhecimento ==")
        for id_problema, codigo, titulo, status in linhas(
            conexao,
            "SELECT id_problema, codigo, titulo, status_validacao FROM problema_tipico WHERE codigo LIKE 'LEGADO-%'",
        ):
            print(f"  #{id_problema} {codigo} '{titulo}' [{status}]")

    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
