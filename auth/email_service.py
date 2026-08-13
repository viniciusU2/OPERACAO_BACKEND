import html
import os
import smtplib
import ssl
from email.message import EmailMessage


def _required(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Variavel de ambiente {name} nao configurada")
    return value


def enviar_email_redefinicao(destinatario: str, link: str, validade_minutos: int) -> None:
    host = _required("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    remetente = _required("SMTP_FROM")
    usuario = (os.getenv("SMTP_USER") or "").strip()
    senha = os.getenv("SMTP_PASSWORD") or ""
    use_ssl = (os.getenv("SMTP_USE_SSL") or "false").lower() in {"1", "true", "yes"}
    use_tls = (os.getenv("SMTP_USE_TLS") or "true").lower() in {"1", "true", "yes"}

    safe_link = html.escape(link, quote=True)
    mensagem = EmailMessage()
    mensagem["Subject"] = "Redefinicao de senha - ENGVI"
    mensagem["From"] = remetente
    mensagem["To"] = destinatario
    mensagem.set_content(
        f"Foi solicitada uma redefinicao de senha no ENGVI.\n\n"
        f"Acesse o link abaixo em ate {validade_minutos} minutos:\n{link}\n\n"
        "Se voce nao fez esta solicitacao, ignore este e-mail."
    )
    mensagem.add_alternative(
        f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#0f172a">
        <div style="max-width:560px;margin:auto;padding:28px;border:1px solid #e2e8f0;border-radius:12px">
          <h2 style="margin-top:0;color:#1d4ed8">Redefinir senha do ENGVI</h2>
          <p>Recebemos uma solicitacao para redefinir sua senha.</p>
          <p><a href="{safe_link}" style="display:inline-block;padding:12px 18px;background:#1d4ed8;color:white;text-decoration:none;border-radius:8px;font-weight:bold">Redefinir minha senha</a></p>
          <p>Este link expira em <strong>{validade_minutos} minutos</strong> e pode ser usado apenas uma vez.</p>
          <p style="color:#64748b;font-size:13px">Se voce nao solicitou esta alteracao, ignore este e-mail. Sua senha continuara a mesma.</p>
        </div></body></html>""",
        subtype="html",
    )

    context = ssl.create_default_context()
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as smtp:
            if usuario:
                smtp.login(usuario, senha)
            smtp.send_message(mensagem)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls(context=context)
            if usuario:
                smtp.login(usuario, senha)
            smtp.send_message(mensagem)
