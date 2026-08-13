from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from datetime import datetime


# Base
class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    foto: Optional[str] = None
    id_subestacao_padrao: Optional[int] = None


# CREATE (cadastro)
class UsuarioCreate(UsuarioBase):
    senha: str
    role: Optional[str] = "usuario"


# LOGIN (entrada)
class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    nova_senha: str = Field(min_length=8, max_length=128)
    confirmar_senha: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validar_confirmacao(self):
        if self.nova_senha != self.confirmar_senha:
            raise ValueError("A confirmacao da senha nao corresponde.")
        return self


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


class UsuarioAtivoOption(BaseModel):
    id: int
    nome: str
    role: str

    class Config:
        from_attributes = True


class UsuarioAdminUpdate(BaseModel):
    role: Optional[str] = None
    ativo: Optional[bool] = None
    id_subestacao_padrao: Optional[int] = None
