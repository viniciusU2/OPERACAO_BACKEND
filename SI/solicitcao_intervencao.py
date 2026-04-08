from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.SI_models import solicitacao_intervencao
from models.instalacao_models import Subestacao
from models.Ativo import Ativo
from SI.schemas import SICreate, SIResponse, SIUpdate

import os
import shutil
import re
from datetime import datetime

from fastapi.responses import FileResponse
from openpyxl import load_workbook
from openpyxl.drawing.image import Image

router = APIRouter(prefix="/si", tags=["Serviço Intervenção"])


# ==============================
# 🔹 UTIL
# ==============================
def nome_arquivo_seguro(texto: str):
    if not texto:
        return "sem_nome"
    
    # 🔥 AGORA permite ponto
    return re.sub(r'[^A-Za-z0-9_.-]', '_', texto)


def limpar(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return str(valor)

from openpyxl.utils import range_boundaries

def set_valor_seguro(ws, celula, valor):
    for merged_range in ws.merged_cells.ranges:
        if celula in merged_range:
            min_col, min_row, _, _ = range_boundaries(str(merged_range))
            ws.cell(row=min_row, column=min_col).value = valor
            return
    ws[celula] = valor


# ==============================
# 🔹 MAPEAMENTO
# ==============================
MAPEAMENTO_CELULAS = {
    "NUM_SI": "H1",
    "NUM_SGI": "H3",
    "ESPECIE": "G5",
    "NUM_APR": "A5",
    "INSTALACAO": "A7",
    "LOCALIZACAO": "D7",
    "CODIGO_ATIVO": "G7",
    "NATUREZA": "A9",
    "CARACTERISTICA_INTERVENCAO": "D9",
    "TIPO": "G9",
    "DOCUMENTOS_REFERENCIA": "A11",
    "DT_INICIO_PRERIODO_TOTAL": "A13",
    "DT_FIM_PRERIODO_TOTAL": "F13",
    "DT_INICIO_MANUTENCAO_TOTAL": "A15",
    "DT_FIM_MANUTENCAO_TOTAL": "F15",
    "JUSTIFICATIVA_PARA_SOLICITACOES_FORA_DOS_PRAZOS": "A17",
    "RESPONSAVEL": "A19",
    "SUBSTITUTO": "F19",
    "DESC_SERVICOS": "A27",
    "OBSERVACOES": "A29",
    "CABOS_DE_ATERRAMENTO": "A31",
    "RISCOS_DE_DESLIGAMENTO": "C33",
    "DEPENDE_DE_CONDICOES_CLIMATICAS": "C36",
    "EXECUCAO_PERIODO_NOTURNO": "C39",
    "RESPONSAVEL_MANUTENCAO_ONS": "B42",
    "RESPONSAVEL_MANUTENCAO_COT": "E42",
    "RESPONSAVEL_MANUTENCAO_SE": "H42",
    "RESPONSAVEL_DATA_MANUTENCAO_ONS": "B43",
    "RESPONSAVEL_DATA_MANUTENCAO_COT": "E43",
    "RESPONSAVEL_DATAMANUTENCAO_SE": "H43",
    "RESPONSAVEL_OPERACAO_ONS": "H52",
    "RESPONSAVEL_OPERACAO_COT": "E52",
    "RESPONSAVEL_OPERACAO_SE": "B52",
    "RESPONSAVEL_DATA_OPERACAO_ONS": "H53",
    "RESPONSAVEL_DATA_OPERACAO_COT": "E53",
    "RESPONSAVEL_DATA_OPERACAO_SE": "B53",
}


# ==============================
# 🔹 GERAR XLSX
# ==============================
def gerar_xlsm(modelo, destino, contexto, mapeamento):

    print("Destino:", destino)
    print("Existe:", os.path.exists(destino))
    print("Tamanho:", os.path.getsize(destino) if os.path.exists(destino) else "N/A")

    if os.path.exists(destino):
        os.remove(destino)

    shutil.copy(modelo, destino)

    wb = load_workbook(destino)
    ws = wb.active

    img = Image("modelos/logo.jpg")
    img.width = 150
    img.height = 45

    ws.add_image(img, "A1")

    for campo, celula in mapeamento.items():
        valor = contexto.get(campo, "")
        set_valor_seguro(ws, celula, valor)

    wb.save(destino)


# ==============================
# 🔹 CONTEXTO
# ==============================
def montar_contexto_si(si, ativo=None, sub=None):

    return {
        "NUM_SI": limpar(si.numero_si),
        "NUM_SGI": limpar(getattr(si, "numero_sgi", "")),
        "ESPECIE": limpar(si.especie),
        "NUM_APR": limpar(si.numero_apr),

        "INSTALACAO": limpar(sub.nome if sub else ""),
        "LOCALIZACAO": "",
        "CODIGO_ATIVO": limpar(ativo.codigo_ativo if ativo else ""),

        "NATUREZA": limpar(getattr(si, "natureza", "")),
        "CARACTERISTICA_INTERVENCAO": limpar(getattr(si, "caracteristica_intervencao", "")),
        "TIPO": limpar(getattr(si, "tipo", "")),
        "DOCUMENTOS_REFERENCIA": limpar(getattr(si, "documentos_referencia", "")),

        "DT_INICIO_PRERIODO_TOTAL": limpar(getattr(si, "data_inicio_periodo_total", None)),
        "DT_FIM_PRERIODO_TOTAL": limpar(getattr(si, "data_fim_periodo_total", None)),
        "DT_INICIO_MANUTENCAO_TOTAL": limpar(getattr(si, "data_inicio_manutencao_total", None)),
        "DT_FIM_MANUTENCAO_TOTAL": limpar(getattr(si, "data_fim_manutencao_total", None)),

        "JUSTIFICATIVA_PARA_SOLICITACOES_FORA_DOS_PRAZOS": limpar(getattr(si, "justificativa", "")),

        "RESPONSAVEL": limpar(si.responsavel),
        "SUBSTITUTO": limpar(si.substituto),

        "DESC_SERVICOS": limpar(si.descricao_servicos),
        "OBSERVACOES": limpar(si.observacoes),
    }


# ==============================
# 🔹 CRIAR
# ==============================
@router.post("", response_model=SIResponse)
def criar_si(dados: SICreate, db: Session = Depends(get_db)):

    nova_si = solicitacao_intervencao(**dados.dict())

    db.add(nova_si)
    db.commit()
    db.refresh(nova_si)

    return nova_si


# ==============================
# 🔹 LISTAR
# ==============================
@router.get("", response_model=list[SIResponse])
def listar_si(db: Session = Depends(get_db)):
    return db.query(solicitacao_intervencao).all()


# ==============================
# 🔹 BUSCAR
# ==============================
@router.get("/{id_si}", response_model=SIResponse)
def buscar_si(id_si: int, db: Session = Depends(get_db)):

    si = db.query(solicitacao_intervencao).filter(
        solicitacao_intervencao.id_si == id_si
    ).first()

    if not si:
        raise HTTPException(404, "SI não encontrada")

    return si


# ==============================
# 🔹 EDITAR
# ==============================
@router.put("/{id_si}", response_model=SIResponse)
def editar_si(id_si: int, dados: SIUpdate, db: Session = Depends(get_db)):

    si = db.query(solicitacao_intervencao).filter(
        solicitacao_intervencao.id_si == id_si
    ).first()

    if not si:
        raise HTTPException(404, "SI não encontrada")

    for campo, valor in dados.dict(exclude_unset=True).items():
        setattr(si, campo, valor)

    db.commit()
    db.refresh(si)

    return si


# ==============================
# 🔹 DELETAR
# ==============================
@router.delete("/{id_si}")
def deletar_si(id_si: int, db: Session = Depends(get_db)):

    si = db.query(solicitacao_intervencao).filter(
        solicitacao_intervencao.id_si == id_si
    ).first()

    if not si:
        raise HTTPException(404, "SI não encontrada")

    db.delete(si)
    db.commit()

    return {"message": "SI deletada com sucesso"}


# ==============================
# 🔹 DOWNLOAD
# ==============================
@router.get("/{id_si}/download")
def download_si(id_si: int, db: Session = Depends(get_db)):

    si = db.query(solicitacao_intervencao).filter(
        solicitacao_intervencao.id_si == id_si
    ).first()

    if not si:
        raise HTTPException(404, "SI não encontrada")

    ativo = db.query(Ativo).filter(
        Ativo.id_ativo == si.id_ativo
    ).first() if si.id_ativo else None

    sub = db.query(Subestacao).filter(
        Subestacao.id_subestacao == si.id_subestacao
    ).first() if si.id_subestacao else None

    contexto = montar_contexto_si(si, ativo, sub)

    pasta_saida = "saida"
    os.makedirs(pasta_saida, exist_ok=True)

    nome_arquivo = nome_arquivo_seguro(f"{si.numero_si}.xlsx")
    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

    gerar_xlsm(
        modelo="modelos/MODELO_SI.xlsx",
        destino=caminho_saida,
        contexto=contexto,
        mapeamento=MAPEAMENTO_CELULAS
    )

    return FileResponse(
        path=caminho_saida,
        filename=nome_arquivo,
        media_type="application/octet-stream"
    )