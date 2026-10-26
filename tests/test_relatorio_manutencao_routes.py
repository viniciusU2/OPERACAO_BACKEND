"""Testes de regressão das rotas de relatórios de manutenção.

Cobrem funções puras usadas pelo download do ZIP, pela leitura da revisão e
pela validação dos identificadores enviados pelo cliente. Não acessam o banco.
"""

import unittest

from fastapi import HTTPException

from relatorio_manutencao.routes import (
    _confianca_numerica,
    _inteiro_do_payload,
    _slug_arquivo,
)


class SlugArquivoTests(unittest.TestCase):
    def test_remove_acentos_e_normaliza(self):
        # Regressão: a função usava unicodedata sem importar o módulo e
        # derrubava o download do ZIP com NameError.
        self.assertEqual(_slug_arquivo("Ativo Árvore Ção"), "ATIVO_ARVORE_CAO")

    def test_limita_tamanho_e_nao_deixa_underscore_final(self):
        resultado = _slug_arquivo("A" * 200, limite=10)
        self.assertLessEqual(len(resultado), 10)
        self.assertFalse(resultado.endswith("_"))

    def test_valor_vazio_usa_padrao(self):
        self.assertEqual(_slug_arquivo(""), "NAO_IDENTIFICADO")
        self.assertEqual(_slug_arquivo(None), "NAO_IDENTIFICADO")


class ConfiancaNumericaTests(unittest.TestCase):
    def test_converte_valores_validos(self):
        self.assertEqual(_confianca_numerica("0.87"), 0.87)
        self.assertEqual(_confianca_numerica(0.5), 0.5)

    def test_nao_quebra_com_valor_invalido_ou_ausente(self):
        # Regressão: float(f.confianca) levantava ValueError na leitura da revisão.
        self.assertEqual(_confianca_numerica("alta"), 0.0)
        self.assertEqual(_confianca_numerica(None), 0.0)
        self.assertEqual(_confianca_numerica(""), 0.0)


class InteiroDoPayloadTests(unittest.TestCase):
    def test_aceita_numero_e_string_numerica(self):
        self.assertEqual(_inteiro_do_payload(7, "ativo"), 7)
        self.assertEqual(_inteiro_do_payload("7", "ativo"), 7)

    def test_valor_invalido_retorna_400(self):
        # Regressão: int("abc") propagava ValueError e a API respondia 500.
        with self.assertRaises(HTTPException) as contexto:
            _inteiro_do_payload("abc", "ativo")
        self.assertEqual(contexto.exception.status_code, 400)
        self.assertIn("ativo", contexto.exception.detail)


if __name__ == "__main__":
    unittest.main()
