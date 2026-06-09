from fastapi import APIRouter, Depends, HTTPException
from pymysql import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from ATIVO  import schemas
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.Ativo import Ativo
from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from models.instalacao_models import Subestacao
from models.familias_models import TipoAtivo
from collections import Counter


router = APIRouter(prefix="", tags=["ATIVO"])


def valor_texto(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).strip()
    return texto if texto and texto != "-" else None


def valor_decimal(valor):
    if pd.isna(valor):
        return None

    return float(valor)


def texto_vazio(valor):
    return valor is None or not str(valor).strip()


def normalizar_codigo_torre(codigo_linha: str, estrutura: str):
    estrutura_limpa = str(estrutura).strip()
    if estrutura_limpa.isdigit():
        estrutura_limpa = estrutura_limpa.zfill(3)

    return f"{codigo_linha.strip()}-T{estrutura_limpa}"


def garantir_colunas_torre(db: Session):
    colunas = {
        "codigo_linha": "VARCHAR(100) NULL",
        "estrutura_operacional": "VARCHAR(50) NULL",
        "vao_vante_m": "DECIMAL(10,3) NULL",
        "sentido": "VARCHAR(50) NULL",
        "tipo_estrutura": "VARCHAR(100) NULL",
    }

    existentes = {
        row[0]
        for row in db.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'ativo'
                """
            )
        ).all()
    }

    for coluna, definicao in colunas.items():
        if coluna not in existentes:
            db.execute(text(f"ALTER TABLE ativo ADD COLUMN {coluna} {definicao}"))


def get_or_create_instalacao_lt(db: Session, codigo_linha: str, sentido: str | None):
    nome = f"LT {codigo_linha.strip()}"
    instalacao = (
        db.query(Subestacao)
        .filter(Subestacao.nome == nome)
        .first()
    )

    if instalacao:
        return instalacao

    instalacao = Subestacao(
        nome=nome,
        localizacao=sentido,
        status="ATIVA",
    )
    db.add(instalacao)
    db.flush()

    return instalacao


def get_or_create_tipo_torre(db: Session, tipo_estrutura: str):
    nome = f"Torre {tipo_estrutura.strip()}"
    tipo = (
        db.query(TipoAtivo)
        .filter(TipoAtivo.nome == nome)
        .first()
    )

    if tipo:
        return tipo

    tipo = TipoAtivo(
        nome=nome,
        descricao=f"Torre de linha de transmissao - estrutura {tipo_estrutura.strip()}",
    )
    db.add(tipo)
    db.flush()

    return tipo


# ---------------- ATIVO ----------------
@router.post("/ativo", response_model=schemas.AtivoResponse)
def criar_ativo(
    ativo: schemas.AtivoCreate,
    db: Session = Depends(get_db)
):
    novo = Ativo(**ativo.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)  # 👈 MUITO IMPORTANTE
    return novo
@router.get("/ativo", response_model=List[schemas.AtivoResponse])
def listar_subestacoes(db: Session = Depends(get_db)):
    return db.query(Ativo).all()

@router.get("/ativos/{id_subestacao}", response_model=List[schemas.AtivoResponse])
def listar_ativos(
    id_subestacao: int,
    db: Session = Depends(get_db)
):
    query = db.query(Ativo)

    if id_subestacao:
        query = query.filter(
            Ativo.id_subestacao == id_subestacao
        )

    return query.all()




@router.get("/ativo/{id_ativo}", response_model=schemas.AtivoResponse)
def buscar_ativo_por_id(
    id_ativo: int,
    db: Session = Depends(get_db)
):
    ativo = (
        db.query(Ativo)
        .filter(Ativo.id_ativo == id_ativo)
        .first()
    )

    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    return ativo




@router.put("/ativos/{id_ativo}")
def editar_ativo(
    id_ativo: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    ativo_db = (
        db.query(Ativo)
        .filter(Ativo.id_ativo == id_ativo)
        .first()
    )

    if not ativo_db:
        raise HTTPException(
            status_code=404,
            detail="Ordem de Serviço não encontrada"
        )

    # Atualiza apenas os campos enviados
    for campo, valor in dados.items():
        if hasattr(ativo_db, campo):
            setattr(ativo_db, campo, valor)

    try:
        db.commit()
        db.refresh(ativo_db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Número da OS já existe"
        )

    return ativo_db


def pontuacao_referencia(ativo, referencia):
    pontos = 0

    if ativo.codigo_ativo and ativo.codigo_ativo == referencia.codigo_ativo:
        pontos += 4
    if ativo.vao and ativo.vao == referencia.vao:
        pontos += 2
    if ativo.fase and ativo.fase == referencia.fase:
        pontos += 2
    if ativo.tensao_nominal_kv and referencia.tensao_nominal_kv:
        if float(ativo.tensao_nominal_kv) == float(referencia.tensao_nominal_kv):
            pontos += 2

    return pontos


@router.post("/ativos/atualizar-fabricantes-gor")
def atualizar_fabricantes_gor(
    id_subestacao_gor: int = 2,
    db: Session = Depends(get_db)
):
    referencias = [
        ativo
        for ativo in db.query(Ativo).filter(Ativo.id_subestacao != id_subestacao_gor).all()
        if not texto_vazio(ativo.fabricante)
    ]

    faltantes = [
        ativo
        for ativo in db.query(Ativo).filter(Ativo.id_subestacao == id_subestacao_gor).all()
        if texto_vazio(ativo.fabricante)
    ]

    fabricantes_por_tipo = {}
    for tipo_id in {ref.id_tipo_ativo for ref in referencias}:
        fabricantes = [
            str(ref.fabricante).strip()
            for ref in referencias
            if ref.id_tipo_ativo == tipo_id and not texto_vazio(ref.fabricante)
        ]
        if fabricantes:
            fabricantes_por_tipo[tipo_id] = Counter(fabricantes).most_common(1)[0][0]

    atualizados = 0
    sem_referencia = []

    for ativo in faltantes:
        candidatos = [
            ref
            for ref in referencias
            if ref.id_tipo_ativo == ativo.id_tipo_ativo
        ]
        candidatos = sorted(
            candidatos,
            key=lambda ref: pontuacao_referencia(ativo, ref),
            reverse=True,
        )

        melhor = candidatos[0] if candidatos and pontuacao_referencia(ativo, candidatos[0]) > 0 else None
        fabricante = getattr(melhor, "fabricante", None) or fabricantes_por_tipo.get(ativo.id_tipo_ativo)

        if texto_vazio(fabricante):
            sem_referencia.append(ativo.codigo_ativo)
            continue

        ativo.fabricante = str(fabricante).strip()
        atualizados += 1

    db.commit()

    return {
        "mensagem": "Fabricantes da GOR atualizados",
        "id_subestacao_gor": id_subestacao_gor,
        "ativos_sem_fabricante_encontrados": len(faltantes),
        "fabricantes_atualizados": atualizados,
        "sem_referencia": sem_referencia,
    }







@router.post("/ativos/importar-xlsx")
async def importar_ativos(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_excel(file.file)

        # 🔴 Validar colunas obrigatórias
        colunas_obrigatorias = [
            "id_subestacao",
            "id_tipo_ativo",
            "codigo_ativo",
            "vao",
            "fase"
        ]

        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Coluna obrigatória ausente: {col}"
                )

        ativos = []

        for i, row in df.iterrows():
            # ⚠️ ignorar linhas vazias
            if pd.isna(row["codigo_ativo"]):
                continue

            ativo = Ativo(
                id_subestacao=int(row["id_subestacao"]),
                id_tipo_ativo=int(row["id_tipo_ativo"]),
                codigo_ativo=str(row["codigo_ativo"]),
                vao=str(row["vao"]) if pd.notna(row["vao"]) else None,
                numero_serie=str(row["numero_serie"]) if pd.notna(row["numero_serie"]) else None,
                fabricante=str(row["fabricante"]) if pd.notna(row["fabricante"]) else None,


                fase=str(row["fase"]) if pd.notna(row["fase"]) else None,
                status="ATIVO"
            )

            ativos.append(ativo)

        # 🚀 inserção em lote (mais rápido)
        db.bulk_save_objects(ativos)
        db.commit()

        return {
            "msg": f"{len(ativos)} ativos importados com sucesso"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ativos/importar-torres-xlsx")
async def importar_torres(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        garantir_colunas_torre(db)

        df = pd.read_excel(file.file, usecols="A:G")
        df.columns = [str(col).strip().lower() for col in df.columns]

        colunas_obrigatorias = [
            "estrutura operacional",
            "vao vante (m)",
            "codigo_ativo",
            "id_linha de transmissão",
            "id_tipo_ativo",
            "tipo",
            "sentido",
        ]

        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Coluna obrigatoria ausente: {col}"
                )

        criadas = 0
        atualizadas = 0
        ignoradas = 0
        instalacoes_criadas = set()
        tipos_criados = set()

        for _, row in df.iterrows():
            estrutura = valor_texto(row["estrutura operacional"])
            codigo_linha = valor_texto(row["codigo_ativo"])
            tipo_estrutura = valor_texto(row["tipo"])
            sentido = valor_texto(row["sentido"])

            if not estrutura or not codigo_linha or not tipo_estrutura:
                ignoradas += 1
                continue

            instalacao = get_or_create_instalacao_lt(db, codigo_linha, sentido)
            if instalacao.nome not in instalacoes_criadas:
                instalacoes_criadas.add(instalacao.nome)

            tipo_ativo = get_or_create_tipo_torre(db, tipo_estrutura)
            if tipo_ativo.nome not in tipos_criados:
                tipos_criados.add(tipo_ativo.nome)

            codigo_torre = normalizar_codigo_torre(codigo_linha, estrutura)
            ativo = (
                db.query(Ativo)
                .filter(
                    Ativo.id_subestacao == instalacao.id_subestacao,
                    Ativo.codigo_ativo == codigo_torre,
                )
                .first()
            )

            dados_torre = {
                "id_subestacao": instalacao.id_subestacao,
                "id_tipo_ativo": tipo_ativo.id_tipo_ativo,
                "codigo_ativo": codigo_torre,
                "codigo_linha": codigo_linha,
                "estrutura_operacional": estrutura,
                "vao_vante_m": valor_decimal(row["vao vante (m)"]),
                "sentido": sentido,
                "tipo_estrutura": tipo_estrutura,
                "vao": f"T{estrutura.zfill(3) if estrutura.isdigit() else estrutura}",
                "fase": sentido,
                "especie": "LINHA DE TRANSMISSAO",
                "status": "ATIVO",
            }

            if ativo:
                for campo, valor in dados_torre.items():
                    setattr(ativo, campo, valor)
                atualizadas += 1
            else:
                db.add(Ativo(**dados_torre))
                criadas += 1

        db.commit()

        return {
            "mensagem": "Torres importadas com sucesso",
            "criadas": criadas,
            "atualizadas": atualizadas,
            "ignoradas": ignoradas,
            "instalacoes_processadas": sorted(instalacoes_criadas),
            "tipos_processados": sorted(tipos_criados),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
