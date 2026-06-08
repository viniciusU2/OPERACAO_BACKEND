import os
from typing import Callable

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models.auth_models import Usuario

load_dotenv()

ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)


def get_secret_key():
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise HTTPException(status_code=500, detail="SECRET_KEY nao configurada")
    return secret_key


def garantir_colunas_usuarios(db: Session):
    existe = db.execute(
        text("SHOW COLUMNS FROM usuarios LIKE :coluna"),
        {"coluna": "id_subestacao_padrao"},
    ).first()
    if not existe:
        db.execute(text("ALTER TABLE usuarios ADD COLUMN id_subestacao_padrao INT NULL"))
        db.commit()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token de acesso ausente")

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_secret_key(),
            algorithms=[ALGORITHM],
        )
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    if not email:
        raise HTTPException(status_code=401, detail="Token invalido")

    garantir_colunas_usuarios(db)
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuario inativo ou nao encontrado")

    return usuario


def require_roles(*roles: str) -> Callable:
    def dependency(usuario: Usuario = Depends(get_current_user)):
        user_role = (usuario.role or "").strip().lower()
        allowed_roles = {role.strip().lower() for role in roles}

        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permissao insuficiente")
        return usuario

    return dependency
