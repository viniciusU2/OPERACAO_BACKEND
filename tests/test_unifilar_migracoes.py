"""Garante que as migrações versionadas do modulo Unifilar existam e sejam idempotentes."""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_MIGRACOES = RAIZ / "migrations"
PADRAO = "*unifilar*.sql"


def _arquivos(apenas_up: bool = True) -> list[Path]:
    arquivos = sorted(PASTA_MIGRACOES.glob(PADRAO))
    if apenas_up:
        return [arq for arq in arquivos if not arq.name.endswith("_down.sql")]
    return arquivos


class MigracoesUnifilarTests(unittest.TestCase):
    def test_ha_migracoes_versionadas(self):
        self.assertTrue(_arquivos(), "Nenhuma migracao do modulo encontrada")

    def test_cada_migracao_tem_versao_down(self):
        for arquivo in _arquivos():
            down = arquivo.with_name(arquivo.stem + "_down.sql")
            self.assertTrue(down.exists(), f"Migracao {arquivo.name} sem arquivo _down")

    def test_migracoes_up_sao_idempotentes(self):
        for arquivo in _arquivos():
            sql = arquivo.read_text(encoding="utf-8")
            sem_if_not_exists = re.findall(r"CREATE TABLE(?! IF NOT EXISTS)", sql)
            self.assertFalse(
                sem_if_not_exists,
                f"{arquivo.name} usa CREATE TABLE sem IF NOT EXISTS",
            )

    def test_tabelas_obrigatorias_existem(self):
        sql = "\n".join(arq.read_text(encoding="utf-8") for arq in _arquivos())
        for tabela in (
            "unifilar_tipo_componente",
            "unifilar_diagrama",
            "unifilar_componente",
            "unifilar_conexao",
            "unifilar_terminal",
        ):
            self.assertRegex(
                sql,
                rf"CREATE TABLE(?: IF NOT EXISTS)?\s+{re.escape(tabela)}\b",
                f"Tabela '{tabela}' sem migracao versionada",
            )

    def test_migracoes_sao_ascii(self):
        for arquivo in _arquivos():
            arquivo.read_text(encoding="ascii")


class InstrucoesSqlTests(unittest.TestCase):
    def test_dividir_instrucoes_ignora_comentarios(self):
        from UNIFILAR import migracoes

        sql = "-- comentario\nCREATE TABLE a (id INT);\n-- outro\nCREATE TABLE b (id INT);\n"
        instrucoes = migracoes._instrucoes(sql)
        self.assertEqual(len(instrucoes), 2)
        self.assertTrue(instrucoes[0].startswith("CREATE TABLE a"))
        self.assertTrue(instrucoes[1].startswith("CREATE TABLE b"))

    def test_dividir_instrucoes_descarta_vazios(self):
        from UNIFILAR import migracoes

        self.assertEqual(migracoes._instrucoes(";;\n-- nada\n;"), [])


if __name__ == "__main__":
    unittest.main()
