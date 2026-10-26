#!/usr/bin/env bash
#
# Estabilização de memória do VPS: swap + swappiness.
#
# - Idempotente: rodar várias vezes não cria swap duplicada nem repete fstab.
# - NÃO reinicia serviços e NÃO altera nginx.
# - Uso: sudo bash deploy/estabilizacao/estabilizar.sh
#
# Variáveis opcionais:
#   ARQUIVO_SWAP=/swapfile    caminho do arquivo de swap
#   TAMANHO_MB=4096           tamanho em MB (default: 4 GB com <4 GB de RAM, 2 GB acima)

set -euo pipefail

ARQUIVO_SWAP="${ARQUIVO_SWAP:-/swapfile}"

if [ "$(id -u)" -ne 0 ]; then
  echo "erro: execute como root (sudo)." >&2
  exit 1
fi

echo "== memória antes =="
free -h
echo

# Leitura direta de /proc/swaps: sem pipe, para não depender de SIGPIPE
# com `set -o pipefail`.
swap_ativo() {
  awk -v alvo="$ARQUIVO_SWAP" 'NR > 1 && $1 == alvo { achou = 1 } END { exit !achou }' /proc/swaps
}

if swap_ativo; then
  echo "swap já ativo em $ARQUIVO_SWAP — nada a criar."
else
  RAM_MB=$(awk '/MemTotal/ { printf "%d", $2 / 1024 }' /proc/meminfo)
  if [ "$RAM_MB" -lt 4096 ]; then
    TAMANHO_MB="${TAMANHO_MB:-4096}"
  else
    TAMANHO_MB="${TAMANHO_MB:-2048}"
  fi

  if [ -f "$ARQUIVO_SWAP" ]; then
    echo "$ARQUIVO_SWAP já existe no disco (${TAMANHO_MB} MB pretendidos) — reutilizando."
  else
    echo "criando $ARQUIVO_SWAP com ${TAMANHO_MB} MB (RAM detectada: ${RAM_MB} MB)"
    if ! fallocate -l "${TAMANHO_MB}M" "$ARQUIVO_SWAP" 2>/dev/null; then
      echo "fallocate indisponível neste filesystem; usando dd (mais lento)."
      rm -f "$ARQUIVO_SWAP"  # fallocate pode ter deixado um arquivo parcial
      dd if=/dev/zero of="$ARQUIVO_SWAP" bs=1M count="$TAMANHO_MB" status=progress
    fi
    chmod 600 "$ARQUIVO_SWAP"
    mkswap "$ARQUIVO_SWAP"
  fi

  swapon "$ARQUIVO_SWAP"
fi

if ! grep -qE "^[[:space:]]*${ARQUIVO_SWAP}[[:space:]]" /etc/fstab; then
  echo "${ARQUIVO_SWAP} none swap sw 0 0" >> /etc/fstab
  echo "entrada adicionada em /etc/fstab (swap volta após reboot)."
else
  echo "entrada já presente em /etc/fstab."
fi

sysctl -w vm.swappiness=10 >/dev/null
if ! grep -q '^vm.swappiness' /etc/sysctl.conf; then
  echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi

echo
echo "== memória depois =="
free -h
echo
swapon --show
echo
echo "pronto. Nenhum serviço foi reiniciado."
echo "próximos passos: deploy/estabilizacao/README.md (seções 4 e 5)."
