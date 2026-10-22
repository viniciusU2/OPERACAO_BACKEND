import os
import re
import tempfile
import unittest
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from database import get_db
from plano_manutencao.inspecoes import PREFIXO_FOTO_INSPECAO, router


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeSession:
    def query(self, *args, **kwargs):
        return _FakeQuery()


def _fake_db():
    yield _FakeSession()


class InspecaoFotoUploadTest(unittest.TestCase):
    def setUp(self):
        self._pasta_anterior = os.environ.get("INSPECAO_FOTO_DIR")
        self._limite_anterior = os.environ.get("INSPECAO_FOTO_MAX_MB")
        self._tempdir = tempfile.TemporaryDirectory(prefix="engvi_inspecao_fotos_")
        os.environ["INSPECAO_FOTO_DIR"] = self._tempdir.name
        os.environ["INSPECAO_FOTO_MAX_MB"] = "2"

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _fake_db
        self.client = TestClient(app)

        buffer = BytesIO()
        Image.new("RGB", (3000, 2000), (20, 80, 140)).save(buffer, format="JPEG")
        self.jpeg = buffer.getvalue()

    def tearDown(self):
        self.client.close()
        self._tempdir.cleanup()

        if self._pasta_anterior is None:
            os.environ.pop("INSPECAO_FOTO_DIR", None)
        else:
            os.environ["INSPECAO_FOTO_DIR"] = self._pasta_anterior

        if self._limite_anterior is None:
            os.environ.pop("INSPECAO_FOTO_MAX_MB", None)
        else:
            os.environ["INSPECAO_FOTO_MAX_MB"] = self._limite_anterior

    def test_envia_normaliza_e_remove_foto(self):
        resposta = self.client.post(
            "/inspecoes/fotos",
            files={"arquivo": ("foto-campo.jpg", self.jpeg, "image/jpeg")},
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)

        dados = resposta.json()
        self.assertTrue(dados["url"].startswith(PREFIXO_FOTO_INSPECAO))
        self.assertRegex(dados["nome_arquivo"], re.compile(r"^[a-f0-9]{32}\.jpg$"))

        download = self.client.get(dados["url"])
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.headers["content-type"], "image/jpeg")
        self.assertIn("immutable", download.headers.get("cache-control", ""))

        with Image.open(BytesIO(download.content)) as imagem:
            self.assertLessEqual(max(imagem.size), 1920)

        remocao = self.client.delete(dados["url"])
        self.assertEqual(remocao.status_code, 204, remocao.text)

        depois = self.client.get(dados["url"])
        self.assertEqual(depois.status_code, 404)

    def test_recusa_arquivo_que_nao_e_imagem(self):
        resposta = self.client.post(
            "/inspecoes/fotos",
            files={"arquivo": ("arquivo.txt", b"nao sou imagem", "text/plain")},
        )
        self.assertEqual(resposta.status_code, 400)

    def test_recusa_caminho_fora_da_pasta(self):
        resposta = self.client.get("/inspecoes/fotos/..%2F..%2Fmain.py")
        self.assertEqual(resposta.status_code, 404)


if __name__ == "__main__":
    unittest.main()
