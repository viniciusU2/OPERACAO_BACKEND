from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, engine
from dotenv import load_dotenv
import os
import re
from SS import solicitacao_servico
from SI import solicitcao_intervencao
from OS import ordem_de_servico
from LR import livro_registro
from familias import familias
from Instalacao import instalacao
from plano_manutencao import plano_manutencao
from plano_manutencao import inspecoes
from auth import auth
import downloads
from database import Base, engine
from ATIVO import ativos
from sqlalchemy import text



load_dotenv()

app = FastAPI(title="Manutenção de Subestações")

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    ativos.garantir_colunas_torre(db)
    inspecoes.garantir_colunas_inspecao(db)
    coluna_numero_ss_os = db.execute(
        text("SHOW COLUMNS FROM ordem_servico LIKE 'numero_ss'")
    ).first()
    if not coluna_numero_ss_os:
        db.execute(text("ALTER TABLE ordem_servico ADD COLUMN numero_ss VARCHAR(30) NULL"))
    coluna_numero_os_ss = db.execute(
        text("SHOW COLUMNS FROM solicitacao_servico LIKE 'numero_os'")
    ).first()
    if not coluna_numero_os_ss:
        db.execute(text("ALTER TABLE solicitacao_servico ADD COLUMN numero_os VARCHAR(30) NULL"))

    colunas_ordem_servico_plano = {
        "id_plano_manutencao": "INT NULL",
        "id_plano_item": "INT NULL",
        "id_plano_execucao": "INT NULL",
        "origem": "VARCHAR(50) NULL",
    }
    for coluna, definicao in colunas_ordem_servico_plano.items():
        existe = db.execute(
            text("SHOW COLUMNS FROM ordem_servico LIKE :coluna"),
            {"coluna": coluna},
        ).first()
        if not existe:
            db.execute(text(f"ALTER TABLE ordem_servico ADD COLUMN {coluna} {definicao}"))

    coluna_execucao_os = db.execute(
        text("SHOW COLUMNS FROM plano_execucao LIKE 'id_os'")
    ).first()
    if not coluna_execucao_os:
        db.execute(text("ALTER TABLE plano_execucao ADD COLUMN id_os INT NULL"))

    colunas_texto = db.execute(
        text(
            """
            SELECT TABLE_NAME, COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND DATA_TYPE IN ('varchar', 'char', 'text', 'mediumtext', 'longtext')
            """
        )
    ).fetchall()
    for sigla_antiga, sigla_nova in (("BJ" + "L", "BJD"), ("GD" + "O", "GOR")):
        for tabela, coluna in colunas_texto:
            db.execute(
                text(
                    f"UPDATE `{tabela}` "
                    f"SET `{coluna}` = REPLACE(`{coluna}`, :old, :new) "
                    f"WHERE `{coluna}` LIKE :pattern"
                ),
                {"old": sigla_antiga, "new": sigla_nova, "pattern": f"%{sigla_antiga}%"},
            )
    aprs_para_corrigir = db.execute(
        text(
            """
            SELECT id_os, numero_apr
            FROM ordem_servico
            WHERE numero_apr LIKE 'OS-%'
               OR numero_apr REGEXP '^APR-[A-Z]+--[0-9]+-[0-9]{4}$'
            """
        )
    ).fetchall()
    for id_os, numero_apr in aprs_para_corrigir:
        numero_apr_corrigido = None
        match_os = re.match(r"^OS-([A-Z]+)-(\d+)-(\d{4})(?:-.+)?$", numero_apr or "")
        match_apr = re.match(r"^APR-([A-Z]+)--(\d+)-(\d{4})$", numero_apr or "")
        if match_os:
            sigla, sequencia, ano = match_os.groups()
            numero_apr_corrigido = f"APR-{sigla}-{sequencia}-{ano}"
        elif match_apr:
            sigla, sequencia, ano = match_apr.groups()
            numero_apr_corrigido = f"APR-{sigla}-{sequencia}-{ano}"
        if numero_apr_corrigido:
            db.execute(
                text("UPDATE ordem_servico SET numero_apr = :numero_apr WHERE id_os = :id_os"),
                {"numero_apr": numero_apr_corrigido, "id_os": id_os},
            )
    db.commit()
finally:
    db.close()



# CORS — TEM QUE VIR ANTES DAS ROTAS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"])

app.include_router(solicitacao_servico.router)
app.include_router(auth.router)
app.include_router(ordem_de_servico.router)
app.include_router(familias.router)
app.include_router(instalacao.router)
app.include_router(plano_manutencao.router)
app.include_router(inspecoes.router)
app.include_router(ativos.router)
app.include_router(solicitcao_intervencao.router)
app.include_router(livro_registro.router)
app.include_router(downloads.router)







GOOGLE_CLIENT_ID =  os.getenv("CLIENT_ID")


