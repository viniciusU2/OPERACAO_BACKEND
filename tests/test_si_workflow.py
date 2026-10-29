"""Testes do rito de status das Solicitacoes de Intervencao (SI).

Cobrem apenas as regras puras de `SI.workflow` (sem banco): matriz de
permissoes, transicoes permitidas, bloqueios definitivos e rotulos.
"""

import unittest
from types import SimpleNamespace

from SI import workflow


def usuario(role):
    return SimpleNamespace(id=1, nome="Fulano", email="fulano@empresa.com", role=role)


def si(status=None, **extra):
    dados = {
        "status": status,
        "status_manutencao": extra.get("status_manutencao", "ABERTA"),
        "status_operacao": extra.get("status_operacao", "ABERTA"),
    }
    return SimpleNamespace(**dados)


MANUTENCAO = usuario("mantenedor")
OPERACAO = usuario("admin")
LEITOR = usuario("usuario")


class PerfilTests(unittest.TestCase):
    def test_mapeia_papeis(self):
        self.assertEqual(workflow.perfil(MANUTENCAO), workflow.PERFIL_MANUTENCAO)
        self.assertEqual(workflow.perfil(OPERACAO), workflow.PERFIL_OPERACAO)
        self.assertIsNone(workflow.perfil(LEITOR))

    def test_operador_tambem_e_centro_de_operacoes(self):
        operador = usuario("operador")
        self.assertEqual(workflow.perfil(operador), workflow.PERFIL_OPERACAO)
        self.assertEqual(
            workflow.acoes_disponiveis(si("ENVIADA"), operador),
            ["aprovar", "rejeitar", "cancelar"],
        )
        self.assertFalse(workflow.pode_visualizar(si("RASCUNHO"), operador))
        self.assertFalse(workflow.pode_editar(si("RASCUNHO"), operador))
        self.assertFalse(workflow.pode_criar(operador))
        self.assertFalse(workflow.pode_excluir(si("RASCUNHO"), operador))

    def test_tolera_maiusculas_e_espacos(self):
        self.assertEqual(
            workflow.perfil(SimpleNamespace(role="  Mantenedor ")),
            workflow.PERFIL_MANUTENCAO,
        )
        self.assertEqual(
            workflow.perfil(SimpleNamespace(role="ADMIN")),
            workflow.PERFIL_OPERACAO,
        )


class StatusAtualTests(unittest.TestCase):
    def test_usa_coluna_status(self):
        self.assertEqual(workflow.status_atual(si("APROVADA")), "APROVADA")

    def test_cai_para_status_legado_quando_status_vazio(self):
        registro = si(None, status_operacao="ENCERRADA")
        self.assertEqual(workflow.status_atual(registro), "ENCERRADA")

    def test_sem_status_nenhum_vira_rascunho(self):
        self.assertEqual(workflow.status_atual(si(None)), "RASCUNHO")


class EdicaoTests(unittest.TestCase):
    def test_manutencao_edita_rascunho_e_rejeitada(self):
        for status in ("RASCUNHO", "REJEITADA"):
            with self.subTest(status=status):
                self.assertTrue(workflow.pode_editar(si(status), MANUTENCAO))

    def test_manutencao_nao_edita_enviada_aprovada_cancelada(self):
        for status in ("ENVIADA", "APROVADA", "CANCELADA"):
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_editar(si(status), MANUTENCAO))

    def test_operacao_nunca_edita(self):
        for status in workflow.STATUS_VALIDOS:
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_editar(si(status), OPERACAO))

    def test_leitor_nunca_edita(self):
        for status in workflow.STATUS_VALIDOS:
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_editar(si(status), LEITOR))

    def test_aprovada_e_cancelada_nao_voltam(self):
        for status in ("APROVADA", "CANCELADA"):
            transicoes = workflow.TRANSICOES[status]
            with self.subTest(status=status):
                self.assertNotIn("RASCUNHO", transicoes)
                self.assertNotIn("ENVIADA", transicoes)
                self.assertNotIn("REJEITADA", transicoes)


class FluxoTests(unittest.TestCase):
    def test_rascunho_so_pode_enviar(self):
        self.assertEqual(workflow.acoes_disponiveis(si("RASCUNHO"), MANUTENCAO), ["enviar"])
        self.assertEqual(workflow.acoes_disponiveis(si("RASCUNHO"), OPERACAO), [])

    def test_enviada_da_as_tres_acoes_para_operacao(self):
        self.assertEqual(
            workflow.acoes_disponiveis(si("ENVIADA"), OPERACAO),
            ["aprovar", "rejeitar", "cancelar"],
        )
        self.assertEqual(workflow.acoes_disponiveis(si("ENVIADA"), MANUTENCAO), [])

    def test_rejeitada_volta_para_manutencao_reenviar(self):
        self.assertEqual(workflow.acoes_disponiveis(si("REJEITADA"), MANUTENCAO), ["enviar"])
        self.assertEqual(workflow.acoes_disponiveis(si("REJEITADA"), OPERACAO), [])

    def test_aprovada_so_pode_ser_cancelada_pela_operacao(self):
        self.assertEqual(
            workflow.acoes_disponiveis(si("APROVADA"), OPERACAO),
            ["concluir", "cancelar"],
        )
        self.assertEqual(workflow.acoes_disponiveis(si("APROVADA"), MANUTENCAO), ["concluir"])

    def test_concluir_e_possivel_aos_dois_perfis_na_aprovada(self):
        for usuario_ in (MANUTENCAO, OPERACAO):
            with self.subTest(role=usuario_.role):
                self.assertTrue(workflow.pode_executar(si("APROVADA"), usuario_, "concluir"))

    def test_concluir_nao_existe_fora_da_aprovada(self):
        for status in ("RASCUNHO", "ENVIADA", "REJEITADA", "CANCELADA", "PROGRAMADA", "CONCLUIDA"):
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_executar(si(status), MANUTENCAO, "concluir"))
                self.assertFalse(workflow.pode_executar(si(status), OPERACAO, "concluir"))

    def test_concluida_e_final(self):
        for papel in (MANUTENCAO, OPERACAO, LEITOR):
            with self.subTest(role=papel.role):
                self.assertEqual(workflow.acoes_disponiveis(si("CONCLUIDA"), papel), [])
        self.assertFalse(workflow.pode_excluir(si("CONCLUIDA"), OPERACAO))

    def test_cancelada_e_final(self):
        for papel in (MANUTENCAO, OPERACAO, LEITOR):
            with self.subTest(role=papel.role):
                self.assertEqual(workflow.acoes_disponiveis(si("CANCELADA"), papel), [])

    def test_programada_legada_ainda_pode_ser_enviada(self):
        self.assertEqual(workflow.acoes_disponiveis(si("PROGRAMADA"), MANUTENCAO), ["enviar"])
        self.assertTrue(workflow.pode_editar(si("PROGRAMADA"), MANUTENCAO))

    def test_concluida_e_encerrada_sem_acoes(self):
        for status in ("CONCLUIDA", "ENCERRADA"):
            with self.subTest(status=status):
                self.assertEqual(workflow.acoes_disponiveis(si(status), MANUTENCAO), [])
                self.assertEqual(workflow.acoes_disponiveis(si(status), OPERACAO), [])
                self.assertFalse(workflow.pode_editar(si(status), MANUTENCAO))


class LiberacoesTests(unittest.TestCase):
    def test_liberacoes_editaveis_no_rascunho_rejeitada_programada(self):
        for status in ("RASCUNHO", "REJEITADA", "PROGRAMADA"):
            with self.subTest(status=status):
                self.assertTrue(workflow.pode_editar_liberacoes(si(status), MANUTENCAO))
                self.assertTrue(workflow.pode_editar_liberacoes(si(status), OPERACAO))

    def test_liberacoes_editaveis_na_aprovada(self):
        # Depois de aprovada a intervencao acontece: liberacao continua aberta.
        self.assertTrue(workflow.pode_editar_liberacoes(si("APROVADA"), MANUTENCAO))
        self.assertTrue(workflow.pode_editar_liberacoes(si("APROVADA"), OPERACAO))

    def test_liberacoes_fechadas_em_analise_e_finais(self):
        for status in ("ENVIADA", "CANCELADA", "CONCLUIDA", "ENCERRADA"):
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_editar_liberacoes(si(status), MANUTENCAO))
                self.assertFalse(workflow.pode_editar_liberacoes(si(status), OPERACAO))

    def test_leitor_nao_edita_liberacoes(self):
        for status in workflow.STATUS_VALIDOS:
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_editar_liberacoes(si(status), LEITOR))


class VisibilidadeTests(unittest.TestCase):
    def test_operacao_nao_ve_rascunho(self):
        self.assertFalse(workflow.pode_visualizar(si("RASCUNHO"), OPERACAO))

    def test_operacao_ve_todos_os_outros(self):
        for status in ("ENVIADA", "REJEITADA", "APROVADA", "CANCELADA", "PROGRAMADA"):
            with self.subTest(status=status):
                self.assertTrue(workflow.pode_visualizar(si(status), OPERACAO))

    def test_manutencao_ve_rascunho(self):
        self.assertTrue(workflow.pode_visualizar(si("RASCUNHO"), MANUTENCAO))


class CriacaoEExclusaoTests(unittest.TestCase):
    def test_somente_manutencao_cria(self):
        self.assertTrue(workflow.pode_criar(MANUTENCAO))
        self.assertFalse(workflow.pode_criar(OPERACAO))
        self.assertFalse(workflow.pode_criar(LEITOR))

    def test_admin_exclui_rascunho_rejeitada_e_cancelada(self):
        self.assertTrue(workflow.pode_excluir(si("RASCUNHO"), OPERACAO))
        self.assertTrue(workflow.pode_excluir(si("REJEITADA"), OPERACAO))
        self.assertTrue(workflow.pode_excluir(si("CANCELADA"), OPERACAO))
        for status in ("ENVIADA", "APROVADA", "CONCLUIDA"):
            with self.subTest(status=status):
                self.assertFalse(workflow.pode_excluir(si(status), OPERACAO))

    def test_manutencao_e_operador_nao_excluem(self):
        self.assertFalse(workflow.pode_excluir(si("RASCUNHO"), MANUTENCAO))
        self.assertFalse(workflow.pode_excluir(si("CANCELADA"), MANUTENCAO))
        self.assertFalse(workflow.pode_excluir(si("CANCELADA"), usuario("operador")))


class ObservacaoTests(unittest.TestCase):
    def test_rejeitar_e_cancelar_exigem_observacao(self):
        self.assertTrue(workflow.observacao_obrigatoria("rejeitar"))
        self.assertTrue(workflow.observacao_obrigatoria("cancelar"))

    def test_aprovar_e_enviar_nao_exigem(self):
        self.assertFalse(workflow.observacao_obrigatoria("aprovar"))
        self.assertFalse(workflow.observacao_obrigatoria("enviar"))


class RotulosTests(unittest.TestCase):
    def test_rotulos_conhecidos(self):
        self.assertEqual(workflow.rotulo("RASCUNHO"), "Rascunho")
        self.assertEqual(workflow.rotulo("ENVIADA"), "Enviada / Em analise")
        self.assertEqual(workflow.rotulo("REJEITADA"), "Rejeitada")
        self.assertEqual(workflow.rotulo("APROVADA"), "Aprovada")
        self.assertEqual(workflow.rotulo("CANCELADA"), "Cancelada")

    def test_rotulos_sem_sufixo_de_origem(self):
        # O usuario nao precisa saber que o fluxo mudou: os status antigos
        # aparecem com o mesmo nome de sempre.
        self.assertEqual(workflow.rotulo("PROGRAMADA"), "Programada")
        self.assertEqual(workflow.rotulo("CONCLUIDA"), "Concluida")
        self.assertEqual(workflow.rotulo("ENCERRADA"), "Encerrada")

    def test_rotulo_de_valor_desconhecido_nao_quebra(self):
        self.assertEqual(workflow.rotulo("EM_ANALISE"), "Em Analise")


if __name__ == "__main__":
    unittest.main()
