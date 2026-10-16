import unittest

from pydantic import ValidationError

from engenharia_protecao import models, schemas
from engenharia_protecao import service_alteracoes


class EngenhariaProtecaoFase3SchemaTests(unittest.TestCase):
    def test_solicitacao_usa_valores_padrao(self):
        dados = schemas.SolicitacaoAlteracaoCreate(id_ied=1, titulo="Ajustar pickup")
        self.assertEqual(dados.tipo, "AJUSTE")
        self.assertEqual(dados.prioridade, "MEDIA")

    def test_tipo_de_alteracao_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.SolicitacaoAlteracaoCreate(id_ied=1, titulo="Ajustar", tipo="MAGIA")

    def test_prioridade_invalida_e_rejeitada(self):
        with self.assertRaises(ValidationError):
            schemas.SolicitacaoAlteracaoCreate(id_ied=1, titulo="Ajustar", prioridade="URGENTE")

    def test_update_exige_versao_positiva(self):
        with self.assertRaises(ValidationError):
            schemas.SolicitacaoAlteracaoUpdate(versao=0, titulo="x")

    def test_validacao_exige_aprovado(self):
        with self.assertRaises(ValidationError):
            schemas.ValidacaoAlteracao()

    def test_importacao_de_itens_exige_grupos(self):
        with self.assertRaises(ValidationError):
            schemas.ImportarItensAlteracao()


class SituacaoItemTests(unittest.TestCase):
    def test_situacoes(self):
        self.assertEqual(service_alteracoes._situacao(None, "6.0"), "ADICIONADO")
        self.assertEqual(service_alteracoes._situacao("5.0", None), "REMOVIDO")
        self.assertEqual(service_alteracoes._situacao("5.0", "5.0"), "IGUAL")
        self.assertEqual(service_alteracoes._situacao("5.0", "6.0"), "ALTERADO")
        self.assertEqual(service_alteracoes._situacao(" 5.0 ", "5.0"), "IGUAL")


class EngenhariaProtecaoFase3ModelTests(unittest.TestCase):
    def test_tabelas_da_fase_tres_estao_no_metadata(self):
        esperadas = {"solicitacao_alteracao", "alteracao_item", "alteracao_historico"}
        self.assertTrue(esperadas.issubset(set(models.Base.metadata.tables)))

    def test_vinculos_da_fase_tres(self):
        def destinos(tabela):
            return {chave.target_fullname for coluna in tabela.columns for chave in coluna.foreign_keys}

        self.assertIn("ied.id_ied", destinos(models.SolicitacaoAlteracao.__table__))
        self.assertIn("ied_configuracao.id_ied_configuracao", destinos(models.SolicitacaoAlteracao.__table__))
        self.assertIn("ied_grupo_ajuste.id_ied_grupo_ajuste", destinos(models.SolicitacaoAlteracao.__table__))
        self.assertIn("ordem_servico.id_os", destinos(models.SolicitacaoAlteracao.__table__))
        self.assertIn("solicitacao_alteracao.id_solicitacao_alteracao", destinos(models.AlteracaoItem.__table__))
        self.assertIn("parametro_definicao.id_parametro_definicao", destinos(models.AlteracaoItem.__table__))
        self.assertIn("solicitacao_alteracao.id_solicitacao_alteracao", destinos(models.AlteracaoHistorico.__table__))


if __name__ == "__main__":
    unittest.main()
