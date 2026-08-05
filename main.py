from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, engine
from dotenv import load_dotenv
import os
from SS import solicitacao_servico
from SI import solicitcao_intervencao
from OS import ordem_de_servico
from LR import livro_registro
from familias import familias
from Instalacao import instalacao
from plano_manutencao import plano_manutencao
from plano_manutencao import inspecoes
from RDO import rdo
from Sobreaviso import sobreaviso
from funcao_operacao import funcao_operacao
from auth import auth
import downloads
from database import Base, engine
from ATIVO import ativos
from ATIVO.grupos_ativos import garantir_estrutura_grupo_ativo, sincronizar_grupos_ativos
from sqlalchemy import text
from models import rdo_models
from models import APR_models
from models import fo



load_dotenv()

app = FastAPI(title="ManutenÃ§Ã£o de SubestaÃ§Ãµes")

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    ordem_de_servico.garantir_colunas_os(db)
    garantir_estrutura_grupo_ativo(db)
    sincronizar_grupos_ativos(db)
    solicitacao_servico.garantir_colunas_ss(db)
    solicitcao_intervencao.garantir_colunas_si(db)
    solicitcao_intervencao.garantir_tabela_liberacoes_si(db)
    ativos.garantir_colunas_torre(db)
    funcao_operacao.service.garantir_estrutura_funcao_operacao(db)
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

    try:
        sobreaviso.sincronizar_colaboradores_usuarios(db)
    except Exception as exc:
        print("Falha ao sincronizar colaboradores de sobreaviso:", exc)

    db.commit()
finally:
    db.close()



# CORS â€” TEM QUE VIR ANTES DAS ROTAS
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
app.include_router(funcao_operacao.router)
app.include_router(instalacao.router)
app.include_router(plano_manutencao.router)
app.include_router(inspecoes.router)
app.include_router(ativos.router)
app.include_router(solicitcao_intervencao.router)
app.include_router(livro_registro.router)
app.include_router(rdo.router)
app.include_router(sobreaviso.router)
app.include_router(downloads.router)







GOOGLE_CLIENT_ID =  os.getenv("CLIENT_ID")



