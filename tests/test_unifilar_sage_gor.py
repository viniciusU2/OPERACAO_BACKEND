"""Regressao da topologia SAGE do unifilar da SE GOR.

Valida, sobre o seed portatil (sem banco), o comportamento operacional
esperado do arranjo de disjuntor e meio:

- abrir 15E7/15E9/15D7/15D8 nao desenergiza o restante da linha;
- os reatores 05E6/05E8 so caem quando 15C2 e 15C4 estao os dois abertos.
"""

import json
import unittest
from collections import deque
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SEED = RAIZ / "scripts" / "seeds" / "unifilar_seed.json"


def _carregar_gor() -> dict:
    dados = json.loads(SEED.read_text(encoding="utf-8"))
    for diagrama in dados.get("diagramas") or []:
        if (diagrama.get("subestacao") or "").strip().upper() == "SE GOR":
            return diagrama
    raise AssertionError("Diagrama da SE GOR nao encontrado no seed")


def _adjacencia(arestas: list[dict]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for aresta in arestas:
        origem, destino = aresta["source"], aresta["target"]
        adj.setdefault(origem, set()).add(destino)
        adj.setdefault(destino, set()).add(origem)
    return adj


def _alcancaveis(inicio: list[str], adj: dict[str, set[str]], bloqueados: set[str]) -> set[str]:
    vistos = set(inicio)
    fila = deque(inicio)
    while fila:
        atual = fila.popleft()
        for vizinho in adj.get(atual, ()):
            if vizinho in vistos or vizinho in bloqueados:
                continue
            vistos.add(vizinho)
            fila.append(vizinho)
    return vistos


class TopologiaSageGorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diagrama = _carregar_gor()
        cls.nos = {no["id"]: no for no in cls.diagrama["nodes"]}
        cls.adj = _adjacencia(cls.diagrama["edges"])
        cls.por_codigo = {
            (no["data"].get("codigo") or "").strip().upper(): no["id"]
            for no in cls.diagrama["nodes"]
        }
        barras = [no for no in cls.diagrama["nodes"] if no["data"]["tipo"] == "BARRAMENTO"]
        cls.fonte = min(barras, key=lambda no: no["position"]["y"])["id"]
        cls.base = _alcancaveis([cls.fonte], cls.adj, set())

    def _perdem(self, *codigos: str) -> set[str]:
        abertos = {self.por_codigo[codigo] for codigo in codigos}
        return self.base - _alcancaveis([self.fonte], self.adj, abertos)

    def test_elo_do_vao_g_existe(self):
        chaves = {
            (aresta["source"], aresta["sourceHandle"], aresta["target"], aresta["targetHandle"])
            for aresta in self.diagrama["edges"]
        }
        a, b = self.por_codigo["35C2-5"], self.por_codigo["95C2"]
        self.assertTrue(
            (a, "T2", b, "T1") in chaves or (b, "T1", a, "T2") in chaves,
            "Falta a ligacao 35C2-5.T2 -> 95C2.T1",
        )

    def test_tudo_energizado_com_tudo_fechado(self):
        self.assertEqual(len(self.base), len(self.nos))

    def test_abrir_barramentos_superiores_nao_derruba_linha(self):
        for codigo in ("15E7", "15E9", "15D7", "15D8"):
            with self.subTest(codigo=codigo):
                perderam = self._perdem(codigo)
                self.assertEqual(
                    perderam, {self.por_codigo[codigo]},
                    f"abrir {codigo} desenergizou {sorted(perderam)}",
                )

    def test_reatores_so_caem_com_os_dois_disjuntores_c(self):
        self.assertIn(self.por_codigo["05E6"], self.base)
        self.assertIn(self.por_codigo["05E8"], self.base)
        self.assertIn(self.por_codigo["05E6"], _alcancaveis(
            [self.fonte], self.adj, {self.por_codigo["15C2"]}
        ))
        self.assertIn(self.por_codigo["05E8"], _alcancaveis(
            [self.fonte], self.adj, {self.por_codigo["15C4"]}
        ))

        perderam = self._perdem("15C2", "15C4")
        self.assertIn(self.por_codigo["05E6"], perderam)
        self.assertIn(self.por_codigo["05E8"], perderam)
        self.assertIn(self.por_codigo["BAR500B"], perderam)


if __name__ == "__main__":
    unittest.main()
