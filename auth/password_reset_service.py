import hashlib
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.email_service import enviar_email_redefinicao
from models.auth_models import Usuario
from models.password_reset_models import PasswordResetToken
from utils.autenticacao import gerar_hash

GENERIC_MESSAGE = "Se o e-mail estiver cadastrado, enviaremos as instrucoes para recuperacao da senha."
TOKEN_MINUTES = max(15, min(30, int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "20"))))
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def verificar_limite(chave: str, limite: int = 5, janela_segundos: int = 900) -> None:
    agora = time.monotonic()
    with _lock:
        eventos = _attempts[chave]
        while eventos and agora - eventos[0] > janela_segundos:
            eventos.popleft()
        if len(eventos) >= limite:
            raise HTTPException(status_code=429, detail="Muitas solicitacoes. Tente novamente mais tarde.")
        eventos.append(agora)


def solicitar_redefinicao(db: Session, email: str) -> None:
    usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email.strip().lower()).first()
    if not usuario or not usuario.ativo:
        return

    agora = datetime.utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == usuario.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: agora}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    registro = PasswordResetToken(
        user_id=usuario.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=agora + timedelta(minutes=TOKEN_MINUTES),
    )
    db.add(registro)
    db.flush()

    frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    link = f"{frontend_url}/redefinir-senha?{urlencode({'token': token})}"
    enviar_email_redefinicao(usuario.email, link, TOKEN_MINUTES)
    db.commit()


def redefinir_senha(db: Session, token: str, nova_senha: str) -> None:
    agora = datetime.utcnow()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    registro = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).with_for_update().first()

    if not registro or registro.used_at is not None or registro.expires_at <= agora:
        raise HTTPException(status_code=400, detail="Link invalido, expirado ou ja utilizado.")

    usuario = db.query(Usuario).filter(Usuario.id == registro.user_id).with_for_update().first()
    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=400, detail="Link invalido, expirado ou ja utilizado.")

    usuario.senha_hash = gerar_hash(nova_senha)
    usuario.auth_version = (usuario.auth_version or 0) + 1
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == usuario.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: agora}, synchronize_session=False)
    db.commit()
