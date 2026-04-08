from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pymysql import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from models.OS_models import OrdemServico
from OS.schemas import OrdemServicoCreate, OrdemServicoCreateLote, OrdemServicoResponse, OrdemServicoUpdate
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.Ativo import Ativo
from models.instalacao_models import Subestacao
from models import OS_models
from openpyxl import load_workbook
from openpyxl.drawing.image import Image
import shutil
from datetime import datetime
import os
import re
from fastapi.background import BackgroundTasks





router = APIRouter(prefix="/os", tags=["Ordem de Serviço"])

def remover_arquivo(path: str):
    if os.path.exists(path):
        os.remove(path)


def nome_arquivo_seguro(texto: str):
    if not texto:
        return "sem_nome"
    
    # substitui tudo que não for letra/número por _
    return re.sub(r'[^A-Za-z0-9_-]', '_', texto)

MAPEAMENTO_CELULAS = {
    "NUM_OS": "H1",
    "NUM_SI": "H2",
    "ESPECIE": "A4",
    "CODIGO_ATIVO": "D4",
    "NUM_APR": "G4",
    "INSTALACAO": "A6",
    "LOCALIZACAO": "D6",
    "COMPLEMENTO": "G6",
    "ORIGENS": "A8",
    "DEFEITO": "F8",
    "ESQUEMA_SERVICOS": "A10",
    "PRIORIDADES": "F10",
    "RESPONSAVEL": "A12",
    "RESPONSAVEL_MANUTENCAO": "D26",
    "RESPONSAVEL_OPERACAO": "D32",
    "SUBSTITUTO": "F12",
    "DT_INICIO_PROGRAMADO": "A14",
    "DT_FIM_PROGRAMADO": "F14",
    "DESC_SERVICOS": "A16",
    "OBSERVACOES": "A18",
    "CAUSAS": "A20",
    "CAUSAS_SEC": "F20",
    "DT_ABERTURA_SS": "A22",
    "DT_INICIO_EXEC": "D22",
    "DT_FIM_EXEC": "G22",
    "DT_INICIO_EXEC2": "D27",
    "DT_FIM_EXEC2": "D33",
    "CENTRO_CUSTOS": "A24",
   
}


def limpar(valor):
    if valor is None:

        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return str(valor)

def gerar_xlsm(modelo, destino, contexto, mapeamento):
    shutil.copy(modelo, destino)
    img = Image("modelos/logo.jpg")  # caminho da sua logo
    # 🔽 Redimensiona a imagem
    img.width = 150
    img.height = 45

    wb = load_workbook(destino, keep_vba=True)
    ws = wb.active
    ws.add_image(img, "A1")
    
    if contexto.get("STATUS", "") == "ENCERRADA":
     ws["H26"] = "INICIADA"
     ws["H32"] = "ENCERRADA"

    for campo, celula in mapeamento.items():
        ws[celula] = contexto.get(campo, "")

    wb.save(destino)

def montar_contexto_os(os, ativo=None):

    codigo_ativo = None

    if ativo:
        codigo_ativo = ativo.codigo_ativo
        local =  ativo.vao
        fase = ativo.fase
    return {
        # ================= IDENTIFICAÇÃO =================
        "NUM_OS": limpar(os.numero_os),
        "NUM_SI": limpar(os.numero_si),
        "ESPECIE": limpar(os.especie),

        # 🔥 AQUI ESTÁ A MÁGICA
        "CODIGO_ATIVO": limpar(codigo_ativo),

        "NUM_APR": limpar(os.numero_apr),

        # ================= LOCALIZAÇÃO =================
        "INSTALACAO": limpar(os.instalacao),
        "LOCALIZACAO": limpar(local),
        "COMPLEMENTO": limpar(fase),

        # ================= DESCRIÇÃO =================
        "ORIGENS": limpar(os.origens),
        "DEFEITO": limpar(os.defeito),
        "ESQUEMA_SERVICOS": limpar(os.esquema_servicos),
        "DESC_SERVICOS": limpar(os.descricao_servicos),
        "OBSERVACOES": limpar(os.observacoes),

        # ================= CAUSAS =================
        "CAUSAS": limpar(os.causa_primaria),
        "CAUSAS_SEC": limpar(os.causa_secundaria),

        # ================= CONTROLE =================
        "PRIORIDADES": limpar(os.prioridade),
        "RESPONSAVEL": limpar(os.responsavel),
        "SUBSTITUTO": limpar(os.substituto),
        "RESPONSAVEL_MANUTENCAO": limpar(os.responsavel_manutencao),
        "RESPONSAVEL_OPERACAO": limpar(os.responsavel_operacao),
        "CENTRO_CUSTOS": limpar(os.centro_custos),
      

        # ================= DATAS =================
        "DT_ABERTURA_SS": limpar(os.data_abertura_ss),
        "DT_INICIO_PROGRAMADO": limpar(os.data_inicio_programado),
        "DT_FIM_PROGRAMADO": limpar(os.data_fim_programado),
        "DT_INICIO_EXEC": limpar(os.data_inicio_execucao),
        "DT_FIM_EXEC": limpar(os.data_fim_execucao),
        "DT_INICIO_EXEC2": limpar(os.data_inicio_execucao),
        "DT_FIM_EXEC2": limpar(os.data_fim_execucao),
        "STATUS": limpar(os.status),  # ✅ AQUI
    }
# ---------------- ORDEM DE SERVIÇO ----------------
@router.post("", response_model=OrdemServicoCreate)
def criar_ordem_servico(
    os_data: OrdemServicoCreate,
    db: Session = Depends(get_db)

    
):
    
    if (
    os_data.data_inicio_programado
    and os_data.data_fim_programado
    and os_data.data_fim_programado < os_data.data_inicio_programado
):
        raise HTTPException(
            status_code=400,
            detail="Data final não pode ser anterior à data inicial"
        )
    # 🔹 Validação de Subestação
    if os_data.id_subestacao:
        sub = db.query(Subestacao).filter(
            Subestacao.id_subestacao == os_data.id_subestacao
        ).first()
  
        os_data.instalacao = sub.nome  # ✅ objeto SQLAlchemy


        if not sub:
            raise HTTPException(
                status_code=400,
                detail="Subestação inválida"
            )

    # 🔹 Validação de Ativo
    ativo = None
    if os_data.id_ativo:
        ativo = db.query(Ativo).filter(
            Ativo.id_ativo == os_data.id_ativo
        ).first()

        if not ativo:
            raise HTTPException(
                status_code=400,
                detail="Ativo inválido"
            )
        

 

    data = os_data.dict(exclude={"codigo_ativo"}) # 👈 REMOVE
    nova_os = OS_models.OrdemServico(**data)

    db.add(nova_os)
    db.commit()
    db.refresh(nova_os)



    # -------------------------
    # 🔥 GERAR XLSM AQUI
    # -------------------------

    pasta_saida = "saida"
    os.makedirs(pasta_saida, exist_ok=True)

    contexto = montar_contexto_os(os_data, ativo)

    numero_os_safe = nome_arquivo_seguro(nova_os.numero_os)

    nome_arquivo = f"{numero_os_safe}.xlsm"

  
    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

    gerar_xlsm(
        modelo="modelos/MODELO_OS.xlsx",
        destino=caminho_saida,
        contexto=contexto,
        mapeamento=MAPEAMENTO_CELULAS
    )

    return nova_os

from fastapi.responses import FileResponse

@router.get("/{id_os}/download")
def baixar_os(id_os: int, db: Session = Depends(get_db)):

    # 🔹 Buscar OS
    os_db = (
        db.query(OS_models.OrdemServico)
        .filter(OS_models.OrdemServico.id_os == id_os)
        .first()
    )

    if not os_db:
        raise HTTPException(
            status_code=404,
            detail="OS não encontrada"
        )

    # 🔹 Buscar ativo (se existir)
    ativo = None
    if os_db.id_ativo:
        ativo = db.query(Ativo).filter(
            Ativo.id_ativo == os_db.id_ativo
        ).first()

    # 🔹 Montar contexto
    contexto = montar_contexto_os(os_db, ativo)

    # 🔹 Nome seguro
    numero_os_safe = nome_arquivo_seguro(os_db.numero_os)
    nome_arquivo = f"{numero_os_safe}.xlsm"

    # 🔹 Caminho temporário
    pasta_temp = "temp"
    os.makedirs(pasta_temp, exist_ok=True)

    caminho_saida = os.path.join(pasta_temp, nome_arquivo)

    # 🔹 Gerar arquivo na hora
    gerar_xlsm(
        modelo="modelos/MODELO_OS.xlsx",  # ⚠️ importante ser XLSM
        destino=caminho_saida,
        contexto=contexto,
        mapeamento=MAPEAMENTO_CELULAS
    )

    # 🔹 Retornar arquivo
    return FileResponse(
        path=caminho_saida,
        filename=nome_arquivo,
        media_type="application/octet-stream"
    )


@router.get("")
def listar_os(
    id_ativo: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(OS_models.OrdemServico)

    if id_ativo:
        query = query.filter(
            OS_models.OrdemServico.id_ativo == id_ativo
        )

    return query.all()

@router.get("/ativo/{id_ativo}")
def listar_os(
    id_ativo: int,
    db: Session = Depends(get_db)
):
    return (
        db.query(OS_models.OrdemServico)
        .filter(OS_models.OrdemServico.id_ativo == id_ativo)
        .all()
    )


@router.put("/{id_os}")
def editar_ordem_servico(
    id_os: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    os_db = (
        db.query(OS_models.OrdemServico)
        .filter(OS_models.OrdemServico.id_os == id_os)
        .first()
    )

    if not os_db:
        raise HTTPException(
            status_code=404,
            detail="Ordem de Serviço não encontrada"
        )


    # Atualiza campos primeiro
    for campo, valor in dados.items():
        if hasattr(os_db, campo):
            setattr(os_db, campo, valor)

    # Atualiza instalação baseado na subestação
    if "id_subestacao" in dados:
        sub = db.query(Subestacao).filter(
            Subestacao.id_subestacao == dados["id_subestacao"]  # ✅ CORRETO
        ).first()

        if not sub:
            raise HTTPException(400, "Subestação inválida")

        os_db.instalacao = sub.nome  # ✅ objeto SQLAlchemy

        


    try:
        db.commit()
        db.refresh(os_db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Número da OS já existe"
        )

    return os_db

@router.get("/{id_os}")
def buscar_os_por_id(
    id_os: int,
    db: Session = Depends(get_db)
):
    os = (
        db.query(OS_models.OrdemServico)
        .filter(OS_models.OrdemServico.id_os == id_os)
        .first()
    )

    if not os:
        raise HTTPException(
            status_code=404,
            detail="Os não encontrado"
        )

    return os

@router.delete("/{id_os}")
def deletar_os(id_os: int, db: Session = Depends(get_db)):

    os = db.query(OrdemServico).filter(
        OrdemServico.id_os == id_os
    ).first()

    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    db.delete(os)
    db.commit()

    return {"message": "OS excluída com sucesso"}




import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List

@router.post("/lote-por-tipo-ativo", response_model=List[OrdemServicoResponse])
def criar_os_lote_por_tipo_ativo(
    payload: OrdemServicoCreateLote,
    db: Session = Depends(get_db),
):
    # ====================== 1. VALIDAÇÃO E BUSCA DA SUBESTAÇÃO ======================
    if not payload.id_subestacao:
        raise HTTPException(status_code=400, detail="id_subestacao é obrigatório")

    subestacao = db.query(Subestacao).filter(
        Subestacao.id_subestacao == payload.id_subestacao
    ).first()

    if not subestacao:
        raise HTTPException(status_code=400, detail="Subestação inválida")

    instalacao_nome = subestacao.nome   # ← Aqui pegamos o nome real da subestação

    # ====================== 2. BUSCAR ATIVOS ======================
    ativos = db.query(Ativo).filter(
        Ativo.id_subestacao == payload.id_subestacao,
        Ativo.id_tipo_ativo == payload.id_tipo_ativo
    ).all()

    if not ativos:
        raise HTTPException(
            status_code=404,
            detail="Nenhum ativo encontrado para esse tipo na subestação."
        )

    # ====================== 3. ORDENAÇÃO CORRETA ======================
    ordem_fase = {"AZ": 1, "BR": 2, "VM": 3}

    def normalizar_fase(fase: str | None) -> str:
        return str(fase).strip().upper() if fase else ""

    def ordenar_codigo_ativo(codigo: str | None) -> tuple:
        if not codigo:
            return (999, "")
        codigo_str = str(codigo).strip().upper()
        match = re.match(r"(\d+)(.*)", codigo_str)
        if match:
            num = int(match.group(1))
            resto = match.group(2)
            return (num, resto)
        return (999, codigo_str)

    ativos.sort(
        key=lambda a: (
            ordenar_codigo_ativo(a.codigo_ativo),
            ordem_fase.get(normalizar_fase(a.fase), 99)
        )
    )

    # ====================== 4. GERAÇÃO DO NÚMERO OS ======================
    if not payload.numero_os:
        raise HTTPException(
            status_code=400,
            detail="numero_os inicial é obrigatório (ex: OS-RTV-BJD-0168-2026)"
        )

    padrao = r"^(.*-)(\d+)-(\d{4})$"
    match = re.match(padrao, payload.numero_os.strip())
    match2 = re.match(padrao, payload.numero_apr.strip())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Use: OS-RTV-BJD-0168-2026"
        )

    prefixo = match.group(1)
    prefixo2 = match2.group(1)

    numero_base = int(match.group(2))
    ano = match.group(3)
    padding = len(match.group(2))

    ordens_criadas = []

    # ====================== 5. CRIAR AS OS ======================
    for index, ativo in enumerate(ativos):
        numero_atual = numero_base + index
        numero_formatado = str(numero_atual).zfill(padding)

        numero_os_final = f"{prefixo}{numero_formatado}-{ano}-{ativo.codigo_ativo}"
        numero_apr_final = f"{prefixo2}-{numero_formatado}-{ano}"

        fase = normalizar_fase(ativo.fase)
        complemento = f"Fase: {fase}"
        local =  f"{ativo.vao}"

        nova_os = OS_models.OrdemServico(
            numero_os=numero_os_final,
            id_subestacao=payload.id_subestacao,
            id_ativo=ativo.id_ativo,
            especie=payload.especie or getattr(payload, "tipo_ativo", None),
            numero_si=payload.numero_si,
            numero_apr=numero_apr_final,

            # ✅ CORRIGIDO: Usa o nome da subestação real
            instalacao=instalacao_nome,
            localizacao=local,
            complemento=complemento,

            origens=payload.origens,
            defeito=payload.defeito,
            esquema_servicos=payload.esquema_servicos,
            causa_primaria=payload.causa_primaria,
            causa_secundaria=payload.causa_secundaria,

            prioridade=payload.prioridade,
            responsavel=payload.responsavel,
            responsavel_manutencao=payload.responsavel_manutencao,
            responsavel_operacao=payload.responsavel_operacao,
            substituto=payload.substituto,

            data_abertura_ss=payload.data_abertura_ss,
            data_inicio_programado=payload.data_inicio_programado,
            data_fim_programado=payload.data_fim_programado,

            descricao_servicos=payload.descricao_servicos,
            observacoes=payload.observacoes,
            centro_custos=payload.centro_custos or "RIALMA TRANSMISSORA V",
            status=payload.status or "ABERTA",
            emissor=payload.emissor,
        )

        try:
            db.add(nova_os)
            db.flush()

            # Gerar XLSM
            ativo_obj = db.query(Ativo).get(ativo.id_ativo)
            contexto = montar_contexto_os(nova_os, ativo_obj)

            pasta_saida = "saida"
            os.makedirs(pasta_saida, exist_ok=True)

            caminho_saida = os.path.join(pasta_saida, f"{nome_arquivo_seguro(nova_os.numero_os)}.xlsm")

            gerar_xlsm(
                modelo="modelos/MODELO_OS.xlsx",
                destino=caminho_saida,
                contexto=contexto,
                mapeamento=MAPEAMENTO_CELULAS
            )

            ordens_criadas.append(nova_os)

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar OS para {ativo.codigo_ativo} - Fase {fase}: {str(e)}"
            )

    db.commit()
    return ordens_criadas