from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Base
class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    foto: Optional[str] = None


# CREATE (cadastro)
class UsuarioCreate(UsuarioBase):
    senha: str
    role: Optional[str] = "usuario"


# LOGIN (entrada)
class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


# RESPONSE (retorno do usuário)
class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    criado_em: datetime
    role: str

    class Config:
        from_attributes = True


# RESPONSE DE LOGIN
class LoginResponse(BaseModel):
    usuario: UsuarioResponse
    access_token: str

    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str