"""Testes das notificacoes por e-mail das SI.

Nao enviam nada: cobrem as regras puras (destinatarios por acao, guardas
de configuracao e montagem das mensagens). O envio real e coberto pelo
fluxo com SMTP desligado (deve ser no-op) e pela resiliencia (SMTP fora
nao derruba a acao).
"""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from SI import notificacoes


def usuario(email, role, ativo=True):
    return SimpleNamespace(email=email, role=role, ativo=ativo, nome="Fulano")


class SmtPConfiguradoTests(unittest.TestCase):
    def test_desligado_sem_variaveis(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(notificacoes.smtp_configurado())

    def test_desligado_com_config_parcial(self):
        with patch.dict(
            os.environ,
            {"SMTP_HOST": "smtp-relay.brevo.com", "SMTP_USER": "x"},
            clear=True,
        ):
            # falta senha e remetente: notificacao fica desligada
            self.assertFalse(notificacoes.smtp_configurado())

    def test_ligado_completo(self):
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp-relay.brevo.com",
                "SMTP_USER": "x",
                "SMTP_PASSWORD": "y",
                "SMTP_FROM": "engvi@gruporialma.com.br",
            },
            clear=True,
        ):
            self.assertTrue(notificacoes.smtp_configurado())


class DestinatariosTests(unittest.TestCase):
    def setUp(self):
        self.usuarios = [
            usuario("adm@empresa.com", "admin"),
            usuario("oper@empresa.com", "operador"),
            usuario("manut1@empresa.com", "mantenedor"),
            usuario("manut2@empresa.com", "mantenedor"),
            usuario("leitor@empresa.com", "usuario"),
            usuario("inativo@empresa.com", "mantenedor", ativo=False),
        ]

    def test_enviar_notifica_operacao(self):
        self.assertEqual(
            notificacoes.emails_por_acao(self.usuarios, "enviar"),
            ["adm@empresa.com", "oper@empresa.com"],
        )

    def test_rejeitar_notifica_manutencao(self):
        self.assertEqual(
            notificacoes.emails_por_acao(self.usuarios, "rejeitar"),
            ["manut1@empresa.com", "manut2@empresa.com"],
        )

    def test_concluir_notifica_os_dois_lados(self):
        self.assertEqual(
            notificacoes.emails_por_acao(self.usuarios, "concluir"),
            ["adm@empresa.com", "manut1@empresa.com", "manut2@empresa.com", "oper@empresa.com"],
        )

    def test_exclui_quem_executou_e_inativos(self):
        self.assertEqual(
            notificacoes.emails_por_acao(self.usuarios, "aprovar", "manut1@empresa.com"),
            ["manut2@empresa.com"],
        )
        self.assertNotIn("inativo@empresa.com", notificacoes.emails_por_acao(self.usuarios, "aprovar"))

    def test_acao_desconhecida_nao_notifica(self):
        self.assertEqual(notificacoes.emails_por_acao(self.usuarios, "criar"), [])


class MensagemTests(unittest.TestCase):
    DADOS = {
        "numero": "SI-BJD-0041-2026",
        "titulo": "REJEITADA — corrija e reenvie",
        "acao": "rejeitar",
        "quem": "Vinicius Gama",
        "quando": "04/11/2026 10:00",
        "instalacao": "SE BJD",
        "ativo": "SINCRONIZADOR",
        "observacao": "Ajustar o período de manutenção informado.",
        "link": "http://frontend/si/72",
        "destinatarios": "manut@empresa.com",
        "host": "smtp-relay.brevo.com",
        "port": 587,
        "remetente": "engvi@gruporialma.com.br",
        "usuario": "x",
        "senha": "y",
        "use_ssl": False,
        "use_tls": True,
    }

    def test_texto_contem_o_essencial(self):
        texto = notificacoes._texto(self.DADOS)
        self.assertIn("SI-BJD-0041-2026", texto)
        self.assertIn("REJEITADA", texto)
        self.assertIn("Ajustar o período", texto)
        self.assertIn("http://frontend/si/72", texto)
        self.assertIn("Vinicius Gama", texto)

    def test_html_contem_observacao_e_botao(self):
        html = notificacoes._html(self.DADOS)
        self.assertIn("SI-BJD-0041-2026", html)
        self.assertIn("Ajustar o período", html)
        self.assertIn('href="http://frontend/si/72"', html)

    def test_mensagem_sem_link_e_sem_observacao_nao_quebra(self):
        dados = {**self.DADOS, "link": "", "observacao": ""}
        self.assertNotIn("href=", notificacoes._html(dados))
        self.assertNotIn("Observação", notificacoes._texto(dados))


class NotificarSITests(unittest.TestCase):
    def test_sem_smtp_e_no_op_sem_tocar_no_banco(self):
        # sem SMTP configurado a funcao retorna antes de consultar usuarios
        with patch.dict(os.environ, {}, clear=True):
            notificacoes.notificar_si(db=None, si=None, acao="aprovar", usuario=None)
        # nao lanca excecao: se chegasse ao banco, None quebraria


if __name__ == "__main__":
    unittest.main()
