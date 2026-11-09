"""Servico do diagrama unifilar por subestacao.

O diagrama e gravado no formato do editor (nos + ligacoes), mas
normalizado em quatro tabelas: ``unifilar_diagrama`` (guia por
subestacao), ``unifilar_componente`` (um no grafico),
``unifilar_terminal`` (terminais declarados do componente) e
``unifilar_conexao`` (ligacao). ``id_externo`` preserva o identificador
usado pelo editor.

O salvamento e substitutivo: apaga e regrava todos os nos/ligacoes do
diagrama em uma transacao (diagrama unico por subestacao, dezenas de
componentes por tela).

Tipos sao validados contra ``unifilar_tipo_componente`` - catalogo
semeado pela migracao 020, espelho do catalogo do frontend.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.instalacao_models import Subestacao

from . import schemas

# Limites de tela - protegem contra payload desproporcional.
MAX_COMPONENTES = 300
MAX_CONEXOES = 600

# Tipos com terminais de barramento (B1-B4) versus equipamento (T1/T2).
TIPOS_TERMINAIS_BARRAMENTO = {"BARRAMENTO", "CONEXAO", "ETIQUETA_VAO"}


def _terminais_do(tipo: str) -> tuple[str, ...]:
    if tipo in TIPOS_TERMINAIS_BARRAMENTO:
        return ("B1", "B2", "B3", "B4")
    return ("T1", "T2")


def _exige_subestacao(db: Session, id_subestacao: int) -> None:
    if not db.query(Subestacao.id_subestacao).filter(
        Subestacao.id_subestacao == id_subestacao
    ).first():
        raise HTTPException(status_code=404, detail="Subestação não encontrada.")


def _tipos_validos(db: Session) -> set[str]:
    return {
        linha[0]
        for linha in db.execute(text("SELECT tipo FROM unifilar_tipo_componente"))
    }


def _limites_por_tipo(db: Session) -> dict[str, int]:
    return {
        str(linha.tipo): int(linha.max_por_terminal)
        for linha in db.execute(
            text("SELECT tipo, max_por_terminal FROM unifilar_tipo_componente")
        )
    }


def catalogo(db: Session) -> list[schemas.TipoComponenteSaida]:
    """Catalogo de tipos gravado no banco (ordem padrao da biblioteca)."""
    linhas = db.execute(
        text(
            "SELECT tipo, nome, categoria, aceita_ativo, max_por_terminal, largura, altura "
            "FROM unifilar_tipo_componente "
            "ORDER BY FIELD(categoria, 'estrutura', 'equipamento', 'instrumento', 'apoio'), tipo"
        )
    )
    return [
        schemas.TipoComponenteSaida(
            tipo=l.tipo,
            nome=l.nome,
            categoria=l.categoria,
            aceita_ativo=bool(l.aceita_ativo),
            max_por_terminal=int(l.max_por_terminal),
            largura=float(l.largura),
            altura=float(l.altura),
        )
        for l in linhas
    ]


def _id_diagrama_de(db: Session, id_subestacao: int) -> int | None:
    linha = db.execute(
        text("SELECT id_diagrama FROM unifilar_diagrama WHERE id_subestacao = :s"),
        {"s": id_subestacao},
    ).first()
    return int(linha[0]) if linha else None


def carregar_diagrama(db: Session, id_subestacao: int) -> schemas.DiagramaSaida:
    """Devolve o diagrama salvo da subestacao (ou vazio, nunca 404)."""
    _exige_subestacao(db, id_subestacao)

    id_diagrama = _id_diagrama_de(db, id_subestacao)
    if id_diagrama is None:
        return schemas.DiagramaSaida(id_subestacao=id_subestacao, atualizado_em=None)

    id_por_pk: dict[int, str] = {}
    nos_saida: list[schemas.NoSaida] = []
    for no in db.execute(
        text(
            "SELECT id_componente, id_externo, tipo, codigo, nome, vao, rotacao, "
            "posicao_x, posicao_y, largura, altura, id_ativo "
            "FROM unifilar_componente WHERE id_diagrama = :d ORDER BY id_componente"
        ),
        {"d": id_diagrama},
    ):
        id_por_pk[int(no.id_componente)] = no.id_externo
        nos_saida.append(
            schemas.NoSaida(
                id=no.id_externo,
                position=schemas.Posicao(x=float(no.posicao_x or 0), y=float(no.posicao_y or 0)),
                data=schemas.DadosNoEntrada(
                    tipo=no.tipo,
                    codigo=no.codigo,
                    nome=no.nome,
                    vao=no.vao,
                    rotacao=int(no.rotacao or 0),
                    largura=float(no.largura) if no.largura is not None else None,
                    altura=float(no.altura) if no.altura is not None else None,
                    id_ativo=int(no.id_ativo) if no.id_ativo is not None else None,
                ),
            )
        )

    ligacoes_saida: list[schemas.LigacaoSaida] = []
    for lig in db.execute(
        text(
            "SELECT id_externo, id_componente_origem, terminal_origem, "
            "id_componente_destino, terminal_destino "
            "FROM unifilar_conexao WHERE id_diagrama = :d ORDER BY id_conexao"
        ),
        {"d": id_diagrama},
    ):
        origem = id_por_pk.get(lig.id_componente_origem)
        destino = id_por_pk.get(lig.id_componente_destino)
        if not origem or not destino:
            continue
        ligacoes_saida.append(
            schemas.LigacaoSaida(
                id=lig.id_externo,
                source=origem,
                sourceHandle=lig.terminal_origem,
                target=destino,
                targetHandle=lig.terminal_destino,
            )
        )

    atualizado = db.execute(
        text("SELECT atualizado_em FROM unifilar_diagrama WHERE id_diagrama = :d"),
        {"d": id_diagrama},
    ).scalar()

    return schemas.DiagramaSaida(
        id_subestacao=id_subestacao,
        atualizado_em=atualizado,
        nodes=nos_saida,
        edges=ligacoes_saida,
    )


def salvar_diagrama(
    db: Session, id_subestacao: int, dados: schemas.DiagramaEntrada, id_usuario: int | None
) -> schemas.DiagramaSaida:
    """Substitui o diagrama da subestacao pelos nos/ligacoes informados."""
    _exige_subestacao(db, id_subestacao)

    if len(dados.nodes) > MAX_COMPONENTES or len(dados.edges) > MAX_CONEXOES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Diagrama muito grande (limite de {MAX_COMPONENTES} componentes "
                f"e {MAX_CONEXOES} ligações)."
            ),
        )

    tipos_validos = _tipos_validos(db)
    limites = _limites_por_tipo(db)
    tipos_com_ativo = {
        str(linha.tipo)
        for linha in db.execute(
            text("SELECT tipo FROM unifilar_tipo_componente WHERE aceita_ativo = 1")
        )
    }
    ids_externos: set[str] = set()
    tipo_por_id: dict[str, str] = {}
    ativos_associados: set[int] = set()
    for no in dados.nodes:
        if no.id in ids_externos:
            raise HTTPException(
                status_code=422, detail=f"Componente repetido no diagrama: {no.id}."
            )
        ids_externos.add(no.id)
        tipo_por_id[no.id] = no.data.tipo
        if no.data.tipo not in tipos_validos:
            raise HTTPException(
                status_code=422,
                detail=f"Tipo de componente desconhecido: {no.data.tipo}.",
            )
        if no.data.rotacao % 90 != 0:
            raise HTTPException(
                status_code=422,
                detail=f"Rotação deve ser múltiplo de 90 (componente {no.id}).",
            )
        if no.data.id_ativo is not None:
            if no.data.tipo not in tipos_com_ativo:
                raise HTTPException(
                    status_code=422,
                    detail=f"O componente {no.id} não aceita associação com ativo.",
                )
            if no.data.id_ativo in ativos_associados:
                raise HTTPException(
                    status_code=422,
                    detail=f"O ativo {no.data.id_ativo} está associado mais de uma vez neste diagrama.",
                )
            pertence = db.execute(
                text(
                    "SELECT id_ativo FROM ativo "
                    "WHERE id_ativo = :ativo AND id_subestacao = :subestacao"
                ),
                {"ativo": no.data.id_ativo, "subestacao": id_subestacao},
            ).first()
            if not pertence:
                raise HTTPException(
                    status_code=422,
                    detail=f"O ativo {no.data.id_ativo} não pertence a esta subestação.",
                )
            ativos_associados.add(no.data.id_ativo)

    chaves_ligacao: set[tuple[str, str, str, str]] = set()
    ids_ligacao: set[str] = set()
    graus: dict[tuple[str, str], int] = {}
    for lig in dados.edges:
        if lig.source not in ids_externos or lig.target not in ids_externos:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Ligação inválida: referência a componente inexistente "
                    f"({lig.source} / {lig.target})."
                ),
            )
        if not lig.sourceHandle or not lig.targetHandle:
            raise HTTPException(
                status_code=422,
                detail="Ligação sem terminal definido — reconecte no editor.",
            )
        if lig.source == lig.target:
            raise HTTPException(status_code=422, detail="Um componente não pode se conectar a si mesmo.")
        terminais_origem = _terminais_do(tipo_por_id[lig.source])
        terminais_destino = _terminais_do(tipo_por_id[lig.target])
        if lig.sourceHandle not in terminais_origem or lig.targetHandle not in terminais_destino:
            raise HTTPException(status_code=422, detail="A ligação referencia um terminal inválido.")
        chave = (lig.source, lig.sourceHandle, lig.target, lig.targetHandle)
        chave_inversa = (lig.target, lig.targetHandle, lig.source, lig.sourceHandle)
        if chave in chaves_ligacao or chave_inversa in chaves_ligacao:
            raise HTTPException(status_code=422, detail="Já existe uma ligação entre esses terminais.")
        chaves_ligacao.add(chave)
        id_ligacao = _id_externo_ligacao(lig)
        if id_ligacao in ids_ligacao:
            raise HTTPException(status_code=422, detail="O diagrama contém identificadores de ligação repetidos.")
        ids_ligacao.add(id_ligacao)
        for no_id, terminal in (
            (lig.source, lig.sourceHandle),
            (lig.target, lig.targetHandle),
        ):
            ponto = (no_id, terminal)
            graus[ponto] = graus.get(ponto, 0) + 1
            limite = limites[tipo_por_id[no_id]]
            if graus[ponto] > limite:
                raise HTTPException(
                    status_code=422,
                    detail=f"Terminal {terminal} sem capacidade para outra ligação.",
                )

    try:
        db.execute(
            text(
                "INSERT INTO unifilar_diagrama (id_subestacao, id_usuario_ultimo) "
                "VALUES (:s, :u) "
                "ON DUPLICATE KEY UPDATE id_usuario_ultimo = :u, "
                "atualizado_em = CURRENT_TIMESTAMP"
            ),
            {"s": id_subestacao, "u": id_usuario},
        )
        id_diagrama = db.execute(
            text("SELECT id_diagrama FROM unifilar_diagrama WHERE id_subestacao = :s"),
            {"s": id_subestacao},
        ).scalar_one()

        db.execute(text("DELETE FROM unifilar_conexao WHERE id_diagrama = :d"), {"d": id_diagrama})
        db.execute(text("DELETE FROM unifilar_componente WHERE id_diagrama = :d"), {"d": id_diagrama})

        id_por_externo: dict[str, int] = {}
        for no in dados.nodes:
            resultado = db.execute(
                text(
                    "INSERT INTO unifilar_componente "
                    "(id_diagrama, id_externo, tipo, codigo, nome, vao, rotacao, "
                    "posicao_x, posicao_y, largura, altura, id_ativo) "
                    "VALUES (:d, :e, :t, :c, :n, :v, :r, :x, :y, :w, :h, :a)"
                ),
                {
                    "d": id_diagrama,
                    "e": no.id,
                    "t": no.data.tipo,
                    "c": no.data.codigo,
                    "n": no.data.nome,
                    "v": no.data.vao,
                    "r": no.data.rotacao,
                    "x": no.position.x,
                    "y": no.position.y,
                    "w": no.data.largura,
                    "h": no.data.altura,
                    "a": no.data.id_ativo,
                },
            )
            id_componente = int(resultado.lastrowid)
            id_por_externo[no.id] = id_componente
            for terminal in _terminais_do(no.data.tipo):
                db.execute(
                    text(
                        "INSERT INTO unifilar_terminal (id_componente, terminal) "
                        "VALUES (:c, :t)"
                    ),
                    {"c": id_componente, "t": terminal},
                )

        for lig in dados.edges:
            db.execute(
                text(
                    "INSERT INTO unifilar_conexao "
                    "(id_diagrama, id_externo, id_componente_origem, terminal_origem, "
                    "id_componente_destino, terminal_destino) "
                    "VALUES (:d, :e, :so, :sh, :ta, :th)"
                ),
                {
                    "d": id_diagrama,
                    "e": _id_externo_ligacao(lig),
                    "so": id_por_externo[lig.source],
                    "sh": lig.sourceHandle,
                    "ta": id_por_externo[lig.target],
                    "th": lig.targetHandle,
                },
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001 - rollback antes de propagar
        db.rollback()
        raise HTTPException(status_code=500, detail="Falha ao salvar o diagrama.") from exc

    return carregar_diagrama(db, id_subestacao)


def _id_externo_ligacao(lig: schemas.LigacaoEntrada) -> str:
    """Id estavel de ligacao no banco."""
    id_editor = (lig.id or "").strip()
    if id_editor:
        return id_editor[:160]
    return f"l-{lig.source}-{lig.sourceHandle}-{lig.target}-{lig.targetHandle}"[:160]
