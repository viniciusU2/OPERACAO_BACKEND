import io
import json
import os
import re
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.familias_models import TipoAtivo
from models.instalacao_models import Subestacao
from models.plano_manutencao_models import PlanoItem, PlanoManutencao
from relatorio_manutencao.models import RelatorioManutencao
from relatorio_manutencao.photo_models import RelatorioManutencaoFoto
from relatorio_manutencao.schemas import RelatorioManutencaoPaginadoResponse, RelatorioManutencaoResponse
from relatorio_manutencao.report_generator import gerar_relatorio_word
from relatorio_manutencao.review_enrichment import criar_miniatura_data_url

router = APIRouter(prefix="/relatorios-manutencao", tags=["Relatorios de manutencao"])

PERIODICIDADES = {"SEMANAL", "MENSAL", "BIMESTRAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "3_ANOS", "5_ANOS", "6_ANOS"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
ASSINATURAS_IMAGEM = {
    ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",), ".webp": (b"RIFF",), ".heic": (b"\x00\x00\x00",),
}
MAX_ZIP_BYTES = int(os.getenv("RELATORIO_MANUTENCAO_MAX_ZIP_MB", "100")) * 1024 * 1024
MAX_EXTRAIDO_BYTES = int(os.getenv("RELATORIO_MANUTENCAO_MAX_EXTRAIDO_MB", "500")) * 1024 * 1024
MAX_FOTOS = int(os.getenv("RELATORIO_MANUTENCAO_MAX_FOTOS", "500"))
PASTA_UPLOADS = Path(os.getenv("RELATORIO_MANUTENCAO_UPLOAD_DIR", "saida/relatorios_manutencao")).resolve()


def _normalizar_periodicidade(valor: str) -> str:
    periodicidade = re.sub(r"\s+", "_", valor.strip().upper())
    if periodicidade not in PERIODICIDADES:
        raise HTTPException(400, f"Periodicidade invalida. Opcoes: {', '.join(sorted(PERIODICIDADES))}.")
    return periodicidade


def _validar_contexto(db: Session, id_subestacao: int, id_tipo_ativo: int) -> None:
    if not db.get(Subestacao, id_subestacao):
        raise HTTPException(404, "Subestacao nao encontrada.")
    if not db.get(TipoAtivo, id_tipo_ativo):
        raise HTTPException(404, "Tipo de ativo nao encontrado.")
    existe = db.query(Ativo.id_ativo).filter(Ativo.id_subestacao == id_subestacao, Ativo.id_tipo_ativo == id_tipo_ativo).first()
    if not existe:
        raise HTTPException(400, "Nao existe ativo desse tipo na subestacao selecionada.")


def _validar_zip(conteudo: bytes) -> int:
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
            arquivos = [item for item in pacote.infolist() if not item.is_dir()]
            if not arquivos:
                raise HTTPException(400, "O ZIP nao contem fotos.")
            if len(arquivos) > MAX_FOTOS:
                raise HTTPException(400, f"O ZIP excede o limite de {MAX_FOTOS} fotos.")
            total_extraido = 0
            for item in arquivos:
                caminho = PurePosixPath(item.filename.replace("\\", "/"))
                if caminho.is_absolute() or ".." in caminho.parts:
                    raise HTTPException(400, "O ZIP contem um caminho de arquivo inseguro.")
                extensao = caminho.suffix.lower()
                if extensao not in EXTENSOES_IMAGEM:
                    raise HTTPException(400, f"Arquivo nao permitido no ZIP: {caminho.name}.")
                total_extraido += item.file_size
                if total_extraido > MAX_EXTRAIDO_BYTES:
                    raise HTTPException(400, "O conteudo extraido do ZIP excede o limite permitido.")
                with pacote.open(item) as foto:
                    cabecalho = foto.read(12)
                if not any(cabecalho.startswith(assinatura) for assinatura in ASSINATURAS_IMAGEM[extensao]):
                    raise HTTPException(400, f"Conteudo de imagem invalido: {caminho.name}.")
                if extensao == ".webp" and cabecalho[8:12] != b"WEBP":
                    raise HTTPException(400, f"Conteudo de imagem invalido: {caminho.name}.")
                if extensao == ".heic" and b"ftyp" not in cabecalho:
                    raise HTTPException(400, f"Conteudo de imagem invalido: {caminho.name}.")
            return len(arquivos)
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Arquivo ZIP invalido ou corrompido.") from exc


@router.get("/periodicidades", response_model=list[str])
def listar_periodicidades():
    return sorted(PERIODICIDADES)


@router.post("", response_model=RelatorioManutencaoResponse, status_code=status.HTTP_201_CREATED)
async def enviar_relatorio(
    id_subestacao: int = Form(...), id_tipo_ativo: int = Form(...), periodicidade: str = Form(...),
    data_referencia: date = Form(...), arquivo: UploadFile = File(...), observacao: str | None = Form(None),
    hora_inicio: str = Form(...), hora_fim: str = Form(...),
    temperatura_inicio: str = Form(...), temperatura_fim: str = Form(...),
    frequencia_inicio: str = Form(...), frequencia_fim: str = Form(...),
    tensao_inicio: str = Form(...), tensao_fim: str = Form(...),
    texto_introducao: str = Form(...), corpo_tecnico_json: str = Form(...),
    numero_os: str | None = Form(None), numero_apr: str | None = Form(None),
    periodo_capa: str = Form(...), concessao: str = Form(...),
    revisao_json: str | None = Form(None),
    db: Session = Depends(get_db), usuario=Depends(get_current_user),
):
    _validar_contexto(db, id_subestacao, id_tipo_ativo)
    periodicidade = _normalizar_periodicidade(periodicidade)
    nome_original = Path(arquivo.filename or "").name
    if not nome_original.lower().endswith(".zip"):
        raise HTTPException(400, "Envie um arquivo .zip com as fotos.")
    conteudo = await arquivo.read(MAX_ZIP_BYTES + 1)
    if not conteudo:
        raise HTTPException(400, "O arquivo ZIP esta vazio.")
    if len(conteudo) > MAX_ZIP_BYTES:
        raise HTTPException(413, f"O ZIP excede o limite de {MAX_ZIP_BYTES // (1024 * 1024)} MB.")
    quantidade_fotos = _validar_zip(conteudo)
    try:
        revisoes = json.loads(revisao_json) if revisao_json else []
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Revisao das evidencias possui JSON invalido.") from exc
    if not isinstance(revisoes, list):
        raise HTTPException(400, "Revisao das evidencias deve ser uma lista.")
    try:
        corpo_tecnico = json.loads(corpo_tecnico_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Corpo tecnico possui JSON invalido.") from exc
    if not isinstance(corpo_tecnico, list) or not corpo_tecnico:
        raise HTTPException(400, "Informe ao menos uma pessoa no corpo tecnico.")
    corpo_tecnico = [
        {"nome": str(pessoa.get("nome", "")).strip(), "funcao": str(pessoa.get("funcao", "")).strip()}
        for pessoa in corpo_tecnico if isinstance(pessoa, dict)
    ]
    if not corpo_tecnico or any(not pessoa["nome"] or not pessoa["funcao"] for pessoa in corpo_tecnico):
        raise HTTPException(400, "Nome e funcao sao obrigatorios para todo o corpo tecnico.")
    obrigatorios = {
        "horario inicial": hora_inicio, "horario final": hora_fim,
        "temperatura inicial": temperatura_inicio, "temperatura final": temperatura_fim,
        "frequencia inicial": frequencia_inicio, "frequencia final": frequencia_fim,
        "tensao inicial": tensao_inicio, "tensao final": tensao_fim,
        "texto de introducao": texto_introducao, "periodo": periodo_capa, "concessao": concessao,
    }
    vazios = [rotulo for rotulo, valor in obrigatorios.items() if not valor.strip()]
    if vazios:
        raise HTTPException(400, f"Preencha os campos obrigatorios: {', '.join(vazios)}.")
    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        nomes_zip = {item.filename.replace("\\", "/") for item in pacote.infolist() if not item.is_dir()}
    for revisao in revisoes:
        nome_foto = str(revisao.get("arquivo", "")).replace("\\", "/")
        if nome_foto not in nomes_zip:
            raise HTTPException(400, f"Foto revisada nao encontrada no ZIP: {nome_foto}.")
        if revisao.get("status") not in {"OK", "NOK", "NA"}:
            raise HTTPException(400, f"Status invalido para {nome_foto}.")
        id_ativo = revisao.get("id_ativo")
        if id_ativo:
            ativo = db.get(Ativo, int(id_ativo))
            if not ativo or ativo.id_subestacao != id_subestacao or ativo.id_tipo_ativo != id_tipo_ativo:
                raise HTTPException(400, f"Ativo invalido para {nome_foto}.")
        id_item = revisao.get("id_plano_item")
        if id_item:
            item = db.query(PlanoItem).join(PlanoManutencao).filter(
                PlanoItem.id_plano_item == int(id_item),
                PlanoManutencao.id_tipo_ativo == id_tipo_ativo,
                PlanoItem.periodicidade == periodicidade,
            ).first()
            if not item:
                raise HTTPException(400, f"Item do plano invalido para {nome_foto}.")
    nome_armazenado = f"{uuid4().hex}.zip"
    PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_UPLOADS / nome_armazenado
    temporario = PASTA_UPLOADS / f".{nome_armazenado}.tmp"
    try:
        temporario.write_bytes(conteudo)
        temporario.replace(destino)
        relatorio = RelatorioManutencao(
            id_subestacao=id_subestacao, id_tipo_ativo=id_tipo_ativo, periodicidade=periodicidade,
            data_referencia=data_referencia, observacao=(observacao or "").strip() or None,
            texto_introducao=texto_introducao.strip(), corpo_tecnico_json=json.dumps(corpo_tecnico, ensure_ascii=False),
            numero_os=(numero_os or "").strip() or None, numero_apr=(numero_apr or "").strip() or None,
            periodo_capa=periodo_capa.strip(), concessao=concessao.strip(),
            hora_inicio=hora_inicio.strip(), hora_fim=hora_fim.strip(),
            temperatura_inicio=temperatura_inicio.strip(), temperatura_fim=temperatura_fim.strip(),
            frequencia_inicio=frequencia_inicio.strip(), frequencia_fim=frequencia_fim.strip(),
            tensao_inicio=tensao_inicio.strip(), tensao_fim=tensao_fim.strip(),
            nome_arquivo_original=nome_original, nome_arquivo_armazenado=nome_armazenado,
            caminho_arquivo=str(destino), tamanho_bytes=len(conteudo), quantidade_fotos=quantidade_fotos,
            status="RECEBIDO", id_usuario_envio=usuario.id,
        )
        db.add(relatorio)
        db.flush()
        for revisao in revisoes:
            db.add(RelatorioManutencaoFoto(
                id_relatorio_manutencao=relatorio.id_relatorio_manutencao,
                id_ativo=int(revisao["id_ativo"]) if revisao.get("id_ativo") else None,
                id_plano_item=int(revisao["id_plano_item"]) if revisao.get("id_plano_item") else None,
                nome_arquivo_zip=str(revisao["arquivo"]).replace("\\", "/"),
                valor_medido=str(revisao.get("valor", "")).strip() or None,
                status_item=revisao.get("status", "OK"),
                observacao=str(revisao.get("observacao", "")).strip() or None,
                incluir=bool(revisao.get("incluir", True)),
                confianca=str(revisao.get("confianca", "")) or None,
            ))
        db.commit()
        db.refresh(relatorio)
        return relatorio
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        temporario.unlink(missing_ok=True)
        raise


@router.get("", response_model=RelatorioManutencaoPaginadoResponse)
def listar_relatorios(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000), id_subestacao: int | None = None,
    id_tipo_ativo: int | None = None, periodicidade: str | None = None, db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    query = db.query(RelatorioManutencao)
    if id_subestacao is not None:
        query = query.filter(RelatorioManutencao.id_subestacao == id_subestacao)
    if id_tipo_ativo is not None:
        query = query.filter(RelatorioManutencao.id_tipo_ativo == id_tipo_ativo)
    if periodicidade:
        query = query.filter(RelatorioManutencao.periodicidade == _normalizar_periodicidade(periodicidade))
    total = query.count()
    items = query.order_by(RelatorioManutencao.criado_em.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{id_relatorio_manutencao}", response_model=RelatorioManutencaoResponse)
def obter_relatorio(id_relatorio_manutencao: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    return relatorio


def _slug_arquivo(valor: str, limite: int = 80) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode().upper()
    texto = re.sub(r"[^A-Z0-9]+", "_", texto).strip("_")
    return (texto or "NAO_IDENTIFICADO")[:limite].rstrip("_")


def _gerar_zip_fotos_renomeadas(relatorio: RelatorioManutencao, fotos: list[RelatorioManutencaoFoto]) -> Path:
    origem = Path(relatorio.caminho_arquivo)
    destino = PASTA_UPLOADS / f".{uuid4().hex}-renomeado.zip"
    revisoes = {foto.nome_arquivo_zip.replace("\\", "/"): foto for foto in fotos}
    contadores: dict[str, int] = {}
    try:
        with zipfile.ZipFile(origem, "r") as entrada, zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as saida:
            for info in entrada.infolist():
                if info.is_dir():
                    continue
                nome_origem = str(PurePosixPath(info.filename.replace("\\", "/")))
                foto = revisoes.get(nome_origem)
                ativo = foto.ativo.codigo_ativo if foto and foto.ativo else "SEM_ATIVO"
                item = foto.plano_item.nome_item if foto and foto.plano_item else "SEM_ITEM"
                base = f"{_slug_arquivo(ativo, 30)}_{_slug_arquivo(item, 90)}"
                contadores[base] = contadores.get(base, 0) + 1
                extensao = Path(nome_origem).suffix.lower() or ".jpg"
                novo_nome = f"{base}_{contadores[base]:02d}{extensao}"
                saida.writestr(novo_nome, entrada.read(info))
        return destino
    except Exception:
        destino.unlink(missing_ok=True)
        raise

@router.get("/{id_relatorio_manutencao}/arquivo")
def baixar_zip(id_relatorio_manutencao: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    caminho = Path(relatorio.caminho_arquivo)
    if not caminho.is_file():
        raise HTTPException(404, "Arquivo do relatorio nao encontrado.")
    fotos = db.query(RelatorioManutencaoFoto).filter(
        RelatorioManutencaoFoto.id_relatorio_manutencao == id_relatorio_manutencao
    ).all()
    try:
        arquivo_renomeado = _gerar_zip_fotos_renomeadas(relatorio, fotos)
    except Exception as exc:
        raise HTTPException(500, f"Nao foi possivel renomear as fotos do ZIP: {exc}") from exc
    nome_download = f"FOTOS-{relatorio.periodicidade}-{relatorio.data_referencia:%Y-%m-%d}.zip"
    return FileResponse(
        arquivo_renomeado,
        media_type="application/zip",
        filename=nome_download,
        background=BackgroundTask(arquivo_renomeado.unlink, missing_ok=True),
    )
@router.get("/{id_relatorio_manutencao}/arquivo-word")
def baixar_word(
    id_relatorio_manutencao: int,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    if not Path(relatorio.caminho_arquivo).is_file():
        raise HTTPException(404, "Arquivo fonte do relatorio nao encontrado.")
    try:
        caminho = gerar_relatorio_word(
            relatorio,
            relatorio.tipo_ativo.nome,
            relatorio.subestacao.nome,
            relatorio.usuario_envio.nome,
            db.query(RelatorioManutencaoFoto).filter(RelatorioManutencaoFoto.id_relatorio_manutencao == id_relatorio_manutencao).all(),
            corpo_tecnico=json.loads(relatorio.corpo_tecnico_json) if relatorio.corpo_tecnico_json else None,
            numero_os=relatorio.numero_os or "", numero_apr=relatorio.numero_apr or "",
            periodo_capa=relatorio.periodo_capa or "", concessao=relatorio.concessao or "Rialma Transmissora de Energia - RTV",
            texto_introducao=relatorio.texto_introducao or "",
            parametros_inspecao={
                "hora_inicio": relatorio.hora_inicio or "", "hora_fim": relatorio.hora_fim or "",
                "temperatura_inicio": relatorio.temperatura_inicio or "", "temperatura_fim": relatorio.temperatura_fim or "",
                "frequencia_inicio": relatorio.frequencia_inicio or "", "frequencia_fim": relatorio.frequencia_fim or "",
                "tensao_inicio": relatorio.tensao_inicio or "", "tensao_fim": relatorio.tensao_fim or "",
            },
        )
    except Exception as exc:
        raise HTTPException(500, f"Nao foi possivel gerar o arquivo Word: {exc}") from exc
    nome_tipo = re.sub(r"[^A-Za-z0-9_-]+", "-", relatorio.tipo_ativo.nome).strip("-")
    nome = f"RELATORIO-{relatorio.periodicidade}-{nome_tipo}-{relatorio.data_referencia:%Y-%m-%d}.docx"
    return FileResponse(
        caminho,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=nome,
    )
@router.get("/{id_relatorio_manutencao}/revisao")
def obter_revisao(id_relatorio_manutencao: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    fotos = db.query(RelatorioManutencaoFoto).filter(RelatorioManutencaoFoto.id_relatorio_manutencao == id_relatorio_manutencao).all()
    ativos = db.query(Ativo).filter(Ativo.id_subestacao == relatorio.id_subestacao, Ativo.id_tipo_ativo == relatorio.id_tipo_ativo).all()
    ids_planos = [linha[0] for linha in db.query(PlanoManutencao.id_plano_manutencao).filter(PlanoManutencao.id_tipo_ativo == relatorio.id_tipo_ativo).all()]
    itens = db.query(PlanoItem).filter(PlanoItem.id_plano_manutencao.in_(ids_planos), PlanoItem.periodicidade == relatorio.periodicidade).order_by(PlanoItem.ordem, PlanoItem.id_plano_item).all() if ids_planos else []
    miniaturas = {}
    try:
        with zipfile.ZipFile(Path(relatorio.caminho_arquivo)) as pacote:
            entradas = {i.filename.replace("\\", "/"): i for i in pacote.infolist() if not i.is_dir()}
            for foto in fotos:
                nome = foto.nome_arquivo_zip.replace("\\", "/")
                miniaturas[nome] = criar_miniatura_data_url(pacote.read(entradas[nome])) if nome in entradas else None
    except (OSError, zipfile.BadZipFile):
        pass
    try:
        corpo_tecnico = json.loads(relatorio.corpo_tecnico_json or "[]")
    except json.JSONDecodeError:
        corpo_tecnico = []
    return {
        "id_relatorio_manutencao": id_relatorio_manutencao, "id_subestacao": relatorio.id_subestacao, "id_tipo_ativo": relatorio.id_tipo_ativo,
        "periodicidade": relatorio.periodicidade, "data_referencia": relatorio.data_referencia, "observacao": relatorio.observacao or "",
        "texto_introducao": relatorio.texto_introducao or "", "corpo_tecnico": corpo_tecnico, "numero_os": relatorio.numero_os or "", "numero_apr": relatorio.numero_apr or "",
        "periodo_capa": relatorio.periodo_capa or "", "concessao": relatorio.concessao or "", "hora_inicio": relatorio.hora_inicio or "", "hora_fim": relatorio.hora_fim or "",
        "temperatura_inicio": relatorio.temperatura_inicio or "", "temperatura_fim": relatorio.temperatura_fim or "", "frequencia_inicio": relatorio.frequencia_inicio or "", "frequencia_fim": relatorio.frequencia_fim or "",
        "tensao_inicio": relatorio.tensao_inicio or "", "tensao_fim": relatorio.tensao_fim or "",
        "ativos": [{"id_ativo": a.id_ativo, "codigo_ativo": a.codigo_ativo, "fase": a.fase, "bay": a.bay} for a in ativos],
        "itens": [{"id_plano_item": i.id_plano_item, "nome_item": i.nome_item, "unidade": i.unidade} for i in itens],
        "fotos": [{"arquivo": f.nome_arquivo_zip.replace("\\", "/"), "miniatura": miniaturas.get(f.nome_arquivo_zip.replace("\\", "/")), "id_ativo": f.id_ativo, "id_plano_item": f.id_plano_item, "valor": f.valor_medido or "", "status": f.status_item, "observacao": f.observacao or "", "incluir": f.incluir, "confianca": float(f.confianca or 0)} for f in fotos],
    }

@router.put("/{id_relatorio_manutencao}/revisao")
def atualizar_revisao(id_relatorio_manutencao: int, payload: dict = Body(...), db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    if "data_referencia" in payload:
        try:
            relatorio.data_referencia = date.fromisoformat(str(payload["data_referencia"]))
        except ValueError as exc:
            raise HTTPException(400, "Data de referencia invalida.") from exc
    if "observacao" in payload:
        relatorio.observacao = str(payload.get("observacao") or "").strip() or None
    for chave in ("texto_introducao", "numero_os", "numero_apr", "periodo_capa", "concessao", "hora_inicio", "hora_fim", "temperatura_inicio", "temperatura_fim", "frequencia_inicio", "frequencia_fim", "tensao_inicio", "tensao_fim"):
        if chave in payload:
            setattr(relatorio, chave, str(payload.get(chave) or "").strip() or None)
    if "corpo_tecnico" in payload:
        pessoas = payload.get("corpo_tecnico")
        if not isinstance(pessoas, list) or not pessoas:
            raise HTTPException(400, "Informe ao menos uma pessoa no corpo tecnico.")
        pessoas = [{"nome": str(p.get("nome", "")).strip(), "funcao": str(p.get("funcao", "")).strip()} for p in pessoas if isinstance(p, dict)]
        if not pessoas or any(not p["nome"] or not p["funcao"] for p in pessoas):
            raise HTTPException(400, "Nome e funcao sao obrigatorios para todo o corpo tecnico.")
        relatorio.corpo_tecnico_json = json.dumps(pessoas, ensure_ascii=False)
    relatorio.id_usuario_edicao = usuario.id
    existentes = {foto.nome_arquivo_zip: foto for foto in db.query(RelatorioManutencaoFoto).filter(RelatorioManutencaoFoto.id_relatorio_manutencao == id_relatorio_manutencao).all()}
    for revisao in payload.get("fotos", []):
        foto = existentes.get(str(revisao.get("arquivo", "")).replace("\\", "/"))
        if not foto:
            raise HTTPException(400, "Fotografia nao pertence ao relatorio.")
        if revisao.get("status") not in {"OK", "NOK", "NA"}:
            raise HTTPException(400, "Status da fotografia invalido.")
        if revisao.get("id_ativo"):
            ativo = db.get(Ativo, int(revisao["id_ativo"]))
            if not ativo or ativo.id_subestacao != relatorio.id_subestacao or ativo.id_tipo_ativo != relatorio.id_tipo_ativo:
                raise HTTPException(400, "Ativo invalido para a fotografia.")
        if revisao.get("id_plano_item"):
            item = db.query(PlanoItem).join(PlanoManutencao).filter(PlanoItem.id_plano_item == int(revisao["id_plano_item"]), PlanoManutencao.id_tipo_ativo == relatorio.id_tipo_ativo, PlanoItem.periodicidade == relatorio.periodicidade).first()
            if not item:
                raise HTTPException(400, "Item do plano invalido para a fotografia.")
        foto.id_ativo = int(revisao["id_ativo"]) if revisao.get("id_ativo") else None
        foto.id_plano_item = int(revisao["id_plano_item"]) if revisao.get("id_plano_item") else None
        foto.valor_medido = str(revisao.get("valor", "")).strip() or None
        foto.status_item = revisao["status"]
        foto.observacao = str(revisao.get("observacao", "")).strip() or None
        foto.incluir = bool(revisao.get("incluir", True))
    db.commit()
    return {"ok": True, "id_relatorio_manutencao": id_relatorio_manutencao}
@router.delete("/{id_relatorio_manutencao}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_relatorio(id_relatorio_manutencao: int, db: Session = Depends(get_db), _usuario=Depends(get_current_user)):
    relatorio = db.get(RelatorioManutencao, id_relatorio_manutencao)
    if not relatorio:
        raise HTTPException(404, "Relatorio de manutencao nao encontrado.")
    caminho_zip = Path(relatorio.caminho_arquivo).resolve()
    pasta_permitida = PASTA_UPLOADS.resolve()
    if pasta_permitida != caminho_zip.parent:
        raise HTTPException(500, "Caminho do arquivo fora da pasta permitida.")
    db.delete(relatorio)
    db.commit()
    caminho_zip.unlink(missing_ok=True)
    caminho_zip.with_suffix(".docx").unlink(missing_ok=True)
    return None








