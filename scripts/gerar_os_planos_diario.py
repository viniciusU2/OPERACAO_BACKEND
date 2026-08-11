"""Executa diariamente a geracao de OS pendentes dos planos de manutencao."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


URL_PADRAO = "http://127.0.0.1:8000/os/gerar-os-planos"


def main() -> int:
    url = os.getenv("OPERACAO_GERAR_OS_URL", URL_PADRAO).strip() or URL_PADRAO
    timeout = int(os.getenv("OPERACAO_GERAR_OS_TIMEOUT", "3600"))
    payload = json.dumps({"simular": False}).encode("utf-8")

    if "--dry-run" in sys.argv:
        print(json.dumps({"url": url, "payload": {"simular": False}}, ensure_ascii=False))
        return 0

    inicio = time.monotonic()
    requisicao = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(requisicao, timeout=timeout) as resposta:
            corpo = resposta.read().decode("utf-8", errors="replace")
            status = resposta.status
    except HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")
        print(
            f"Falha HTTP ao gerar OS dos planos: status={erro.code} resposta={corpo}",
            file=sys.stderr,
        )
        return 1
    except (URLError, TimeoutError, OSError) as erro:
        print(f"Falha de conexao ao gerar OS dos planos: {erro}", file=sys.stderr)
        return 1

    duracao = round(time.monotonic() - inicio, 2)
    try:
        resultado = json.loads(corpo)
    except json.JSONDecodeError:
        resultado = corpo

    print(
        json.dumps(
            {
                "executado_em_utc": datetime.now(timezone.utc).isoformat(),
                "status_http": status,
                "duracao_segundos": duracao,
                "resultado": resultado,
            },
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
