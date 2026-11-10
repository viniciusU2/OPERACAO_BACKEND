"""Seed do arranjo 500 kV - disjuntor e meio, vaos G e H (SE BJD).

Reproduz o diagrama de referencia: dois barramentos de 500 kV, vaos G e H
em serie entre os barramentos (seccionadora, disjuntor, reator de linha,
seccionadoras e aterramentos), e os reatores de barra 05E6 e 05E8 na base
do barramento inferior. Valida terminais e capacidades antes de gravar.

Uso:
    ENGVI_SEED_TOKEN=<token> python scripts/seed_unifilar_500kv_disjuntor_meio.py [id_subestacao]
"""

import os
import sys

import requests

BASE = "http://127.0.0.1:8000"
SESSAO = requests.Session()

DIMS = {
    "BARRAMENTO": (800, 10), "DISJUNTOR": (44, 72), "SECCIONADORA": (40, 72),
    "SECCIONADORA_ATERRAMENTO": (40, 96), "REATOR": (44, 110),
    "CONEXAO": (16, 16), "ETIQUETA_VAO": (110, 26),
}
TERM_BARRA = ("B1", "B2", "B3", "B4")
TERM_EQ = ("T1", "T2")
MAX_EQ = 1


def login():
    token = os.getenv("ENGVI_SEED_TOKEN", "")
    if not token:
        raise SystemExit("Defina ENGVI_SEED_TOKEN.")
    SESSAO.headers["Authorization"] = f"Bearer {token}"


def construir():
    nodes, edges = [], []

    def no(tipo, codigo, x, y, nome="", largura=None):
        w, h = DIMS.get(tipo, (40, 72))
        if largura:
            w = largura
        nodes.append({
            "id": codigo.lower(), "type": "noUnifilar", "position": {"x": x, "y": y},
            "width": w, "height": h,
            "data": {"tipo": tipo, "codigo": codigo, "nome": nome, "vao": "", "rotacao": 0,
                     "largura": w, "altura": h},
        })
        return codigo.lower()

    def lig(a, ta, b, tb):
        edges.append({"id": f"l-{a}-{ta}-{b}-{tb}", "type": "smoothstep",
                      "source": a, "sourceHandle": ta, "target": b, "targetHandle": tb})

    def cadeia(x, y0, vao, itens, bar_topo, bar_base_term):
        """Encadeia equipamentos (eq) e junções (cx) entre dois barramentos."""
        y = y0
        anterior = None  # (id, terminal_de_saida)
        for item in itens:
            if item[0] == "eq":
                _, tipo, codigo, nome = item
                h = DIMS[tipo][1]
                cid = no(tipo, codigo, x, y, nome)
                if anterior is None:
                    lig(bar_topo, bar_base_term, cid, "T1")
                else:
                    lig(anterior[0], anterior[1], cid, "T1")
                anterior = (cid, "T2")
                y += h + 14
            else:
                _, codigo_j, codigo_terra, nome_terra = item
                cid = no("CONEXAO", codigo_j, x + 12, y, f"Juncao {vao}")
                lig(anterior[0], anterior[1], cid, "B1")
                tid = no("SECCIONADORA_ATERRAMENTO", codigo_terra, x + 70, y - 12, nome_terra)
                lig(cid, "B3", tid, "T1")
                anterior = (cid, "B2")
                y += 30
        return anterior, y

    # Barramentos de 500 kV
    bar_a = no("BARRAMENTO", "BAR500A", 60, 40, "Barramento 500 kV A", largura=900)
    no("ETIQUETA_VAO", "VAO_G", 150, 12, "Vao G")
    no("ETIQUETA_VAO", "VAO_H", 600, 12, "Vao H")

    itens_g = [
        ("eq", "SECCIONADORA", "35E7-4", "Secc. 35E7-4"),
        ("eq", "DISJUNTOR", "15E7", "Disjuntor 15E7"),
        ("eq", "REATOR", "95E7", "Reator de linha 95E7 (3+1R) 50 MVAr"),
        ("eq", "SECCIONADORA", "35E7-5", "Secc. 35E7-5"),
        ("cx", "J_E7", "75E7-1", "Aterr. 75E7-1"),
        ("eq", "SECCIONADORA", "35D7-1", "Secc. 35D7-1"),
        ("eq", "DISJUNTOR", "15D7", "Disjuntor 15D7"),
        ("eq", "REATOR", "95D7", "Reator de linha 95D7"),
        ("eq", "SECCIONADORA", "35D7-2", "Secc. 35D7-2"),
        ("cx", "J_C2", "75C2", "Aterr. 75C2"),
        ("eq", "SECCIONADORA", "35C2-5", "Secc. 35C2-5"),
        ("eq", "REATOR", "95C2", "Reator de linha 95C2"),
        ("eq", "DISJUNTOR", "15C2", "Disjuntor 15C2"),
        ("eq", "SECCIONADORA", "35C2-4", "Secc. 35C2-4"),
    ]
    itens_h = [
        ("eq", "SECCIONADORA", "35E9-4", "Secc. 35E9-4"),
        ("eq", "DISJUNTOR", "15E9", "Disjuntor 15E9"),
        ("eq", "REATOR", "95E9", "Reator de linha 95E9"),
        ("eq", "SECCIONADORA", "35E9-5", "Secc. 35E9-5"),
        ("cx", "J_E9", "75E9-1", "Aterr. 75E9-1"),
        ("eq", "SECCIONADORA", "35D8-1", "Secc. 35D8-1"),
        ("eq", "DISJUNTOR", "15D8", "Disjuntor 15D8"),
        ("eq", "REATOR", "95D8", "Reator de linha 95D8"),
        ("eq", "SECCIONADORA", "35D8-2", "Secc. 35D8-2"),
        ("cx", "J_C4", "75C4", "Aterr. 75C4"),
        ("eq", "SECCIONADORA", "35C4-5", "Secc. 35C4-5"),
        ("eq", "REATOR", "95C4", "Reator de linha 95C4"),
        ("eq", "DISJUNTOR", "15C4", "Disjuntor 15C4"),
        ("eq", "SECCIONADORA", "35C4-4", "Secc. 35C4-4"),
    ]

    fim_g, y_fim = cadeia(180, 110, "G", itens_g, bar_a, "B4")
    fim_h, y_fim_h = cadeia(600, 110, "H", itens_h, bar_a, "B4")
    y_base = max(y_fim, y_fim_h) + 60

    bar_b = no("BARRAMENTO", "BAR500B", 60, y_base, "Barramento 500 kV B", largura=900)
    lig(fim_g[0], fim_g[1], bar_b, "B3")
    lig(fim_h[0], fim_h[1], bar_b, "B3")
    no("ETIQUETA_VAO", "LT_C2", 180, y_base + 16, "LT Bom Jesus da Lapa II C2")
    no("ETIQUETA_VAO", "LT_C3", 600, y_base + 16, "LT Bom Jesus da Lapa II C3")

    # Ramos de reator de barra na base do barramento B
    def ramo(x, sec, cx_id, reator, terra_reator, nome_reator, terra_secc):
        y = y_base + 60
        s = no("SECCIONADORA", sec, x, y, f"Secc. {sec}")
        j = no("CONEXAO", f"J_{sec}", x + 12, y + 90, f"Juncao {sec}")
        lig(bar_b, "B4", s, "T1")
        lig(s, "T2", j, "B1")
        t1 = no("SECCIONADORA_ATERRAMENTO", terra_secc, x + 70, y + 84, f"Aterr. {terra_secc}")
        lig(j, "B3", t1, "T1")
        r = no("REATOR", reator, x, y + 140, nome_reator)
        lig(j, "B2", r, "T1")
        t2 = no("SECCIONADORA_ATERRAMENTO", terra_reator, x + 70, y + 250, f"Aterr. {terra_reator}")
        lig(r, "T2", t2, "T1")

    ramo(180, "35C2-7", None, "05E6", "75E6-2", "Reator de barra 05E6 (3+1R) 66 MVAr", "75C2-2")
    ramo(600, "35C4-7", None, "05E8", "75E8-2", "Reator de barra 05E8 (3+1R) 66 MVAr", "75C4-2")

    return {"nodes": nodes, "edges": edges}


def validar(diagrama):
    ids = {n["id"]: n["data"]["tipo"] for n in diagrama["nodes"]}
    assert len(ids) == len(diagrama["nodes"]), "ids duplicados"
    erros = []
    graus = {}
    for e in diagrama["edges"]:
        for no_id, term in ((e["source"], e["sourceHandle"]), (e["target"], e["targetHandle"])):
            tipo = ids.get(no_id)
            if tipo is None:
                erros.append(f"no inexistente {no_id}")
                continue
            validos = TERM_BARRA if tipo in ("BARRAMENTO", "CONEXAO", "ETIQUETA_VAO") else TERM_EQ
            if term not in validos:
                erros.append(f"terminal {term} invalido em {no_id} ({tipo})")
            graus[(no_id, term)] = graus.get((no_id, term), 0) + 1
            if tipo not in ("BARRAMENTO", "CONEXAO", "ETIQUETA_VAO") and graus[(no_id, term)] > MAX_EQ:
                erros.append(f"terminal {term} de {no_id} com mais de {MAX_EQ} ligacao")
    if erros:
        raise SystemExit("Diagrama invalido:\n  " + "\n  ".join(erros[:20]))


def main():
    id_sub = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    login()
    diagrama = construir()
    validar(diagrama)
    r = SESSAO.put(f"{BASE}/unifilar/diagrama/{id_sub}", json=diagrama, timeout=60)
    r.raise_for_status()
    salvo = r.json()
    print(f"Arranjo 500 kV salvo na subestacao {id_sub}: {len(salvo['nodes'])} nos, {len(salvo['edges'])} ligacoes.")


if __name__ == "__main__":
    main()
