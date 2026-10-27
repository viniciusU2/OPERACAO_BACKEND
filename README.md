# OPERACAO_BACK

## Produção (VPS)

Servidor `v343407gjsqt.vpsn.in` · aplicação em `/root/OPERACAO_BACKEND`.

| Porta | Serviço systemd | O que é |
|---|---|---|
| 80 / 443 | `nginx` | entrada pública (`engvi.com.br`, TLS Let's Encrypt) |
| 8001 | **`operacao.service`** | **API ENGVI — este repositório** |
| 8000 | `api.service` | outro projeto (FastAPI Telhado Verde) — não mexer |

- **Deploy:** `git push` aqui → no VPS `cd /root/OPERACAO_BACKEND && git pull && systemctl restart operacao.service`.
- **Logs:** `journalctl -u operacao.service -f` (aplicação) e `tail -f /var/log/nginx/error.log` (proxy).
- **OCR** (Tesseract) desligado por padrão; reative com `Environment=RELATORIO_OCR=1` em `systemctl edit operacao.service`.

Mapa completo da VPS, diagnóstico do incidente de 26/10/2026 (travamento por OCR no
event loop) e scripts de estabilização:
[`deploy/estabilizacao/README.md`](deploy/estabilizacao/README.md).
