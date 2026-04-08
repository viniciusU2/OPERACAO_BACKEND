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
from auth import auth
from database import Base, engine
from ATIVO import ativos



load_dotenv()

app = FastAPI(title="Manutenção de Subestações")

Base.metadata.create_all(bind=engine)



# CORS — TEM QUE VIR ANTES DAS ROTAS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://10.102.40.50:5173",
        
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

app.include_router(solicitacao_servico.router)
app.include_router(auth.router)
app.include_router(ordem_de_servico.router)
app.include_router(familias.router)
app.include_router(instalacao.router)
app.include_router(plano_manutencao.router)
app.include_router(ativos.router)
app.include_router(solicitcao_intervencao.router)
app.include_router(livro_registro.router)







GOOGLE_CLIENT_ID =  os.getenv("CLIENT_ID")


