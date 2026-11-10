# Seed do Unifilar na VPS

## 1. Migracoes

O modulo aplica as migrations na subida do backend (import de `main.py`),
lendo `migrations/*unifilar*.sql` e registrando na tabela de controle
`unifilar_migracao`:

- `020_diagrama_unifilar.sql` - tabelas e catalogo de tipos
- `021_unifilar_reator_svg.sql` - dimensoes do reator
- `022_unifilar_indice_ativo.sql` - indice de `id_ativo`
- `023_unifilar_tc_svg.sql` - dimensoes do TC

Conferir depois do deploy/restart:

```sql
SELECT nome, aplicado_em FROM unifilar_migracao ORDER BY nome;
SHOW TABLES LIKE 'unifilar%';
```

Se a `022` falhar por indice duplicado (processo interrompido entre o ALTER
e o registro), confira `information_schema.statistics` e registre a linha
manualmente em `unifilar_migracao` antes de subir novamente.

## 2. Atualizar o seed (ambiente local)

Sempre que o diagrama mudar no banco local:

```bash
python scripts/exportar_unifilar_seed.py
git add scripts/seeds/unifilar_seed.json
git commit -m "chore: atualiza seed do unifilar"
git push
```

O export grava a instalacao pelo **nome** e cada componente com
`ativo_codigo` / `ativo_fase` (sem `id_ativo`, que muda entre bancos).

## 3. Aplicar na VPS

```bash
cd /root/OPERACAO_BACKEND
git pull
systemctl restart operacao.service
venv/bin/python scripts/seed_unifilar.py --dry-run
venv/bin/python scripts/seed_unifilar.py --substituir
```

- `--dry-run` valida o JSON e as migracoes sem gravar.
- `--substituir` e obrigatorio se a instalacao ja tiver diagrama.
- A instalacao e localizada por nome. Se o nome diferir na VPS:
  `--id-subestacao <id>`.
- Ativos sao casados por `codigo_ativo` (preferindo a fase AZ). Se um ativo
  nao existir na VPS, o vinculo fica nulo e o codigo aparece como aviso; o
  desenho e criado normalmente.

## 4. Conferir

```bash
mysql -u <usuario> -p manutencao -e \
  "SELECT d.id_subestacao, s.nome, COUNT(c.id_componente) componentes
     FROM unifilar_diagrama d
     JOIN subestacao s ON s.id_subestacao = d.id_subestacao
     LEFT JOIN unifilar_componente c ON c.id_diagrama = d.id_diagrama
    GROUP BY d.id_subestacao, s.nome;"
```

Ou abrir `/unifilar` na aplicacao.

Observacao: o seed atual contem apenas a **SE GOR** (56 componentes e 55
ligacoes). A SE BJD foi removida do banco local e nao faz parte do arquivo.
