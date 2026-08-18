from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload
from models.familias_models import TipoAtivo
from models.Ativo import Ativo, GrupoAtivo
from models.problemas_tipicos_models import AcaoRecomendada, CausaProblema, MetodoDeteccaoProblema, ProblemaTipico, SSProblema, SintomaProblema

def load_options():
    return (selectinload(ProblemaTipico.sintomas), selectinload(ProblemaTipico.causas), selectinload(ProblemaTipico.acoes_recomendadas), selectinload(ProblemaTipico.metodos_deteccao))

def _replace(problema, data):
    problema.sintomas = [SintomaProblema(**x) for x in data.pop("sintomas", [])]
    problema.causas = [CausaProblema(**x) for x in data.pop("causas", [])]
    problema.acoes_recomendadas = [AcaoRecomendada(**x) for x in data.pop("acoes_recomendadas", [])]
    problema.metodos_deteccao = [MetodoDeteccaoProblema(**x) for x in data.pop("metodos_deteccao", [])]
    for k, v in data.items(): setattr(problema, k, v)

def salvar(db: Session, payload, problema=None):
    data = payload.model_dump()
    if not db.get(TipoAtivo, data["id_tipo_ativo"]): raise HTTPException(400, "Tipo de ativo inexistente")
    problema = problema or ProblemaTipico()
    _replace(problema, data)
    db.add(problema); db.commit(); db.refresh(problema)
    return consultar(db, problema.id_problema)

def consultar(db, pid):
    p = db.query(ProblemaTipico).options(*load_options()).filter(ProblemaTipico.id_problema == pid).first()
    if not p: raise HTTPException(404, "Problema típico não encontrado")
    return p

def listar(db, *, busca=None, id_tipo_ativo=None, sistema=None, categoria=None, criticidade=None, especialidade=None, ativo=None):
    q=db.query(ProblemaTipico).options(*load_options())
    if id_tipo_ativo: q=q.filter(ProblemaTipico.id_tipo_ativo==id_tipo_ativo)
    if sistema: q=q.filter(ProblemaTipico.sistema==sistema)
    if categoria: q=q.filter(ProblemaTipico.categoria==categoria)
    if criticidade: q=q.filter(ProblemaTipico.criticidade_padrao==criticidade)
    if especialidade: q=q.filter(ProblemaTipico.especialidade==especialidade)
    if ativo is not None: q=q.filter(ProblemaTipico.ativo==ativo)
    if busca:
        t=f"%{busca.strip()}%"
        q=q.outerjoin(SintomaProblema).outerjoin(CausaProblema).filter(or_(ProblemaTipico.titulo.ilike(t),ProblemaTipico.descricao.ilike(t),ProblemaTipico.modo_falha.ilike(t),SintomaProblema.sintoma.ilike(t),CausaProblema.causa.ilike(t))).distinct()
    return q.order_by(ProblemaTipico.titulo).all()

def sincronizar_ss(db, ss, itens):
    ss.problemas.clear(); db.flush()
    ids=set()
    for item in itens:
        data=item.model_dump()
        if data["id_problema"] in ids: raise HTTPException(400, "Problema duplicado na SS")
        ids.add(data["id_problema"])
        p=consultar(db,data["id_problema"])
        id_tipo = db.query(Ativo.id_tipo_ativo).filter(Ativo.id_ativo == ss.id_ativo).scalar() if ss.id_ativo else db.query(GrupoAtivo.id_tipo_ativo).filter(GrupoAtivo.id_grupo_ativo == ss.id_grupo_ativo).scalar()
        if id_tipo and p.id_tipo_ativo != id_tipo: raise HTTPException(400, f"Problema '{p.titulo}' incompatível com o tipo do ativo")
        ss.problemas.append(SSProblema(**data))
