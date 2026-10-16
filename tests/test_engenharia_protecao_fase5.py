import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import ValidationError

from engenharia_protecao import models, schemas, service_ocorrencias


class Fase5SchemaTests(unittest.TestCase):
    def test_ocorrencia_usa_valores_padrao(self):
        dados = schemas.OcorrenciaCreate(titulo="Atuação da proteção 21")
        self.assertEqual(dados.tipo, "ALARME")
        self.assertEqual(dados.severidade, "MEDIA")

    def test_tipo_de_ocorrencia_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.OcorrenciaCreate(titulo="Evento", tipo="MAGICO")

    def test_severidade_de_ocorrencia_invalida_e_rejeitada(self):
        with self.assertRaises(ValidationError):
            schemas.OcorrenciaCreate(titulo="Evento", severidade="URGENTE")

    def test_status_de_ocorrencia_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.OcorrenciaUpdate(versao=1, status="FECHADA")

    def test_oscilografia_usa_valores_padrao(self):
        dados = schemas.OscilografiaCreate(nome="Oscilografia 101")
        self.assertEqual(dados.tipo, "OSCILOGRAFIA")
        self.assertIsNone(dados.duracao_ms)

    def test_tipo_de_oscilografia_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.OscilografiaCreate(nome="Registro", tipo="SISMOGRAFIA")

    def test_relatorio_usa_valores_padrao(self):
        dados = schemas.RelatorioCreate(titulo="Relatório de ocorrência")
        self.assertEqual(dados.tipo, "OCORRENCIA")
        self.assertIsNone(dados.data_emissao)

    def test_tipo_de_relatorio_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.RelatorioCreate(titulo="Relatório", tipo="POESIA")

    def test_status_de_relatorio_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.RelatorioUpdate(versao=1, status="PUBLICADO")

    def test_updates_exigem_versao_positiva(self):
        for classe in (schemas.OcorrenciaUpdate, schemas.OscilografiaUpdate, schemas.RelatorioUpdate):
            with self.subTest(classe=classe.__name__):
                with self.assertRaises(ValidationError):
                    classe(versao=0)

    def test_resumo_traz_indicadores(self):
        campos = schemas.ResumoOcorrenciaOut.model_fields
        for nome in (
            "total_ocorrencias",
            "ocorrencias_abertas",
            "ocorrencias_criticas",
            "total_oscilografias",
            "total_relatorios",
            "por_severidade",
        ):
            with self.subTest(nome=nome):
                self.assertIn(nome, campos)

    def test_auditoria_expoe_acao_e_usuario(self):
        campos = schemas.AuditoriaOut.model_fields
        self.assertIn("acao", campos)
        self.assertIn("nome_usuario", campos)


class Fase5ModelTests(unittest.TestCase):
    TABELAS = {
        "ied_ocorrencia",
        "ied_ocorrencia_arquivo",
        "ied_ocorrencia_historico",
        "ied_oscilografia",
        "ied_oscilografia_arquivo",
        "ied_relatorio",
        "ied_relatorio_arquivo",
    }

    def test_tabelas_da_fase_cinco_estao_no_metadata(self):
        self.assertTrue(self.TABELAS.issubset(set(models.Base.metadata.tables)))

    def test_vinculos_da_fase_cinco(self):
        def destinos(tabela):
            return {chave.target_fullname for coluna in tabela.columns for chave in coluna.foreign_keys}

        self.assertIn("ied.id_ied", destinos(models.IEDOcorrencia.__table__))
        self.assertIn("ordem_servico.id_os", destinos(models.IEDOcorrencia.__table__))
        self.assertIn(
            "ied_ocorrencia.id_ied_ocorrencia", destinos(models.IEDOcorrenciaArquivo.__table__)
        )
        self.assertIn("arquivo.id_arquivo", destinos(models.IEDOcorrenciaArquivo.__table__))
        self.assertIn(
            "ied_ocorrencia.id_ied_ocorrencia", destinos(models.IEDOcorrenciaHistorico.__table__)
        )
        self.assertIn("ied.id_ied", destinos(models.IEDOscilografia.__table__))
        self.assertIn("ied_ocorrencia.id_ied_ocorrencia", destinos(models.IEDOscilografia.__table__))
        self.assertIn(
            "ied_oscilografia.id_ied_oscilografia", destinos(models.IEDOscilografiaArquivo.__table__)
        )
        self.assertIn("ied.id_ied", destinos(models.IEDRelatorio.__table__))
        self.assertIn("ied_ocorrencia.id_ied_ocorrencia", destinos(models.IEDRelatorio.__table__))
        self.assertIn("arquivo.id_arquivo", destinos(models.IEDRelatorioArquivo.__table__))

    def test_numero_e_unico_por_ied(self):
        for modelo in (models.IEDOcorrencia, models.IEDOscilografia, models.IEDRelatorio):
            with self.subTest(modelo=modelo.__name__):
                nomes = {c.name for c in modelo.__table__.constraints if c.name}
                self.assertIn(f"uq_{modelo.__tablename__}_numero", nomes)


class Fase5ServiceTests(unittest.TestCase):
    def test_verificar_versao_detecta_conflito(self):
        registro = SimpleNamespace(versao=4)
        service_ocorrencias._verificar_versao(registro, 4, "O registro")  # não deve levantar
        with self.assertRaises(HTTPException) as contexto:
            service_ocorrencias._verificar_versao(registro, 3, "O registro")
        self.assertEqual(contexto.exception.status_code, 409)

    def test_caminho_download_rejeita_arquivo_inexistente(self):
        class QueryFalsa:
            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return None

        class DbFalsa:
            def query(self, *args, **kwargs):
                return QueryFalsa()

        with self.assertRaises(HTTPException) as contexto:
            service_ocorrencias._caminho_download(DbFalsa(), 999)
        self.assertEqual(contexto.exception.status_code, 404)

    def test_funcoes_do_servico_exportadas(self):
        for nome in (
            "listar_ocorrencias",
            "listar_ocorrencias_ied",
            "criar_ocorrencia",
            "obter_ocorrencia",
            "atualizar_ocorrencia",
            "remover_ocorrencia",
            "encerrar_ocorrencia",
            "anexar_arquivo_ocorrencia",
            "remover_arquivo_ocorrencia",
            "caminho_download_ocorrencia",
            "listar_oscilografias",
            "criar_oscilografia",
            "obter_oscilografia",
            "atualizar_oscilografia",
            "remover_oscilografia",
            "anexar_arquivo_oscilografia",
            "caminho_download_oscilografia",
            "listar_relatorios",
            "criar_relatorio",
            "obter_relatorio",
            "atualizar_relatorio",
            "remover_relatorio",
            "anexar_arquivo_relatorio",
            "caminho_download_relatorio",
            "listar_auditoria",
            "resumo_ocorrencias",
        ):
            with self.subTest(nome=nome):
                self.assertTrue(callable(getattr(service_ocorrencias, nome)))


if __name__ == "__main__":
    unittest.main()
