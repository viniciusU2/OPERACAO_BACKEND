from dotenv import load_dotenv
from datetime import datetime, timedelta

from fastapi import HTTPException
from fastapi import APIRouter, Depends
from jose import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import schemas
from database import get_db
from models.auth_models import Usuario
from utils.autenticacao import verificar_senha, gerar_hash
from auth.dependencies import get_secret_key, require_roles

load_dotenv()

ALGORITHM = "HS256"

router = APIRouter(prefix="", tags=["AUTENTICACAO"])


def garantir_colunas_usuarios(db: Session):
    existe = db.execute(
        text("SHOW COLUMNS FROM usuarios LIKE :coluna"),
        {"coluna": "id_subestacao_padrao"},
    ).first()
    if not existe:
        db.execute(text("ALTER TABLE usuarios ADD COLUMN id_subestacao_padrao INT NULL"))
        db.commit()

def criar_token(data: dict):
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


@router.post("/login")
def login(data: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    garantir_colunas_usuarios(db)
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not verificar_senha(data.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha inválida")
    
    usuario.role = (usuario.role or "usuario").strip().lower()
    token = criar_token({"sub": usuario.email, "role": usuario.role})

    return {
        "usuario": usuario,
        "access_token": token
    }


@router.post("/register")
def register(data: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    garantir_colunas_usuarios(db)
    usuario_existente = db.query(Usuario).filter(Usuario.email == data.email).first()

    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    role = (data.role or "usuario").strip().lower()
    role = role if role in ["usuario", "mantenedor"] else "usuario"

    novo_usuario = Usuario(
        nome=data.nome,
        email=data.email,
        senha_hash=gerar_hash(data.senha),
        role=role
    )

    db.add(novo_usuario)
    db.commit()

    return {"msg": "Usuário criado"}


@router.get("/usuarios", response_model=list[schemas.UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin")),
):
    garantir_colunas_usuarios(db)
    return db.query(Usuario).order_by(Usuario.nome.asc()).all()


@router.get("/usuarios/ativos", response_model=list[schemas.UsuarioAtivoOption])
def listar_usuarios_ativos(
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor")),
):
    garantir_colunas_usuarios(db)
    return (
        db.query(Usuario)
        .filter(Usuario.ativo.is_(True))
        .order_by(Usuario.nome.asc())
        .all()
    )


@router.put("/usuarios/{usuario_id}", response_model=schemas.UsuarioResponse)
def atualizar_usuario_admin(
    usuario_id: int,
    dados: schemas.UsuarioAdminUpdate,
    db: Session = Depends(get_db),
    usuario_admin=Depends(require_roles("admin")),
):
    garantir_colunas_usuarios(db)
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    payload = dados.model_dump(exclude_unset=True)

    if "role" in payload:
        role = (payload["role"] or "usuario").strip().lower()
        if role not in ["admin", "mantenedor", "usuario"]:
            raise HTTPException(status_code=400, detail="Perfil invalido")
        if usuario_id == usuario_admin.id and role != "admin":
            raise HTTPException(
                status_code=400,
                detail="Nao e possivel remover o proprio perfil admin",
            )
        usuario.role = role

    if "ativo" in payload:
        if usuario_id == usuario_admin.id and payload["ativo"] is False:
            raise HTTPException(
                status_code=400,
                detail="Nao e possivel desativar o proprio usuario",
            )
        usuario.ativo = bool(payload["ativo"])

    if "id_subestacao_padrao" in payload:
        usuario.id_subestacao_padrao = payload["id_subestacao_padrao"]

    db.commit()
    db.refresh(usuario)
    return usuario
