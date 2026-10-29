import io
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import and_, or_, text as QueryText
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.plano_manutencao_models import (
    PeriodicidadeEnum,
    PlanoManutencao,
    Inspecao,
    PlanoExecucao,
    PlanoItem,
    ResultadoItemInspecao,
)
from models.Ativo import Ativo
from models.OS_models import OrdemServico
from plano_manutencao.schemas import (
    FotoInspecaoUploadOut,
    InspecaoCreate,
    InspecaoRead,
    InspecaoReadFull,
    InspecaoUpdate,
    PlanoExecucaoRead,
    PlanoItemRead,
)

router = APIRouter(prefix="/inspecoes", tags=["inspecoes"])

PREFIXO_FOTO_INSPECAO = "/inspecoes/fotos/"
PASTA_FOTOS_PADRAO = "saida/inspecoes/fotos"
NOME_FOTO_RE = re.compile(r"^[a-f0-9]{32}\.jpg$")


def _pasta_fotos_inspecao() -> Path:
    pasta = Path(os.getenv("INSPECAO_FOTO_DIR", PASTA_FOTOS_PADRAO)).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _limite_foto_bytes() -> int:
    try:
        limite_mb = float(os.getenv("INSPECAO_FOTO_MAX_MB", "20"))
    except (TypeError, ValueError):
        limite_mb = 20.0
    return int(max(limite_mb, 1.0) * 1024 * 1024)


def _lado_maximo_foto() -> int:
    try:
        return max(int(os.getenv("INSPECAO_FOTO_MAX_LADO", "1920")), 320)
    except (TypeError, ValueError):
        return 1920


def _normalizar_foto(conteudo: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem)

            if imagem.mode in ("RGBA", "LA") or (
                imagem.mode == "P" and "transparency" in imagem.info
            ):
                rgba = imagem.convert("RGBA")
                fundo = Image.new("RGB", rgba.size, (255, 255, 255))
                fundo.paste(rgba, mask=rgba.split()[-1])
                imagem = fundo
            elif imagem.mode != "RGB":
                imagem = imagem.convert("RGB")

            lado = _lado_maximo_foto()
            imagem.thumbnail((lado, lado), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            imagem.save(buffer, format="JPEG", quality=85, optimize=True)
            return buffer.getvalue()
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado nao e uma imagem valida. Use JPG, PNG ou WEBP.",
        ) from exc
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=400,
            detail="A imagem enviada e grande demais para processamento.",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail="Nao foi possivel processar a imagem enviada.",
        ) from exc


def _caminho_foto_inspecao(nome_arquivo: str) -> Optional[Path]:
    if not NOME_FOTO_RE.fullmatch(nome_arquivo or ""):
        return None

    pasta = _pasta_fotos_inspecao()
    caminho = (pasta / nome_arquivo).resolve()
    if caminho.parent != pasta:
        return None
    return caminho


def _fotos_informadas(resultados) -> set[str]:
    return {
        resultado.foto
        for resultado in resultados
        if resultado.foto and resultado.foto.startswith(PREFIXO_FOTO_INSPECAO)
    }


def _remover_fotos_orfaos(db: Session, urls: set[str]) -> None:
    for url in urls:
        nome = url[len(PREFIXO_FOTO_INSPECAO):]
        if not NOME_FOTO_RE.fullmatch(nome):
            continue

        em_uso = (
            db.query(ResultadoItemInspecao.id_resultado)
            .filter(ResultadoItemInspecao.foto == url)
            .first()
        )
        if em_uso:
            continue

        caminho = _caminho_foto_inspecao(nome)
        if not caminho:
            continue
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass


def garantir_colunas_inspecao(db: Session):
    valores_periodicidade = ",".join(
        f"'{periodicidade.name}'" for periodicidade in PeriodicidadeEnum
    )
    for tabela in ("plano_item", "inspecao"):
        coluna_periodicidade = db.execute(
            QueryText(
                """
                SELECT DATA_TYPE, COLUMN_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :tabela
                  AND COLUMN_NAME = 'periodicidade'
                """
            ),
            {"tabela": tabela},
        ).first()
        if (
            coluna_periodicidade
            and coluna_periodicidade[0] == "enum"
            and "'ANUAL'" not in coluna_periodicidade[1]
        ):
            db.execute(
                QueryText(
                    f"ALTER TABLE {tabela} MODIFY COLUMN periodicidade "
                    f"ENUM({valores_periodicidade}) NOT NULL"
                )
            )

    colunas_inspecao = {
        row[0]
        for row in db.execute(
            QueryText(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'inspecao'
                """
            )
        ).fetchall()
    }

    if "ficha_inspecao_url" not in colunas_inspecao:
        db.execute(QueryText("ALTER TABLE inspecao ADD COLUMN ficha_inspecao_url VARCHAR(500) NULL"))

    colunas = {
        row[0]
        for row in db.execute(
            QueryText(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'resultado_item_inspecao'
                """
            )
        ).fetchall()
    }

    if "id_plano_item" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN id_plano_item INT NULL"))
    if "nome_item" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN nome_item VARCHAR(200) NULL"))
    if "valor_referencia" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN valor_referencia DECIMAL(12, 4) NULL"))
    if "tolerancia" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN tolerancia DECIMAL(12, 4) NULL"))
    if "foto" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN foto VARCHAR(500) NULL"))
    if "id_item_template" in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao MODIFY COLUMN id_item_template INT NULL"))


@router.post("/fotos", response_model=FotoInspecaoUploadOut, status_code=201)
async def enviar_foto_inspecao(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    tipos_genericos = {"application/octet-stream", "binary/octet-stream"}
    if (
        content_type
        and content_type not in tipos_genericos
        and not content_type.startswith("image/")
    ):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem.")

    limite = _limite_foto_bytes()
    if arquivo.size and arquivo.size > limite:
        raise HTTPException(
            status_code=413,
            detail=f"A imagem excede o limite de {limite // (1024 * 1024)} MB.",
        )

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="A imagem esta vazia.")
    if len(conteudo) > limite:
        raise HTTPException(
            status_code=413,
            detail=f"A imagem excede o limite de {limite // (1024 * 1024)} MB.",
        )

    normalizado = _normalizar_foto(conteudo)
    nome_arquivo = f"{uuid.uuid4().hex}.jpg"
    destino = _pasta_fotos_inspecao() / nome_arquivo
    destino.write_bytes(normalizado)

    return FotoInspecaoUploadOut(
        url=f"{PREFIXO_FOTO_INSPECAO}{nome_arquivo}",
        nome_arquivo=nome_arquivo,
    )


@router.get("/fotos/{nome_arquivo}", response_class=FileResponse)
def obter_foto_inspecao(nome_arquivo: str):
    caminho = _caminho_foto_inspecao(nome_arquivo)
    if not caminho or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Foto nao encontrada.")

    return FileResponse(
        caminho,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/fotos/{nome_arquivo}", status_code=204)
def excluir_foto_inspecao(nome_arquivo: str, db: Session = Depends(get_db)):
    caminho = _caminho_foto_inspecao(nome_arquivo)
    if not caminho:
        raise HTTPException(status_code=404, detail="Foto nao encontrada.")

    url = f"{PREFIXO_FOTO_INSPECAO}{nome_arquivo}"
    em_uso = (
        db.query(ResultadoItemInspecao.id_resultado)
        .filter(ResultadoItemInspecao.foto == url)
        .first()
    )
    if em_uso:
        raise HTTPException(
            status_code=409,
            detail="A foto esta vinculada a uma inspecao e nao pode ser removida.",
        )

    try:
        caminho.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel remover o arquivo da foto.",
        ) from exc

    return None


def atualizar_resultados(db: Session, inspecao: Inspecao, resultados):
    status_geral = "OK" if resultados else "NA"

    for resultado in list(inspecao.resultados):
        db.delete(resultado)
    db.flush()

    for res in resultados:
        plano_item = (
            db.query(PlanoItem)
            .filter(PlanoItem.id_plano_item == res.id_plano_item)
            .first()
        )
        if not plano_item:
            raise HTTPException(
                status_code=400,
                detail=f"PlanoItem {res.id_plano_item} nao encontrado",
            )

        db.add(
            ResultadoItemInspecao(
                id_inspecao=inspecao.id_inspecao,
                id_plano_item=plano_item.id_plano_item,
                nome_item=plano_item.nome_item,
                valor_referencia=plano_item.valor_referencia,
                tolerancia=plano_item.tolerancia,
                valor_medido=res.valor_medido,
                status_item=res.status_item,
                observacao_item=res.observacao_item,
                foto=res.foto,
            )
        )

        if res.status_item == "NOK":
            status_geral = "NOK"

    # Inspecoes registram resultados; o calendario avanca pelo encerramento da OS.
    inspecao.status_geral = status_geral


def carregar_inspecao(db: Session, inspecao_id: int):
    inspecao = (
        db.query(Inspecao)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados).joinedload(ResultadoItemInspecao.plano_item),
        )
        .filter(Inspecao.id_inspecao == inspecao_id)
        .first()
    )
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspecao nao encontrada")
    return inspecao


@router.get("/ativo/{ativo_id}", response_model=List[InspecaoReadFull])
def listar_por_ativo(ativo_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Inspecao)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados),
        )
        .filter(Inspecao.id_ativo == ativo_id)
        .order_by(Inspecao.data_inspecao.desc())
        .all()
    )


@router.get("/pendentes/{ativo_id}", response_model=List[PlanoItemRead])
def itens_pendentes(
    ativo_id: int,
    periodicidade: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    ativo = db.query(Ativo).filter(Ativo.id_ativo == ativo_id).first()
    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo nao encontrado")

    query = (
        db.query(PlanoItem)
        .join(PlanoManutencao, PlanoManutencao.id_plano_manutencao == PlanoItem.id_plano_manutencao)
        .filter(
            (PlanoItem.id_ativo == ativo_id)
            | ((PlanoItem.id_ativo.is_(None)) & (PlanoManutencao.id_tipo_ativo == ativo.id_tipo_ativo))
        )
    )
    if periodicidade:
        query = query.filter(PlanoItem.periodicidade == periodicidade)
    return query.order_by(PlanoItem.ordem).all()


@router.get("/agenda/{ativo_id}", response_model=List[PlanoExecucaoRead])
def agenda_execucao(ativo_id: int, db: Session = Depends(get_db)):
    return (
        db.query(PlanoExecucao)
        .filter(PlanoExecucao.id_ativo == ativo_id)
        .order_by(PlanoExecucao.proxima_execucao)
        .all()
    )


@router.get("/atrasados/{ativo_id}", response_model=List[PlanoExecucaoRead])
def itens_atrasados(ativo_id: int, db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)
    return (
        db.query(PlanoExecucao)
        .filter(
            PlanoExecucao.id_ativo == ativo_id,
            PlanoExecucao.proxima_execucao < agora,
        )
        .all()
    )


@router.get("", response_model=List[InspecaoRead])
@router.get("/", response_model=List[InspecaoRead])
def listar_todas(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = Query(default=None),
    periodicidade: Optional[str] = Query(default=None),
    id_ativo: Optional[int] = Query(default=None),
    id_subestacao: Optional[int] = Query(default=None),
    id_tipo_ativo: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Inspecao).options(
        joinedload(Inspecao.ativo),
        joinedload(Inspecao.ordem_servico),
    )
    if status and status != "all":
        query = query.filter(Inspecao.status_geral == status)
    if periodicidade and periodicidade != "all":
        query = query.filter(Inspecao.periodicidade == periodicidade)
    if id_ativo:
        query = query.filter(Inspecao.id_ativo == id_ativo)
    if id_subestacao or id_tipo_ativo:
        query = query.join(Ativo, Ativo.id_ativo == Inspecao.id_ativo)
        if id_subestacao:
            query = query.filter(Ativo.id_subestacao == id_subestacao)
        if id_tipo_ativo:
            query = query.filter(Ativo.id_tipo_ativo == id_tipo_ativo)
    return (
        query.order_by(Inspecao.data_inspecao.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def periodicidade_da_os(esquema_servicos: str | None):
    texto = (esquema_servicos or "").upper().replace("-", "_").replace(" ", "_")
    aliases = (
        ("6_ANOS", PeriodicidadeEnum.SEIS_ANOS),
        ("SEIS_ANOS", PeriodicidadeEnum.SEIS_ANOS),
        ("5_ANOS", PeriodicidadeEnum.CINCO_ANOS),
        ("CINCO_ANOS", PeriodicidadeEnum.CINCO_ANOS),
        ("3_ANOS", PeriodicidadeEnum.TRES_ANOS),
        ("TRES_ANOS", PeriodicidadeEnum.TRES_ANOS),
        ("SEMESTRAL", PeriodicidadeEnum.SEMESTRAL),
        ("BIMESTRAL", PeriodicidadeEnum.BIMESTRAL),
        ("TRIMESTRAL", PeriodicidadeEnum.TRIMESTRAL),
        ("MENSAL", PeriodicidadeEnum.MENSAL),
        ("SEMANAL", PeriodicidadeEnum.SEMANAL),
        ("ANUAL", PeriodicidadeEnum.ANUAL),
    )
    return next((periodicidade for termo, periodicidade in aliases if termo in texto), None)


@router.post("/preparar-os-em-execucao")
def preparar_inspecoes_os_em_execucao(
    id_subestacao: int = Query(default=2, gt=0),
    id_tipo_ativo: int = Query(default=4, gt=0),
    periodicidade: Optional[PeriodicidadeEnum] = Query(default=None),
    responsavel: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    ordens = (
        db.query(OrdemServico)
        .join(Ativo, Ativo.id_ativo == OrdemServico.id_ativo)
        .filter(
            OrdemServico.id_subestacao == id_subestacao,
            Ativo.id_tipo_ativo == id_tipo_ativo,
            OrdemServico.status == "EM_EXECUCAO",
        )
        .order_by(OrdemServico.id_os)
        .with_for_update()
        .all()
    )

    criadas = []
    existentes = []
    sem_periodicidade = []

    for ordem in ordens:
        inspecao_existente = (
            db.query(Inspecao)
            .filter(Inspecao.id_os == ordem.id_os)
            .first()
        )
        if inspecao_existente:
            existentes.append({
                "id_os": ordem.id_os,
                "numero_os": ordem.numero_os,
                "id_inspecao": inspecao_existente.id_inspecao,
            })
            continue

        periodicidade_final = periodicidade or periodicidade_da_os(ordem.esquema_servicos)
        if not periodicidade_final:
            sem_periodicidade.append({
                "id_os": ordem.id_os,
                "numero_os": ordem.numero_os,
                "esquema_servicos": ordem.esquema_servicos,
            })
            continue

        inspecao = Inspecao(
            id_ativo=ordem.id_ativo,
            id_os=ordem.id_os,
            data_inspecao=datetime.now(timezone.utc),
            periodicidade=periodicidade_final,
            responsavel=responsavel or ordem.responsavel,
            observacao_geral=f"Inspecao para OS {ordem.numero_os}",
        )
        db.add(inspecao)
        db.flush()

        itens = (
            db.query(PlanoItem)
            .join(
                PlanoManutencao,
                PlanoManutencao.id_plano_manutencao == PlanoItem.id_plano_manutencao,
            )
            .join(Ativo, Ativo.id_ativo == ordem.id_ativo)
            .filter(
                or_(
                    PlanoItem.id_ativo == ordem.id_ativo,
                    and_(
                        PlanoItem.id_ativo.is_(None),
                        PlanoManutencao.id_tipo_ativo == Ativo.id_tipo_ativo,
                    ),
                ),
                PlanoItem.periodicidade == periodicidade_final,
            )
            .order_by(PlanoItem.ordem, PlanoItem.id_plano_item)
            .all()
        )

        for item in itens:
            db.add(ResultadoItemInspecao(
                id_inspecao=inspecao.id_inspecao,
                id_plano_item=item.id_plano_item,
                nome_item=item.nome_item,
                valor_referencia=item.valor_referencia,
                tolerancia=item.tolerancia,
                status_item="OK",
            ))

        if itens:
            inspecao.status_geral = "OK"

        criadas.append({
            "id_os": ordem.id_os,
            "numero_os": ordem.numero_os,
            "id_inspecao": inspecao.id_inspecao,
            "periodicidade": periodicidade_final.value,
            "itens_preenchidos_ok": len(itens),
        })

    db.commit()
    return {
        "id_subestacao": id_subestacao,
        "id_tipo_ativo": id_tipo_ativo,
        "os_encontradas": len(ordens),
        "inspecoes_criadas": criadas,
        "inspecoes_existentes": existentes,
        "os_sem_periodicidade": sem_periodicidade,
    }

@router.post("", response_model=InspecaoReadFull, status_code=201)
@router.post("/", response_model=InspecaoReadFull, status_code=201)
def criar_inspecao(inspecao_in: InspecaoCreate, db: Session = Depends(get_db)):
    if inspecao_in.id_os is not None:
        ordem = db.query(OrdemServico).filter(OrdemServico.id_os == inspecao_in.id_os).first()
        if ordem is None or ordem.status != "EM_EXECUCAO":
            raise HTTPException(
                status_code=400,
                detail="Inspeção só pode ser vinculada a uma OS em execução.",
            )

    db_inspecao = Inspecao(
        id_ativo=inspecao_in.id_ativo,
        id_os=inspecao_in.id_os,
        data_inspecao=inspecao_in.data_inspecao or datetime.now(timezone.utc),
        data_proxima_inspecao=inspecao_in.data_proxima_inspecao,
        periodicidade=inspecao_in.periodicidade,
        responsavel=inspecao_in.responsavel,
        ficha_inspecao_url=inspecao_in.ficha_inspecao_url,
        observacao_geral=inspecao_in.observacao_geral or "",
    )
    db.add(db_inspecao)
    db.flush()

    atualizar_resultados(db, db_inspecao, inspecao_in.resultados)
    db.commit()

    return carregar_inspecao(db, db_inspecao.id_inspecao)


@router.get("/{inspecao_id}", response_model=InspecaoReadFull)
def buscar_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    return carregar_inspecao(db, inspecao_id)


@router.put("/{inspecao_id}", response_model=InspecaoReadFull)
def atualizar_inspecao(
    inspecao_id: int,
    dados: InspecaoUpdate,
    db: Session = Depends(get_db),
):
    inspecao = carregar_inspecao(db, inspecao_id)
    fotos_antigas = _fotos_informadas(inspecao.resultados)
    payload = dados.model_dump(exclude_unset=True)
    resultados = payload.pop("resultados", None)

    if "id_os" in payload and payload["id_os"] is not None:
        ordem = db.query(OrdemServico).filter(OrdemServico.id_os == payload["id_os"]).first()
        if ordem is None or ordem.status != "EM_EXECUCAO":
            raise HTTPException(
                status_code=400,
                detail="Inspeção só pode ser vinculada a uma OS em execução.",
            )

    for campo, valor in payload.items():
        setattr(inspecao, campo, valor)

    if resultados is not None:
        atualizar_resultados(db, inspecao, dados.resultados or [])

    db.commit()
    _remover_fotos_orfaos(db, fotos_antigas)
    return carregar_inspecao(db, inspecao_id)


@router.delete("/{inspecao_id}", status_code=204)
def excluir_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    inspecao = carregar_inspecao(db, inspecao_id)
    fotos = _fotos_informadas(inspecao.resultados)
    db.delete(inspecao)
    db.commit()
    _remover_fotos_orfaos(db, fotos)
    return None
