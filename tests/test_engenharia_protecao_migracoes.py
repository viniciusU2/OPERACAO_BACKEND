"""Garante que as migrações versionadas do módulo continuem sendo a fonte do esquema.

Estes testes impedem *drift*: toda tabela declarada em
``engenharia_protecao/models.py`` precisa existir em alguma migração versionada,
e as migrações precisam ser idempotentes.
"""

import re
import unittest
from pathlib import Path

from engenharia_protecao import migracoes

RAIZ = Path(__file__).resolve().parent.parent
PASTA_MIGRACOES = RAIZ / "migrations"
MODELS_PY = RAIZ / "engenharia_protecao" / "models.py"
PADRAO = "*_engenharia_protecao_fase*.sql"


def _arquivos(apenas_up: bool = True) -> list[Path]:
    arquivos = sorted(PASTA_MIGRACOES.glob(PADRAO))
    if apenas_up:
        return [arq for arq in arquivos if not arq.name.endswith("_down.sql")]
    return arquivos


class MigracoesEngenhariaTests(unittest.TestCase):
    def test_ha_migracoes_versionadas(self):
        self.assertTrue(_arquivos(), "Nenhuma migração do módulo encontrada")

    def test_toda_tabela_do_modulo_tem_migracao(self):
        fonte = MODELS_PY.read_text(encoding="utf-8")
        tabelas = set(re.findall(r'__tablename__\s*=\s*"([^"]+)"', fonte))
        self.assertTrue(tabelas)
        sql = "\n".join(arq.read_text(encoding="utf-8") for arq in _arquivos())
        for tabela in sorted(tabelas):
            self.assertRegex(
                sql,
                rf"CREATE TABLE(?: IF NOT EXISTS)?\s+{re.escape(tabela)}\b",
                f"Tabela '{tabela}' declarada nos models sem migração versionada",
            )

    def test_cada_migracao_tem_versao_down(self):
        for arquivo in _arquivos():
            down = arquivo.with_name(arquivo.stem + "_down.sql")
            self.assertTrue(down.exists(), f"Migração {arquivo.name} sem arquivo _down")

    def test_migracoes_up_sao_idempotentes(self):
        for arquivo in _arquivos():
            sql = arquivo.read_text(encoding="utf-8")
            sem_if_not_exists = re.findall(r"CREATE TABLE(?! IF NOT EXISTS)", sql)
            self.assertFalse(
                sem_if_not_exists,
                f"{arquivo.name} usa CREATE TABLE sem IF NOT EXISTS",
            )


class InstrucoesSqlTests(unittest.TestCase):
    def test_dividir_instrucoes_ignora_comentarios(self):
        sql = "-- comentario\nCREATE TABLE a (id INT);\n-- outro\nCREATE TABLE b (id INT);\n"
        instrucoes = migracoes._instrucoes(sql)
        self.assertEqual(len(instrucoes), 2)
        self.assertTrue(instrucoes[0].startswith("CREATE TABLE a"))
        self.assertTrue(instrucoes[1].startswith("CREATE TABLE b"))

    def test_dividir_instrucoes_descarta_vazios(self):
        self.assertEqual(migracoes._instrucoes(";;\n-- nada\n;"), [])


if __name__ == "__main__":
    unittest.main()
