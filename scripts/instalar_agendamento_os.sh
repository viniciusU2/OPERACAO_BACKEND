#!/usr/bin/env bash
set -euo pipefail

REPOSITORIO="/root/OPERACAO_BACKEND"
UNIDADES="${REPOSITORIO}/deploy/systemd"

test -f "${UNIDADES}/operacao-gerar-os-diario.service"
test -f "${UNIDADES}/operacao-gerar-os-diario.timer"
test -f "${REPOSITORIO}/scripts/gerar_os_planos_diario.py"
test -x "${REPOSITORIO}/venv/bin/python"

install -m 0644 \
  "${UNIDADES}/operacao-gerar-os-diario.service" \
  /etc/systemd/system/operacao-gerar-os-diario.service

install -m 0644 \
  "${UNIDADES}/operacao-gerar-os-diario.timer" \
  /etc/systemd/system/operacao-gerar-os-diario.timer

systemctl daemon-reload
systemctl enable --now operacao-gerar-os-diario.timer

systemctl status operacao-gerar-os-diario.timer --no-pager
systemctl list-timers operacao-gerar-os-diario.timer --no-pager
