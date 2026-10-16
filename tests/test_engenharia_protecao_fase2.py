import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError

from engenharia_protecao import models, schemas
from engenharia_protecao import service_config


class EngenhariaProtecaoFase2SchemaTests(unittest.TestCase):
    def test_codigo_da_funcao_ansi_e_normalizado(self):
        dados = schemas.FuncaoANSICreate(codigo=" 50n ", nome="Sobrecorrente de neutro")
        self.assertEqual(dados.codigo, "50N")
        self.assertTrue(dados.ativo)

    def test_tipo_de_dado_do_parametro_e_normalizado(self):
        dados = schemas.ParametroDefinicaoCreate(codigo="Pickup", nome="Corrente de partida", tipo_dado="numerico")
        self.assertEqual(dados.tipo_dado, "NUMERICO")

    def test_tipo_de_dado_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.ParametroDefinicaoCreate(codigo="Pickup", nome="Corrente de partida", tipo_dado="MOEDA")

    def test_motivo_da_configuracao_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.ConfiguracaoCreate(rotulo="Backup", motivo="QUALQUER", data_coleta=date(2026, 10, 16))

    def test_configuracao_usa_motivo_padrao(self):
        dados = schemas.ConfiguracaoCreate(rotulo="Backup", data_coleta=date(2026, 10, 16))
        self.assertEqual(dados.motivo, "OUTRO")

    def test_resultado_de_validacao_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.ValidacaoCreate(resultado="TALVEZ")

    def test_lote_de_parametros_aceita_lista_vazia(self):
        lote = schemas.ConfigParametroLote()
        self.assertEqual(lote.parametros, [])


class EngenhariaProtecaoFase2ModelTests(unittest.TestCase):
    def test_tabelas_da_fase_dois_estao_no_metadata(self):
        esperadas = {
            "funcao_ansi",
            "parametro_definicao",
            "ied_funcao",
            "ied_grupo_ajuste",
            "config_parametro",
            "arquivo",
            "ied_configuracao",
            "configuracao_arquivo",
            "ied_backup_validacao",
        }
        self.assertTrue(esperadas.issubset(set(models.Base.metadata.tables)))

    def test_vinculos_da_fase_dois_referenciam_entidades_existentes(self):
        def destinos(tabela):
            return {chave.target_fullname for coluna in tabela.columns for chave in coluna.foreign_keys}

        self.assertIn("ied.id_ied", destinos(models.IEDFuncao.__table__))
        self.assertIn("funcao_ansi.id_funcao_ansi", destinos(models.IEDFuncao.__table__))
        self.assertIn("ied_grupo_ajuste.id_ied_grupo_ajuste", destinos(models.ConfigParametro.__table__))
        self.assertIn("parametro_definicao.id_parametro_definicao", destinos(models.ConfigParametro.__table__))
        self.assertIn("ordem_servico.id_os", destinos(models.IEDConfiguracao.__table__))
        self.assertIn("arquivo.id_arquivo", destinos(models.ConfiguracaoArquivo.__table__))
        self.assertIn("ied_configuracao.id_ied_configuracao", destinos(models.IEDBackupValidacao.__table__))


class ArquivoFase2Tests(unittest.TestCase):
    def test_extensoes_permitidas_incluem_formato_siemens(self):
        self.assertIn(".cid", service_config.EXTENSOES_PERMITIDAS)
        self.assertIn(".zip", service_config.EXTENSOES_PERMITIDAS)

    def test_categoria_e_deduzida_pela_extensao(self):
        self.assertEqual(service_config._categoria_por_extensao(".cid"), "DIGSI")
        self.assertEqual(service_config._categoria_por_extensao(".scd"), "SCL")
        self.assertEqual(service_config._categoria_por_extensao(".inexistente"), "OUTRO")

    def test_limite_de_arquivo_positivo(self):
        self.assertGreater(service_config.MAX_ARQUIVO_BYTES, 0)


class ValidacaoDeConteudoTests(unittest.TestCase):
    def test_pdf_com_assinatura_valida_e_aceito(self):
        service_config.validar_conteudo(".pdf", b"%PDF-1.7\nconteudo")

    def test_pdf_sem_assinatura_e_rejeitado(self):
        with self.assertRaises(HTTPException) as ctx:
            service_config.validar_conteudo(".pdf", b"nao e um pdf")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_zip_com_assinatura_valida_e_aceito(self):
        service_config.validar_conteudo(".zip", b"PK\x03\x04resto")

    def test_zip_sem_assinatura_e_rejeitado(self):
        with self.assertRaises(HTTPException):
            service_config.validar_conteudo(".zip", b"MZ")

    def test_scd_deve_ser_xml(self):
        service_config.validar_conteudo(".scd", b"<?xml version='1.0'?><SCL/>")
        with self.assertRaises(HTTPException):
            service_config.validar_conteudo(".scd", b"nao e xml")

    def test_formatos_sem_assinatura_nao_sao_validados_por_conteudo(self):
        service_config.validar_conteudo(".cfg", b"station,dev\n")
        service_config.validar_conteudo(".txt", b"qualquer coisa")
        service_config.validar_conteudo(".dat", b"\x00\x01\x02")


if __name__ == "__main__":
    unittest.main()
