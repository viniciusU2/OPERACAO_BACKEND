"""Valida, sem banco de dados, o catálogo da base de conhecimento de problemas típicos.

Estes testes protegem a qualidade mínima do conteúdo: quantidade, unicidade,
cobertura das categorias, campos obrigatórios, vocabulários controlados e
respeito aos limites de coluna declarados em ``models/problemas_tipicos_models.py``.
"""

import unittest

from problemas_tipicos.catalogo import CATALOGO

CATEGORIAS_ESPERADAS = {
    "Disjuntor de Alta Tensão",
    "Chave Seccionadora e de Aterramento",
    "Transformador de Corrente (TC)",
    "Transformador de Potencial (TP/TPC)",
    "Para-raios",
    "Transformador de Potência e Reator",
    "Proteção, Controle e Supervisão",
    "Sistema CC 125 Vcc",
    "Serviços Auxiliares em CA",
    "Comunicação e Infraestrutura",
    "Barramentos, Conexões e Isoladores",
}

SISTEMAS_ESPERADOS = {
    "Alta Tensão",
    "Transformação",
    "Proteção e Controle",
    "Corrente Contínua",
    "Serviços Auxiliares",
    "Comunicação",
    "Barramento e Conexões",
}

# Tipos de ativo previstos: os existentes no ENGVI e os criados pela seed.
TIPOS_ATIVOS_PERMITIDOS = {
    "Disjuntor",
    "Seccionadora",
    "Relé de Proteção",
    "Transformador de Corrente",
    "Transformador de Potencial",
    "Transformador de Potencial Capacitivo",
    "Para-Raios",
    "Transformador de Potência",
    "Reator Derivação",
    "Painel",
    "Relé de Proteção",
    "Supervisório",
    "Sincronizador",
    "Registrador de Perturbações",
    "Retificador",
    "Banco de Baterias",
    "Grupo Motor Gerador",
    "Barramento",
    "Isolador",
    "Geral",
}

CRITICIDADES = {"BAIXA", "MEDIA", "ALTA", "CRITICA"}
DETECTABILIDADES = {"ALTA", "MEDIA", "BAIXA"}
RISCOS = {"BAIXO", "MEDIO", "ALTO"}
CONDICOES = {"ENERGIZADO", "DESENERGIZADO", "INDIFERENTE"}
TIPOS_ACAO_CORRETIVA = {"INSPECAO", "ENSAIO", "CORRECAO", "SUBSTITUICAO", "MONITORAMENTO", "INVESTIGACAO"}

LIMITES = {
    "codigo": 80,
    "titulo": 150,
    "categoria": 50,
    "sistema": 50,
    "especialidade": 100,
}


class CatalogoProblemasTipicosTests(unittest.TestCase):
    def test_volume_minimo_e_codigos_unicos(self):
        self.assertGreaterEqual(len(CATALOGO), 60, "A base inicial deve ter ao menos 60 problemas")
        codigos = [item["codigo"] for item in CATALOGO]
        self.assertEqual(len(codigos), len(set(codigos)), "Há códigos duplicados no catálogo")
        for codigo in codigos:
            self.assertTrue(codigo.startswith("BDC-"), f"Código fora do padrão da seed: {codigo}")

    def test_chave_natural_tipo_titulo_e_unica(self):
        chaves = [(item["tipo_ativo"], item["titulo"]) for item in CATALOGO]
        self.assertEqual(len(chaves), len(set(chaves)), "Título repetido para o mesmo tipo de ativo")

    def test_cobertura_de_categorias_e_sistemas(self):
        categorias = {item["categoria"] for item in CATALOGO}
        sistemas = {item["sistema"] for item in CATALOGO}
        self.assertEqual(categorias, CATEGORIAS_ESPERADAS)
        self.assertTrue(sistemas <= SISTEMAS_ESPERADOS, f"Sistemas inesperados: {sistemas - SISTEMAS_ESPERADOS}")
        self.assertTrue(sistemas, "Nenhum sistema informado")

    def test_tipos_de_ativo_previstos(self):
        usados = {item["tipo_ativo"] for item in CATALOGO}
        self.assertTrue(usados <= TIPOS_ATIVOS_PERMITIDOS, f"Tipos inesperados: {usados - TIPOS_ATIVOS_PERMITIDOS}")

    def test_vocabularios_controlados(self):
        for item in CATALOGO:
            self.assertIn(item["criticidade"], CRITICIDADES, item["codigo"])
            self.assertIn(item["detectabilidade"], DETECTABILIDADES, item["codigo"])
            self.assertIn(item["risco_operacional"], RISCOS, item["codigo"])
            self.assertIn(item["condicao_intervencao"], CONDICOES, item["codigo"])
            self.assertIsInstance(item["requer_desligamento"], bool)
            self.assertIsInstance(item["requer_equipe_especializada"], bool)

    def test_campos_obrigatorios_preenchidos(self):
        for item in CATALOGO:
            self.assertGreaterEqual(len(item["descricao"]), 80, item["codigo"])
            self.assertGreaterEqual(len(item["sintomas"]), 2, item["codigo"])
            self.assertGreaterEqual(len(item["causas"]), 2, item["codigo"])
            self.assertGreaterEqual(len(item["metodos_deteccao"]), 1, item["codigo"])
            self.assertGreaterEqual(len(item["palavras_chave"]), 2, item["codigo"])
            self.assertTrue(item["modo_falha"], item["codigo"])
            self.assertTrue(item["efeito_falha"], item["codigo"])
            self.assertTrue(item["referencias_tecnicas"], item["codigo"])
            self.assertTrue(item["especialidade"], item["codigo"])

    def test_acoes_corretivas_e_preventivas(self):
        for item in CATALOGO:
            acoes = item["acoes_recomendadas"]
            corretivas = [a for a in acoes if a["tipo_acao"] != "PREVENCAO"]
            preventivas = [a for a in acoes if a["tipo_acao"] == "PREVENCAO"]
            self.assertGreaterEqual(len(corretivas), 1, item["codigo"])
            self.assertGreaterEqual(len(preventivas), 1, item["codigo"])
            for acao in corretivas:
                self.assertIn(acao["tipo_acao"], TIPOS_ACAO_CORRETIVA, item["codigo"])
                self.assertTrue(acao["prioridade"], item["codigo"])

    def test_alertas_de_seguranca_nos_casos_criticos(self):
        """Atividades de alto risco devem trazer alerta explícito de segurança."""
        for item in CATALOGO:
            exige_alerta = (
                item["criticidade"] == "CRITICA"
                or item["tipo_ativo"] in {"Transformador de Corrente", "Disjuntor"}
                or "secundário" in " ".join(item["sintomas"]).lower()
            )
            if exige_alerta:
                self.assertTrue(item["alerta_seguranca"], f"{item['codigo']} sem alerta de segurança")

    def test_limites_de_coluna_respeitados(self):
        for item in CATALOGO:
            for campo, limite in LIMITES.items():
                if item.get(campo):
                    self.assertLessEqual(len(item[campo]), limite, f"{item['codigo']}.{campo}")
            for campo in ("modo_falha", "efeito_falha", "descricao", "alerta_seguranca", "referencias_tecnicas"):
                self.assertTrue(len(item[campo]) <= 5000, f"{item['codigo']}.{campo} excede TEXT razoável")
            for sintoma in item["sintomas"] + item["causas"] + item["alarmes"]:
                self.assertLessEqual(len(sintoma), 500, item["codigo"])
            for metodo in item["metodos_deteccao"]:
                self.assertLessEqual(len(metodo), 400, item["codigo"])
            for palavra in item["palavras_chave"]:
                self.assertLessEqual(len(palavra), 80, item["codigo"])
            for instrumento in item["instrumentos"]:
                self.assertLessEqual(len(instrumento), 150, item["codigo"])
            for acao in item["acoes_recomendadas"]:
                self.assertLessEqual(len(acao["descricao"]), 500, item["codigo"])

    def test_sem_duplicidade_de_conteudo(self):
        """Evita registros que só diferem pelo título."""
        assinaturas = [(item["categoria"], item["descricao"].strip().lower()[:120]) for item in CATALOGO]
        self.assertEqual(len(assinaturas), len(set(assinaturas)), "Descrições duplicadas no catálogo")


if __name__ == "__main__":
    unittest.main()
