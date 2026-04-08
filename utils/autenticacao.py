from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def gerar_hash(senha: str):
    senha_sha = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    return pwd_context.hash(senha_sha)

def verificar_senha(senha: str, senha_hash: str):
    senha_sha = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    return pwd_context.verify(senha_sha, senha_hash)


