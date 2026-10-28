import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from models.plano_manutencao_models import StatusItemEnum
from relatorio_manutencao import importar_inspecoes as importacao


def _resultado(
    id_resultado=1,
    foto=None,
    nome_item="Item",
    ordem=1,
    valor=None,
    status=StatusItemEnum.OK,
    observacao="",
    id_plano_item=None,
):
    return SimpleNamespace(
        id_resultado=id_resultado,
        foto=foto,
        nome_item=nome_item,
        valor_medido=valor,
        status_item=status,
        observacao_item=observacao,
        id_plano_item=id_plano_item if id_plano_item is not None else ordem,
        plano_item=SimpleNamespace(ordem=ordem),
    )


def _inspecao(id_inspecao=1, codigo="GMG-P", resultados=None):
    return SimpleNamespace(
        id_inspecao=id_inspecao,
        id_ativo=10,
        ativo=SimpleNamespace(codigo_ativo=codigo, fase="CA"),
        data_inspecao=None,
        resultados=resultados or [],
    )


class ImportarInspecoesTest(unittest.TestCase):
    def setUp(self):
        self._pasta_anterior = os.environ.get("INSPECAO_FOTO_DIR")
        self._tempdir = tempfile.TemporaryDirectory(prefix="engvi_importacao_")
        os.environ["INSPECAO_FOTO_DIR"] = self._tempdir.name
        self.nome_foto = "a" * 32 + ".jpg"
        (Path(self._tempdir.name) / self.nome_foto).write_bytes(b"\xff\xd8\xfffake-jpeg")

    def tearDown(self):
        self._tempdir.cleanup()
        if self._pasta_anterior is None:
            os.environ.pop("INSPECAO_FOTO_DIR", None)
        else:
            os.environ["INSPECAO_FOTO_DIR"] = self._pasta_anterior

    def test_formatar_valor(self):
        self.assertEqual(importacao.formatar_valor(Decimal("12.0000")), "12")
        self.assertEqual(importacao.formatar_valor(Decimal("1790.0000")), "1790")
        self.assertEqual(importacao.formatar_valor(Decimal("11.5000")), "11.5")
        self.assertIsNone(importacao.formatar_valor(None))

    def test_periodo_e_texto_padrao(self):
        self.assertEqual(importacao.periodo_capa(date(2026, 9, 24)), "Setembro/ 2026")
        texto = importacao.texto_introducao_padrao(date(2026, 9, 24), "SE GOR", "Grupo Motor Gerador")
        self.assertIn("24/09/2026", texto)
        self.assertIn("SE GOR", texto)
        self.assertIn("Grupo Motor Gerador", texto)

    def test_ignora_foto_que_nao_esta_no_backend(self):
        self.assertIsNotNone(importacao._conteudo_foto_backend(f"{importacao.PREFIXO_FOTO_BACKEND}{self.nome_foto}"))
        self.assertIsNone(importacao._conteudo_foto_backend("https://empresa.sharepoint.com/x.jpg"))
        self.assertIsNone(importacao._conteudo_foto_backend(None))
        self.assertIsNone(importacao._conteudo_foto_backend(f"{importacao.PREFIXO_FOTO_BACKEND}{'b' * 32}.jpg"))

    def test_montar_fotos_usa_apenas_fotos_internas(self):
        inspecao = _inspecao(
            resultados=[
                _resultado(
                    id_resultado=7,
                    foto=f"{importacao.PREFIXO_FOTO_BACKEND}{self.nome_foto}",
                    nome_item="Nível do óleo",
                    ordem=2,
                    valor=Decimal("75.0000"),
                ),
                _resultado(
                    id_resultado=8,
                    foto="https://empresa.sharepoint.com/foto.jpg",
                    nome_item="Temperatura",
                    ordem=3,
                ),
            ]
        )

        fotos, sem_foto = importacao.montar_fotos([inspecao])

        self.assertEqual(len(fotos), 1)
        self.assertEqual(sem_foto, [])
        foto = fotos[0]
        self.assertEqual(foto.nome_zip, "GMG-P/001 - Nível do óleo.jpg")
        self.assertEqual(foto.valor, "75")
        self.assertEqual(foto.status, "OK")
        self.assertEqual(foto.id_ativo, 10)

    def test_inspecao_sem_foto_interna_entra_em_sem_foto(self):
        inspecao = _inspecao(
            resultados=[
                _resultado(foto="https://empresa.sharepoint.com/foto.jpg"),
            ]
        )

        fotos, sem_foto = importacao.montar_fotos([inspecao])

        self.assertEqual(fotos, [])
        self.assertEqual(sem_foto, [inspecao])

    def test_nome_arquivo_original(self):
        nome = importacao.nome_arquivo_original(
            "SEMANAL", "SE GOR", "Grupo Motor Gerador", date(2026, 9, 24)
        )
        self.assertEqual(
            nome, "inspecoes-semanal-se-gor-grupo-motor-gerador-2026-09-24.zip"
        )


if __name__ == "__main__":
    unittest.main()
