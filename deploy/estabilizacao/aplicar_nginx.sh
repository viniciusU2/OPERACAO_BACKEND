#!/usr/bin/env bash
#
# Instala a configuração do site engvi (frontend + /api/ -> 127.0.0.1:8001)
# com backup e rollback automático se o `nginx -t` reprovar.
#
# - Não reinicia a API.
# - Uso: sudo bash deploy/estabilizacao/aplicar_nginx.sh [arquivo.conf]
#
# Sem argumento, usa o nginx-engvi.conf ao lado deste script.

set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
ORIGEM="${1:-$AQUI/nginx-engvi.conf}"
DESTINO="/etc/nginx/sites-available/engvi"
HABILITADO="/etc/nginx/sites-enabled/engvi"

if [ "$(id -u)" -ne 0 ]; then
  echo "erro: execute como root (sudo)." >&2
  exit 1
fi

if [ ! -f "$ORIGEM" ]; then
  echo "erro: arquivo nao encontrado: $ORIGEM" >&2
  exit 1
fi

if [ ! -f "$DESTINO" ]; then
  echo "erro: $DESTINO nao existe; este script espera substituir a config atual." >&2
  exit 1
fi

BACKUP="${DESTINO}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$DESTINO" "$BACKUP"
echo "backup criado: $BACKUP"

install -m 644 "$ORIGEM" "$DESTINO"

if nginx -t; then
  systemctl reload nginx
  echo "configuracao aplicada e nginx recarregado."
else
  echo "nginx -t reprovou; restaurando o backup." >&2
  cp "$BACKUP" "$DESTINO"
  if nginx -t; then
    echo "revertido ao estado anterior (nada foi recarregado)." >&2
  else
    echo "ATENCAO: a config anterior tambem nao passa no nginx -t." >&2
  fi
  exit 1
fi

if [ ! -L "$HABILITADO" ]; then
  echo "aviso: $HABILITADO nao e um symlink; o site pode nao estar habilitado." >&2
fi
