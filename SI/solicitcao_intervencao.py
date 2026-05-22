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

SUBESTACOES_SIGLAS = ["BJD", "GDO", "JAB"]


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


def sigla_por_subestacao(id_subestacao: int | None):
    if not id_subestacao:
        return "GERAL"

    try:
        return SUBESTACOES_SIGLAS[id_subestacao - 1]
    except IndexError:
        return "GERAL"


def gerar_numero_si(db: Session, sigla: str):
    ano_atual = datetime.now().year
    registros = (
        db.query(solicitacao_intervencao.numero_si)
        .filter(solicitacao_intervencao.numero_si.like(f"%{sigla}%{ano_atual}%"))
        .all()
    )

    numeros = []
    for (numero_si,) in registros:
        numero_si = numero_si or ""
        if sigla not in numero_si:
            continue
        match = re.search(rf"(\d+)-{ano_atual}", numero_si)
        if match:
            numeros.append(int(match.group(1)))

    proximo = max(numeros) + 1 if numeros else 1
    return f"SI-{sigla}-{str(proximo).zfill(4)}-{ano_atual}"


# ==============================
# 🔹 MAPEAMENTO
# ==============================
MAPEAMENTO_CELULAS = {
    "NUM_SI": "H1",
    "NUM_SGI": "H3",
    "NUM_APR": "A5",
    "NUM_OS": "C5",
    "ESPECIE": "G5",
    "INSTALACAO": "A7",
    "LOCALIZACAO": "D7",
    "CODIGO_ATIVO": "G7",
    "NATUREZA": "A9",
    "CARACTERISTICA_INTERVENCAO": "D9",
    "TIPO": "G9",
    "DOCUMENTOS_REFERENCIA": "A11",
    "DT_INICIO_PRERIODO_TOTAL": "A13",
    "DT_FIM_PRERIODO_TOTAL": "F13",
    "DT_INICIO_PRERIODO_MANUTENCAO": "A15",
    "DT_FIM_PRERIODO_MANUTENCAO": "F15",
    "JUSTIFICATIVA": "A17",
    "RESPONSAVEL": "A19",
    "SUBSTITUTO": "F19",
    "APROVEITAMENTO": "A21",
    "INCLUSAO_SERVICO": "E21",
    "ORGAOS": "I21",
    "TIPO_PROGRAMACAO": "A24",
    "DIAS_EXCECAO": "C24",
    "TEMPO_RETORNO": "F24",
    "DESC_SERVICOS": "A27",
    "OBSERVACOES": "A29",
    "CABO_ATERRAMENTO": "A31",
    "RISCO_DESLIGAMENTO": "A33",
    "CONDICOES_CLIMATICAS": "A36",
    "EXECUCAO_PERIODO_NOTURNO": "A39",
    "RESPONSAVEL_MANUTENCAO_ONS": "B42",
    "RESPONSAVEL_MANUTENCAO_COT": "E42",
    "RESPONSAVEL_MANUTENCAO_SE": "H42",
    "RESPONSAVEL_DATA_MANUTENCAO_ONS": "B43",
    "RESPONSAVEL_DATA_MANUTENCAO_COT": "E43",
    "RESPONSAVEL_DATA_MANUTENCAO_SE": "H43",
    "ASSINATURA_MANUTENCAO": "D44",
    "STATUS_MANUTENCAO": "H44",
    "DATA_MANUTENCAO": "D45",
    "RESPONSAVEL_OPERACAO_SE": "B52",
    "RESPONSAVEL_OPERACAO_COT": "E52",
    "RESPONSAVEL_OPERACAO_ONS": "H52",
    "ASSINATURA_OPERACAO": "D50",
    "STATUS_OPERACAO": "H50",
    "DATA_OPERACAO": "D51",
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
    def primeiro(*valores):
        for valor in valores:
            if valor not in (None, ""):
                return valor
        return ""

    def sim_nao(valor):
        if valor in (None, ""):
            return ""
        return str(valor).replace("NAO", "NÃO")

    localizacao = ""
    if ativo:
        localizacao = " - ".join(
            str(valor)
            for valor in (ativo.codigo_ativo, ativo.fase, ativo.vao)
            if valor not in (None, "")
        )

    tempo_retorno = limpar(getattr(si, "tempo_retorno", ""))
    disponivel = limpar(getattr(si, "disponivel", ""))
    if tempo_retorno and disponivel:
        tempo_retorno = f"{tempo_retorno} | Disponível: {disponivel}"
    elif disponivel:
        tempo_retorno = f"Disponível: {disponivel}"

    return {
        "NUM_SI": limpar(si.numero_si),
        "NUM_SGI": limpar(getattr(si, "numero_sgi", "")),
        "NUM_OS": limpar(getattr(si, "numero_os", "")),
        "NUM_APR": limpar(si.numero_apr),
        "ESPECIE": limpar(si.especie),

        "INSTALACAO": limpar(sub.nome if sub else ""),
        "LOCALIZACAO": limpar(localizacao),
        "CODIGO_ATIVO": limpar(ativo.codigo_ativo if ativo else ""),

        "NATUREZA": limpar(getattr(si, "natureza", "")),
        "CARACTERISTICA_INTERVENCAO": limpar(getattr(si, "caracteristica_intervencao", "")),
        "TIPO": limpar(getattr(si, "tipo", "")),
        "DOCUMENTOS_REFERENCIA": limpar(getattr(si, "documentos_referencia", "")),

        "DT_INICIO_PRERIODO_TOTAL": limpar(si.data_inicio_preriodo_total),
        "DT_FIM_PRERIODO_TOTAL": limpar(si.data_fim_preriodo_total),
        "DT_INICIO_PRERIODO_MANUTENCAO": limpar(si.data_inicio_preriodo_manutencao),
        "DT_FIM_PRERIODO_MANUTENCAO": limpar(si.data_fim_preriodo_manutencao),

        "JUSTIFICATIVA": limpar(getattr(si, "justificativa", "")),

        "RESPONSAVEL": limpar(si.responsavel),
        "SUBSTITUTO": limpar(si.substituto),

        "APROVEITAMENTO": sim_nao(getattr(si, "aproveitamento", "")),
        "INCLUSAO_SERVICO": sim_nao(getattr(si, "inclusao_servico", "")),
        "ORGAOS": limpar(getattr(si, "orgaos", "")),
        "TIPO_PROGRAMACAO": limpar(primeiro(
            getattr(si, "tipo_programacao", ""),
            getattr(si, "tipo_progrmacao", ""),
        )),
        "DIAS_EXCECAO": limpar(getattr(si, "dias_excecao", "")),
        "TEMPO_RETORNO": tempo_retorno,

        "DESC_SERVICOS": limpar(si.descricao_servicos),
        "OBSERVACOES": limpar(si.observacoes),
        "CABO_ATERRAMENTO": limpar(getattr(si, "cabo_aterramento", "")),
        "RISCO_DESLIGAMENTO": sim_nao(getattr(si, "risco_desligamento", "")),
        "CONDICOES_CLIMATICAS": sim_nao(getattr(si, "condicoes_climaticas", "")),
        "EXECUCAO_PERIODO_NOTURNO": sim_nao(getattr(si, "execucao_periodo_noturno", "")),

        "RESPONSAVEL_MANUTENCAO_ONS": limpar(si.responsavel_ons_manutencao),
        "RESPONSAVEL_MANUTENCAO_COT": limpar(si.responsavel_cot_manutencao),
        "RESPONSAVEL_MANUTENCAO_SE": limpar(si.responsavel_se_manutencao),
        "RESPONSAVEL_DATA_MANUTENCAO_ONS": limpar(si.responsavel_data_ons_manutencao),
        "RESPONSAVEL_DATA_MANUTENCAO_COT": limpar(si.responsavel_data_cot_manutencao),
        "RESPONSAVEL_DATA_MANUTENCAO_SE": limpar(si.responsavel_data_se_manutencao),
        "ASSINATURA_MANUTENCAO": limpar(primeiro(
            si.responsavel_se_manutencao,
            si.responsavel_cot_manutencao,
            si.responsavel_ons_manutencao,
        )),
        "STATUS_MANUTENCAO": limpar(si.status_manutencao),
        "DATA_MANUTENCAO": limpar(primeiro(
            si.responsavel_data_se_manutencao,
            si.responsavel_data_cot_manutencao,
            si.responsavel_data_ons_manutencao,
        )),

        "RESPONSAVEL_OPERACAO_SE": limpar(si.responsavel_se_operacao),
        "RESPONSAVEL_OPERACAO_COT": limpar(si.responsavel_cot_operacao),
        "RESPONSAVEL_OPERACAO_ONS": limpar(si.responsavel_ons_operacao),
        "ASSINATURA_OPERACAO": limpar(primeiro(
            si.responsavel_se_operacao,
            si.responsavel_cot_operacao,
            si.responsavel_ons_operacao,
        )),
        "STATUS_OPERACAO": limpar(si.status_operacao),
        "DATA_OPERACAO": limpar(primeiro(
            si.responsavel_data_se_operacao,
            si.responsavel_data_cot_operacao,
            si.responsavel_data_ons_operacao,
        )),
    }


# ==============================
# 🔹 CRIAR
# ==============================
@router.post("", response_model=SIResponse)
def criar_si(dados: SICreate, db: Session = Depends(get_db)):

    data = dados.dict()
    if not data.get("numero_si"):
        data["numero_si"] = gerar_numero_si(
            db,
            sigla_por_subestacao(data.get("id_subestacao")),
        )

    nova_si = solicitacao_intervencao(**data)

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
