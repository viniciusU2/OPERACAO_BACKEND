from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.auth_models import  Usuario
from dotenv import load_dotenv
import os
from database import get_db
router = APIRouter(prefix="", tags=["AUTENTICACAO"])
from jose import jwt
from datetime import datetime, timedelta
from utils.autenticacao import verificar_senha, gerar_hash
from auth import schemas


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"




load_dotenv()

def criar_token(data: dict):
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login")
def login(data: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not verificar_senha(data.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha inválida")
    
    token = criar_token({"sub": usuario.email})

    return {
        "usuario": usuario,
        "access_token": token
    }


@router.post("/register")
def register(data: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    usuario_existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    print(gerar_hash("123456"))

    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=data.nome,
        email=data.email,
        senha_hash=gerar_hash(data.senha)
    )

    db.add(novo_usuario)
    db.commit()

    return {"msg": "Usuário criado"}
