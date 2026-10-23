import re
import secrets
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from models.familias_models import TipoAtivo
from models.Ativo import Ativo, GrupoAtivo
from models.problemas_tipicos_models import (
    AcaoRecomendada,
    AlarmeProblema,
    CausaProblema,
    InstrumentoProblema,
    MetodoDeteccaoProblema,
    PalavraChaveProblema,
    ProblemaTipico,
    SSProblema,
    SintomaProblema,
    StatusValidacaoProblema,
)


def load_options():
    return (
        selectinload(ProblemaTipico.sintomas),
        selectinload(ProblemaTipico.causas),
        selectinload(ProblemaTipico.acoes_recomendadas),
        selectinload(ProblemaTipico.metodos_deteccao),
        selectinload(ProblemaTipico.alarmes),
        selectinload(ProblemaTipico.palavras_chave),
        selectinload(ProblemaTipico.instrumentos),
    )


def _replace(problema, data):
    problema.sintomas = [SintomaProblema(**x) for x in data.pop("sintomas", [])]
    problema.causas = [CausaProblema(**x) for x in data.pop("causas", [])]
    problema.acoes_recomendadas = [AcaoRecomendada(**x) for x in data.pop("acoes_recomendadas", [])]
    problema.metodos_deteccao = [MetodoDeteccaoProblema(**x) for x in data.pop("metodos_deteccao", [])]
    problema.alarmes = [AlarmeProblema(**x) for x in data.pop("alarmes", [])]
    problema.palavras_chave = [PalavraChaveProblema(**x) for x in data.pop("palavras_chave", [])]
    problema.instrumentos = [InstrumentoProblema(**x) for x in data.pop("instrumentos", [])]
    for k, v in data.items(): setattr(problema, k, v)


def gerar_codigo(titulo: str) -> str:
    """Código legível e único para problemas cadastrados manualmente pela API."""
    base = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode().upper()
    base = re.sub(r"[^A-Z0-9]+", "-", base).strip("-")[:50] or "PROBLEMA"
    return f"MAN-{base}-{secrets.token_hex(3).upper()}"


def salvar(db: Session, payload, problema=None):
    data = payload.model_dump()
    if not db.get(TipoAtivo, data["id_tipo_ativo"]): raise HTTPException(400, "Tipo de ativo inexistente")
    codigo = (data.pop("codigo", None) or "").strip()
    if problema is None:
        problema = ProblemaTipico(codigo=codigo or gerar_codigo(data["titulo"]))
    elif codigo and codigo != problema.codigo:
        problema.codigo = codigo
    _replace(problema, data)
    db.add(problema)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.query(ProblemaTipico).filter(ProblemaTipico.codigo == problema.codigo).first():
            raise HTTPException(409, f"Já existe um problema com o código '{problema.codigo}'")
        raise HTTPException(409, "Já existe um problema com o mesmo título para este tipo de ativo")
    db.refresh(problema)
    return consultar(db, problema.id_problema)


def consultar(db, pid):
    p = db.query(ProblemaTipico).options(*load_options()).filter(ProblemaTipico.id_problema == pid).first()
    if not p: raise HTTPException(404, "Problema típico não encontrado")
    return p


def listar(db, *, busca=None, id_tipo_ativo=None, sistema=None, categoria=None, criticidade=None, especialidade=None,
           risco_operacional=None, status_validacao=None, origem_registro=None, ativo=None):
    q = db.query(ProblemaTipico).options(*load_options())
    if id_tipo_ativo: q = q.filter(ProblemaTipico.id_tipo_ativo == id_tipo_ativo)
    if sistema: q = q.filter(ProblemaTipico.sistema == sistema)
    if categoria: q = q.filter(ProblemaTipico.categoria == categoria)
    if criticidade: q = q.filter(ProblemaTipico.criticidade_padrao == criticidade)
    if especialidade: q = q.filter(ProblemaTipico.especialidade == especialidade)
    if risco_operacional: q = q.filter(ProblemaTipico.risco_operacional == risco_operacional)
    if status_validacao: q = q.filter(ProblemaTipico.status_validacao == status_validacao)
    if origem_registro: q = q.filter(ProblemaTipico.origem_registro == origem_registro)
    if ativo is not None: q = q.filter(ProblemaTipico.ativo == ativo)
    if busca:
        t = f"%{busca.strip()}%"
        # EXISTS por relacionamento: evita produto cartesiano entre as listas.
        q = q.filter(or_(
            ProblemaTipico.codigo.ilike(t),
            ProblemaTipico.titulo.ilike(t),
            ProblemaTipico.descricao.ilike(t),
            ProblemaTipico.modo_falha.ilike(t),
            ProblemaTipico.efeito_falha.ilike(t),
            ProblemaTipico.sintomas.any(SintomaProblema.sintoma.ilike(t)),
            ProblemaTipico.causas.any(CausaProblema.causa.ilike(t)),
            ProblemaTipico.alarmes.any(AlarmeProblema.alarme.ilike(t)),
            ProblemaTipico.palavras_chave.any(PalavraChaveProblema.palavra_chave.ilike(t)),
        ))
    return q.order_by(ProblemaTipico.categoria, ProblemaTipico.titulo).all()


def opcoes(db):
    def distintos(coluna):
        return [v for (v,) in db.query(coluna).distinct().order_by(coluna) if v]

    return {
        "sistemas": distintos(ProblemaTipico.sistema),
        "categorias": distintos(ProblemaTipico.categoria),
        "especialidades": distintos(ProblemaTipico.especialidade),
        "status_validacao": [s.value for s in StatusValidacaoProblema],
        "riscos_operacionais": ["BAIXO", "MEDIO", "ALTO"],
    }


def estatisticas(db):
    por_categoria = [
        {"categoria": categoria, "total": total}
        for categoria, total in db.query(ProblemaTipico.categoria, func.count(ProblemaTipico.id_problema))
        .group_by(ProblemaTipico.categoria)
        .order_by(ProblemaTipico.categoria)
    ]
    por_criticidade = {
        (c.value if hasattr(c, "value") else c): total
        for c, total in db.query(ProblemaTipico.criticidade_padrao, func.count(ProblemaTipico.id_problema))
        .group_by(ProblemaTipico.criticidade_padrao)
    }
    por_status = {
        (c.value if hasattr(c, "value") else c): total
        for c, total in db.query(ProblemaTipico.status_validacao, func.count(ProblemaTipico.id_problema))
        .group_by(ProblemaTipico.status_validacao)
    }
    return {
        "total": db.query(func.count(ProblemaTipico.id_problema)).scalar() or 0,
        "por_categoria": por_categoria,
        "por_criticidade": por_criticidade,
        "por_status_validacao": por_status,
    }


def sincronizar_ss(db, ss, itens):
    ss.problemas.clear(); db.flush()
    ids = set()
    for item in itens:
        data = item.model_dump()
        if data["id_problema"] in ids: raise HTTPException(400, "Problema duplicado na SS")
        ids.add(data["id_problema"])
        p = consultar(db, data["id_problema"])
        id_tipo = db.query(Ativo.id_tipo_ativo).filter(Ativo.id_ativo == ss.id_ativo).scalar() if ss.id_ativo else db.query(GrupoAtivo.id_tipo_ativo).filter(GrupoAtivo.id_grupo_ativo == ss.id_grupo_ativo).scalar()
        if id_tipo and p.id_tipo_ativo != id_tipo: raise HTTPException(400, f"Problema '{p.titulo}' incompatível com o tipo do ativo")
        ss.problemas.append(SSProblema(**data))
