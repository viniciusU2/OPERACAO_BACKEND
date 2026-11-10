"""Diagrama unifilar 500 kV (disjuntor e meio, vaos G e H) da SE GOR, com ativos reais.

Os componentes sao lidos do cadastro de ativos da propria subestacao (id 2,
SE GOR). Cada componente recebe o tipo cadastrado (Disjuntor, Seccionadora,
Reator Derivacao -> REATOR, Transformador de Corrente -> TC, TPC, Para-Raios)
e o id_ativo do registro da fase AZ (ou a primeira fase disponivel).

Uso:
    ENGVI_SEED_TOKEN=<token> python scripts/seed_unifilar_gor_500kv.py
"""

import os
import sys

import requests

BASE = "http://127.0.0.1:8000"
SE_GOR = 2
SESSAO = requests.Session()

TIPO_POR_CADASTRO = {
    "Disjuntor": "DISJUNTOR",
    "Seccionadora": "SECCIONADORA",
    "Reator Derivação": "REATOR",
    "Transformador de Corrente": "TC",
    "Transformador de Potencial Capacitivo": "TPC",
    "Para-Raios": "PARA_RAIOS",
}
DIMS = {
    "BARRAMENTO": (900, 10), "DISJUNTOR": (44, 72), "SECCIONADORA": (40, 72),
    "REATOR": (44, 110), "TC": (32, 108), "TPC": (44, 104), "PARA_RAIOS": (40, 96),
    "CONEXAO": (16, 16), "ETIQUETA_VAO": (110, 26),
}
TERM_BARRA = ("B1", "B2", "B3", "B4")
TERM_EQ = ("T1", "T2")

# Sequencias de cada vao, de cima para baixo. ("eq", codigo) ou
# ("cx", id_junção, codigo_para_raios) para um ponto de conexao com aterramento.
VAO_G = [
    ("eq", "35E7-4"), ("eq", "15E7"), ("eq", "05E7"), ("eq", "35E7-5"),
    ("cx", "J_E7", "75E7-1"),
    ("eq", "35D7-1"), ("eq", "15D7"), ("eq", "95D7"), ("eq", "35D7-2"),
    ("eq", "35C2-5"), ("eq", "95C2"), ("eq", "15C2"), ("eq", "35C2-4"),
]
VAO_H = [
    ("eq", "35E9-4"), ("eq", "15E9"), ("eq", "05E9"), ("eq", "35E9-5"),
    ("cx", "J_E9", "75E9-1"),
    ("eq", "35D8-1"), ("eq", "15D8"), ("eq", "95D8"), ("eq", "35D8-2"),
    ("eq", "35C4-5"), ("eq", "95C4"), ("eq", "15C4"), ("eq", "35C4-4"),
]
RAMO_C2 = dict(sec="35C2-7", junc="J_C2", pr_junc="75C2", reator_seq=["35E6-8", "05E6"], pr_fim="75E6-2", tpc="85C2")
RAMO_C4 = dict(sec="35C4-7", junc="J_C4", pr_junc="75C4", reator_seq=["35E8-8", "05E8"], pr_fim="75E8-2", tpc="85C4")


def login():
    token = os.getenv("ENGVI_SEED_TOKEN", "")
    if not token:
        raise SystemExit("Defina ENGVI_SEED_TOKEN.")
    SESSAO.headers["Authorization"] = f"Bearer {token}"


def carregar_cadastro():
    """Indexa os ativos da SE GOR por codigo, escolhendo a fase AZ quando houver."""
    ativos = SESSAO.get(f"{BASE}/ativos/{SE_GOR}", timeout=60).json()
    por_codigo = {}
    for a in ativos:
        codigo = a["codigo_ativo"]
        fase = (a.get("fase") or "").upper()
        atual = por_codigo.get(codigo)
        if atual is None or (fase == "AZ" and (atual.get("fase") or "").upper() != "AZ"):
            por_codigo[codigo] = a
    return por_codigo


def construir(cadastro):
    nodes, edges, erros = [], [], []
    usados = set()

    def no_ativo(codigo, x, y):
        a = cadastro.get(codigo)
        if a is None:
            erros.append(f"ativo {codigo} nao existe na SE GOR")
            return None
        tipo = TIPO_POR_CADASTRO.get((a.get("tipo_ativo") or {}).get("nome"))
        if tipo is None:
            erros.append(f"tipo de {codigo} sem equivalente no unifilar")
            return None
        if a["id_ativo"] in usados:
            erros.append(f"ativo {codigo} usado mais de uma vez")
            return None
        usados.add(a["id_ativo"])
        return no(tipo, codigo, x, y, "",
                  id_ativo=a["id_ativo"], vao=a.get("bay") or "")

    def no(tipo, codigo, x, y, nome="", id_ativo=None, vao=""):
        w, h = DIMS.get(tipo, (40, 72))
        identificador = codigo.lower()
        nodes.append({
            "id": identificador, "type": "noUnifilar", "position": {"x": x, "y": y},
            "width": w, "height": h,
            "data": {"tipo": tipo, "codigo": codigo, "nome": nome, "vao": vao, "rotacao": 0,
                     "largura": w, "altura": h, "id_ativo": id_ativo},
        })
        return identificador

    def lig(a, ta, b, tb):
        edges.append({"id": f"l-{a}-{ta}-{b}-{tb}", "type": "smoothstep",
                      "source": a, "sourceHandle": ta, "target": b, "targetHandle": tb})

    def cadeia(x, y0, sequencia, barra_topo):
        y = y0
        anterior = None
        for item in sequencia:
            if item[0] == "eq":
                cid = no_ativo(item[1], x, y)
                if cid is None:
                    continue
                if anterior is None:
                    lig(barra_topo, "B4", cid, "T1")
                else:
                    lig(anterior[0], anterior[1], cid, "T1")
                anterior = (cid, "T2")
                y += DIMS[TIPO_POR_CADASTRO.get((cadastro.get(item[1], {}).get("tipo_ativo") or {}).get("nome"), "SECCIONADORA")][1] + 14
            else:
                _, jid, terra = item
                cx = no("CONEXAO", jid, x + 12, y, f"Juncao {jid}")
                lig(anterior[0], anterior[1], cx, "B1")
                pr = no_ativo(terra, x + 70, y - 12)
                if pr:
                    lig(cx, "B3", pr, "T1")
                anterior = (cx, "B2")
                y += 30
        return anterior, y

    barra_a = no("BARRAMENTO", "BAR500A", 60, 40, "Barramento 500 kV A")
    no("ETIQUETA_VAO", "VAO_G", 150, 12, "Vao G", vao="GX")
    no("ETIQUETA_VAO", "VAO_H", 600, 12, "Vao H", vao="HX")

    fim_g, y_g = cadeia(180, 110, VAO_G, barra_a)
    fim_h, y_h = cadeia(600, 110, VAO_H, barra_a)
    y_base = max(y_g, y_h) + 80

    barra_b = no("BARRAMENTO", "BAR500B", 60, y_base, "Barramento 500 kV B")
    if fim_g:
        lig(fim_g[0], fim_g[1], barra_b, "B3")
    if fim_h:
        lig(fim_h[0], fim_h[1], barra_b, "B3")

    def ramo(x, r):
        y = y_base + 60
        sec = no_ativo(r["sec"], x, y)
        if sec is None:
            return
        lig(barra_b, "B4", sec, "T1")
        cx = no("CONEXAO", r["junc"], x + 12, y + 90, f"Juncao {r['junc']}")
        lig(sec, "T2", cx, "B1")
        pr = no_ativo(r["pr_junc"], x + 70, y + 84)
        if pr:
            lig(cx, "B3", pr, "T1")
        tpc = no_ativo(r["tpc"], x + 70, y + 130)
        if tpc:
            lig(cx, "B4", tpc, "T1")
        anterior = (cx, "B2")
        yy = y + 150
        for codigo in r["reator_seq"]:
            cid = no_ativo(codigo, x, yy)
            if cid is None:
                return
            lig(anterior[0], anterior[1], cid, "T1")
            anterior = (cid, "T2")
            yy += 130
        fim = no_ativo(r["pr_fim"], x + 70, yy - 40)
        if fim:
            lig(anterior[0], anterior[1], fim, "T1")

    ramo(180, RAMO_C2)
    ramo(600, RAMO_C4)

    return {"nodes": nodes, "edges": edges}, erros


def validar(diagrama):
    ids = {n["id"]: n["data"]["tipo"] for n in diagrama["nodes"]}
    assert len(ids) == len(diagrama["nodes"]), "ids duplicados"
    erros, graus, ativos = [], {}, set()
    for n in diagrama["nodes"]:
        ativo = n["data"].get("id_ativo")
        if ativo is not None:
            if ativo in ativos:
                erros.append(f"ativo {ativo} repetido")
            ativos.add(ativo)
    for e in diagrama["edges"]:
        for no_id, term in ((e["source"], e["sourceHandle"]), (e["target"], e["targetHandle"])):
            tipo = ids.get(no_id)
            if tipo is None:
                erros.append(f"no inexistente {no_id}")
                continue
            barramento = tipo in ("BARRAMENTO", "CONEXAO", "ETIQUETA_VAO")
            if term not in (TERM_BARRA if barramento else TERM_EQ):
                erros.append(f"terminal {term} invalido em {no_id} ({tipo})")
            if not barramento:
                graus[(no_id, term)] = graus.get((no_id, term), 0) + 1
                if graus[(no_id, term)] > 1:
                    erros.append(f"terminal {term} de {no_id} com mais de 1 ligacao")
    if erros:
        raise SystemExit("Diagrama invalido:\n  " + "\n  ".join(erros[:25]))


def main():
    login()
    cadastro = carregar_cadastro()
    diagrama, erros = construir(cadastro)
    if erros:
        raise SystemExit("Cadastro incompleto para o arranjo:\n  " + "\n  ".join(erros))
    validar(diagrama)
    r = SESSAO.put(f"{BASE}/unifilar/diagrama/{SE_GOR}", json=diagrama, timeout=60)
    r.raise_for_status()
    salvo = r.json()
    com_ativo = sum(1 for n in salvo["nodes"] if n["data"].get("id_ativo"))
    print(f"SE GOR: {len(salvo['nodes'])} nos ({com_ativo} vinculados a ativos), {len(salvo['edges'])} ligacoes.")


if __name__ == "__main__":
    main()
