from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import require_roles
from database import get_db
from . import schemas, service

router = APIRouter(prefix="", tags=["Funcoes de Operacao"])


@router.post("/funcoes-operacao", response_model=schemas.FuncaoOperacaoOut)
def criar_funcao_operacao(dados: schemas.FuncaoOperacaoCreate, db: Session = Depends(get_db), _usuario=Depends(require_roles("admin"))):
    return service.criar_funcao_operacao(db, dados)


@router.get("/funcoes-operacao", response_model=List[schemas.FuncaoOperacaoOut])
def listar_funcoes_operacao(id_subestacao: Optional[int] = None, db: Session = Depends(get_db)):
    return service.listar_funcoes_operacao(db, id_subestacao)


@router.get("/funcoes-operacao/{id_funcao_operacao}", response_model=schemas.FuncaoOperacaoOut)
def obter_funcao_operacao(id_funcao_operacao: int, db: Session = Depends(get_db)):
    return service.obter_funcao_operacao(db, id_funcao_operacao)


@router.put("/funcoes-operacao/{id_funcao_operacao}", response_model=schemas.FuncaoOperacaoOut)
def atualizar_funcao_operacao(id_funcao_operacao: int, dados: schemas.FuncaoOperacaoUpdate, db: Session = Depends(get_db), _usuario=Depends(require_roles("admin"))):
    return service.atualizar_funcao_operacao(db, id_funcao_operacao, dados)


@router.delete("/funcoes-operacao/{id_funcao_operacao}")
def excluir_funcao_operacao(id_funcao_operacao: int, db: Session = Depends(get_db), _usuario=Depends(require_roles("admin"))):
    return service.excluir_funcao_operacao(db, id_funcao_operacao)


@router.get("/funcoes-operacao/{id_funcao_operacao}/ativos", response_model=List[schemas.FuncaoOperacaoAtivoOut])
def listar_ativos_associados(id_funcao_operacao: int, db: Session = Depends(get_db)):
    return service.listar_ativos_associados(db, id_funcao_operacao)
