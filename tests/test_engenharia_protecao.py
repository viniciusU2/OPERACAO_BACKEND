import unittest
from datetime import date

from pydantic import ValidationError

from engenharia_protecao import models, schemas, service


class EngenhariaProtecaoSchemaTests(unittest.TestCase):
    def test_status_do_ied_e_normalizado(self):
        dados = schemas.IEDCreate(
            tag_operacional="IED-01",
            id_ativo=1,
            id_modelo_ied=1,
            id_subestacao=1,
            painel_instalacao="Painel P1",
            data_instalacao=date(2026, 10, 15),
            status_operacional="em_operacao",
        )
        self.assertEqual(dados.status_operacional, "EM_OPERACAO")

    def test_status_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.IEDCreate(
                tag_operacional="IED-01",
                id_ativo=1,
                id_modelo_ied=1,
                id_subestacao=1,
                painel_instalacao="Painel P1",
                data_instalacao=date(2026, 10, 15),
                status_operacional="DESCONHECIDO",
            )

    def test_texto_vazio_vira_nulo(self):
        self.assertIsNone(service._texto("   "))
        self.assertEqual(service._texto(" 7SL87 "), "7SL87")


class EngenhariaProtecaoModelTests(unittest.TestCase):
    def test_tabelas_da_fase_um_estao_no_metadata(self):
        esperadas = {
            "modelo_ied",
            "ied",
            "ied_instalacao",
            "ied_modulo",
            "ied_firmware_historico",
            "ied_equipamento",
        }
        self.assertTrue(esperadas.issubset(set(models.Base.metadata.tables)))

    def test_ied_referencia_entidades_existentes(self):
        tabela = models.IED.__table__
        destinos = {chave.target_fullname for coluna in tabela.columns for chave in coluna.foreign_keys}
        self.assertIn("subestacao.id_subestacao", destinos)
        self.assertIn("funcao_operacao.id_funcao_operacao", destinos)
        self.assertIn("modelo_ied.id_modelo_ied", destinos)
        self.assertIn("ativo.id_ativo", destinos)


if __name__ == "__main__":
    unittest.main()
