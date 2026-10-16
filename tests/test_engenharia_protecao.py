import inspect
import unittest
from datetime import date
from typing import get_args

from pydantic import ValidationError
from starlette.requests import Request

from engenharia_protecao import audit, models, schemas, service, service_alteracoes, service_config


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


class EngenhariaProtecaoHardeningTests(unittest.TestCase):
    """Fase 6: segregação de funções, reversão, auditoria transversal e integridade."""

    def test_novos_estados_e_acoes_de_alteracao(self):
        estados = get_args(schemas.StatusAlteracao)
        for esperado in ("EM_ANALISE", "EM_VALIDACAO", "CONCLUIDA", "REVERTIDA"):
            self.assertIn(esperado, estados)
        acoes = get_args(schemas.AcaoAlteracao)
        for esperada in ("ANALISE", "INICIO_VALIDACAO", "CONCLUSAO", "REVERSAO"):
            self.assertIn(esperada, acoes)

    def test_reversao_exige_motivo_e_configuracao(self):
        with self.assertRaises(ValidationError):
            schemas.ReversaoAlteracao(id_configuracao_rollback=0, motivo="motivo valido")
        with self.assertRaises(ValidationError):
            schemas.ReversaoAlteracao(id_configuracao_rollback=1, motivo="abc")
        dados = schemas.ReversaoAlteracao(id_configuracao_rollback=9, motivo="rollback de ajuste")
        self.assertEqual(dados.id_configuracao_rollback, 9)

    def test_evidencia_de_implantacao_limita_tamanho(self):
        schemas.ImplantacaoAlteracao(evidencia_implantacao="x" * 4000)
        with self.assertRaises(ValidationError):
            schemas.ImplantacaoAlteracao(evidencia_implantacao="x" * 4001)

    def test_solicitacao_out_expoe_implantador_e_reversao(self):
        campos = set(schemas.SolicitacaoAlteracaoOut.model_fields)
        for esperado in (
            "id_usuario_implantador",
            "nome_implantador",
            "id_usuario_reversao",
            "nome_usuario_reversao",
            "id_configuracao_rollback",
            "data_reversao",
            "evidencia_implantacao",
        ):
            self.assertIn(esperado, campos)

    def test_colunas_novas_no_modelo_de_alteracao(self):
        colunas = set(models.SolicitacaoAlteracao.__table__.columns.keys())
        for esperada in (
            "id_usuario_implantador",
            "id_usuario_reversao",
            "id_configuracao_rollback",
            "data_reversao",
            "evidencia_implantacao",
        ):
            self.assertIn(esperada, colunas)

    def test_checks_de_status_e_acao_foram_ampliados(self):
        def sql_do_check(nome: str, tabela) -> str:
            for constraint in tabela.constraints:
                if getattr(constraint, "name", None) == nome:
                    return str(constraint.sqltext)
            self.fail(f"constraint {nome} ausente")

        status = sql_do_check("ck_solicitacao_alteracao_status", models.SolicitacaoAlteracao.__table__)
        for valor in ("EM_ANALISE", "EM_VALIDACAO", "CONCLUIDA", "REVERTIDA"):
            self.assertIn(valor, status)

        acao = sql_do_check("ck_alteracao_historico_acao", models.AlteracaoHistorico.__table__)
        for valor in ("ANALISE", "INICIO_VALIDACAO", "CONCLUSAO", "REVERSAO"):
            self.assertIn(valor, acao)

    def test_tabela_de_auditoria_esta_no_metadata(self):
        self.assertIn("engenharia_protecao_auditoria", models.Base.metadata.tables)
        colunas = set(models.EngenhariaProtecaoAuditoria.__table__.columns.keys())
        for esperada in ("acao", "metodo", "caminho", "recurso", "id_recurso", "status_http", "endereco_ip", "criado_em"):
            self.assertIn(esperada, colunas)

    def test_alteracao_em_analise_pode_ser_cancelada(self):
        self.assertIn("EM_ANALISE", service_alteracoes.STATUS_CANCELAVEIS)

    def test_transicoes_de_analise_validacao_e_reversao_existem(self):
        for nome in ("iniciar_analise", "iniciar_validacao", "reverter"):
            self.assertTrue(callable(getattr(service_alteracoes, nome)), f"{nome} ausente")

    def test_classificacao_da_auditoria(self):
        def requisicao(metodo: str, caminho: str) -> Request:
            return Request(
                {
                    "type": "http",
                    "method": metodo,
                    "path": caminho,
                    "query_string": b"",
                    "scheme": "http",
                    "server": ("testserver", 80),
                    "client": ("127.0.0.1", 1234),
                    "headers": [],
                }
            )

        self.assertEqual(
            audit._classificar(requisicao("POST", "/engenharia-protecao/ieds/8/arquivar")),
            ("ARQUIVAMENTO", "ieds", "8"),
        )
        self.assertEqual(
            audit._classificar(requisicao("POST", "/engenharia-protecao/ieds/8/reativar")),
            ("REATIVACAO", "ieds", "8"),
        )
        self.assertEqual(
            audit._classificar(requisicao("DELETE", "/engenharia-protecao/ieds/8")),
            ("REMOCAO", "ieds", "8"),
        )
        self.assertEqual(
            audit._classificar(requisicao("GET", "/engenharia-protecao/arquivos/4/download")),
            ("DOWNLOAD", "arquivos", "4"),
        )
        self.assertIsNone(audit._classificar(requisicao("GET", "/engenharia-protecao/dashboard")))
        self.assertTrue(callable(audit.listar_auditoria))

    def test_exclusao_definitiva_e_arquivamento_sao_operacoes_distintas(self):
        parametros_definitivo = list(inspect.signature(service.remover_ied).parameters)
        self.assertEqual(parametros_definitivo, ["db", "id_ied"])
        self.assertEqual(list(inspect.signature(service.arquivar_ied).parameters), ["db", "id_ied", "id_usuario"])
        self.assertEqual(list(inspect.signature(service.reativar_ied).parameters), ["db", "id_ied", "id_usuario"])

    def test_helper_de_integridade_de_arquivo_disponivel(self):
        self.assertTrue(callable(service_config._caminho_integro))


if __name__ == "__main__":
    unittest.main()
