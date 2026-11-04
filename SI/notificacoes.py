"""Notificacoes por e-mail das mudancas de status das SI.

Como funciona
-------------

- Usa as mesmas variaveis ``SMTP_*`` do restante do sistema (hoje o relay
  e o Brevo, ``smtp-relay.brevo.com``). Enquanto ``SMTP_HOST`` /
  ``SMTP_USER`` / ``SMTP_PASSWORD`` / ``SMTP_FROM`` nao estiverem todos
  preenchidos, a notificacao fica desligada e nada acontece.
- O envio roda em uma thread separada, depois do commit da acao: a
  aprovacao/rejeicao/etc nunca falha nem demora por causa do e-mail. Se o
  SMTP estiver fora, o erro e registrado no log e a acao segue valendo.
- Quem recebe:
    enviar   -> Centro de Operacoes (admin + operador)
    aprovar  -> Manutencao Local (mantenedor)
    rejeitar -> Manutencao Local (com a justificativa em destaque)
    cancelar -> Manutencao Local (com a justificativa)
    concluir -> os dois lados
  Quem executou a acao nao recebe o proprio e-mail.

Variavel extra: ``FRONTEND_URL`` (ex.: http://192.99.140.211) monta o
link direto para a SI no corpo da mensagem. Sem ela, o e-mail sai sem link.
"""

import logging
import os
import smtplib
import ssl
import threading
from datetime import datetime
from email.message import EmailMessage

logger = logging.getLogger("si_notificacoes")

# Papel de quem deve receber cada acao.
PAPEIS_POR_ACAO = {
    "enviar": ("admin", "operador"),
    "aprovar": ("mantenedor",),
    "rejeitar": ("mantenedor",),
    "cancelar": ("mantenedor",),
    "concluir": ("admin", "operador", "mantenedor"),
}

TITULO_POR_ACAO = {
    "enviar": "enviada para análise",
    "aprovar": "APROVADA",
    "rejeitar": "REJEITADA — corrija e reenvie",
    "cancelar": "CANCELADA",
    "concluir": "CONCLUÍDA",
}


def smtp_configurado() -> bool:
    """So notifica quando o SMTP esta completo (evita ruido de config parcial)."""
    return all(
        (os.getenv(variavel) or "").strip()
        for variavel in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
    )


def emails_por_acao(usuarios, acao: str, email_excluido: str = "") -> list[str]:
    """E-mails dos usuarios que devem receber a notificacao da acao."""
    papeis = PAPEIS_POR_ACAO.get(acao)
    if not papeis:
        return []
    emails = []
    for usuario in usuarios:
        if not getattr(usuario, "ativo", True):
            continue
        papel = (getattr(usuario, "role", "") or "").strip().lower()
        email = (getattr(usuario, "email", "") or "").strip().lower()
        if papel in papeis and email and email != (email_excluido or "").lower():
            emails.append(email)
    return sorted(set(emails))


def notificar_si(db, si, acao: str, usuario, observacao: str | None = None) -> None:
    """Dispara a notificacao da acao da SI em segundo plano.

    Nunca lanca excecao para o chamador: problema de e-mail e problema do
    log, nao da acao que ja foi confirmada.
    """
    try:
        if acao not in PAPEIS_POR_ACAO or not smtp_configurado():
            return

        from models.auth_models import Usuario

        usuarios = db.query(Usuario).all()
        destinatarios = emails_por_acao(
            usuarios, acao, (getattr(usuario, "email", "") or "").strip()
        )
        if not destinatarios:
            return

        instalacao = ""
        codigo_ativo = ""
        if si.id_subestacao:
            from models.instalacao_models import Subestacao

            sub = db.query(Subestacao).filter(
                Subestacao.id_subestacao == si.id_subestacao
            ).first()
            instalacao = sub.nome if sub else ""
        if si.id_ativo:
            from models.Ativo import Ativo

            ativo = db.query(Ativo).filter(Ativo.id_ativo == si.id_ativo).first()
            codigo_ativo = ativo.codigo_ativo if ativo else ""

        nome_usuario = getattr(usuario, "nome", None) or getattr(usuario, "email", "") or ""
        frontend = (os.getenv("FRONTEND_URL") or "").strip().rstrip("/")

        dados = {
            "numero": si.numero_si or f"#{si.id_si}",
            "titulo": TITULO_POR_ACAO[acao],
            "acao": acao,
            "quem": nome_usuario,
            "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "instalacao": instalacao,
            "ativo": codigo_ativo,
            "observacao": (observacao or "").strip(),
            "link": f"{frontend}/si/{si.id_si}" if frontend else "",
            "destinatarios": ", ".join(destinatarios),
            "host": (os.getenv("SMTP_HOST") or "").strip(),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "remetente": (os.getenv("SMTP_FROM") or "").strip(),
            "usuario": (os.getenv("SMTP_USER") or "").strip(),
            "senha": os.getenv("SMTP_PASSWORD") or "",
            "use_ssl": (os.getenv("SMTP_USE_SSL") or "false").lower() in {"1", "true", "yes"},
            "use_tls": (os.getenv("SMTP_USE_TLS") or "true").lower() in {"1", "true", "yes"},
        }

        threading.Thread(target=_enviar, args=(dados,), daemon=True).start()
    except Exception:
        logger.exception("Falha ao preparar notificacao da SI")


def _enviar(dados: dict) -> None:
    try:
        mensagem = EmailMessage()
        mensagem["Subject"] = f"SI {dados['numero']} — {dados['titulo']}"
        mensagem["From"] = dados["remetente"]
        mensagem["To"] = dados["destinatarios"]
        mensagem.set_content(_texto(dados))
        mensagem.add_alternative(_html(dados), subtype="html")

        contexto = ssl.create_default_context()
        if dados["use_ssl"]:
            with smtplib.SMTP_SSL(dados["host"], dados["port"], timeout=20, context=contexto) as smtp:
                if dados["usuario"]:
                    smtp.login(dados["usuario"], dados["senha"])
                smtp.send_message(mensagem)
        else:
            with smtplib.SMTP(dados["host"], dados["port"], timeout=20) as smtp:
                if dados["use_tls"]:
                    smtp.starttls(context=contexto)
                if dados["usuario"]:
                    smtp.login(dados["usuario"], dados["senha"])
                smtp.send_message(mensagem)
        logger.info(
            "Notificacao da SI %s (%s) enviada para %s",
            dados.get("numero"),
            dados.get("acao"),
            dados.get("destinatarios"),
        )
    except Exception:
        logger.exception("Falha ao enviar notificacao da SI %s", dados.get("numero"))


def _texto(dados: dict) -> str:
    linhas = [
        f"SI {dados['numero']} — {dados['titulo']}",
        "",
    ]
    if dados["instalacao"]:
        linhas.append(f"Instalação: {dados['instalacao']}")
    if dados["ativo"]:
        linhas.append(f"Ativo: {dados['ativo']}")
    linhas.append(f"Quem: {dados['quem']}")
    linhas.append(f"Quando: {dados['quando']}")
    if dados["observacao"]:
        linhas += ["", f"Observação: {dados['observacao']}"]
    if dados["link"]:
        linhas += ["", f"Abrir no ENGVI: {dados['link']}"]
    linhas += ["", "Mensagem automática do ENGVI — não responda este e-mail."]
    return "\n".join(linhas)


def _html(dados: dict) -> str:
    observacao = ""
    if dados["observacao"]:
        observacao = (
            f'<p style="margin:14px 0 4px;font-size:13px;color:#334155">'
            f'<strong>Observação:</strong></p>'
            f'<div style="padding:12px 14px;border-left:4px solid #ef4444;'
            f'background:#fef2f2;border-radius:6px;color:#7f1d1d">'
            f'{dados["observacao"]}</div>'
        )
    contexto = " · ".join(
        parte for parte in (dados["instalacao"], dados["ativo"]) if parte
    )
    botao = ""
    if dados["link"]:
        botao = (
            f'<p><a href="{dados["link"]}" style="display:inline-block;padding:12px 18px;'
            f'background:#1d4ed8;color:white;text-decoration:none;border-radius:8px;'
            f'font-weight:bold">Abrir no ENGVI</a></p>'
        )
    return f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#0f172a">
    <div style="max-width:560px;margin:auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px">
      <h2 style="margin-top:0;color:#1d4ed8">SI {dados["numero"]}</h2>
      <p style="font-size:16px"><strong>{dados["titulo"]}</strong></p>
      <p style="color:#475569">{contexto}</p>
      <p style="color:#475569;font-size:13px">
        Por <strong>{dados["quem"]}</strong> em {dados["quando"]}
      </p>
      {observacao}
      {botao}
      <p style="color:#94a3b8;font-size:12px">
        Mensagem automática do ENGVI — não responda este e-mail.
      </p>
    </div></body></html>"""
