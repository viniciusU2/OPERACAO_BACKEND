"""Seed idempotente da base de conhecimento de problemas típicos de subestações.

Uso:
    python -m scripts.seed_problemas_tipicos
    python -m scripts.seed_problemas_tipicos --dry-run
    python -m scripts.seed_problemas_tipicos --sem-atualizar

Garantias:
- idempotente: a chave natural é ``problema_tipico.codigo`` (prefixo ``BDC-``);
- nunca sobrescreve registros validados por especialista, ocorrências reais nem
  o campo ``ativo`` de registros existentes;
- não apaga nem altera dados operacionais (SS, OS, ativos, subestações);
- transacional: cada problema é aplicado em um SAVEPOINT próprio, de modo que
  uma falha isolada não interrompe a carga e não deixa registros parciais;
- registra a quantidade de registros inseridos, atualizados, inalterados e
  preservados.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from database import SessionLocal  # noqa: E402
from problemas_tipicos import migracoes as problemas_tipicos_migracoes  # noqa: E402
from problemas_tipicos.catalogo import CATALOGO  # noqa: E402

LOGGER = logging.getLogger("seed.problemas_tipicos")

# Tipos de ativo criados somente quando ausentes no catálogo do ENGVI.
TIPOS_ATIVOS_NOVOS = {
    "Transformador de Potência": "Transformador de potência de subestação",
    "Transformador de Potencial": "Transformador de potencial indutivo (TP) para proteção e medição",
    "Barramento": "Barramentos, conexões e emendas de subestação",
    "Isolador": "Isoladores de subestação e de linha de transmissão",
}

CAMPOS_ESCALARES = (
    "id_tipo_ativo",
    "titulo",
    "categoria",
    "sistema",
    "descricao",
    "criticidade_padrao",
    "modo_falha",
    "efeito_falha",
    "detectabilidade",
    "especialidade",
    "requer_desligamento",
    "risco_operacional",
    "condicao_intervencao",
    "requer_equipe_especializada",
    "alerta_seguranca",
    "referencias_tecnicas",
)


def normalizar(texto: str) -> str:
    """Compara nomes de tipo de ativo ignorando acentos, caixa e espaçamento."""
    limpo = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", limpo.lower())


def _enum(classe, valor):
    return classe[valor] if isinstance(valor, str) else valor


def _conteudo_esperado(item: dict, id_tipo_ativo: int) -> dict:
    """Conteúdo de referência usado para detectar necessidade real de update."""
    da_seed = item
    return {
        "id_tipo_ativo": id_tipo_ativo,
        "titulo": da_seed["titulo"],
        "categoria": da_seed["categoria"],
        "sistema": da_seed["sistema"],
        "descricao": da_seed["descricao"],
        "criticidade_padrao": da_seed["criticidade"],
        "modo_falha": da_seed["modo_falha"],
        "efeito_falha": da_seed["efeito_falha"],
        "detectabilidade": da_seed["detectabilidade"],
        "especialidade": da_seed["especialidade"],
        "requer_desligamento": da_seed["requer_desligamento"],
        "risco_operacional": da_seed["risco_operacional"],
        "condicao_intervencao": da_seed["condicao_intervencao"],
        "requer_equipe_especializada": da_seed["requer_equipe_especializada"],
        "alerta_seguranca": da_seed["alerta_seguranca"],
        "referencias_tecnicas": da_seed["referencias_tecnicas"],
    }


def _conteudo_atual(problema) -> dict:
    def valor(campo):
        atual = getattr(problema, campo)
        return atual.value if hasattr(atual, "value") else atual

    atual = {campo: valor(campo) for campo in CAMPOS_ESCALARES}
    atual["sintomas"] = [s.sintoma for s in problema.sintomas]
    atual["causas"] = [c.causa for c in problema.causas]
    atual["metodos_deteccao"] = [m.metodo for m in problema.metodos_deteccao]
    atual["alarmes"] = [a.alarme for a in problema.alarmes]
    atual["palavras_chave"] = [p.palavra_chave for p in problema.palavras_chave]
    atual["instrumentos"] = [i.instrumento for i in problema.instrumentos]
    atual["acoes_recomendadas"] = sorted(
        (
            a.tipo_acao.value if hasattr(a.tipo_acao, "value") else a.tipo_acao,
            a.descricao,
            a.prioridade,
            a.prazo_recomendado,
        )
        for a in problema.acoes_recomendadas
    )
    return atual


def _conteudo_catalogo(item: dict, id_tipo_ativo: int) -> dict:
    esperado = _conteudo_esperado(item, id_tipo_ativo)
    esperado["sintomas"] = list(item["sintomas"])
    esperado["causas"] = list(item["causas"])
    esperado["metodos_deteccao"] = list(item["metodos_deteccao"])
    esperado["alarmes"] = list(item["alarmes"])
    esperado["palavras_chave"] = list(item["palavras_chave"])
    esperado["instrumentos"] = list(item["instrumentos"])
    esperado["acoes_recomendadas"] = sorted(
        (a["tipo_acao"], a["descricao"], a["prioridade"], a["prazo_recomendado"])
        for a in item["acoes_recomendadas"]
    )
    return esperado


def _aplicar_conteudo(problema, item: dict, id_tipo_ativo: int, modelos) -> None:
    (SintomaProblema, CausaProblema, MetodoDeteccaoProblema, AlarmeProblema,
     PalavraChaveProblema, InstrumentoProblema, AcaoRecomendada, CriticidadeProblema,
     DetectabilidadeProblema, RiscoOperacional, CondicaoIntervencao, TipoAcao) = modelos

    for campo, valor in _conteudo_esperado(item, id_tipo_ativo).items():
        if campo in ("criticidade_padrao", "detectabilidade", "risco_operacional", "condicao_intervencao"):
            classe = {
                "criticidade_padrao": CriticidadeProblema,
                "detectabilidade": DetectabilidadeProblema,
                "risco_operacional": RiscoOperacional,
                "condicao_intervencao": CondicaoIntervencao,
            }[campo]
            valor = _enum(classe, valor) if valor else None
        setattr(problema, campo, valor)

    problema.sintomas = [SintomaProblema(sintoma=x) for x in item["sintomas"]]
    problema.causas = [CausaProblema(causa=x) for x in item["causas"]]
    problema.metodos_deteccao = [MetodoDeteccaoProblema(metodo=x) for x in item["metodos_deteccao"]]
    problema.alarmes = [AlarmeProblema(alarme=x) for x in item["alarmes"]]
    problema.palavras_chave = [PalavraChaveProblema(palavra_chave=x) for x in item["palavras_chave"]]
    problema.instrumentos = [InstrumentoProblema(instrumento=x) for x in item["instrumentos"]]
    problema.acoes_recomendadas = [
        AcaoRecomendada(
            tipo_acao=TipoAcao[a["tipo_acao"]],
            descricao=a["descricao"],
            prioridade=a["prioridade"],
            prazo_recomendado=a["prazo_recomendado"],
        )
        for a in item["acoes_recomendadas"]
    ]


def _carregar_modelos():
    import main  # noqa: F401  # registra todos os models e aplica a migração na subida

    from models.familias_models import TipoAtivo
    from models.problemas_tipicos_models import (
        AcaoRecomendada,
        AlarmeProblema,
        CausaProblema,
        CondicaoIntervencao,
        CriticidadeProblema,
        DetectabilidadeProblema,
        InstrumentoProblema,
        MetodoDeteccaoProblema,
        OrigemRegistroProblema,
        PalavraChaveProblema,
        ProblemaTipico,
        RiscoOperacional,
        SintomaProblema,
        StatusValidacaoProblema,
        TipoAcao,
    )

    return {
        "TipoAtivo": TipoAtivo,
        "ProblemaTipico": ProblemaTipico,
        "OrigemRegistroProblema": OrigemRegistroProblema,
        "StatusValidacaoProblema": StatusValidacaoProblema,
        "CriticidadeProblema": CriticidadeProblema,
        "DetectabilidadeProblema": DetectabilidadeProblema,
        "RiscoOperacional": RiscoOperacional,
        "CondicaoIntervencao": CondicaoIntervencao,
        "TipoAcao": TipoAcao,
        "SintomaProblema": SintomaProblema,
        "CausaProblema": CausaProblema,
        "MetodoDeteccaoProblema": MetodoDeteccaoProblema,
        "AlarmeProblema": AlarmeProblema,
        "PalavraChaveProblema": PalavraChaveProblema,
        "InstrumentoProblema": InstrumentoProblema,
        "AcaoRecomendada": AcaoRecomendada,
    }


def _modelos_acao(modelos):
    return (
        modelos["SintomaProblema"],
        modelos["CausaProblema"],
        modelos["MetodoDeteccaoProblema"],
        modelos["AlarmeProblema"],
        modelos["PalavraChaveProblema"],
        modelos["InstrumentoProblema"],
        modelos["AcaoRecomendada"],
        modelos["CriticidadeProblema"],
        modelos["DetectabilidadeProblema"],
        modelos["RiscoOperacional"],
        modelos["CondicaoIntervencao"],
        modelos["TipoAcao"],
    )


def _resolver_tipos(db, modelos, criar_tipos: bool, resumo: dict) -> dict:
    """Mapa normalizado(nome) -> id_tipo_ativo, criando os tipos ausentes."""
    TipoAtivo = modelos["TipoAtivo"]
    indice = {normalizar(t.nome): t.id_tipo_ativo for t in db.query(TipoAtivo).all()}

    necessarios = {item["tipo_ativo"] for item in CATALOGO}
    for nome in sorted(necessarios):
        chave = normalizar(nome)
        if chave in indice:
            continue
        if not criar_tipos or nome not in TIPOS_ATIVOS_NOVOS:
            LOGGER.warning("Tipo de ativo '%s' não encontrado e não será criado.", nome)
            resumo["tipos_ausentes"].append(nome)
            continue
        tipo = TipoAtivo(nome=nome, descricao=TIPOS_ATIVOS_NOVOS[nome])
        db.add(tipo)
        db.flush()
        indice[chave] = tipo.id_tipo_ativo
        resumo["tipos_criados"].append(nome)
        LOGGER.info("Tipo de ativo criado: %s (%s)", nome, tipo.id_tipo_ativo)
    return indice


def executar(*, dry_run: bool = False, atualizar: bool = True, criar_tipos: bool = True,
             migrar: bool = True) -> dict:
    modelos = _carregar_modelos()
    ProblemaTipico = modelos["ProblemaTipico"]
    OrigemRegistroProblema = modelos["OrigemRegistroProblema"]
    StatusValidacaoProblema = modelos["StatusValidacaoProblema"]

    resumo = {
        "inseridos": 0,
        "atualizados": 0,
        "inalterados": 0,
        "preservados": 0,
        "ignorados_por_opcao": 0,
        "ignorados_sem_tipo": 0,
        "tipos_criados": [],
        "tipos_ausentes": [],
        "erros": [],
        "migracoes_aplicadas": [],
        "dry_run": dry_run,
    }

    db = SessionLocal()
    try:
        if migrar:
            resumo["migracoes_aplicadas"] = problemas_tipicos_migracoes.aplicar_migracoes(db)

        indice_tipos = _resolver_tipos(db, modelos, criar_tipos, resumo)
        acoes = _modelos_acao(modelos)

        for item in CATALOGO:
            id_tipo_ativo = indice_tipos.get(normalizar(item["tipo_ativo"]))
            if not id_tipo_ativo:
                resumo["ignorados_sem_tipo"] += 1
                continue

            try:
                with db.begin_nested():
                    existente = (
                        db.query(ProblemaTipico)
                        .filter(ProblemaTipico.codigo == item["codigo"])
                        .one_or_none()
                    )

                    if existente is None:
                        problema = ProblemaTipico(
                            codigo=item["codigo"],
                            origem_registro=OrigemRegistroProblema.REFERENCIA_TECNICA,
                            status_validacao=StatusValidacaoProblema.PENDENTE,
                        )
                        _aplicar_conteudo(problema, item, id_tipo_ativo, acoes)
                        db.add(problema)
                        resumo["inseridos"] += 1
                        continue

                    # Protege dados curados e ocorrências reais.
                    if existente.origem_registro == OrigemRegistroProblema.OCORRENCIA_REAL:
                        resumo["preservados"] += 1
                        continue
                    if existente.status_validacao in (
                        StatusValidacaoProblema.VALIDADO,
                        StatusValidacaoProblema.REPROVADO,
                    ):
                        resumo["preservados"] += 1
                        continue

                    if _conteudo_atual(existente) == _conteudo_catalogo(item, id_tipo_ativo):
                        resumo["inalterados"] += 1
                        continue

                    if not atualizar:
                        resumo["ignorados_por_opcao"] += 1
                        continue

                    _aplicar_conteudo(existente, item, id_tipo_ativo, acoes)
                    resumo["atualizados"] += 1
            except Exception as exc:  # noqa: BLE001 - uma falha não impede as demais
                resumo["erros"].append({"codigo": item["codigo"], "erro": str(exc)})
                LOGGER.exception("Falha ao aplicar o problema %s", item["codigo"])

        if dry_run:
            db.rollback()
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return resumo


def _configurar_log(arquivo: str | None) -> None:
    manipuladores: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if arquivo:
        Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
        manipuladores.append(logging.FileHandler(arquivo, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=manipuladores,
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed da base de conhecimento de problemas típicos.")
    parser.add_argument("--dry-run", action="store_true", help="executa sem gravar (rollback ao final)")
    parser.add_argument("--sem-atualizar", action="store_true", help="apenas insere; não atualiza registros existentes")
    parser.add_argument("--sem-criar-tipos", action="store_true", help="não cria tipos de ativo ausentes")
    parser.add_argument("--sem-migrar", action="store_true", help="não aplica a migração do módulo")
    parser.add_argument("--log-arquivo", default=None, help="grava o log também neste arquivo")
    parser.add_argument("--json", action="store_true", help="imprime o resumo em JSON ao final")
    args = parser.parse_args(argv)

    _configurar_log(args.log_arquivo)

    resumo = executar(
        dry_run=args.dry_run,
        atualizar=not args.sem_atualizar,
        criar_tipos=not args.sem_criar_tipos,
        migrar=not args.sem_migrar,
    )

    if args.json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
    else:
        LOGGER.info(
            "Seed concluída%s: %d inseridos, %d atualizados, %d inalterados, %d preservados, "
            "%d ignorados por opção, %d ignorados sem tipo, %d erros.",
            " (dry-run)" if args.dry_run else "",
            resumo["inseridos"],
            resumo["atualizados"],
            resumo["inalterados"],
            resumo["preservados"],
            resumo["ignorados_por_opcao"],
            resumo["ignorados_sem_tipo"],
            len(resumo["erros"]),
        )
        if resumo["tipos_criados"]:
            LOGGER.info("Tipos de ativo criados: %s", ", ".join(resumo["tipos_criados"]))
        for erro in resumo["erros"]:
            LOGGER.error("Erro em %s: %s", erro["codigo"], erro["erro"])

    return 1 if resumo["erros"] else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
