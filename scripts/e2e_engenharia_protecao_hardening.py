# -*- coding: utf-8 -*-
"""E2E do endurecimento (fase 6) contra o backend real.

Cobre: perfis, segregação de funções, novos estados, reversão, auditoria
transversal, arquivamento/reativação, integridade de arquivos e dashboard.
Cria um IED descartável (com filhos) e o remove ao final.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

import main  # noqa: E402,F401
from database import SessionLocal  # noqa: E402
from models.Ativo import Ativo  # noqa: E402

BASE = "http://127.0.0.1:8000"
EP = BASE + "/engenharia-protecao"
ADMIN = {
    "email": os.getenv("ENGVI_E2E_EMAIL", ""),
    "senha": os.getenv("ENGVI_E2E_SENHA", ""),
}
if not ADMIN["email"] or not ADMIN["senha"]:
    raise SystemExit("Defina ENGVI_E2E_EMAIL e ENGVI_E2E_SENHA para rodar o E2E.")
SUFIXO = uuid.uuid4().hex[:6].upper()
CONTA_USUARIOS = 0

RESULTADOS: list[tuple[bool, str]] = []


def chk(condicao: bool, rotulo: str, extra: object = None) -> bool:
    RESULTADOS.append((bool(condicao), rotulo))
    marca = "OK   " if condicao else "FALHA"
    print(f"{marca} {rotulo}" + ("" if condicao or extra is None else f"  >> {extra}"))
    return bool(condicao)


def sessao(email: str, senha: str) -> requests.Session:
    s = requests.Session()
    r = s.post(BASE + "/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": "Bearer " + r.json()["access_token"]})
    return s


def criar_usuario(admin: requests.Session, papel: str) -> tuple[requests.Session, dict]:
    global CONTA_USUARIOS

    CONTA_USUARIOS += 1
    email = f"e2e.hardening.{SUFIXO}.{CONTA_USUARIOS}.{papel}@example.com"
    senha = "SenhaForte123"
    r = admin.post(BASE + "/register", json={"nome": f"E2E {papel}", "email": email, "senha": senha})
    assert r.status_code in (200, 201), r.text
    usuarios = admin.get(BASE + "/usuarios").json()
    alvo = next(u for u in usuarios if u["email"] == email)
    r = admin.put(BASE + f"/usuarios/{alvo['id']}", json={"role": papel})
    assert r.status_code == 200, r.text
    return sessao(email, senha), alvo


admin = sessao(**ADMIN)

# ---------------------------------------------------------------- setup ------
with SessionLocal() as db:
    ref = db.query(Ativo).first()
    ativo = Ativo(
        id_subestacao=ref.id_subestacao,
        id_tipo_ativo=ref.id_tipo_ativo,
        codigo_ativo=f"TMP-HP-{SUFIXO}",
        status="OPERANTE",
    )
    db.add(ativo)
    db.commit()
    id_ativo, id_sub = ativo.id_ativo, ativo.id_subestacao

modelo_id = admin.get(EP + "/ieds", params={"page_size": 1}).json()["items"][0]["id_modelo_ied"]
res = admin.post(
    EP + "/ieds",
    json={
        "tag_operacional": f"TMP-HP-{SUFIXO}",
        "id_ativo": id_ativo,
        "id_modelo_ied": modelo_id,
        "id_subestacao": id_sub,
        "painel_instalacao": "PAINEL E2E",
        "data_instalacao": date.today().isoformat(),
        "status_operacional": "EM_OPERACAO",
    },
)
chk(res.status_code == 201, "IED descartável criado", res.text[:200])
id_ied = res.json()["id_ied"]
versao_ied = res.json()["versao"]

funcao_ansi = admin.get(EP + "/funcoes-ansi", params={"page_size": 1}).json()["items"][0]["id_funcao_ansi"]
chk(admin.post(EP + f"/ieds/{id_ied}/funcoes", json={"id_funcao_ansi": funcao_ansi}).status_code == 201,
    "função ANSI habilitada no IED")

r = admin.post(EP + f"/ieds/{id_ied}/grupos-ajuste", json={"numero": 1, "nome": "GRUPO E2E"})
chk(r.status_code == 201, "grupo de ajuste criado", r.text[:200])
id_grupo = r.json()["id_ied_grupo_ajuste"]

definicoes = admin.get(EP + "/parametros-definicao", params={"id_funcao_ansi": funcao_ansi}).json()
chk(len(definicoes) > 0, "catálogo ANSI expõe definições de parâmetro", len(definicoes))
id_parametro = definicoes[0]["id_parametro_definicao"]
r = admin.put(
    EP + f"/grupos-ajuste/{id_grupo}/parametros",
    json={"parametros": [{"id_parametro_definicao": id_parametro, "valor": "1.0"}]},
)
chk(r.status_code == 200, "valores do grupo definidos", r.text[:200])
itens = admin.get(EP + f"/grupos-ajuste/{id_grupo}/parametros").json()["itens"]
chk(len(itens) > 0, "grupo expõe os parâmetros configurados", len(itens))

r = admin.post(
    EP + f"/ieds/{id_ied}/configuracoes",
    json={"rotulo": f"CFG E2E {SUFIXO}", "motivo": "BACKUP_PERIODICO", "data_coleta": date.today().isoformat()},
)
chk(r.status_code == 201, "configuração criada para o IED descartável", r.text[:200])
id_configuracao = r.json()["id_ied_configuracao"]

CONTEUDO_XML = b'<?xml version="1.0" encoding="UTF-8"?><SCL><Header id="e2e"/></SCL>'
r = admin.post(
    EP + f"/configuracoes/{id_configuracao}/arquivos",
    files={"arquivo": ("e2e.xml", CONTEUDO_XML, "application/xml")},
    data={"papel": "PRINCIPAL", "descricao": "arquivo do E2E"},
)
chk(r.status_code == 201, "upload de arquivo .xml aceito", r.text[:200])
arquivo = r.json()["arquivos"][0]["arquivo"]
id_arquivo, sha256 = arquivo["id_arquivo"], arquivo["sha256"]

# --------------------------------------------------- integridade de arquivo --
r = admin.get(EP + f"/arquivos/{id_arquivo}/download")
chk(r.status_code == 200 and r.content == CONTEUDO_XML, "download íntegro devolve o conteúdo")

with SessionLocal() as db:
    from sqlalchemy import text as _text

    caminho = db.execute(
        _text("SELECT caminho FROM arquivo WHERE id_arquivo = :id"), {"id": id_arquivo}
    ).scalar()

with open(caminho, "ab") as manipulador:
    manipulador.write(b"corrompido")
r = admin.get(EP + f"/arquivos/{id_arquivo}/download")
chk(r.status_code == 409, "download detecta arquivo corrompido (SHA-256 divergente)", r.status_code)
os.remove(caminho)
with open(caminho, "wb") as manipulador:
    manipulador.write(CONTEUDO_XML)
r = admin.get(EP + f"/arquivos/{id_arquivo}/download")
chk(r.status_code == 200, "download volta a funcionar após restaurar o arquivo")

# -------------------------------------------------------- arquivar/reativar --
r = admin.post(EP + f"/ieds/{id_ied}/arquivar")
chk(r.status_code == 200, "arquivamento aceito", r.text[:200])
r = admin.get(EP + f"/ieds/{id_ied}")
chk(
    r.status_code == 200 and r.json()["ativo"] is False and r.json()["status_operacional"] == "RETIRADO",
    "IED arquivado sai do inventário vigente",
    r.json() if r.status_code == 200 else r.text[:200],
)
chk(r.json()["versao"] > versao_ied, "arquivamento incrementa a versão (lock otimista)")

tags_ativos = [i["tag_operacional"] for i in admin.get(EP + "/ieds", params={"page_size": 200}).json()["items"]]
tags_todos = [
    i["tag_operacional"]
    for i in admin.get(EP + "/ieds", params={"page_size": 200, "somente_ativos": False}).json()["items"]
]
chk(f"TMP-HP-{SUFIXO}" not in tags_ativos, "IED arquivado não aparece na listagem padrão")
chk(f"TMP-HP-{SUFIXO}" in tags_todos, "IED arquivado aparece em somente_ativos=false")

r = admin.post(EP + f"/ieds/{id_ied}/reativar")
chk(
    r.status_code == 200 and r.json()["ativo"] is True and r.json()["status_operacional"] == "EM_OPERACAO",
    "reativação devolve o IED ao inventário",
    r.text[:200],
)
chk(admin.post(EP + f"/ieds/{id_ied}/reativar").status_code == 400, "reativar IED já ativo devolve 400")

# ---------------------------------------------------------------- perfis -----
usuario_s, _ = criar_usuario(admin, "usuario")
engenheiro_a, _ = criar_usuario(admin, "engenheiro_protecao")
engenheiro_b, _ = criar_usuario(admin, "engenheiro_protecao")
tecnico, _ = criar_usuario(admin, "tecnico_manutencao")
auditor, _ = criar_usuario(admin, "auditor")

chk(admin.get(EP + "/auditoria").status_code == 200, "auditoria acessível ao admin")
chk(auditor.get(EP + "/auditoria").status_code == 200, "auditoria acessível ao auditor")
chk(usuario_s.get(EP + "/auditoria").status_code == 403, "auditoria negada ao perfil usuario")
chk(requests.get(EP + "/auditoria").status_code in (401, 403), "auditoria exige autenticação")

r = tecnico.post(EP + f"/ieds/{id_ied}/arquivar")
chk(r.status_code == 200, "técnico de manutenção pode arquivar (escrita)")
admin.post(EP + f"/ieds/{id_ied}/reativar")
chk(tecnico.delete(EP + f"/ieds/{id_ied}").status_code == 403, "exclusão definitiva negada ao técnico")
chk(engenheiro_a.delete(EP + f"/ieds/{id_ied}").status_code == 403, "exclusão definitiva negada ao engenheiro")
chk(admin.post(EP + f"/ieds/{id_ied}/arquivar").status_code == 200, "rearquivamento para seguir o fluxo")
admin.post(EP + f"/ieds/{id_ied}/reativar")

# ------------------------------------------------- fluxo de alterações ------
def nova_alteracao(prioridade: str) -> tuple[int, int]:
    r = admin.post(
        EP + "/alteracoes",
        json={
            "id_ied": id_ied,
            "titulo": f"E2E {prioridade} {SUFIXO}",
            "descricao": "alteração do E2E de endurecimento",
            "tipo": "AJUSTE",
            "prioridade": prioridade,
        },
    )
    assert r.status_code == 201, r.text
    ident = r.json()["id_solicitacao_alteracao"]
    r = admin.post(
        EP + f"/alteracoes/{ident}/itens",
        json={"id_parametro_definicao": id_parametro, "valor_atual": "1.0", "valor_proposto": "1.5"},
    )
    assert r.status_code == 201, r.text
    r = admin.post(EP + f"/alteracoes/{ident}/submeter", json={})
    assert r.status_code == 200 and r.json()["status"] == "SUBMETIDA", r.text
    return ident, r.json()["versao"]


id_alt, _ = nova_alteracao("ALTA")
chk(engenheiro_a.post(EP + f"/alteracoes/{id_alt}/iniciar-analise", json={}).status_code == 200,
    "engenheiro inicia a análise")
chk(admin.post(EP + f"/alteracoes/{id_alt}/aprovar", json={}).status_code == 403,
    "solicitante não pode aprovar a própria alteração")
r = engenheiro_a.post(EP + f"/alteracoes/{id_alt}/aprovar", json={"comentario": "ok"})
chk(r.status_code == 200 and r.json()["status"] == "APROVADA", "engenheiro aprova a alteração", r.text[:200])
chk(r.json()["nome_aprovador"], "aprovador registrado no detalhe", r.json().get("nome_aprovador"))

r = admin.post(EP + f"/alteracoes/{id_alt}/implantar", json={"comentario": "implantada"})
chk(r.status_code == 200 and r.json()["status"] == "IMPLANTADA", "implantação registrada", r.text[:200])
chk(r.json()["nome_implantador"], "implantador registrado", r.json().get("nome_implantador"))

chk(engenheiro_a.post(EP + f"/alteracoes/{id_alt}/iniciar-validacao", json={}).status_code == 403,
    "aprovador não pode conduzir a validação")
chk(admin.post(EP + f"/alteracoes/{id_alt}/validar", json={"aprovado": True}).status_code == 403,
    "solicitante não pode validar")
r = engenheiro_b.post(EP + f"/alteracoes/{id_alt}/iniciar-validacao", json={})
chk(r.status_code == 200 and r.json()["status"] == "EM_VALIDACAO", "validador independente inicia a validação", r.text[:200])
r = engenheiro_b.post(EP + f"/alteracoes/{id_alt}/validar", json={"aprovado": True, "comentario": "conforme"})
chk(r.status_code == 200 and r.json()["status"] == "CONCLUIDA", "validação conclui a alteração", r.text[:200])

r = admin.post(
    EP + f"/alteracoes/{id_alt}/reverter",
    json={"id_configuracao_rollback": id_configuracao, "motivo": "reversão solicitada no E2E"},
)
chk(r.status_code == 200 and r.json()["status"] == "REVERTIDA", "reversão registrada", r.text[:200])
chk(r.json()["data_reversao"] is not None and r.json()["id_configuracao_rollback"] == id_configuracao,
    "rollback e data registrados")

id_alt_critica, _ = nova_alteracao("CRITICA")
chk(engenheiro_a.post(EP + f"/alteracoes/{id_alt_critica}/aprovar", json={}).status_code == 200,
    "alteração crítica aprovada")
chk(admin.post(EP + f"/alteracoes/{id_alt_critica}/implantar", json={}).status_code == 400,
    "implantação crítica exige evidência")
r = admin.post(
    EP + f"/alteracoes/{id_alt_critica}/implantar",
    json={"evidencia_implantacao": "protocolo E2E-1234 e registro fotográfico"},
)
chk(r.status_code == 200 and r.json()["evidencia_implantacao"], "evidência de implantação é persistida")

r = admin.get(EP + f"/alteracoes/{id_alt}", params={})
detalhe = admin.get(EP + f"/alteracoes/{id_alt}").json()
acoes = {h["acao"] for h in detalhe.get("historico", [])}
chk({"ANALISE", "APROVACAO", "IMPLANTACAO", "INICIO_VALIDACAO", "CONCLUSAO", "REVERSAO"}.issubset(acoes),
    "histórico registra o ciclo completo", sorted(acoes))
TRANSICOES = {"SUBMISSAO", "ANALISE", "APROVACAO", "IMPLANTACAO", "INICIO_VALIDACAO", "CONCLUSAO", "REVERSAO"}
chk(
    all(
        h["status_anterior"] != h["status_novo"]
        for h in detalhe.get("historico", [])
        if h["acao"] in TRANSICOES
    ),
    "histórico não repete o mesmo status em anterior/novo",
    [(h["acao"], h["status_anterior"], h["status_novo"]) for h in detalhe.get("historico", [])],
)

# -------------------------------------------------------------- auditoria ---
r = admin.get(EP + "/auditoria", params={"recurso": "ieds", "page_size": 200})
acoes_ied = {linha["acao"] for linha in r.json()["items"]}
chk({"ARQUIVAMENTO", "REATIVACAO"}.issubset(acoes_ied), "auditoria distingue arquivamento e reativação", sorted(acoes_ied))
r = admin.get(EP + "/auditoria", params={"acao": "IMPLANTACAO"})
chk(r.json()["total"] >= 1, "auditoria filtra por ação")
r = admin.get(EP + "/auditoria", params={"page_size": 5})
chk(r.json()["total"] > 5 and len(r.json()["items"]) == 5, "auditoria é paginada", r.json()["total"])
chk(all(linha["metodo"] in {"POST", "PUT", "PATCH", "DELETE"} for linha in r.json()["items"]),
    "auditoria registra métodos mutáveis")

# -------------------------------------------------------------- dashboard ---
r = admin.get(EP + "/dashboard")
novas = {"backups_desatualizados", "sem_backup_validado", "alteracoes_pendentes",
         "implantadas_nao_validadas", "ensaios_vencidos", "ocorrencias_abertas", "por_fabricante"}
chk(r.status_code == 200 and novas.issubset(r.json()), "dashboard expõe os novos indicadores", sorted(r.json())[:5])
r = admin.get(EP + "/dashboard", params={"id_subestacao": id_sub})
chk(r.status_code == 200 and r.json()["total_ieds"] >= 1, "dashboard aceita filtro por subestação", r.text[:200])

# --------------------------------------------------------------- limpeza ----
r = admin.delete(EP + f"/ieds/{id_ied}")
chk(r.status_code == 200, "exclusão definitiva do IED descartável", r.text[:200])
chk(admin.get(EP + f"/ieds/{id_ied}").status_code == 404, "IED removido definitivamente")
with SessionLocal() as db:
    from sqlalchemy import text as _text

    db.execute(_text("DELETE FROM usuarios WHERE email LIKE :p"), {"p": f"e2e.hardening.{SUFIXO}.%"})
    db.execute(_text("DELETE FROM ativo WHERE id_ativo = :id"), {"id": id_ativo})
    db.commit()
    restantes = db.execute(_text("SELECT COUNT(*) FROM arquivo WHERE id_arquivo = :id"), {"id": id_arquivo}).scalar()
chk(restantes == 0, "arquivo do cenário foi limpo junto com o IED")

total = len(RESULTADOS)
ok = sum(1 for condicao, _ in RESULTADOS if condicao)
print(f"\n{ok}/{total} verificações OK")
if ok != total:
    print("FALHAS:")
    for condicao, rotulo in RESULTADOS:
        if not condicao:
            print("  -", rotulo)
