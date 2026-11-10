"""Seed do diagrama unifilar 'Disjuntor e Meio' com reatores de barra e linha.

Cria um diagrama representativo de um arranjo de disjuntor e meio
(breaker-and-a-half) para uma subestacao, com dois barramentos
principais, tres baias (Linha A, Linha B, Acoplador), reator de barra
e reator de linha.

Uso:
    ENGVI_SEED_TOKEN=<token> python scripts/seed_unifilar_disjuntor_meio.py [id_subestacao]

Por padrao usa a subestacao 1 (SE BJD).
"""

import os
import sys

import requests

BASE = "http://127.0.0.1:8000"
SESSAO = requests.Session()


def login():
    token = os.getenv("ENGVI_SEED_TOKEN", "")
    if token:
        SESSAO.headers["Authorization"] = f"Bearer {token}"
        return
    email = os.getenv("ENGVI_SEED_EMAIL", "")
    senha = os.getenv("ENGVI_SEED_SENHA", "")
    if not email or not senha:
        raise SystemExit("Defina ENGVI_SEED_TOKEN ou ENGVI_SEED_EMAIL/ENGVI_SEED_SENHA.")
    r = SESSAO.post(BASE + "/login", json={"email": email, "senha": senha}, timeout=30)
    r.raise_for_status()
    SESSAO.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


TERMINAIS = {
    "BARRAMENTO": ("B1", "B2", "B3", "B4"),
    "CONEXAO": ("B1", "B2", "B3", "B4"),
    "ETIQUETA_VAO": ("B1", "B2", "B3", "B4"),
}


def terminais(tipo):
    return TERMINAIS.get(tipo, ("T1", "T2"))


def construir_diagrama():
    nodes = []
    edges = []

    def add(tipo, codigo, x, y, nome="", vao="", rotacao=0, largura=None):
        dims = {
            "BARRAMENTO": (200, 10), "DISJUNTOR": (44, 72),
            "SECCIONADORA": (40, 72), "TC": (32, 108),
            "TP": (44, 88), "REATOR": (44, 110),
            "ETIQUETA_VAO": (110, 26), "CONEXAO": (16, 16),
            "PARA_RAIOS": (40, 96),
        }
        w, h = dims.get(tipo, (40, 72))
        if largura is not None:
            w = largura
        nodes.append({
            "id": codigo.lower(),
            "type": "noUnifilar",
            "position": {"x": x, "y": y},
            "width": w,
            "height": h,
            "data": {
                "tipo": tipo,
                "codigo": codigo,
                "nome": nome,
                "vao": vao,
                "rotacao": rotacao,
                "largura": w,
                "altura": h,
            },
        })

    def ligar(origem, to, destino, td, eid=None):
        o = origem.lower()
        d = destino.lower()
        edges.append({
            "id": eid or f"l-{o}-{to}-{d}-{td}",
            "type": "smoothstep",
            "source": o,
            "sourceHandle": to,
            "target": d,
            "targetHandle": td,
        })

    # ------------------------------------------------------------------ #
    # Barramentos principais
    # ------------------------------------------------------------------ #
    add("BARRAMENTO", "BAR1", 60, 50, nome="Barramento 1 - 138 kV", largura=800)
    add("BARRAMENTO", "BAR2", 60, 560, nome="Barramento 2 - 138 kV", largura=800)

    # Etiquetas de vao
    add("ETIQUETA_VAO", "VAO_A", 80, 10, nome="Linha A")
    add("ETIQUETA_VAO", "VAO_B", 320, 10, nome="Linha B")
    add("ETIQUETA_VAO", "VAO_C", 560, 10, nome="Acoplador")

    # ------------------------------------------------------------------ #
    # Reator de barra (conectado ao Barramento 1)
    # ------------------------------------------------------------------ #
    add("SECCIONADORA", "SEC_RB", 720, 70, nome="Secc. reator de barra")
    add("REATOR", "REA_B", 720, 170, nome="Reator de barra")
    add("CONEXAO", "CX_RB", 720, 290, nome="Aterramento reator de barra")
    ligar("BAR1", "B2", "SEC_RB", "T1", "l-bar1-secrb")
    ligar("SEC_RB", "T2", "REA_B", "T1", "l-secrb-reab")
    ligar("REA_B", "T2", "CX_RB", "B1", "l-reab-aterr")

    # ------------------------------------------------------------------ #
    # Baias: Linha A, Linha B, Acoplador
    # ------------------------------------------------------------------ #
    baias = [("A", 100), ("B", 340), ("C", 580)]
    for letra, x in baias:
        add("SECCIONADORA", f"SEC1{letra}", x, 90, nome=f"Secc. superior {letra}")
        add("DISJUNTOR", f"DJ{letra}", x + 8, 190, nome=f"Disjuntor {letra}")
        add("SECCIONADORA", f"SEC2{letra}", x, 300, nome=f"Secc. inferior {letra}")

        # Juncao principal entre seccionadora superior e disjuntor
        add("CONEXAO", f"CX{letra}", x + 8, 140, nome=f"Juncao principal {letra}")
        ligar("BAR1", "B3", f"SEC1{letra}", "T1", f"l-bar1-sec1{letra}")
        ligar(f"SEC1{letra}", "T2", f"CX{letra}", "B1", f"l-sec1{letra}-cx{letra}")
        ligar(f"CX{letra}", "B2", f"DJ{letra}", "T1", f"l-cx{letra}-dj{letra}")
        ligar(f"DJ{letra}", "T2", f"SEC2{letra}", "T1", f"l-dj{letra}-sec2{letra}")
        ligar(f"SEC2{letra}", "T2", "BAR2", "B3", f"l-sec2{letra}-bar2")

        # TC e TP na saida da linha (apenas Linha A e B)
        if letra in ("A", "B"):
            add("TC", f"TC{letra}", x + 60, 90, nome=f"TC {letra}")
            add("TP", f"TP{letra}", x + 60, 210, nome=f"TP {letra}")
            # Juncao TC: conecta em paralelo via juncao principal
            add("CONEXAO", f"CXT{letra}", x + 50, 140, nome=f"Juncao TC {letra}")
            ligar(f"CX{letra}", "B3", f"CXT{letra}", "B1", f"l-cx{letra}-cxt{letra}")
            ligar(f"CXT{letra}", "B2", f"TC{letra}", "T1", f"l-cxt{letra}-tc{letra}")
            ligar(f"TC{letra}", "T2", f"TP{letra}", "T1", f"l-tc{letra}-tp{letra}")

            # Reator de linha
            add("SECCIONADORA", f"SECRL{letra}", x + 120, 90, nome=f"Secc. reator de linha {letra}")
            add("REATOR", f"REA_L{letra}", x + 120, 180, nome=f"Reator de linha {letra}")
            add("CONEXAO", f"CXRL{letra}", x + 110, 140, nome=f"Juncao reator {letra}")
            ligar(f"CXT{letra}", "B3", f"CXRL{letra}", "B1", f"l-cxt{letra}-cxrl{letra}")
            ligar(f"CXRL{letra}", "B2", f"SECRL{letra}", "T1", f"l-cxrl{letra}-secrl{letra}")
            ligar(f"SECRL{letra}", "T2", f"REA_L{letra}", "T1", f"l-secrl{letra}-real{letra}")
            add("CONEXAO", f"CX_RL{letra}", x + 120, 300, nome=f"Aterramento reator de linha {letra}")
            ligar(f"REA_L{letra}", "T2", f"CX_RL{letra}", "B1", f"l-real{letra}-aterr")

    # ------------------------------------------------------------------ #
    # Para-raios em cada barramento
    # ------------------------------------------------------------------ #
    for x in (30, 270, 510):
        add("PARA_RAIOS", f"PR1_{x}", x, 10, nome="Para-raios Barramento 1")
        ligar("BAR1", "B3", f"PR1_{x}", "T1", f"l-bar1-pr1_{x}")

    return {"nodes": nodes, "edges": edges}


def main():
    id_subestacao = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    login()
    diagrama = construir_diagrama()
    r = SESSAO.put(f"{BASE}/unifilar/diagrama/{id_subestacao}", json=diagrama, timeout=60)
    r.raise_for_status()
    salvo = r.json()
    print(f"Diagrama 'Disjuntor e Meio' salvo na subestacao {id_subestacao}.")
    print(f"  Nos: {len(salvo.get('nodes', []))}")
    print(f"  Ligacoes: {len(salvo.get('edges', []))}")


if __name__ == "__main__":
    main()
