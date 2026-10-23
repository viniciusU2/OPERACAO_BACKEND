"""Testes de integração da seed de problemas típicos contra o MariaDB.

Dependem de um banco real e, por isso, só executam quando habilitados
explicitamente:

    $env:PROBLEMAS_TIPOS_TESTE_DB=1   # PowerShell
    PROBLEMAS_TIPICOS_TESTE_DB=1      # bash
    python -m unittest tests.test_problemas_tipicos_seed -v

Os testes reexecutam a própria seed (operação documentada e idempotente) e
verificam integridade referencial. Nenhum dado é apagado.
"""

import os
import unittest

from sqlalchemy import text

HABILITADO = os.getenv("PROBLEMAS_TIPICOS_TESTE_DB") == "1"
MOTIVO = "Defina PROBLEMAS_TIPOS_TESTE_DB=1 para executar contra o banco configurado."

TABELAS_FILHAS = (
    "sintoma_problema",
    "causa_problema",
    "metodo_deteccao_problema",
    "alarme_problema",
    "palavra_chave_problema",
    "instrumento_problema",
    "acao_recomendada",
)


@unittest.skipUnless(HABILITADO, MOTIVO)
class SeedProblemasTipicosIntegracaoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import engine  # noqa: PLC0415
        from scripts import seed_problemas_tipicos  # noqa: PLC0415

        cls.engine = engine
        cls.seed = seed_problemas_tipicos
        # Aplicação inicial: cria o que faltar, sem apagar nada.
        cls.resumo_inicial = seed_problemas_tipicos.executar()

    def _contar(self, sql, **params):
        with self.engine.connect() as conexao:
            return conexao.execute(text(sql), params).scalar()

    def test_seed_e_idempotente(self):
        primeiro = self.seed.executar(migrar=False)
        segundo = self.seed.executar(migrar=False)
        self.assertEqual(primeiro["erros"], [])
        self.assertEqual(segundo["erros"], [])
        self.assertEqual(segundo["inseridos"], 0, "Reexecução não pode inserir novamente")
        self.assertEqual(segundo["atualizados"], 0, "Reexecução não pode atualizar sem mudança de conteúdo")
        self.assertEqual(segundo["inalterados"], len(self.seed.CATALOGO))
        self.assertEqual(segundo["ignorados_sem_tipo"], 0)

    def test_todos_os_itens_do_catalogo_estao_no_banco(self):
        total = self._contar(
            "SELECT COUNT(*) FROM problema_tipico WHERE codigo LIKE 'BDC-%'"
        )
        self.assertEqual(total, len(self.seed.CATALOGO))
        self.assertEqual(self.seed.executar(migrar=False)["ignorados_sem_tipo"], 0)

    def test_integridade_referencial(self):
        for tabela in TABELAS_FILHAS:
            orfaos = self._contar(
                f"SELECT COUNT(*) FROM {tabela} x "
                "LEFT JOIN problema_tipico p ON p.id_problema = x.id_problema "
                "WHERE p.id_problema IS NULL"
            )
            self.assertEqual(orfaos, 0, f"{tabela} possui registros órfãos")

    def test_todos_os_problemas_tem_sintoma_causa_e_acao(self):
        sem_filhos = self._contar(
            "SELECT COUNT(*) FROM problema_tipico p "
            "WHERE p.codigo LIKE 'BDC-%' AND ("
            "  NOT EXISTS (SELECT 1 FROM sintoma_problema s WHERE s.id_problema = p.id_problema) OR "
            "  NOT EXISTS (SELECT 1 FROM causa_problema c WHERE c.id_problema = p.id_problema) OR "
            "  NOT EXISTS (SELECT 1 FROM acao_recomendada a WHERE a.id_problema = p.id_problema))"
        )
        self.assertEqual(sem_filhos, 0)

    def test_registros_da_seed_sao_referencia_tecnica(self):
        inconsistentes = self._contar(
            "SELECT COUNT(*) FROM problema_tipico "
            "WHERE codigo LIKE 'BDC-%' AND origem_registro <> 'REFERENCIA_TECNICA'"
        )
        self.assertEqual(inconsistentes, 0)

    def test_ss_problema_preserva_fk_restrict(self):
        """A FK de ss_problema não pode usar CASCADE: apagar um problema usado em SS deve falhar."""
        with self.engine.connect() as conexao:
            regra = conexao.execute(
                text(
                    "SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'ss_problema' "
                    "AND REFERENCED_TABLE_NAME = 'problema_tipico'"
                )
            ).scalar()
        self.assertEqual(regra, "RESTRICT")


if __name__ == "__main__":
    unittest.main()
