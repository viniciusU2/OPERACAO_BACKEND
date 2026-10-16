"""Populacao de dados do modulo ENGVI Protecao (Fases 1 a 5).

Estrategia: usa a API real (mesmos caminhos/validacoes da aplicacao).
Os IEDs sao vinculados a ativos de 'Rele de Protecao' da SE 2 (GOR).
Idempotente por TAG de IED: reexecucao nao duplica os IEDs ja criados.

Os dados NAO buscam fidelidade topologica (conforme solicitado) - apenas
produzem um conjunto coerente e realista para navegacao e testes.
"""

import json
import random
import sys
from datetime import date, datetime, timedelta

import os

import requests

BASE = "http://127.0.0.1:8000"
EP = BASE + "/engenharia-protecao"
SE_GOR = 2

random.seed(20261016)

SESSAO = requests.Session()
ERROS = []
RESUMO = {}


def log(chave, qtd=1):
    RESUMO[chave] = RESUMO.get(chave, 0) + qtd


def req(metodo, url, **kw):
    r = SESSAO.request(metodo, url, timeout=90, **kw)
    if r.status_code >= 400:
        ERROS.append((metodo, url.replace(BASE, ""), r.status_code, r.text[:220]))
        return None
    if r.status_code == 204 or not r.content:
        return {}
    try:
        return r.json()
    except ValueError:
        return {}


def dia(inicio, fim):
    return (inicio + timedelta(days=random.randint(0, (fim - inicio).days))).isoformat()


HOJE = date(2026, 10, 16)
D0 = date(2025, 1, 1)
D1 = HOJE


# --------------------------------------------------------------------------- #
# Login e catalogos de apoio
# --------------------------------------------------------------------------- #

def login():
    email = os.getenv("ENGVI_SEED_EMAIL", "")
    senha = os.getenv("ENGVI_SEED_SENHA", "")
    if not email or not senha:
        raise SystemExit("Defina ENGVI_SEED_EMAIL e ENGVI_SEED_SENHA para rodar o seed.")
    r = SESSAO.post(BASE + "/login", json={"email": email, "senha": senha})
    r.raise_for_status()
    SESSAO.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


def carregar_ativos_gor():
    ativos = SESSAO.get(BASE + f"/ativos/{SE_GOR}").json()
    pools = {5: [], 3: [], 6: [], 7: [], 10: [], 35: [], 32: [], 36: []}
    for a in ativos:
        pools.setdefault(a["id_tipo_ativo"], []).append(a["id_ativo"])
    return pools


def garantir_modelos(necessarios):
    existentes = {
        (m["fabricante"], m["modelo"]): m["id_modelo_ied"]
        for m in req("get", EP + "/modelos?somente_ativos=false&page_size=200")["items"]
    }
    novos = [
        ("ABB", "REL670", "SIPROTEC/670", "Proteção de distância e diferencial de linha", "AB"),
        ("ABB", "RET670", "670", "Diferencial de transformador", "AB"),
        ("SEL", "SEL-421", "SEL-4xx", "Proteção de distância de linha", "SE"),
        ("GE", "T60", "UR", "Diferencial de transformador", "GE"),
        ("GE", "D60", "UR", "Proteção de distância de linha", "GE"),
    ]
    for fab, mod, fam, apl, _ in novos:
        if (fab, mod) not in existentes:
            criado = req("post", EP + "/modelos", json={"fabricante": fab, "modelo": mod, "familia": fam, "aplicacao": apl})
            if criado:
                existentes[(fab, mod)] = criado["id_modelo_ied"]
                log("modelos")
    return existentes


# --------------------------------------------------------------------------- #
# Definicao dos IEDs
# --------------------------------------------------------------------------- #

IEDS = [
    dict(tag="21C2-GOR", fab="ABB", mod="REL670", painel="PA-01", hw="V4.1",
         funcoes=[1, 4, 14], equip=["DISJ", "TC"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION"), ("ETH-PB", "PROCESS_BUS", "PROCESS")],
         goose=[("GCB_TRIP_C2", "PUBLICADO")], circuitos=3, sinais=6, ensaios=2,
         ocorrencias=[("ATUACAO_PROTECAO", "ALTA"), ("OSCILACAO", "MEDIA")], oscil=2, relatorios=1,
         alteracao="VALIDADA"),
    dict(tag="21C3-GOR", fab="ABB", mod="REL670", painel="PA-01", hw="V4.1",
         funcoes=[1, 4], equip=["DISJ"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=2, sinais=4, ensaios=1,
         ocorrencias=[("ALARME", "BAIXA")], oscil=1, relatorios=1, alteracao="IMPLANTADA"),
    dict(tag="87L-C2-GOR", fab="SEL", mod="SEL-421", painel="PA-02", hw="V3.0",
         funcoes=[22, 1], equip=["DISJ", "TC"],
         interfaces=[("ETH-PB", "PROCESS_BUS", "PROCESS"), ("ETH-ST", "ETHERNET", "STATION")],
         goose=[("GCB_87L_C2", "PUBLICADO"), ("GCB_RECV_C2", "ASSINADO")],
         circuitos=2, sinais=5, ensaios=2, ocorrencias=[("DISPARO", "CRITICA")], oscil=1, relatorios=1,
         alteracao="SUBMETIDA"),
    dict(tag="87T-AT1-GOR", fab="Siemens", mod="7UT85", painel="PA-03", hw="V4.6",
         funcoes=[23, 8, 24], equip=["DISJ", "TC"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=2, sinais=4, ensaios=1,
         ocorrencias=[("SOBRECORRENTE", "ALTA")], oscil=0, relatorios=1, alteracao="RASCUNHO"),
    dict(tag="87T-AT2-GOR", fab="GE", mod="T60", painel="PA-03", hw="V7.2",
         funcoes=[23], equip=["DISJ"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=1, sinais=3, ensaios=1,
         ocorrencias=[], oscil=0, relatorios=1, alteracao=None),
    dict(tag="87B-B1-GOR", fab="Siemens", mod="7VK87", painel="PA-05", hw="V2.3",
         funcoes=[24], equip=[],
         interfaces=[("ETH-PB", "PROCESS_BUS", "PROCESS")], goose=[("GCB_87B_B1", "PUBLICADO")],
         circuitos=1, sinais=3, ensaios=0, ocorrencias=[], oscil=0, relatorios=0, alteracao=None),
    dict(tag="51C2-GOR", fab="Siemens", mod="7SJ85", painel="PA-04", hw="V5.0",
         funcoes=[12, 9, 10, 8], equip=["DISJ", "TC"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=2, sinais=5, ensaios=1,
         ocorrencias=[("SOBRECORRENTE", "MEDIA"), ("ALARME", "BAIXA")], oscil=1, relatorios=1,
         alteracao="VALIDADA"),
    dict(tag="51N-C3-GOR", fab="Siemens", mod="7SJ85", painel="PA-04", hw="V5.0",
         funcoes=[13, 10], equip=["TC"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=1, sinais=3, ensaios=1,
         ocorrencias=[("FALTA_ENERGIA", "ALTA")], oscil=0, relatorios=0, alteracao=None),
    dict(tag="79C2-GOR", fab="Siemens", mod="7SL87", painel="PA-06", hw="V3.4",
         funcoes=[19, 3], equip=["DISJ"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[("GCB_79_C2", "PUBLICADO")],
         circuitos=2, sinais=4, ensaios=1, ocorrencias=[("REARME", "MEDIA")], oscil=1, relatorios=1,
         alteracao="APROVADA"),
    dict(tag="27C2-GOR", fab="GE", mod="D60", painel="PA-06", hw="V7.2",
         funcoes=[4, 14, 20], equip=["DISJ"],
         interfaces=[("ETH-ST", "ETHERNET", "STATION")], goose=[], circuitos=1, sinais=3, ensaios=0,
         ocorrencias=[], oscil=0, relatorios=1, alteracao=None),
]

TIPOS_CIRCUITO = ["TRIP", "FECHAMENTO", "SINALIZACAO", "ALARME", "BLOQUEIO", "SUPERVISAO", "MEDICAO"]
MOTIVOS_CONFIG = ["BACKUP_PERIODICO", "ALTERACAO_AJUSTE", "PRE_MANUTENCAO", "POS_MANUTENCAO", "POS_FIRMWARE"]
TIPOS_INTERFACE_PROTO = {
    "STATION": [("IEC61850_MMS", "SERVIDOR", "102"), ("SNTP", "CLIENTE", "123")],
    "PROCESS": [("IEC61850_GOOSE", "PUBLICADOR", None), ("IEC61850_SV", "PUBLICADOR", None)],
}
SINAIS_POR_TIPO = {
    "DIGITAL_ENTRADA": ["Fechamento do disjuntor", "Abertura do disjuntor", "Falha de disjuntor", "Rele de gás"],
    "DIGITAL_SAIDA": ["Trip A", "Trip B", "Trip C", "Alarme geral"],
    "ANALOGICA_ENTRADA": ["Corrente IA", "Corrente IB", "Corrente IC", "Tensão VA", "Tensão VB"],
    "ANALOGICA_SAIDA": ["Corrente de trip", "Sinal de sincronismo"],
}


# --------------------------------------------------------------------------- #
# Populacao de cada IED
# --------------------------------------------------------------------------- #

def params_da_funcao(id_funcao):
    return req("get", EP + f"/parametros-definicao?id_funcao_ansi={id_funcao}") or []


def valor_padrao(parametro):
    tipo = parametro.get("tipo_dado")
    if tipo == "NUMERICO":
        return f"{random.choice([1, 2, 5, 10, 20, 50])}.{random.randint(0, 9)}"
    if tipo == "TEMPO":
        return f"{random.choice([0.05, 0.1, 0.3, 0.5, 1, 2])}"
    if tipo == "BOOLEANO":
        return random.choice(["true", "false"])
    return random.choice(["IEC Normal Inverse", "IEC Very Inverse", "Definite Time"])


def popular_ied(cfg, id_modelo, ativos_por_tipo):
    existente = req("get", EP + f"/ieds?busca={cfg['tag']}&page_size=5")
    if existente and any(i["tag_operacional"] == cfg["tag"] for i in existente["items"]):
        print(f"  [skip] {cfg['tag']} ja existe")
        return

    # equipo(s) protegido(s): escolhe ativos do tipo, rotacionando para nao repetir
    equipos = []
    for i, tipo in enumerate(cfg["equip"]):
        pool = ativos_por_tipo["DISJ"] if tipo == "DISJ" else ativos_por_tipo["TC"]
        if not pool:
            continue
        equipos.append((pool.pop(0), i == 0, tipo))

    ied = req("post", EP + "/ieds", json={
        "tag_operacional": cfg["tag"],
        "id_ativo": ativos_por_tipo["RELE"].pop(),
        "id_modelo_ied": id_modelo,
        "id_subestacao": SE_GOR,
        "painel_instalacao": cfg["painel"],
        "numero_serie": f"{cfg['fab'][:2].upper()}{random.randint(10**8, 10**9 - 1)}",
        "codigo_produto": f"{cfg['mod']}-{random.randint(100, 999)}",
        "versao_hardware": cfg["hw"],
        "versao_firmware": f"{random.randint(7, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "data_instalacao": dia(date(2024, 1, 1), date(2025, 6, 30)),
        "status_operacional": random.choice(["EM_OPERACAO", "EM_OPERACAO", "EM_OPERACAO", "EM_MANUTENCAO"]),
        "observacoes_tecnicas": f"IED de proteção instalado no painel {cfg['painel']} da SE GOR.",
    })
    if not ied:
        print(f"  [ERRO] nao criou IED {cfg['tag']}")
        return
    id_ied = ied["id_ied"]
    log("ieds")
    print(f"  IED {cfg['tag']} -> id {id_ied}")

    # ----- Fase 1: modulos, firmware, equipamentos -----
    for slot, tipo_mod in [(f"A{random.randint(1, 8)}", "Modulo de E/S digital (BI/BO)"),
                           (f"M{random.randint(1, 4)}", "Modulo de medicao de corrente"),
                           (f"C{random.randint(1, 3)}", "Modulo de comunicacao Ethernet")]:
        req("post", EP + f"/ieds/{id_ied}/modulos", json={
            "tipo_modulo": tipo_mod, "slot": slot, "numero_serie": f"MOD{random.randint(10000, 99999)}",
            "versao_hardware": cfg["hw"], "status_operacional": "INSTALADO",
            "data_instalacao": dia(date(2024, 1, 1), date(2025, 6, 30)),
        })
        log("modulos")

    base_firmware = date(2024, 6, 1)
    for i, versao in enumerate([f"{random.randint(7, 8)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                                f"{random.randint(8, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}"]):
        req("post", EP + f"/ieds/{id_ied}/firmwares", json={
            "versao_firmware": versao, "data_inicio": (base_firmware + timedelta(days=180 * (i + 1))).isoformat(),
            "motivo": random.choice(["Atualização de fábrica", "Correção de defeito", "Implantação de melhoria"]),
        })
        log("firmwares")

    id_equipos = []
    for id_ativo, principal, _tipo in equipos:
        eq = req("post", EP + f"/ieds/{id_ied}/equipamentos", json={
            "id_ativo": id_ativo, "principal": principal,
            "data_inicio": dia(date(2024, 1, 1), date(2025, 6, 30)),
            "observacoes": "Equipamento protegido por este IED.",
        })
        if eq:
            id_equipos.append(eq["equipamentos"][-1]["id_ied_equipamento"] if isinstance(eq, dict) and eq.get("equipamentos") else None)
            log("equipamentos")

    # ----- Fase 2: funcoes ANSI, grupo de ajuste, configuracao -----
    for id_funcao in cfg["funcoes"]:
        req("post", EP + f"/ieds/{id_ied}/funcoes", json={
            "id_funcao_ansi": id_funcao, "instancia": 1, "habilitada": True,
            "observacoes": "Função habilitada na parametrização vigente.",
        })
        log("funcoes")

    grupo = req("post", EP + f"/ieds/{id_ied}/grupos-ajuste", json={
        "numero": 1, "nome": "Grupo A — vigente", "ativo": True,
        "descricao": "Grupo de ajuste ativo em operação.",
    })
    id_grupo = grupo["id_ied_grupo_ajuste"] if grupo else None
    log("grupos")

    if id_grupo:
        itens = []
        for id_funcao in cfg["funcoes"]:
            for p in params_da_funcao(id_funcao):
                itens.append({"id_parametro_definicao": p["id_parametro_definicao"], "valor": valor_padrao(p),
                              "ajustado_em": dia(date(2025, 1, 1), D1)})
        if itens:
            req("put", EP + f"/grupos-ajuste/{id_grupo}/parametros", json={"parametros": itens})
            log("params_ajuste", len(itens))

    for n in range(random.randint(1, 2)):
        conf = req("post", EP + f"/ieds/{id_ied}/configuracoes", json={
            "rotulo": f"Config {cfg['tag']} — {['vigente', 'pós-ajuste', 'pré-manutenção'][n % 3]}",
            "motivo": random.choice(MOTIVOS_CONFIG), "versao_digsi": f"V{random.randint(6, 9)}.{random.randint(0, 9)}",
            "versao_firmware": f"{random.randint(7, 8)}.{random.randint(0, 9)}",
            "data_coleta": dia(date(2025, 3, 1), D1), "id_grupo_ajuste": id_grupo,
            "observacoes": "Coleta automática via DIGSI/SEL.",
        })
        if not conf:
            continue
        id_conf = conf["id_ied_configuracao"]
        log("configuracoes")
        req("post", EP + f"/configuracoes/{id_conf}/arquivos",
            files={"arquivo": (f"par-{cfg['tag']}-{n}.zip", b"PK\x03\x04 parametros " + cfg['tag'].encode(), "application/zip")},
            data={"papel": "PRINCIPAL", "descricao": "Arquivo de parâmetros"})
        req("post", EP + f"/configuracoes/{id_conf}/arquivos",
            files={"arquivo": (f"{cfg['tag']}.scd", b"<?xml version='1.0'?><SCL/>", "application/xml")},
            data={"papel": "SCL", "descricao": "Descrição SCL"})
        req("post", EP + f"/configuracoes/{id_conf}/validacoes", json={
            "resultado": random.choice(["APROVADO", "APROVADO", "REPROVADO"]),
            "observacoes": "Validação de integridade e comparativo de ajustes.",
            "data_validacao": dia(date(2025, 4, 1), D1),
        })
        log("validacoes")

    # ----- Fase 3: solicitação de alteração -----
    if cfg.get("alteracao"):
        sol = req("post", EP + "/alteracoes", json={
            "titulo": f"Ajuste de proteção — {cfg['tag']}",
            "descricao": "Revisão de ajustes conforme estudo de coordenação.",
            "tipo": random.choice(["AJUSTE", "AJUSTE", "FIRMWARE", "COMUNICACAO"]),
            "prioridade": random.choice(["MEDIA", "ALTA", "ALTA", "CRITICA"]),
            "id_ied": id_ied, "id_grupo_ajuste": id_grupo,
            "justificativa": "Adequação da coordenação após ensaio de curto-circuito.",
            "data_necessidade": dia(date(2026, 1, 1), date(2026, 12, 1)),
        })
        if sol:
            id_sol = sol["id_ied_solicitacao_alteracao"] if "id_ied_solicitacao_alteracao" in sol else sol.get("id_solicitacao_alteracao")
            log("alteracoes")
            definicoes = []
            for id_funcao in cfg["funcoes"]:
                definicoes.extend(params_da_funcao(id_funcao))
            for p in random.sample(definicoes, min(2, len(definicoes))):
                req("post", EP + f"/alteracoes/{id_sol}/itens", json={
                    "id_parametro_definicao": p["id_parametro_definicao"],
                    "valor_atual": valor_padrao(p), "valor_proposto": valor_padrao(p),
                    "observacoes": "Ajuste proposto pelo estudo.",
                })
            fluxo = cfg["alteracao"]
            if fluxo != "RASCUNHO":
                req("post", EP + f"/alteracoes/{id_sol}/submeter", json={"comentario": "Solicitação submetida para análise."})
            if fluxo in ("APROVADA", "IMPLANTADA", "VALIDADA"):
                req("post", EP + f"/alteracoes/{id_sol}/aprovar", json={"comentario": "Aprovado pelo engenheiro responsável."})
            if fluxo in ("IMPLANTADA", "VALIDADA"):
                req("post", EP + f"/alteracoes/{id_sol}/implantar", json={"comentario": "Ajustes implantados em campo.", "data_implantacao": dia(date(2026, 2, 1), D1)})
            if fluxo == "VALIDADA":
                req("post", EP + f"/alteracoes/{id_sol}/validar", json={"aprovado": True, "comentario": "Ensaio pós-implantação aprovado.", "data_validacao": dia(date(2026, 3, 1), D1)})

    # ----- Fase 4: comunicação / circuito / sinais / ensaios -----
    id_interfaces = {}
    for nome, tipo, papel_tipo in cfg["interfaces"]:
        inter = req("post", EP + f"/ieds/{id_ied}/interfaces", json={
            "nome": nome, "tipo": tipo,
            "meio": "Fibra óptica" if tipo == "PROCESS_BUS" else "Cabo de rede",
            "mac_address": ":".join(f"{random.randint(0, 255):02X}" for _ in range(6)),
            "endereco_ip": f"10.{SE_GOR}.{random.randint(1, 20)}.{random.randint(2, 250)}",
            "mascara": "255.255.255.0", "gateway": f"10.{SE_GOR}.1.1",
            "vlan": str(random.choice([1, 10, 20, 100])), "velocidade": "100 Mbps", "conectada": True,
            "descricao": "Interface de comunicação do IED.",
        })
        if not inter:
            continue
        id_interfaces[nome] = inter["id_ied_interface_comunicacao"]
        log("interfaces")
        for proto, papel, porta in TIPOS_INTERFACE_PROTO[papel_tipo]:
            req("post", EP + f"/interfaces/{id_interfaces[nome]}/protocolos", json={
                "protocolo": proto, "papel": papel, "porta": porta, "habilitado": True,
                "observacoes": "Protocolo habilitado.",
            })
            log("protocolos")

    for nome_ctrl, direcao in cfg["goose"]:
        req("post", EP + f"/ieds/{id_ied}/goose", json={
            "tipo": "GOOSE", "direcao": direcao, "nome_controle": f"PROT/LLN0$GO${nome_ctrl}",
            "id_ied_interface_comunicacao": id_interfaces.get("ETH-PB"),
            "dataset": f"PROT/LLN0$ds{nome_ctrl}", "appid": f"{random.randint(0x1000, 0x3FFF):04X}",
            "mac_destino": "01:0C:CD:01:" + ":".join(f"{random.randint(0, 255):02X}" for _ in range(2)),
            "vlan": "1", "conf_rev": random.randint(1, 5), "tempo_retransmissao_ms": random.choice([2, 4, 8]),
            "habilitado": True,
        })
        log("goose")

    funcoes_ied = req("get", EP + f"/ieds/{id_ied}/funcoes") or []
    id_funcoes_ied = [f["id_ied_funcao"] for f in funcoes_ied]
    id_circuitos = []
    for n in range(cfg["circuitos"]):
        circ = req("post", EP + f"/ieds/{id_ied}/circuitos", json={
            "codigo": f"C{n + 1:02d}", "nome": f"Circuito {n + 1} de {cfg['tag']}",
            "tipo": random.choice(TIPOS_CIRCUITO),
            "id_funcao_ansi": (funcoes_ied[n % len(funcoes_ied)]["id_funcao_ansi"] if funcoes_ied else None),
            "id_ied_equipamento": (id_equipos[n % len(id_equipos)] if id_equipos else None),
            "descricao": "Circuito de proteção/controle.", "ativo": True,
        })
        if circ:
            id_circuitos.append(circ["id_ied_circuito"])
            log("circuitos")

    tipos_sinal = ["DIGITAL_ENTRADA", "DIGITAL_SAIDA", "ANALOGICA_ENTRADA"]
    for n in range(cfg["sinais"]):
        tipo_sinal = tipos_sinal[n % len(tipos_sinal)]
        descricoes = SINAIS_POR_TIPO[tipo_sinal]
        req("post", EP + f"/ieds/{id_ied}/sinais", json={
            "tipo": tipo_sinal, "mnemonico": f"{tipo_sinal[:3]}{n + 1:02d}",
            "descricao": f"{descricoes[n % len(descricoes)]} — {cfg['tag']}",
            "id_ied_circuito": (id_circuitos[n % len(id_circuitos)] if id_circuitos else None),
            "id_funcao_ansi": (funcoes_ied[n % len(funcoes_ied)]["id_funcao_ansi"] if funcoes_ied else None),
            "id_ied_equipamento": (id_equipos[n % len(id_equipos)] if id_equipos else None),
            "numero_terminal": f"X{n + 1}:{random.randint(1, 20)}",
            "unidade": "A" if "ANALOGICA" in tipo_sinal else None,
            "valor_nominal": "5 A" if "ANALOGICA" in tipo_sinal else None,
            "estado": random.choice(["COMISSIONADO", "COMISSIONADO", "PENDENTE"]),
        })
        log("sinais")

    for n in range(cfg["ensaios"]):
        ensaio = req("post", EP + f"/ieds/{id_ied}/ensaios", json={
            "titulo": f"Ensaio {['de rotina anual', 'de aceitação', 'pós-reparo', 'de comissionamento'][n % 4]} — {cfg['tag']}",
            "tipo": random.choice(["ROTINA", "ACEITACAO", "PERIODICO", "POS_REPARO", "COMISSIONAMENTO"]),
            "descricao": "Ensaio funcional com injeção secundária.",
            "data_prevista": dia(date(2026, 1, 1), date(2026, 11, 1)),
            "instrumentos": random.choice(["Maleta Doble F6150", "OMICRON CMC 356", "Megômetro"]),
            "observacoes": "Ensaio executado conforme rotina de manutenção.",
        })
        if not ensaio:
            continue
        id_ensaio = ensaio["id_ied_ensaio"]
        log("ensaios")
        for k, p in enumerate([x for f in cfg["funcoes"] for x in params_da_funcao(f)][:3]):
            req("post", EP + f"/ensaios/{id_ensaio}/itens", json={
                "descricao": f"Verificação de {p['nome']}",
                "id_funcao_ansi": None, "ordem": k + 1,
                "valor_esperado": valor_padrao(p), "valor_medido": valor_padrao(p),
                "resultado": random.choice(["APROVADO", "APROVADO", "APROVADO", "NAO_APLICAVEL"]),
            })
            log("ensaio_itens")
        req("post", EP + f"/ensaios/{id_ensaio}/arquivos",
            files={"arquivo": (f"ensaio-{cfg['tag']}-{n}.pdf", b"%PDF-1.4 ensaio " + cfg['tag'].encode(), "application/pdf")},
            data={"descricao": "Relatório de ensaio"})
        log("ensaio_arquivos")
        # conclui parte dos ensaios
        if random.random() < 0.6:
            detalhe = req("get", EP + f"/ensaios/{id_ensaio}")
            if detalhe:
                req("put", EP + f"/ensaios/{id_ensaio}", json={
                    "versao": detalhe["versao"],
                    "status": random.choice(["APROVADO", "APROVADO", "EM_ANDAMENTO"]),
                    "resultado": "Aprovado no ensaio funcional.",
                })

    # ----- Fase 5: ocorrências, oscilografias, relatórios -----
    tipos_osc = ["OSCILOGRAFIA", "PERTURBACAO", "RELIGAMENTO", "FALTA"]
    for idx, (tipo_oc, sev) in enumerate(cfg["ocorrencias"]):
        descricao = {
            "ATUACAO_PROTECAO": "Atuação da proteção em falta monofásica na linha.",
            "OSCILACAO": "Oscilação de potência detectada no sistema.",
            "ALARME": "Alarme de supervisão do IED.",
            "DISPARO": "Disparo do disjuntor associado ao IED.",
            "SOBRECORRENTE": "Sobrecorrente identificada no circuito protegido.",
            "FALTA_ENERGIA": "Perda de alimentação auxiliar do painel.",
            "REARME": "Religamento automático após atuação.",
        }.get(tipo_oc, "Ocorrência registrada no IED.")
        oc = req("post", EP + f"/ieds/{id_ied}/ocorrencias", json={
            "titulo": f"{dict(ATUACAO_PROTECAO='Atuação', OSCILACAO='Oscilação', ALARME='Alarme', DISPARO='Disparo', SOBRECORRENTE='Sobrecorrente', FALTA_ENERGIA='Falta de energia', REARME='Religamento').get(tipo_oc, 'Ocorrência')} — {cfg['tag']}",
            "tipo": tipo_oc, "severidade": sev,
            "data_hora": datetime.fromisoformat(dia(D0, D1) + f"T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}").isoformat(),
            "descricao": descricao,
            "causa_provavel": random.choice(["Descarga atmosférica", "Falha de isolamento", "Sobrecarga", "Vento forte", "A ser investigada"]),
            "acao_tomada": random.choice(["Inspeção em campo", "Análise de oscilografia", "Ajuste de proteção", ""]) or None,
        })
        if not oc:
            continue
        id_oc = oc["id_ied_ocorrencia"]
        log("ocorrencias")
        req("post", EP + f"/ocorrencias/{id_oc}/arquivos",
            files={"arquivo": (f"ocorrencia-{cfg['tag']}-{idx + 1}.pdf", b"%PDF-1.4 ocorrencia", "application/pdf")},
            data={"descricao": "Evidência da ocorrência"})
        log("ocorrencia_arquivos")

        for k in range(cfg["oscil"] if idx == 0 else 0):
            osc = req("post", EP + f"/ieds/{id_ied}/oscilografias", json={
                "nome": f"OSC-{cfg['tag']}-{k + 1:02d}", "tipo": random.choice(tipos_osc),
                "data_hora": oc["data_hora"], "duracao_ms": random.choice([500, 1000, 2500, 5000]),
                "frequencia_amostragem_hz": random.choice([4800, 9600, 20000]),
                "numero_canais": random.choice([8, 12, 16]), "origem": "Registrador de perturbações",
                "id_ocorrencia": id_oc, "observacoes": "Registro COMTRADE da ocorrência.",
            })
            if not osc:
                continue
            id_osc = osc["id_ied_oscilografia"]
            log("oscilografias")
            for ext, conteudo, mime in [("cfg", b"station,dev\nEQUIPMENT,ENGVI\n", "text/plain"),
                                        ("dat", b"\x00\x01\x02\x03\x04\x05", "application/octet-stream")]:
                req("post", EP + f"/oscilografias/{id_osc}/arquivos",
                    files={"arquivo": (f"{cfg['tag']}-{k + 1:02d}.{ext}", conteudo, mime)},
                    data={"descricao": f"Arquivo COMTRADE .{ext}"})
                log("oscilografia_arquivos")

        if random.random() < 0.7:
            detalhe = req("get", EP + f"/ocorrencias/{id_oc}")
            if detalhe:
                req("post", EP + f"/ocorrencias/{id_oc}/encerrar", json={"comentario": "Analisada e encerrada pelo engenheiro responsável."})

    for n in range(cfg["relatorios"]):
        rel = req("post", EP + f"/ieds/{id_ied}/relatorios", json={
            "titulo": f"Relatório {['de análise de ocorrência', 'de inspeção periódica', 'de manutenção preventiva'][n % 3]} — {cfg['tag']}",
            "tipo": random.choice(["OCORRENCIA", "INSPECAO", "ANALISE", "PERIODICO", "MANUTENCAO"]),
            "periodo_inicio": dia(date(2025, 6, 1), date(2026, 6, 1)),
            "periodo_fim": dia(date(2026, 7, 1), D1),
            "resumo": "Análise técnica consolidada com recomendações de manutenção.",
            "observacoes": "Documento revisado pela engenharia de proteção.",
        })
        if not rel:
            continue
        id_rel = rel["id_ied_relatorio"]
        log("relatorios")
        req("post", EP + f"/relatorios/{id_rel}/arquivos",
            files={"arquivo": (f"relatorio-{cfg['tag']}-{n + 1}.pdf", b"%PDF-1.4 relatorio tecnico", "application/pdf")},
            data={"descricao": "Relatório técnico"})
        log("relatorio_arquivos")
        detalhe = req("get", EP + f"/relatorios/{id_rel}")
        if detalhe:
            status = random.choice(["RASCUNHO", "EMITIDO", "APROVADO", "APROVADO"])
            if status != "RASCUNHO":
                detalhe = req("put", EP + f"/relatorios/{id_rel}", json={"versao": detalhe["versao"], "status": "EMITIDO"}) or detalhe
            if status == "APROVADO" and detalhe:
                req("put", EP + f"/relatorios/{id_rel}", json={"versao": detalhe["versao"], "status": "APROVADO"})


# --------------------------------------------------------------------------- #

def main():
    login()
    pools = carregar_ativos_gor()
    necessarios = {(c["fab"], c["mod"]) for c in IEDS}
    modelos = garantir_modelos(necessarios)

    ativos_por_tipo = {
        "RELE": pools.get(5, []),
        "DISJ": pools.get(3, []),
        "TC": pools.get(6, []),
    }
    if not ativos_por_tipo["RELE"]:
        print("Sem ativos de Rele de Protecao na SE 2. Abortando.")
        sys.exit(1)

    print(f"Ativos disponiveis: RELE={len(ativos_por_tipo['RELE'])} DISJ={len(ativos_por_tipo['DISJ'])} TC={len(ativos_por_tipo['TC'])}")
    random.shuffle(ativos_por_tipo["DISJ"])
    random.shuffle(ativos_por_tipo["TC"])

    for cfg in IEDS:
        id_modelo = modelos.get((cfg["fab"], cfg["mod"]))
        if not id_modelo:
            print(f"  [ERRO] modelo {cfg['fab']} {cfg['mod']} ausente")
            continue
        print(f"\n== {cfg['tag']} ==")
        popular_ied(cfg, id_modelo, ativos_por_tipo)

    print("\n================ RESUMO ================")
    for chave, qtd in sorted(RESUMO.items()):
        print(f"  {chave:24} {qtd}")
    print(f"\nErros: {len(ERROS)}")
    for erro in ERROS[:40]:
        print("  ", erro)


if __name__ == "__main__":
    main()
