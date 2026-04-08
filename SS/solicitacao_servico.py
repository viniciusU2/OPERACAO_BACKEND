from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.SS_models import SolicitacaoServico 
from SS.schemas import SolicitacaoServicoCreate, SolicitacaoServicoResponse


router = APIRouter(prefix="/ss", tags=["Solicitação de Serviço"])


@router.post("", response_model=SolicitacaoServicoResponse)
def criar_ss(ss: SolicitacaoServicoCreate, db: Session = Depends(get_db)):

    nova_ss = SolicitacaoServico(**ss.dict())

    db.add(nova_ss)
    db.commit()
    db.refresh(nova_ss)

    return nova_ss


@router.get("", response_model=list[SolicitacaoServicoResponse])
def listar_ss(db: Session = Depends(get_db)):

    return db.query(SolicitacaoServico).all()