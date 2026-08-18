from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from auth.dependencies import require_roles
from models.problemas_tipicos_models import ProblemaTipico
from problemas_tipicos import schemas, service

router=APIRouter(prefix="/problemas-tipicos", tags=["Problemas Típicos"])

@router.get("", response_model=list[schemas.ProblemaResponse])
def listar(busca:Optional[str]=None,id_tipo_ativo:Optional[int]=None,sistema:Optional[str]=None,categoria:Optional[str]=None,criticidade:Optional[str]=None,especialidade:Optional[str]=None,ativo:Optional[bool]=None,db:Session=Depends(get_db)):
    return service.listar(db,busca=busca,id_tipo_ativo=id_tipo_ativo,sistema=sistema,categoria=categoria,criticidade=criticidade,especialidade=especialidade,ativo=ativo)

@router.get("/tipo-ativo/{id_tipo_ativo}", response_model=list[schemas.ProblemaResponse])
def por_tipo(id_tipo_ativo:int,db:Session=Depends(get_db)): return service.listar(db,id_tipo_ativo=id_tipo_ativo,ativo=True)

@router.get("/{id_problema}", response_model=schemas.ProblemaResponse)
def consultar(id_problema:int,db:Session=Depends(get_db)): return service.consultar(db,id_problema)

@router.post("", response_model=schemas.ProblemaResponse,status_code=201)
def criar(payload:schemas.ProblemaCreate,db:Session=Depends(get_db),_u=Depends(require_roles("admin","mantenedor","operador"))): return service.salvar(db,payload)

@router.put("/{id_problema}", response_model=schemas.ProblemaResponse)
def editar(id_problema:int,payload:schemas.ProblemaUpdate,db:Session=Depends(get_db),_u=Depends(require_roles("admin","mantenedor"))): return service.salvar(db,payload,service.consultar(db,id_problema))

@router.patch("/{id_problema}/status", response_model=schemas.ProblemaResponse)
def status(id_problema:int,ativo:bool=Query(...),db:Session=Depends(get_db),_u=Depends(require_roles("admin","mantenedor"))):
    p=service.consultar(db,id_problema); p.ativo=ativo; db.commit(); return service.consultar(db,id_problema)
