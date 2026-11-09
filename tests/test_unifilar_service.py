"""Testes de regressao das funcoes puras do servico Unifilar."""

import unittest

from UNIFILAR.service import _terminais_do, _id_externo_ligacao
from UNIFILAR import schemas


class TerminaisPorTipoTests(unittest.TestCase):
    def test_equipamento_tem_t1_t2(self):
        self.assertEqual(_terminais_do("DISJUNTOR"), ("T1", "T2"))
        self.assertEqual(_terminais_do("TC"), ("T1", "T2"))

    def test_barramento_tem_b1_b4(self):
        self.assertEqual(_terminais_do("BARRAMENTO"), ("B1", "B2", "B3", "B4"))
        self.assertEqual(_terminais_do("CONEXAO"), ("B1", "B2", "B3", "B4"))
        self.assertEqual(_terminais_do("ETIQUETA_VAO"), ("B1", "B2", "B3", "B4"))


class IdExternoLigacaoTests(unittest.TestCase):
    def test_usa_id_do_editor_quando_presente(self):
        lig = schemas.LigacaoEntrada(id="e-123", source="a", sourceHandle="T1", target="b", targetHandle="T2")
        self.assertEqual(_id_externo_ligacao(lig), "e-123")

    def test_gera_id_estavel_quando_ausente(self):
        lig = schemas.LigacaoEntrada(source="a", sourceHandle="T1", target="b", targetHandle="T2")
        self.assertEqual(_id_externo_ligacao(lig), "l-a-T1-b-T2")

    def test_id_gerado_nao_excede_160(self):
        lig = schemas.LigacaoEntrada(
            source="a" * 120, sourceHandle="T1", target="b" * 120, targetHandle="T2"
        )
        self.assertLessEqual(len(_id_externo_ligacao(lig)), 160)


if __name__ == "__main__":
    unittest.main()
