"""Sincronização incremental dos dados offline do aplicativo móvel.

O aplicativo informa a data da última sincronização e o maior ID de cada
entidade já armazenado no aparelho. A API retorna apenas os registros novos
(ou atualizados quando a tabela possui marca de tempo), evitando baixar a base
inteira a cada sincronização.

As tabelas de referência (instalações, tipos de ativo, funções de operação,
grupos e problemas típicos) são pequenas e voltam sempre completas.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.Ativo import Ativo
from models.OS_models import OrdemServico
from models.SS_models import SolicitacaoServico
from models.plano_manutencao_models import PlanoManutencao, PlanoItem
from models.instalacao_models import Subestacao
from models.familias_models import TipoAtivo
from models.fo import FuncaoOperacao
from models.problemas_tipicos_models import ProblemaTipico

from ATIVO.schemas import AtivoResponse
from ATIVO.grupos_ativos import grupos_por_funcao
from Instalacao.schemas import SubestacaoResponse
from familias.schemas import TipoAtivoOut
from funcao_operacao.schemas import FuncaoOperacaoOut
from funcao_operacao.service import listar_funcoes_operacao
from OS.schemas import OrdemServicoResponse
from SS.schemas import SolicitacaoServicoResponse
from plano_manutencao.schemas import PlanoManutencaoRead, PlanoItemRead
from problemas_tipicos.schemas import ProblemaResponse


router = APIRouter(prefix="/sync", tags=["Sincronização"])


class SyncRequest(BaseModel):
    ultima_sincronizacao: Optional[datetime] = None
    max_ids: dict[str, int] = Field(default_factory=dict)
    contadores: dict[str, int] = Field(default_factory=dict)


class SyncResponse(BaseModel):
    ultima_sincronizacao: datetime
    completo: bool
    subestacoes: list[SubestacaoResponse]
    tipos_ativo: list[TipoAtivoOut]
    funcoes_operacao: list[FuncaoOperacaoOut]
    grupos_ativo: list[dict]
    problemas_tipicos: list[ProblemaResponse]
    ativos: list[AtivoResponse]
    ordens_servico: list[OrdemServicoResponse]
    solicitacoes_servico: list[SolicitacaoServicoResponse]
    planos_manutencao: list[PlanoManutencaoRead]
    plano_itens: list[PlanoItemRead]
    max_ids: dict[str, int]


def _max_id(max_ids: dict[str, int], chave: str) -> int:
    valor = max_ids.get(chave, 0)
    return valor if valor and valor > 0 else 0


@router.post("", response_model=SyncResponse)
def sincronizar(body: SyncRequest, db: Session = Depends(get_db)):
    ultima = body.ultima_sincronizacao
    max_ids = body.max_ids or {}
    completo = ultima is None and not max_ids

    # ===== Referência (volume pequeno, sempre completa) =====
    subestacoes = db.query(Subestacao).all()
    tipos = db.query(TipoAtivo).all()

    funcoes_orm = db.query(FuncaoOperacao).order_by(FuncaoOperacao.id_funcao_operacao).all()
    funcoes = listar_funcoes_operacao(db)

    grupos: list[dict] = []
    for funcao in funcoes_orm:
        grupos.extend(grupos_por_funcao(db, funcao.id_funcao_operacao))

    problemas = db.query(ProblemaTipico).order_by(ProblemaTipico.id_problema).all()

    # ===== Incremental (apenas registros novos/atualizados) =====
    ativos = (
        db.query(Ativo)
        .options(
            joinedload(Ativo.subestacao),
            joinedload(Ativo.tipo_ativo),
            joinedload(Ativo.funcao_operacao),
        )
        .filter(Ativo.id_ativo > _max_id(max_ids, "ativo"))
        .order_by(Ativo.id_ativo)
        .all()
    )

    max_id_os = _max_id(max_ids, "ordem_servico")
    os_filtro = OrdemServico.id_os > max_id_os
    if ultima is not None:
        os_filtro = os_filtro | (OrdemServico.criado_em > ultima)

    ordens = (
        db.query(OrdemServico)
        .options(
            joinedload(OrdemServico.ativo),
            joinedload(OrdemServico.grupo_ativo),
        )
        .filter(os_filtro)
        .order_by(OrdemServico.id_os)
        .all()
    )

    solicitacoes = (
        db.query(SolicitacaoServico)
        .options(
            selectinload(SolicitacaoServico.ativo),
            selectinload(SolicitacaoServico.grupo_ativo),
        )
        .filter(SolicitacaoServico.id > _max_id(max_ids, "solicitacao_servico"))
        .order_by(SolicitacaoServico.id)
        .all()
    )

    planos = (
        db.query(PlanoManutencao)
        .filter(PlanoManutencao.id_plano_manutencao > _max_id(max_ids, "plano_manutencao"))
        .order_by(PlanoManutencao.id_plano_manutencao)
        .all()
    )

    itens = (
        db.query(PlanoItem)
        .filter(PlanoItem.id_plano_item > _max_id(max_ids, "plano_item"))
        .order_by(PlanoItem.id_plano_item)
        .all()
    )

    return {
        "ultima_sincronizacao": datetime.now(timezone.utc).replace(tzinfo=None),
        "completo": completo,
        "subestacoes": subestacoes,
        "tipos_ativo": tipos,
        "funcoes_operacao": funcoes,
        "grupos_ativo": grupos,
        "problemas_tipicos": problemas,
        "ativos": ativos,
        "ordens_servico": ordens,
        "solicitacoes_servico": solicitacoes,
        "planos_manutencao": planos,
        "plano_itens": itens,
        "max_ids": {
            "ativo": max(a.id_ativo for a in ativos) if ativos else _max_id(max_ids, "ativo"),
            "ordem_servico": max(o.id_os for o in ordens) if ordens else _max_id(max_ids, "ordem_servico"),
            "solicitacao_servico": max(s.id for s in solicitacoes) if solicitacoes else _max_id(max_ids, "solicitacao_servico"),
            "plano_manutencao": max(p.id_plano_manutencao for p in planos) if planos else _max_id(max_ids, "plano_manutencao"),
            "plano_item": max(i.id_plano_item for i in itens) if itens else _max_id(max_ids, "plano_item"),
        },
    }
