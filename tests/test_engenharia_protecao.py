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

    def test_ied_possui_cascata_para_os_filhos(self):
        """A exclusão do IED depende do cascade do ORM/DB para não deixar órfãos."""
        relacoes_com_cascata = {
            "instalacoes",
            "modulos",
            "firmwares",
            "equipamentos",
            "funcoes",
            "grupos_ajuste",
            "configuracoes",
            "alteracoes",
            "interfaces_comunicacao",
            "goose_controles",
            "circuitos",
            "sinais",
            "ensaios",
            "ocorrencias",
            "oscilografias",
            "relatorios",
        }
        # `_props` é preenchido na construção do mapper e não dispara
        # `configure_mappers()` (que exigiria importar todos os modelos do ENGVI).
        props = models.IED.__mapper__._props
        for nome in relacoes_com_cascata:
            self.assertIn(nome, props, f"relacionamento {nome} ausente no IED")
            self.assertIn("delete", props[nome].cascade, f"{nome} sem cascade de exclusão")


class EngenhariaProtecaoRemocaoIEDTests(unittest.TestCase):
    def test_remocao_de_ied_esta_disponivel_no_service(self):
        self.assertTrue(callable(service.remover_ied))

    def test_schema_de_remocao_expoe_o_resultado(self):
        dados = schemas.IEDRemocaoOut(id_ied=8, tag_operacional="21C2-GOR", arquivos_removidos=3)
        self.assertEqual(dados.id_ied, 8)
        self.assertEqual(dados.tag_operacional, "21C2-GOR")
        self.assertEqual(dados.arquivos_removidos, 3)


if __name__ == "__main__":
    unittest.main()
