"""Bootstrap para scripts de linha de comando que acessam o banco direto.

Importa os modulos de modelo para que o SQLAlchemy resolva os relacionamentos
sem executar a inicializacao da aplicacao (main.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from models import (  # noqa: E402,F401
    APR_models,
    Ativo,
    OS_models,
    SI_models,
    SS_models,
    auth_models,
    familias_models,
    fo,
    instalacao_models,
    livro_registro,
    password_reset_models,
    planning_resource_models,
    plano_manutencao_models,
    problemas_tipicos_models,
    rdo_models,
    sobreaviso_models,
)
