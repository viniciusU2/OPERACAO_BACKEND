# VPS — processos, estabilização e causa raiz do travamento

Servidor: `v343407gjsqt.vpsn.in` · aplicação em `/root/OPERACAO_BACKEND` (venv em `venv/`).

> Registro do incidente de 26/10/2026: API travando, `upstream timed out` no nginx,
> 504/erro para todos e 413 nos uploads de relatório.
> **Resolvido** — causa raiz e correção na seção 11.
> As seções 1–10 são o histórico do diagnóstico e o pacote de infraestrutura;
> os scripts (§3–§5) eu **não** executei — aplique na ordem e valide cada passo.

## 0. Mapa da VPS (referência rápida)

| Porta | Processo | Serviço systemd | Diretório | O que é |
|---|---|---|---|---|
| 80 / 443 | nginx | `nginx` | `/etc/nginx` | entrada pública, TLS Let's Encrypt de `engvi.com.br` |
| 8001 | uvicorn | **`operacao.service`** | `/root/OPERACAO_BACKEND` | **API ENGVI — este repositório** |
| 8000 | uvicorn | `api.service` | `/root/back_telhado_verde` | **outro projeto** (FastAPI Telhado Verde) |

Sites nginx habilitados (`/etc/nginx/sites-enabled/`):

| Site | Domínio / porta | Destino |
|---|---|---|
| `engvi` | `engvi.com.br` (443) | frontend `/var/www/engvi`; `/api/` → `127.0.0.1:8001` |
| `operacao` | `192.99.140.211:8080` | `/` → `localhost:5173` (**Vite dev**); `/api/` → `127.0.0.1:8001` |
| `api`, `atlas-rsu`, `telhado_verde` | outros projetos | — |

`engvi.backup` existe em `sites-available` mas **não** está habilitado.

### Fatos que já custaram tempo

- `operacao.service` roda `uvicorn main:app --host 0.0.0.0 --port 8001` —
  **sem** `--workers` e **sem** `--limit-concurrency`.
- A porta **8000 é do Telhado Verde**, não da Operação.
- O timer `operacao-gerar-os-diario.service` **não está instalado** → nenhuma OS
  é gerada automaticamente.
- **Não existe `limit_req`/`limit_conn`** no nginx: 503/504 vinham de upstream
  travado, não de rate limit.
- O banco guarda o caminho absoluto dos ZIPs
  (`/root/OPERACAO_BACKEND/saida/relatorios_manutencao/...`). Banco restaurado
  em outra máquina aponta para arquivos que não existem (404 ao baixar).
- A API em `0.0.0.0:8001` aceita conexão direta da internet, fora do nginx
  (endurecer para `127.0.0.1` quando possível).
- OCR desligado por padrão; `RELATORIO_OCR=1` reativa (§11).

### Inspeção

```bash
ss -ltnp                                   # portas e processos donos
systemctl status operacao.service --no-pager
systemctl cat operacao.service             # ExecStart real
ls -l /etc/nginx/sites-enabled/
nginx -T 2>/dev/null | grep -nE "server_name|listen |proxy_pass"
systemctl list-units --type=service --state=running
free -h && df -h
```

### Operação

```bash
systemctl restart operacao.service         # reiniciar a API
journalctl -u operacao.service -f          # log da aplicação
tail -f /var/log/nginx/error.log           # log do proxy
```

### Deploy

```bash
# Windows: commit + push
# VPS:
cd /root/OPERACAO_BACKEND && git pull && systemctl restart operacao.service
```

## 1. O que está acontecendo

| Fato | Evidência |
|---|---|
| O `503` não vem do backend | não existe nenhuma ocorrência de `503` no código |
| O processo já caiu/reiniciou | log: `Stopped` 18:29:56 → `startup complete` 18:30:07 (11 s sem escutar) |
| O maior relatório tem 16,2 MB e 182 fotos | `SELECT tamanho_bytes, quantidade_fotos ...` |
| `GET /{id}/revisao` devolve **todas** as fotos em base64 num único JSON | `relatorio_manutencao/routes.py` (`"fotos": [...]`) |
| Estimativa do JSON do relatório #19 | **20–25 MB** (182 × ~119 KB) |
| Cada abertura **reprocessa e reencoda todas as fotos**, sem cache | `criar_miniatura_data_url` chamada no laço de `obter_revisao` |
| Pico de memória no app + outra cópia no nginx | → OOM kill → restart → **503** durante a janela |

O `503` é sintoma; a causa provável é memória (ou timeout) ao montar essa resposta.

## 2. Como confirmar (antes de aplicar)

```bash
# tamanho/tempo reais da resposta (troque $TOKEN)
time curl -s -o /tmp/rev.json -H "Authorization: Bearer $TOKEN" \
  -w "HTTP=%{http_code} TAMANHO=%{size_download} TEMPO=%{time_total}s\n" \
  http://127.0.0.1:8001/relatorios-manutencao/19/revisao
ls -lh /tmp/rev.json

# memória e causa da morte do processo
free -h
dmesg -T | grep -iE "oom|killed process" | tail -5
systemctl show operacao.service -p NRestarts
tail -30 /var/log/nginx/error.log
```

- `Killed process ... uvicorn` no `dmesg` → **memória** (aplicar passos 3, 4 e 5).
- `upstream timed out` no nginx → **tempo** (passos 4 e 5).
- `HTTP=200` local e 503 só de fora → problema no proxy/Cloudflare, não no app.

## 3. Swap (o que mais ajuda imediatamente)

```bash
sudo bash deploy/estabilizacao/estabilizar.sh
```

Cria 4 GB de swap (2 GB se a máquina tiver ≥ 4 GB de RAM), persiste no
`/etc/fstab` e ajusta `vm.swappiness=10`. É idempotente: rodar de novo não duplica nada.

## 4. nginx — timeouts, tamanho e buffering

No `server { }` do domínio da API, substitua o `location` que hoje faz proxy
para `127.0.0.1:8001` pelo conteúdo de
[`nginx-operacao.conf`](./nginx-operacao.conf).

```bash
# 0) confirme qual proxy está na frente (o log mostra X-Forwarded-For, então existe um)
ss -ltnp | grep -E ':(80|443)\b'
systemctl is-active nginx 2>/dev/null || echo "nginx não está ativo — me avise se for Caddy/Traefik/Cloudflare Tunnel"

# 1) descubra o arquivo do site (o nome varia)
grep -rl "proxy_pass.*8001" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null

# 2) faça backup ANTES de editar
sudo cp /etc/nginx/sites-enabled/<site> /etc/nginx/sites-enabled/<site>.bak

# 3) edite e valide
sudo nginx -t && sudo systemctl reload nginx
```

> Se o passo 0 mostrar que **não** há nginx (ex.: Cloudflare Tunnel ou Caddy),
> não aplique este arquivo: me diga qual é e eu adapto as diretivas.

O que muda na prática:

| Diretiva | Por quê |
|---|---|
| `client_max_body_size 120m` | default do nginx é **1 MB** → upload de ZIP volta `413` antes de chegar no app |
| `proxy_read_timeout 300s` | gerar 182 miniaturas pode passar dos 60 s do default |
| `proxy_buffering off` | evita uma segunda cópia de ~20 MB na memória do nginx |
| `proxy_request_buffering off` | o app já lê o ZIP em memória; evita gravar 100 MB em disco no nginx |

## 5. systemd — reinício automático

```bash
sudo mkdir -p /etc/systemd/system/operacao.service.d
sudo cp deploy/estabilizacao/operacao.service.d/10-estabilidade.conf \
        /etc/systemd/system/operacao.service.d/
sudo systemctl daemon-reload
sudo systemctl restart operacao.service
systemctl status operacao.service --no-pager
```

Garante `Restart=always` (volta sozinho após OOM) e `TimeoutStopSec=60`
(não corta um request longo no meio ao reiniciar).

## 6. Validar depois

```bash
free -h
swapon --show
curl -s -o /dev/null -w "HTTP=%{http_code} %{time_total}s\n" http://127.0.0.1:8001/docs
systemctl show operacao.service -p NRestarts
dmesg -T | grep -iE "oom|killed process" | tail -5
journalctl -u operacao.service -f
```

Critério de sucesso: abrir a revisão do relatório #19 **três vezes seguidas**
sem `NRestarts` subir e sem linha de OOM no `dmesg`.

## 7. Rollback

```bash
# nginx
sudo cp /etc/nginx/sites-enabled/<site>.bak /etc/nginx/sites-enabled/<site>
sudo nginx -t && sudo systemctl reload nginx

# systemd
sudo rm /etc/systemd/system/operacao.service.d/10-estabilidade.conf
sudo systemctl daemon-reload && sudo systemctl restart operacao.service

# swap
sudo swapoff /swapfile && sudo rm /swapfile
sudo sed -i '/\/swapfile/d' /etc/fstab
```

## 8. O que este pacote **não** resolve

O pico de memória de ~20 MB por abertura de revisão continua existindo: o
nginx e o swap apenas absorvem. Se o problema voltar com dois usuários
abrindo relatórios grandes ao mesmo tempo, a correção de fundo é reduzir o
payload (endpoint por foto, paginação ou miniatura menor) — mudança de código
que **não** foi feita aqui.

> O **travamento** da API (upstream timed out em endpoints triviais) é outro
> problema e foi resolvido — ver §11.

Mitigações manuais até lá:

- evitar abrir o mesmo relatório grande em várias abas/usuários ao mesmo tempo;
- reiniciar o serviço antes de picos de uso: `sudo systemctl restart operacao.service`;
- opcional: reciclar o worker periodicamente, acrescentando
  `--limit-max-requests 500` ao `ExecStart` do uvicorn.

## 9. Achados extras (não corrigidos)

1. **A geração diária de OS não está agendada neste servidor.**
   `systemctl cat operacao-gerar-os-diario.service` responde *"No files found"* —
   o timer do repositório (`deploy/systemd/operacao-gerar-os-diario.service`) não
   está instalado. O `OPERACAO_GERAR_OS_URL` apontando para a porta 8000 é,
   portanto, inofensivo hoje — mas significa que **nenhuma OS é gerada
   automaticamente**. Se isso for esperado, ignore; se não, instale o timer e
   corrija a porta para 8001.

2. **A porta 8000 pertence a outro projeto — não à Operação.**
   `pid 763` = `api.service` (*FastAPI Telhado Verde*), cwd `/root/back_telhado_verde`,
   em `127.0.0.1:8000` desde 09/08. É um sistema independente e **não** influencia
   a API da Operação (8001). Consequência prática: se o timer
   `operacao-gerar-os-diario.service` fosse instalado com o
   `OPERACAO_GERAR_OS_URL=http://127.0.0.1:8000/...` do repositório, ele chamaria
   **o Telhado Verde**, não a Operação. Ao instalar, troque para `:8001`.

3. **uvicorn exposto na internet.**
   A API está em `0.0.0.0:8001` e recebe `CONNECT cloudflare.com%3A443` /
   `Invalid HTTP request received` — varredura usando a porta como proxy.
   Se houver proxy na frente, o correto é `127.0.0.1:8001`. Confirme antes:

   ```bash
   ss -ltnp | grep -E ':(80|443)\b'
   systemctl is-active nginx 2>/dev/null
   ```

4. **`orm_mode` deprecado** em `ATIVO/schemas.py` (4 classes). Em Pydantic v2 a
   chave é ignorada; se essas respostas receberem objetos ORM, quebram na
   validação. Troca para `model_config = ConfigDict(from_attributes=True)`.

## 10. Config real do site engvi.com.br (inspecionada no VPS)

O `sites-enabled/engvi` tinha dois defeitos independentes do 503:

| Diretiva | Encontrado | Efeito prático |
|---|---|---|
| `client_max_body_size` | **ausente** → default 1 MB | **todo upload de relatório acima de 1 MB retornava 413**, cortado pelo nginx antes de chegar no FastAPI (cujo limite é 100 MB). Os ZIPs reais têm 3–16 MB. |
| `proxy_read_timeout` | 60 s | `/revisao` (~20 MB, 182 miniaturas) estoura → 504 |
| `proxy_buffering` | default (on) | segunda cópia de ~20 MB na memória do nginx |
| `proxy_request_buffering` | default (on) | upload de até 100 MB gravado em disco no nginx |
| `limit_req` / `limit_conn` | ausentes no arquivo | o 503 **não** vem daqui |

O `413` do primeiro item é o "erro de tamanho de arquivo" — mas no **envio**,
não no download.

Arquivo corrigido: [`nginx-engvi.conf`](./nginx-engvi.conf).

```bash
sudo bash deploy/estabilizacao/aplicar_nginx.sh
```

O script faz backup, instala, roda `nginx -t` e só recarrega se passar; se
reprovar, restaura o backup sozinho.

Teste depois (pela URL real, não por localhost):

```bash
curl -s -o /tmp/rev.json \
  -w "HTTP=%{http_code} TAMANHO=%{size_download} TEMPO=%{time_total}s\n" \
  -H "Authorization: Bearer $TOKEN" \
  https://engvi.com.br/api/relatorios-manutencao/19/revisao
```

### Sobre o site `operacao` (porta 8080)

`/etc/nginx/sites-enabled/operacao` atende `192.99.140.211:8080` e manda
`location /` para `localhost:5173` — ou seja, um **Vite dev server**. Se ninguém
usa essa porta, desabilite (o nginx para de expor uma porta a mais):

```bash
sudo unlink /etc/nginx/sites-enabled/operacao
sudo nginx -t && sudo systemctl reload nginx
```

`/etc/nginx/sites-available/engvi.backup` existe mas não está habilitado — pode
ficar como histórico.

## 11. Causa raiz do travamento (resolvida em 26/10/2026)

### Sintoma

`nginx/error.log` com `upstream timed out (110)` em endpoints **triviais**
(`/tipo-ativo`, `/periodicidades`, `/subestacao/ativas`), sempre logo após um
`POST /api/relatorios-manutencao/analisar`. Depois do restart manual:
`104 Connection reset by peer` e `111 Connection refused`.

### Causa

`relatorio_manutencao/analysis_routes.py` declarava `async def analisar_zip` e
executava **dentro do event loop**:

- `zipfile.ZipFile(...).read()` de todas as fotos;
- `pytesseract.image_to_string(...)` — até 2 passadas por foto, `timeout=4..6` cada;
- `PIL` (miniatura + heurísticas visuais) de cada foto;
- `SequenceMatcher` para sugerir ativo/item.

Com **um único worker uvicorn**, um ZIP de 182 fotos prendia o loop por minutos:
nenhuma outra requisição era sequer despachada, o nginx estourava o
`proxy_read_timeout 60s` e todo mundo recebia 504.

### Correção aplicada

1. `async def` → `def` em `/analisar` e `/analisar-imagem`, lendo o upload por
   `arquivo.file.read(...)`. O FastAPI passa a executar a rota na **threadpool**:
   uma análise longa não bloqueia mais o resto da API.
2. OCR **desligado por padrão** (`_ocr_ativo()`, env `RELATORIO_OCR`). O
   Tesseract era o maior custo; a sugestão continua usando nome do arquivo e
   heurísticas visuais.

### Resultado medido

ZIP com 30 fotos: **1,64 s** (antes: minutos com a API inteira parada).
`/analisar-imagem` validado no mesmo teste.

### Reativar o OCR

```bash
sudo systemctl edit operacao.service
# [Service]
# Environment=RELATORIO_OCR=1
sudo systemctl daemon-reload && sudo systemctl restart operacao.service
```

### Pendências que continuam abertas

- `GET /{id}/revisao` ainda devolve ~20 MB de JSON com as fotos em base64 (§8).
- Upload de relatório acima de 1 MB depende do `client_max_body_size` no nginx (§10).

