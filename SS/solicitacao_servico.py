import io
import os
import re
import shutil
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from openpyxl import load_workbook
from openpyxl.drawing.image import Image
from openpyxl.utils import range_boundaries
from PIL import Image as PilImage, ImageOps, UnidentifiedImageError
from sqlalchemy import String, case, cast, func, or_, text
from sqlalchemy.orm import Session, selectinload

from database import get_db
from utils.busca_inteligente import condicoes_textuais, termos_busca_inteligente
from auth.dependencies import get_current_user, require_roles
from models.Ativo import Ativo, GrupoAtivo
from ATIVO.grupos_ativos import garantir_estrutura_grupo_ativo, sincronizar_grupos_ativos, validar_selecao_ativo
from models.OS_models import OrdemServico
from models.SS_models import SolicitacaoServico, SolicitacaoServicoFoto
from models.sobreaviso_models import SobreavisoColaborador
from problemas_tipicos.service import sincronizar_ss
from models.instalacao_models import Subestacao
from SS.schemas import (
    FotoSSUploadOut,
    SolicitanteSSOut,
    SolicitacaoServicoCreate,
    SolicitacaoServicoPaginadaResponse,
    SolicitacaoServicoResponse,
    SolicitacaoServicoUpdate,
)
from SS.importacao_massa import importar_planilha_ss, sigla_ss_subestacao
from utils.documentos_operacao import especie_documento_por_ativo


router = APIRouter(prefix="/ss", tags=["Solicita??o de Servi?o"])
_ESTRUTURA_SS_GARANTIDA = False

PREFIXO_FOTO_SS = "/ss/fotos/"
PASTA_FOTOS_SS_PADRAO = "saida/ss/fotos"
NOME_FOTO_SS_RE = re.compile(r"^[a-f0-9]{32}\.jpg$")


def _pasta_fotos_ss() -> Path:
    pasta = Path(os.getenv("SS_FOTO_DIR", PASTA_FOTOS_SS_PADRAO)).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _limite_foto_ss_bytes() -> int:
    try:
        limite_mb = float(os.getenv("SS_FOTO_MAX_MB", "20"))
    except (TypeError, ValueError):
        limite_mb = 20.0
    return int(max(limite_mb, 1.0) * 1024 * 1024)


def _lado_maximo_foto_ss() -> int:
    try:
        return max(int(os.getenv("SS_FOTO_MAX_LADO", "1920")), 320)
    except (TypeError, ValueError):
        return 1920


def _normalizar_foto_ss(conteudo: bytes) -> bytes:
    try:
        with PilImage.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem)

            if imagem.mode in ("RGBA", "LA") or (
                imagem.mode == "P" and "transparency" in imagem.info
            ):
                rgba = imagem.convert("RGBA")
                fundo = PilImage.new("RGB", rgba.size, (255, 255, 255))
                fundo.paste(rgba, mask=rgba.split()[-1])
                imagem = fundo
            elif imagem.mode != "RGB":
                imagem = imagem.convert("RGB")

            lado = _lado_maximo_foto_ss()
            imagem.thumbnail((lado, lado), PilImage.Resampling.LANCZOS)
            saida = io.BytesIO()
            imagem.save(saida, format="JPEG", quality=85, optimize=True)
            return saida.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Arquivo de imagem invalido.") from exc


def _salvar_fotos_ss(db: Session, id_ss: int, fotos: list[str]) -> list[str]:
    """Substitui as fotos da SS (maximo 5), mantendo a ordem escolhida."""
    urls: list[str] = []
    for valor in fotos or []:
        url = (valor or "").strip()
        if not url:
            continue
        if not url.startswith(PREFIXO_FOTO_SS):
            raise HTTPException(
                status_code=422,
                detail="Foto invalida: envie as imagens pelo campo de fotos da SS.",
            )
        nome = url[len(PREFIXO_FOTO_SS):]
        if not NOME_FOTO_SS_RE.match(nome):
            raise HTTPException(status_code=422, detail="Foto invalida.")
        if url not in urls:
            urls.append(url)

    if len(urls) > 5:
        raise HTTPException(status_code=422, detail="A SS aceita no maximo 5 fotos.")

    db.query(SolicitacaoServicoFoto).filter(
        SolicitacaoServicoFoto.id_ss == id_ss
    ).delete(synchronize_session=False)

    for ordem, url in enumerate(urls):
        db.add(
            SolicitacaoServicoFoto(
                id_ss=id_ss,
                url=url,
                nome_arquivo=url[len(PREFIXO_FOTO_SS):],
                ordem=ordem,
            )
        )
    db.flush()
    return urls


def _apagar_foto_orfa(db: Session, url: str) -> None:
    """Remove o arquivo quando nenhuma SS o referencia mais."""
    if not url or not url.startswith(PREFIXO_FOTO_SS):
        return
    em_uso = (
        db.query(SolicitacaoServicoFoto.id_foto)
        .filter(SolicitacaoServicoFoto.url == url)
        .first()
    )
    if em_uso:
        return
    nome = url[len(PREFIXO_FOTO_SS):]
    if not NOME_FOTO_SS_RE.match(nome):
        return
    caminho = _pasta_fotos_ss() / nome
    try:
        caminho.unlink(missing_ok=True)
    except OSError:
        pass


def garantir_colunas_ss(db: Session):
    global _ESTRUTURA_SS_GARANTIDA
    if _ESTRUTURA_SS_GARANTIDA:
        return
    colunas = {
        "emissor": "TEXT NULL",
        "editado_por": "TEXT NULL",
    }

    for coluna, definicao in colunas.items():
        existe = db.execute(
            text("SHOW COLUMNS FROM solicitacao_servico LIKE :coluna"),
            {"coluna": coluna},
        ).first()
        if not existe:
            db.execute(text(f"ALTER TABLE solicitacao_servico ADD COLUMN {coluna} {definicao}"))

    db.execute(
        text(
            "CREATE TABLE IF NOT EXISTS solicitacao_servico_foto ("
            "id_foto INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
            "id_ss INT NOT NULL, "
            "url VARCHAR(500) NOT NULL, "
            "nome_arquivo VARCHAR(255) NULL, "
            "ordem INT NOT NULL DEFAULT 0, "
            "criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE KEY uk_ss_foto_url (id_ss, url), "
            "KEY ix_ss_foto_ss (id_ss), "
            "CONSTRAINT fk_ss_foto_ss FOREIGN KEY (id_ss) "
            "REFERENCES solicitacao_servico (id) ON DELETE CASCADE"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
    )

    db.commit()
    _ESTRUTURA_SS_GARANTIDA = True

MAPEAMENTO_CELULAS = {
    "NUM_SS": "H1",
    "DT_SOLICITACAO": "A4",
    "DT_ABERTURA": "D4",
    "DT_LIMITE": "G4",
    "SOLICITANTE": "A6",
    "MATRICULA": "D6",
    "FUNCAO": "G6",
    "TELEFONE": "A8",
    "EMAIL": "D8",
    "ORGAO": "G8",
    "INSTALACAO": "A10",
    "LOCALIZACAO": "D10",
    "COMPLEMENTO": "G10",
    "CODIGO_ATIVO": "A12",
    "ESQUEMA_SERVICO": "D12",
    "PRIORIDADE": "G12",
    "DESC_PROBLEMA": "A14",
    "CAUSA": "A18",
    "CAUSA_SECUNDARIA": "D18",
    "EQUIPE": "G18",
    "CENTRO_CUSTO": "A20",
    "STATUS": "G20",
}


def nome_arquivo_seguro(texto: str):
    if not texto:
        return "sem_nome"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", texto)


def limpar(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return str(valor)


def set_valor_seguro(ws, celula, valor):
    for merged_range in ws.merged_cells.ranges:
        if celula in merged_range:
            min_col, min_row, _, _ = range_boundaries(str(merged_range))
            ws.cell(row=min_row, column=min_col).value = valor
            return
    ws[celula] = valor


def sigla_por_subestacao(db: Session, id_subestacao: int | None) -> str:
    """Deriva a sigla do cadastro da instalacao, sem usar prefixo GERAL.

    A numeracao da SS precisa identificar a instalacao mesmo quando o documento
    e aberto por grupo/ativo (sem id_ativo individual). O fallback pelo id do
    ativo gerava "SS-GERAL-..." para qualquer instalacao fora da lista fixa.
    """
    if not id_subestacao:
        raise HTTPException(400, "Selecione a instalacao para gerar o numero da SS")

    subestacao = db.query(Subestacao).filter(
        Subestacao.id_subestacao == id_subestacao
    ).first()
    if not subestacao:
        raise HTTPException(400, "Instalacao invalida para gerar o numero da SS")

    sigla = str(getattr(subestacao, "sigla", "") or "").strip().upper()
    if not sigla or sigla == "GERAL":
        raise HTTPException(400, "Nao foi possivel definir a sigla da instalacao")

    circuito = re.search(
        r"\bC\s*[-_]?\s*(\d+)\b",
        str(subestacao.nome or ""),
        re.IGNORECASE,
    )
    if circuito:
        sigla = f"{sigla}-C{circuito.group(1)}"
    return sigla


def gerar_numero_ss(db: Session, sigla: str):
    ano_atual = datetime.now().year
    registros = (
        db.query(SolicitacaoServico.numero_ss)
        .filter(SolicitacaoServico.numero_ss.like(f"SS-{sigla}-%-{ano_atual}"))
        .all()
    )

    numeros = []
    for (numero_ss,) in registros:
        match = re.search(rf"SS-{sigla}-(\d+)-{ano_atual}", numero_ss or "")
        if match:
            numeros.append(int(match.group(1)))

    proximo = max(numeros) + 1 if numeros else 1
    return f"SS-{sigla}-{str(proximo).zfill(4)}-{ano_atual}"


def gerar_numero_os_atendimento_ss(db: Session, sigla: str):
    ano_atual = datetime.now().year
    registros = (
        db.query(OrdemServico.numero_os)
        .filter(OrdemServico.numero_os.like(f"OS-{sigla}-%-{ano_atual}%"))
        .all()
    )

    numeros = []
    for (numero_os,) in registros:
        match = re.search(rf"OS-{sigla}-(\d+)-{ano_atual}", numero_os or "")
        if match:
            numeros.append(int(match.group(1)))

    proximo = max(numeros) + 1 if numeros else 1
    numero_formatado = str(proximo).zfill(4)
    numero_os = f"OS-{sigla}-{numero_formatado}-{ano_atual}"
    numero_apr = f"APR-{sigla}-{numero_formatado}-{ano_atual}"

    return numero_os, numero_apr


def gerar_xlsx(modelo, destino, contexto, mapeamento):
    if os.path.exists(destino):
        os.remove(destino)

    shutil.copy(modelo, destino)

    wb = load_workbook(destino)
    ws = wb.active

    logo_path = "modelos/logo.jpg"
    if os.path.exists(logo_path):
        img = Image(logo_path)
        img.width = 150
        img.height = 45
        ws.add_image(img, "A1")

    for campo, celula in mapeamento.items():
        set_valor_seguro(ws, celula, contexto.get(campo, ""))

    wb.save(destino)


def resumo_problemas_ss(ss):
    linhas = []
    for ocorrencia in ss.problemas or []:
        problema = ocorrencia.problema
        criticidade = ocorrencia.criticidade_identificada or problema.criticidade_padrao
        valor_criticidade = criticidade.value if hasattr(criticidade, "value") else criticidade
        linha = f"- {problema.titulo} [{valor_criticidade}]"
        if ocorrencia.observacao:
            linha += f" — {ocorrencia.observacao.strip()}"
        if ocorrencia.confirmado:
            linha += " — confirmado"
        linhas.append(linha)
    return "\n".join(linhas)


def descricao_com_problemas_ss(ss):
    blocos = []
    if ss.descricao_problema and ss.descricao_problema.strip():
        blocos.append(ss.descricao_problema.strip())
    resumo = resumo_problemas_ss(ss)
    if resumo:
        blocos.append(f"PROBLEMAS IDENTIFICADOS:\n{resumo}")
    return "\n\n".join(blocos)

def montar_contexto_ss(ss, ativo=None):
    return {
        "NUM_SS": limpar(ss.numero_ss),
        "DT_SOLICITACAO": limpar(ss.data_hora_solicitacao),
        "DT_ABERTURA": limpar(ss.data_hora_abertura),
        "DT_LIMITE": limpar(ss.data_hora_limite),
        "SOLICITANTE": limpar(ss.solicitante),
        "MATRICULA": limpar(ss.matricula),
        "FUNCAO": limpar(ss.funcao),
        "TELEFONE": limpar(ss.telefone),
        "EMAIL": limpar(ss.email),
        "ORGAO": limpar(ss.orgao),
        "INSTALACAO": limpar(ss.instalacao),
        "LOCALIZACAO": limpar(ss.localizacao),
        "COMPLEMENTO": limpar(ss.complemento),
        "CODIGO_ATIVO": limpar(ativo.codigo_ativo if ativo else ""),
        "ESQUEMA_SERVICO": limpar(ss.esquema_servico),
        "CENTRO_CUSTO": limpar(ss.centro_custo),
        "CAUSA": limpar(ss.causa),
        "CAUSA_SECUNDARIA": limpar(ss.causa_secundaria),
        "EQUIPE": limpar(ss.equipe),
        "DESC_PROBLEMA": limpar(descricao_com_problemas_ss(ss)),
        "PRIORIDADE": limpar(ss.prioridade),
        "STATUS": limpar(ss.status),
    }


@router.post("", response_model=SolicitacaoServicoResponse)
def criar_ss(ss: SolicitacaoServicoCreate, db: Session = Depends(get_db)):
    garantir_colunas_ss(db)
    data = ss.model_dump()
    problemas = data.pop("problemas", [])
    fotos = data.pop("fotos", [])
    validar_selecao_ativo(db, data.get("id_subestacao"), data.get("id_funcao_operacao"), data.get("id_grupo_ativo"), data.get("escopo_ativo"), data.get("id_ativo"))
    id_subestacao = data.pop("id_subestacao", None)
    if not data.get("numero_ss"):
        data["numero_ss"] = gerar_numero_ss(
            db,
            sigla_por_subestacao(db, id_subestacao),
        )

    nova_ss = SolicitacaoServico(**data)

    db.add(nova_ss)
    db.flush()
    _salvar_fotos_ss(db, nova_ss.id, fotos)
    sincronizar_ss(db, nova_ss, ss.problemas)
    db.commit()
    db.refresh(nova_ss)

    return nova_ss


@router.post("/importar-massa")
async def importar_ss_em_massa(
    arquivo: UploadFile = File(...),
    emissor: str | None = None,
    db: Session = Depends(get_db),
):
    garantir_colunas_ss(db)
    nome_arquivo = arquivo.filename or ""
    if not nome_arquivo.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Envie uma planilha .xlsx ou .xlsm.")

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="A planilha esta vazia.")
    if len(conteudo) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="A planilha excede o limite de 10 MB.")

    return importar_planilha_ss(conteudo, emissor, db, gerar_numero_ss)


@router.get("", response_model=list[SolicitacaoServicoResponse])
def listar_ss(db: Session = Depends(get_db)):
    garantir_colunas_ss(db)
    return (
        db.query(SolicitacaoServico)
        .options(
            selectinload(SolicitacaoServico.ativo),
            selectinload(SolicitacaoServico.grupo_ativo),
        )
        .all()
    )


@router.get("/paginado", response_model=SolicitacaoServicoPaginadaResponse)
def listar_ss_paginado(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    status: str | None = None,
    id_subestacao: int | None = None,
    prazo: str | None = None,
    id_tipo_ativo: int | None = None,
    filter_field: list[str] = Query(default=[]),
    filter_value: list[str] = Query(default=[]),
    data_limite_inicio: date | None = None,
    data_limite_fim: date | None = None,
    ordenar_por: str = Query("data_limite", pattern="^(data_limite|mais_recentes)$"),
    db: Session = Depends(get_db),
):
    garantir_colunas_ss(db)
    query = db.query(SolicitacaoServico)
    ativos_associados = False

    if search and search.strip():
        query = query.outerjoin(
            Ativo, SolicitacaoServico.id_ativo == Ativo.id_ativo
        ).outerjoin(
            GrupoAtivo, SolicitacaoServico.id_grupo_ativo == GrupoAtivo.id_grupo_ativo
        )
        ativos_associados = True
        for palavra in termos_busca_inteligente(search):
            termo = f"%{palavra}%"
            query = query.filter(or_(
                *condicoes_textuais(SolicitacaoServico, palavra),
                Ativo.codigo_ativo.ilike(termo),
                Ativo.bay.ilike(termo),
                Ativo.fase.ilike(termo),
                GrupoAtivo.codigo_ativo.ilike(termo),
            ))

    if status:
        query = query.filter(SolicitacaoServico.status == status)

    if id_tipo_ativo:
        query = query.filter(or_(
            SolicitacaoServico.id_ativo.in_(
                db.query(Ativo.id_ativo).filter(Ativo.id_tipo_ativo == id_tipo_ativo)
            ),
            SolicitacaoServico.id_grupo_ativo.in_(
                db.query(GrupoAtivo.id_grupo_ativo).filter(GrupoAtivo.id_tipo_ativo == id_tipo_ativo)
            ),
        ))
    colunas = {coluna.name for coluna in SolicitacaoServico.__table__.columns}
    for campo, valor in zip(filter_field, filter_value):
        valor = valor.strip()
        if not valor:
            continue
        if campo == "codigo_ativo":
            termo = f"%{valor}%"
            query = query.filter(or_(
                SolicitacaoServico.id_ativo.in_(
                    db.query(Ativo.id_ativo).filter(Ativo.codigo_ativo.ilike(termo))
                ),
                SolicitacaoServico.id_grupo_ativo.in_(
                    db.query(GrupoAtivo.id_grupo_ativo).filter(GrupoAtivo.codigo_ativo.ilike(termo))
                ),
            ))
        elif campo in colunas:
            query = query.filter(cast(getattr(SolicitacaoServico, campo), String).ilike(f"%{valor}%"))

    hoje = datetime.combine(date.today(), time.min)
    amanha = hoje + timedelta(days=1)

    if prazo == "vencidas":
        query = query.filter(SolicitacaoServico.data_hora_limite < hoje)
    elif prazo == "hoje":
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= hoje,
            SolicitacaoServico.data_hora_limite < amanha,
        )
    elif prazo == "proximos_7_dias":
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= hoje,
            SolicitacaoServico.data_hora_limite < hoje + timedelta(days=8),
        )
    elif prazo == "proximos_30_dias":
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= hoje,
            SolicitacaoServico.data_hora_limite < hoje + timedelta(days=31),
        )
    elif prazo == "proximos_60_dias":
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= hoje,
            SolicitacaoServico.data_hora_limite < hoje + timedelta(days=61),
        )
    elif prazo == "proximos_180_dias":
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= hoje,
            SolicitacaoServico.data_hora_limite < hoje + timedelta(days=181),
        )
    elif prazo == "sem_prazo":
        query = query.filter(SolicitacaoServico.data_hora_limite.is_(None))

    if data_limite_inicio:
        query = query.filter(
            SolicitacaoServico.data_hora_limite >= datetime.combine(data_limite_inicio, time.min)
        )
    if data_limite_fim:
        query = query.filter(
            SolicitacaoServico.data_hora_limite < datetime.combine(data_limite_fim + timedelta(days=1), time.min)
        )

    if id_subestacao:
        subestacao = db.query(Subestacao).filter(
            Subestacao.id_subestacao == id_subestacao
        ).first()
        if not ativos_associados:
            query = query.outerjoin(
                Ativo, SolicitacaoServico.id_ativo == Ativo.id_ativo
            ).outerjoin(
                GrupoAtivo, SolicitacaoServico.id_grupo_ativo == GrupoAtivo.id_grupo_ativo
            )
        query = query.filter(
            or_(
                Ativo.id_subestacao == id_subestacao,
                GrupoAtivo.id_subestacao == id_subestacao,
                SolicitacaoServico.instalacao == (subestacao.nome if subestacao else ""),
            )
        )

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    if ordenar_por == "data_limite":
        ordenacao = (
            case((SolicitacaoServico.data_hora_limite.is_(None), 1), else_=0).asc(),
            SolicitacaoServico.data_hora_limite.asc(),
            SolicitacaoServico.id.desc(),
        )
    else:
        ordenacao = (SolicitacaoServico.id.desc(),)

    items = (
        query
        .options(
            selectinload(SolicitacaoServico.ativo),
            selectinload(SolicitacaoServico.grupo_ativo),
        )
        .order_by(*ordenacao)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/fotos", response_model=FotoSSUploadOut, status_code=201)
async def enviar_foto_ss(arquivo: UploadFile = File(...)):
    content_type = (arquivo.content_type or "").lower()
    tipos_genericos = {"application/octet-stream", "binary/octet-stream"}
    if (
        content_type
        and content_type not in tipos_genericos
        and not content_type.startswith("image/")
    ):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem.")

    limite = _limite_foto_ss_bytes()
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

    normalizado = _normalizar_foto_ss(conteudo)
    nome_arquivo = f"{uuid.uuid4().hex}.jpg"
    destino = _pasta_fotos_ss() / nome_arquivo
    destino.write_bytes(normalizado)

    return FotoSSUploadOut(
        url=f"{PREFIXO_FOTO_SS}{nome_arquivo}",
        nome_arquivo=nome_arquivo,
    )


@router.get("/fotos/{nome_arquivo}", response_class=FileResponse)
def obter_foto_ss(nome_arquivo: str):
    if not NOME_FOTO_SS_RE.match(nome_arquivo):
        raise HTTPException(status_code=404, detail="Foto nao encontrada.")
    caminho = _pasta_fotos_ss() / nome_arquivo
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Foto nao encontrada.")

    return FileResponse(
        caminho,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/fotos/{nome_arquivo}", status_code=204)
def excluir_foto_ss(nome_arquivo: str, db: Session = Depends(get_db)):
    garantir_colunas_ss(db)
    if not NOME_FOTO_SS_RE.match(nome_arquivo):
        raise HTTPException(status_code=404, detail="Foto nao encontrada.")

    url = f"{PREFIXO_FOTO_SS}{nome_arquivo}"
    em_uso = (
        db.query(SolicitacaoServicoFoto.id_foto)
        .filter(SolicitacaoServicoFoto.url == url)
        .first()
    )
    if em_uso:
        raise HTTPException(
            status_code=409,
            detail="Foto vinculada a uma SS. Remova pelo formulario e salve a SS.",
        )

    caminho = _pasta_fotos_ss() / nome_arquivo
    if caminho.is_file():
        caminho.unlink()
    return None


def _colaborador_do_usuario(db: Session, usuario) -> SobreavisoColaborador | None:
    """Localiza o cadastro de colaborador do usuario logado.

    Ordem: vinculo direto (id_usuario), e-mail e, por ultimo, nome exato
    quando houver apenas um colaborador com esse nome.
    """
    base = db.query(SobreavisoColaborador).filter(SobreavisoColaborador.ativo == 1)

    por_usuario = (
        base.filter(SobreavisoColaborador.id_usuario == usuario.id)
        .order_by(SobreavisoColaborador.id_colaborador)
        .first()
    )
    if por_usuario:
        return por_usuario

    email = (getattr(usuario, "email", "") or "").strip().lower()
    if email:
        por_email = (
            base.filter(func.lower(func.trim(SobreavisoColaborador.email)) == email)
            .order_by(SobreavisoColaborador.id_colaborador)
            .first()
        )
        if por_email:
            return por_email

    nome = (getattr(usuario, "nome", "") or "").strip()
    if nome:
        candidatos = (
            base.filter(func.lower(func.trim(SobreavisoColaborador.nome)) == nome.lower())
            .all()
        )
        if len(candidatos) == 1:
            return candidatos[0]

    return None


@router.get("/solicitante", response_model=SolicitanteSSOut)
def obter_solicitante_ss(
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    """Dados do solicitante para pre-carregar o formulario de SS."""
    colaborador = _colaborador_do_usuario(db, usuario)

    if colaborador:
        return SolicitanteSSOut(
            nome=(colaborador.nome or getattr(usuario, "nome", "") or "").strip(),
            matricula=(colaborador.matricula or "").strip(),
            funcao=(colaborador.cargo or "").strip(),
            telefone=(colaborador.telefone or "").strip(),
            email=(colaborador.email or getattr(usuario, "email", "") or "").strip(),
        )

    return SolicitanteSSOut(
        nome=(getattr(usuario, "nome", "") or "").strip(),
        email=(getattr(usuario, "email", "") or "").strip(),
    )


@router.get("/{id_ss}", response_model=SolicitacaoServicoResponse)
def buscar_ss(id_ss: int, db: Session = Depends(get_db)):
    garantir_colunas_ss(db)
    ss = db.query(SolicitacaoServico).filter(
        SolicitacaoServico.id == id_ss
    ).first()

    if not ss:
        raise HTTPException(404, "SS nao encontrada")

    return ss


@router.put("/{id_ss}", response_model=SolicitacaoServicoResponse)
def editar_ss(
    id_ss: int,
    dados: SolicitacaoServicoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    garantir_colunas_ss(db)
    ss = db.query(SolicitacaoServico).filter(
        SolicitacaoServico.id == id_ss
    ).first()

    if not ss:
        raise HTTPException(404, "SS nao encontrada")

    alteracoes = dados.model_dump(exclude_unset=True)
    id_subestacao_informada = alteracoes.pop("id_subestacao", None)
    problemas = alteracoes.pop("problemas", None)
    fotos = alteracoes.pop("fotos", None)
    fotos_antigas = [foto.url for foto in ss.fotos_registros]

    # O id_subestacao da SS e derivado do ativo/grupo (propriedade no model),
    # portanto nao pode ser gravado diretamente. Ele e usado aqui para validar
    # que o ativo/grupo escolhido na edicao pertence a instalacao selecionada.
    validar_selecao_ativo(
        db,
        id_subestacao_informada,
        alteracoes.get("id_funcao_operacao", ss.id_funcao_operacao),
        alteracoes.get("id_grupo_ativo", ss.id_grupo_ativo),
        alteracoes.get("escopo_ativo", ss.escopo_ativo),
        alteracoes.get("id_ativo", ss.id_ativo),
    )

    for campo, valor in alteracoes.items():
        if campo == "emissor":
            continue
        setattr(ss, campo, valor)

    if problemas is not None:
        sincronizar_ss(db, ss, dados.problemas or [])

    if fotos is not None:
        _salvar_fotos_ss(db, ss.id, fotos)

    ss.editado_por = getattr(usuario, "nome", None) or getattr(usuario, "email", None)

    db.commit()
    db.refresh(ss)

    if fotos is not None:
        mantidas = set(fotos or [])
        for url in fotos_antigas:
            if url not in mantidas:
                _apagar_foto_orfa(db, url)

    return ss


@router.delete("/{id_ss}")
def deletar_ss(
    id_ss: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin")),
):
    garantir_colunas_ss(db)
    ss = db.query(SolicitacaoServico).filter(
        SolicitacaoServico.id == id_ss
    ).first()

    if not ss:
        raise HTTPException(404, "SS nao encontrada")

    fotos_antigas = [foto.url for foto in ss.fotos_registros]
    db.delete(ss)
    db.commit()
    for url in fotos_antigas:
        _apagar_foto_orfa(db, url)

    return {"message": "SS deletada com sucesso"}


@router.post("/{id_ss}/atender")
def atender_ss(
    id_ss: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor", "operador")),
):
    ss = db.query(SolicitacaoServico).filter(
        SolicitacaoServico.id == id_ss
    ).first()

    if not ss:
        raise HTTPException(404, "SS nao encontrada")

    os_existente = db.query(OrdemServico).filter(
        OrdemServico.numero_ss == ss.numero_ss
    ).first()

    if os_existente:
        ss.numero_os = os_existente.numero_os
        db.commit()
        db.refresh(ss)
        return {
            "message": "SS ja possui OS vinculada",
            "ss": ss,
            "os": os_existente,
        }

    ativo = db.query(Ativo).filter(
        Ativo.id_ativo == ss.id_ativo
    ).first() if ss.id_ativo else None

    if not ativo or not ativo.id_subestacao:
        raise HTTPException(
            status_code=400,
            detail="SS precisa estar vinculada a um ativo com subestacao para gerar OS",
        )

    subestacao = db.query(Subestacao).filter(
        Subestacao.id_subestacao == ativo.id_subestacao
    ).first()

    if not subestacao:
        raise HTTPException(400, "Subestacao do ativo nao encontrada")

    sigla = sigla_ss_subestacao(subestacao)
    numero_os, numero_apr = gerar_numero_os_atendimento_ss(
        db,
        sigla,
    )

    nova_os = OrdemServico(
        numero_os=numero_os,
        numero_apr=numero_apr,
        numero_ss=ss.numero_ss,
        id_subestacao=ativo.id_subestacao,
        id_ativo=ativo.id_ativo,
        especie=especie_documento_por_ativo(ativo) or ativo.especie,
        instalacao=subestacao.nome,
        localizacao=ativo.bay or ss.localizacao,
        complemento=ativo.fase or ss.complemento,
        origens=f"SS {ss.numero_ss}",
        defeito=ss.descricao_problema,
        esquema_servicos=ss.esquema_servico,
        prioridade=ss.prioridade,
        responsavel=ss.equipe,
        responsavel_manutencao=ss.equipe,
        data_abertura_ss=ss.data_hora_abertura or datetime.now(),
        descricao_servicos=ss.descricao_problema,
        causa_primaria=ss.causa,
        causa_secundaria=ss.causa_secundaria,
        centro_custos=ss.centro_custo,
        status="PROGRAMADA",
    )

    ss.status = "PROGRAMADA"
    ss.numero_os = nova_os.numero_os

    db.add(nova_os)
    db.commit()
    db.refresh(nova_os)
    db.refresh(ss)

    return {
        "message": "SS atendida e OS criada com sucesso",
        "ss": ss,
        "os": nova_os,
    }


@router.get("/{id_ss}/download")
def download_ss(id_ss: int, db: Session = Depends(get_db)):
    ss = db.query(SolicitacaoServico).filter(
        SolicitacaoServico.id == id_ss
    ).first()

    if not ss:
        raise HTTPException(404, "SS nao encontrada")

    ativo = db.query(Ativo).filter(
        Ativo.id_ativo == ss.id_ativo
    ).first() if ss.id_ativo else None

    contexto = montar_contexto_ss(ss, ativo)

    pasta_saida = "saida"
    os.makedirs(pasta_saida, exist_ok=True)

    nome_arquivo = nome_arquivo_seguro(f"{ss.numero_ss}.xlsx")
    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

    gerar_xlsx(
        modelo="modelos/MODELO_SS.xlsx",
        destino=caminho_saida,
        contexto=contexto,
        mapeamento=MAPEAMENTO_CELULAS,
    )

    return FileResponse(
        path=caminho_saida,
        filename=nome_arquivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


