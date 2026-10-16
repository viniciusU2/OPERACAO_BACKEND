import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import ValidationError

from engenharia_protecao import models, schemas, service_engenharia


class Fase4SchemaTests(unittest.TestCase):
    def test_interface_usa_valores_padrao(self):
        dados = schemas.InterfaceComunicacaoCreate(nome="Porta A")
        self.assertEqual(dados.tipo, "ETHERNET")
        self.assertTrue(dados.conectada)

    def test_tipo_de_interface_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.InterfaceComunicacaoCreate(nome="Porta A", tipo="MAGICO")

    def test_protocolo_padrao_e_papel(self):
        dados = schemas.ProtocoloComunicacaoCreate(protocolo="IEC61850_GOOSE")
        self.assertEqual(dados.papel, "SERVIDOR")
        self.assertTrue(dados.habilitado)

    def test_protocolo_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.ProtocoloComunicacaoCreate(protocolo="PROFINET")

    def test_papel_de_protocolo_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.ProtocoloComunicacaoCreate(protocolo="DNP3", papel="MESTRE")

    def test_goose_usa_valores_padrao(self):
        dados = schemas.GooseControleCreate(nome_controle="PROT/LLN0$GO$GCB1")
        self.assertEqual(dados.tipo, "GOOSE")
        self.assertEqual(dados.direcao, "PUBLICADO")

    def test_tipo_de_goose_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.GooseControleCreate(nome_controle="X", tipo="MMS")

    def test_circuito_usa_valores_padrao(self):
        dados = schemas.CircuitoCreate(codigo="C1", nome="Circuito 1")
        self.assertEqual(dados.tipo, "SINALIZACAO")
        self.assertTrue(dados.ativo)

    def test_tipo_de_circuito_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.CircuitoCreate(codigo="C1", nome="Circuito 1", tipo="DESLIGAMENTO")

    def test_sinal_usa_valores_padrao(self):
        dados = schemas.SinalCreate(mnemonico="52a", descricao="Contato de disjuntor fechado")
        self.assertEqual(dados.tipo, "DIGITAL_ENTRADA")
        self.assertEqual(dados.estado, "PENDENTE")

    def test_estado_de_sinal_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.SinalCreate(mnemonico="52a", descricao="Contato", estado="ATIVO")

    def test_ensaio_usa_valores_padrao(self):
        dados = schemas.EnsaioCreate(titulo="Ensaio de rotina")
        self.assertEqual(dados.tipo, "ROTINA")

    def test_tipo_de_ensaio_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.EnsaioCreate(titulo="Ensaio", tipo="MAGIA")

    def test_status_de_ensaio_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.EnsaioUpdate(versao=1, status="EXECUTANDO")

    def test_item_de_ensaio_usa_valores_padrao(self):
        dados = schemas.EnsaioItemCreate(descricao="Verificar atuação da função 50")
        self.assertEqual(dados.ordem, 0)
        self.assertIsNone(dados.resultado)

    def test_resultado_de_item_invalido_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            schemas.EnsaioItemCreate(descricao="Verificar", resultado="OK")

    def test_updates_exigem_versao_positiva(self):
        for classe in (
            schemas.InterfaceComunicacaoUpdate,
            schemas.GooseControleUpdate,
            schemas.CircuitoUpdate,
            schemas.SinalUpdate,
            schemas.EnsaioUpdate,
        ):
            with self.subTest(classe=classe.__name__):
                with self.assertRaises(ValidationError):
                    classe(versao=0)

    def test_ensaio_out_traz_tag_do_ied(self):
        campos = schemas.EnsaioOut.model_fields
        self.assertIn("ied_tag", campos)
        self.assertIsNone(campos["ied_tag"].default)


class Fase4ModelTests(unittest.TestCase):
    TABELAS = {
        "ied_interface_comunicacao",
        "ied_protocolo_comunicacao",
        "ied_goose_controle",
        "ied_circuito",
        "ied_sinal",
        "ied_ensaio",
        "ied_ensaio_item",
        "ied_ensaio_arquivo",
    }

    def test_tabelas_da_fase_quatro_estao_no_metadata(self):
        self.assertTrue(self.TABELAS.issubset(set(models.Base.metadata.tables)))

    def test_vinculos_da_fase_quatro(self):
        def destinos(tabela):
            return {chave.target_fullname for coluna in tabela.columns for chave in coluna.foreign_keys}

        self.assertIn("ied.id_ied", destinos(models.IEDInterfaceComunicacao.__table__))
        self.assertIn(
            "ied_interface_comunicacao.id_ied_interface_comunicacao",
            destinos(models.IEDProtocoloComunicacao.__table__),
        )
        self.assertIn("ied.id_ied", destinos(models.IEDGooseControle.__table__))
        self.assertIn(
            "ied_interface_comunicacao.id_ied_interface_comunicacao",
            destinos(models.IEDGooseControle.__table__),
        )
        self.assertIn("funcao_ansi.id_funcao_ansi", destinos(models.IEDCircuito.__table__))
        self.assertIn("ied_equipamento.id_ied_equipamento", destinos(models.IEDCircuito.__table__))
        self.assertIn("ied_circuito.id_ied_circuito", destinos(models.IEDSinal.__table__))
        self.assertIn("funcao_ansi.id_funcao_ansi", destinos(models.IEDSinal.__table__))
        self.assertIn("ordem_servico.id_os", destinos(models.IEDEnsaio.__table__))
        self.assertIn("ied_ensaio.id_ied_ensaio", destinos(models.IEDEnsaioItem.__table__))
        self.assertIn("ied_sinal.id_ied_sinal", destinos(models.IEDEnsaioItem.__table__))
        self.assertIn("arquivo.id_arquivo", destinos(models.IEDEnsaioArquivo.__table__))
        self.assertIn("ied_ensaio.id_ied_ensaio", destinos(models.IEDEnsaioArquivo.__table__))


class Fase4ServiceTests(unittest.TestCase):
    def test_verificar_versao_detecta_conflito(self):
        registro = SimpleNamespace(versao=3)
        service_engenharia._verificar_versao(registro, 3, "O registro")  # não deve levantar
        with self.assertRaises(HTTPException) as contexto:
            service_engenharia._verificar_versao(registro, 2, "O registro")
        self.assertEqual(contexto.exception.status_code, 409)

    def test_funcoes_do_servico_exportadas(self):
        for nome in (
            "listar_interfaces",
            "criar_interface",
            "atualizar_interface",
            "remover_interface",
            "adicionar_protocolo",
            "remover_protocolo",
            "listar_goose",
            "criar_goose",
            "remover_goose",
            "listar_circuitos",
            "criar_circuito",
            "remover_circuito",
            "listar_sinais",
            "criar_sinal",
            "remover_sinal",
            "listar_ensaios",
            "criar_ensaio",
            "obter_ensaio",
            "atualizar_ensaio",
            "adicionar_item",
            "atualizar_item",
            "remover_item",
            "anexar_arquivo",
            "remover_arquivo",
            "caminho_download_ensaio",
            "resumo_engenharia",
        ):
            with self.subTest(nome=nome):
                self.assertTrue(callable(getattr(service_engenharia, nome)))


if __name__ == "__main__":
    unittest.main()
