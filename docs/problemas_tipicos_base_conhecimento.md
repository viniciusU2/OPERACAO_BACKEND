# Base de conhecimento de problemas típicos de subestações (ENGVI)

Documento de entrega da Fase 1 da base de conhecimento de **problemas típicos**
de subestações, integrada ao backend ENGVI existente e consumível pelo frontend
atual.

- Seed: [`scripts/seed_problemas_tipicos.py`](../scripts/seed_problemas_tipicos.py)
- Catálogo: [`problemas_tipicos/catalogo.py`](../problemas_tipicos/catalogo.py)
- Verificação (somente leitura): [`scripts/verificar_problemas_tipicos.py`](../scripts/verificar_problemas_tipicos.py)
- Migração de esquema: [`migrations/017_problemas_tipicos_base_conhecimento.sql`](../migrations/017_problemas_tipicos_base_conhecimento.sql)
- Reversão: [`migrations/017_problemas_tipicos_base_conhecimento_down.sql`](../migrations/017_problemas_tipicos_base_conhecimento_down.sql)

---

## 1. Objetivo e escopo

Popular a base de conhecimento de manutenção com **70 problemas típicos** de
subestações, cada um separando explicitamente:

- sintomas observados;
- causas prováveis (registradas separadamente);
- procedimentos de diagnóstico (como confirmar);
- ações corretivas;
- ações preventivas;
- alarmes, instrumentos e palavras-chave para busca;
- criticidade, risco operacional, condição de intervenção e necessidade de
  equipe especializada;
- alertas de segurança;
- referências técnicas;
- status de validação e origem do registro (referência técnica x ocorrência real).

A base é **independente de instalação**: nenhum registro é vinculado a ativo,
subestação, OS ou ocorrência fictícia. Nenhum limite de fabricante, ajuste de
proteção ou código de alarme foi inventado; onde o valor depende do equipamento
o texto remete a *“conforme manual do fabricante e ajustes aprovados”*.

---

## 2. Modelo de dados

### 2.1 Reutilização do modelo existente

Foram **estendidos** os modelos já existentes em
[`models/problemas_tipicos_models.py`](../models/problemas_tipicos_models.py)
(`problema_tipico` e suas tabelas filhas), em vez de criar estruturas paralelas.
Isso preserva a API, o frontend e os vínculos de `ss_problema` já existentes.

### 2.2 Mapa “campo pedido → onde vive”

| Campo solicitado | Estrutura |
| --- | --- |
| Título | `problema_tipico.titulo` |
| Descrição técnica | `problema_tipico.descricao` |
| Categoria | `problema_tipico.categoria` |
| Tipo de equipamento | `problema_tipico.id_tipo_ativo` → `tipo_ativo.nome` |
| Sistema | `problema_tipico.sistema` |
| Sintomas | `sintoma_problema.sintoma` (N por problema) |
| Alarmes | `alarme_problema.alarme` (**nova**) |
| Causas prováveis | `causa_problema.causa` (N por problema) |
| Diagnóstico | `metodo_deteccao_problema.metodo` (N por problema) |
| Ações corretivas | `acao_recomendada` com `tipo_acao ≠ PREVENCAO` |
| Ações preventivas | `acao_recomendada` com `tipo_acao = PREVENCAO` |
| Instrumentos | `instrumento_problema.instrumento` (**nova**) |
| Criticidade | `problema_tipico.criticidade_padrao` (vocabulário do ENGVI) |
| Risco operacional | `problema_tipico.risco_operacional` (**nova**) |
| Condição de intervenção | `problema_tipico.condicao_intervencao` (**nova**) |
| Equipe especializada | `problema_tipico.requer_equipe_especializada` (**nova**) |
| Referências | `problema_tipico.referencias_tecnicas` (**nova**) |
| Palavras-chave | `palavra_chave_problema.palavra_chave` (**nova**) |
| Status de validação | `problema_tipico.status_validacao` (**nova**) |
| Referência técnica x ocorrência real | `problema_tipico.origem_registro` (**nova**) |
| Chave natural da seed | `problema_tipico.codigo` (**nova**, `UNIQUE`) |
| Alerta de segurança | `problema_tipico.alerta_seguranca` (**nova**) |
| FMEA (modo/efeito/detectabilidade) | colunas já existentes em `problema_tipico` |

### 2.3 Justificativa das estruturas novas

- **`codigo`** (`VARCHAR(80) NOT NULL UNIQUE`) — chave natural estável da seed
  (`BDC-SE-DJ-001`, `BDC-SE-TC-004`, ...). É o que torna a carga idempotente sem
  depender de `id` auto-incremental. Registros anteriores à base recebem
  `LEGADO-<id>` pela migração, preservando o histórico.
- **Tabelas `alarme_problema`, `palavra_chave_problema`, `instrumento_problema`** —
  seguiram exatamente o padrão das filhas já existentes (`sintoma_problema`,
  `causa_problema`), com `ON DELETE CASCADE` e índice em `id_problema`, para não
  introduzir um padrão de modelagem diferente.
- **`PREVENCAO` em `acao_recomendada.tipo_acao`** — ações preventivas são ações
  recomendadas; criar uma tabela separada duplicaria colunas e quebraria o
  reaproveitamento atual. O DDL preserva o `DEFAULT 'INVESTIGACAO'`.
- **`metodo_deteccao_problema.metodo` → `VARCHAR(400)`** — passos completos de
  diagnóstico não cabiam em `VARCHAR(150)`. O default permaneceu
  `INVESTIGACAO`; nenhuma regra existente foi alterada.
- **Sem novas tabelas de vínculo com ativos/OS/inspeções** — não há dados reais
  para vincular e o escopo proíbe registros fictícios. Os vínculos existentes
  (`ss_problema`) continuam sendo o único caminho de uso real.

### 2.4 Enums adicionados

| Enum | Valores | Uso |
| --- | --- | --- |
| `RiscoOperacional` | `BAIXO`, `MEDIO`, `ALTO` | `risco_operacional` |
| `CondicaoIntervencao` | `ENERGIZADO`, `DESENERGIZADO`, `INDIFERENTE` | `condicao_intervencao` |
| `StatusValidacaoProblema` | `PENDENTE`, `EM_REVISAO`, `VALIDADO`, `REPROVADO` | `status_validacao` |
| `OrigemRegistroProblema` | `REFERENCIA_TECNICA`, `OCORRENCIA_REAL` | `origem_registro` |

A criticidade continua sendo o vocabulário já existente do ENGVI:
`BAIXA`, `MEDIA`, `ALTA`, `CRITICA`.

---

## 3. Vocabulários controlados do catálogo

**Categorias (11):**

`Disjuntor de Alta Tensão`, `Chave Seccionadora e de Aterramento`,
`Transformador de Corrente (TC)`, `Transformador de Potencial (TP/TPC)`,
`Para-raios`, `Transformador de Potência e Reator`,
`Proteção, Controle e Supervisão`, `Sistema CC 125 Vcc`,
`Serviços Auxiliares em CA`, `Comunicação e Infraestrutura`,
`Barramentos, Conexões e Isoladores`.

**Sistemas:** `Alta Tensão`, `Transformação`, `Proteção e Controle`,
`Corrente Contínua`, `Serviços Auxiliares`, `Comunicação`,
`Barramento e Conexões`.

### 3.1 Tipos de ativo criados

A seed **cria apenas 4** registros em `tipo_ativo`, quando ausentes, e registra
isso no log (nenhum outro dado mestre é alterado):

| id | Nome | Motivo |
| --- | --- | --- |
| 45 | `Barramento` | não existia; usado nos 2 problemas de barramento/conexões |
| 46 | `Isolador` | não existia; usado nos 2 problemas de isoladores |
| 47 | `Transformador de Potencial` | não existia (havia apenas `Transformador de Potencial Capacitivo`) |
| 48 | `Transformador de Potência` | não existia; equipamento central dos problemas de transformadores |

Os demais 19 tipos usados já existiam no ENGVI. Use `--sem-criar-tipos` para
proibir a criação; nesse caso os itens sem tipo são ignorados e contados em
`ignorados_sem_tipo`.

---

## 4. Como executar

O projeto usa o virtualenv `op/`. Execute a partir da raiz do backend.

**Pré-requisito:** `DATABASE_URL` válido (o `.env` do projeto já aponta para o
MariaDB local) e o banco acessível.

```powershell
# 1) Simulação: não grava nada (rollback ao final)
.\op\Scripts\python.exe -m scripts.seed_problemas_tipicos --dry-run

# 2) Carga real
.\op\Scripts\python.exe -m scripts.seed_problemas_tipicos

# 3) Reexecução (idempotente): deve reportar 0 inseridos e 0 atualizados
.\op\Scripts\python.exe -m scripts.seed_problemas_tipicos
```

Opções:

| Flag | Efeito |
| --- | --- |
| `--dry-run` | aplica tudo e faz `rollback` no final |
| `--sem-atualizar` | só insere; registros que mudariam ficam em `ignorados_por_opcao` |
| `--sem-criar-tipos` | não cria tipos de ativo ausentes |
| `--sem-migrar` | não aplica a migração do módulo (assume esquema já pronto) |
| `--log-arquivo CAMINHO` | grava o log também em arquivo |
| `--json` | imprime o resumo em JSON |

A migração de esquema é aplicada **automaticamente**:

- na subida da aplicação (`main.py` chama `problemas_tipicos.migracoes.aplicar_migracoes`);
- na execução da seed, através do mesmo migrador, controlado pela tabela
  `problemas_tipicos_migracao` (cada arquivo `migrations/*_problemas_tipicos*.sql`
  é aplicado uma única vez).

Não é necessário rodar SQL manualmente em ambiente novo.

---

## 5. Como verificar no MariaDB

### 5.1 Script pronto (somente leitura)

```powershell
.\op\Scripts\python.exe -m scripts.verificar_problemas_tipicos
```

Imprime totais por categoria, criticidade, risco, status, origem, quantidades de
cada lista estruturada, integridade referencial e o registro legado preservado.
Retorna código de saída `1` se encontrar inconsistência.

### 5.2 Consultas SQL

```sql
-- Total da seed
SELECT COUNT(*) FROM problema_tipico WHERE codigo LIKE 'BDC-%';

-- Distribuição por categoria
SELECT categoria, COUNT(*) FROM problema_tipico
 WHERE codigo LIKE 'BDC-%' GROUP BY categoria ORDER BY 2 DESC;

-- Classificação
SELECT criticidade_padrao, risco_operacional, COUNT(*)
  FROM problema_tipico WHERE codigo LIKE 'BDC-%'
 GROUP BY criticidade_padrao, risco_operacional;

-- Status e origem (rastreabilidade)
SELECT status_validacao, origem_registro, COUNT(*)
  FROM problema_tipico WHERE codigo LIKE 'BDC-%'
 GROUP BY status_validacao, origem_registro;

-- Quantidade de itens nas listas estruturadas
SELECT 'sintomas' AS lista, COUNT(*) FROM sintoma_problema s
  JOIN problema_tipico p ON p.id_problema = s.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'causas', COUNT(*) FROM causa_problema c
  JOIN problema_tipico p ON p.id_problema = c.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'alarmes', COUNT(*) FROM alarme_problema a
  JOIN problema_tipico p ON p.id_problema = a.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'palavras_chave', COUNT(*) FROM palavra_chave_problema k
  JOIN problema_tipico p ON p.id_problema = k.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'instrumentos', COUNT(*) FROM instrumento_problema i
  JOIN problema_tipico p ON p.id_problema = i.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'metodos', COUNT(*) FROM metodo_deteccao_problema m
  JOIN problema_tipico p ON p.id_problema = m.id_problema WHERE p.codigo LIKE 'BDC-%'
UNION ALL
SELECT 'acoes', COUNT(*) FROM acao_recomendada r
  JOIN problema_tipico p ON p.id_problema = r.id_problema WHERE p.codigo LIKE 'BDC-%';

-- Ações por tipo (corretivas x preventivas)
SELECT a.tipo_acao, COUNT(*) FROM acao_recomendada a
  JOIN problema_tipico p ON p.id_problema = a.id_problema
 WHERE p.codigo LIKE 'BDC-%' GROUP BY a.tipo_acao ORDER BY 2 DESC;

-- Integridade referencial: todas devem retornar 0
SELECT COUNT(*) FROM sintoma_problema x
  LEFT JOIN problema_tipico p ON p.id_problema = x.id_problema WHERE p.id_problema IS NULL;
-- (repetir para causa_problema, metodo_deteccao_problema, alarme_problema,
--  palavra_chave_problema, instrumento_problema, acao_recomendada)

-- Registro legado preservado
SELECT id_problema, codigo, titulo FROM problema_tipico WHERE codigo LIKE 'LEGADO-%';
```

### 5.3 Testes automatizados

```powershell
# Catálogo (não precisa de banco)
.\op\Scripts\python.exe -m unittest tests.test_problemas_tipicos_catalogo -v

# Integração com o banco configurado (opt-in explícito; não apaga dados)
$env:PROBLEMAS_TIPICOS_TESTE_DB="1"
.\op\Scripts\python.exe -m unittest tests.test_problemas_tipicos_seed -v
```

---

## 6. Idempotência e proteção dos dados

A chave natural é `problema_tipico.codigo`. Em cada execução, para cada item do
catálogo:

1. **não existe** → insere (`inseridos`);
2. **existe com `origem_registro = OCORRENCIA_REAL`** → preserva (`preservados`);
3. **existe com `status_validacao ∈ {VALIDADO, REPROVADO}`** → preserva
   (`preservados`) — conteúdo curado por especialista não é sobrescrito;
4. **existe e o conteúdo é idêntico** → nada faz (`inalterados`);
5. **existe, conteúdo diferente e `--sem-atualizar`** → `ignorados_por_opcao`;
6. **existe, conteúdo diferente** → atualiza (`atualizados`), **preservando**
   `codigo`, `ativo`, `criado_em`, `status_validacao` (quando não é
   `PENDENTE`), `origem_registro`, `validado_por` e `validado_em`.

Garantias adicionais:

- **nada é apagado** — a seed só usa `SELECT`, `INSERT` e `UPDATE`;
- **nenhum dado operacional é tocado** (ativos, subestações, SS, OS, planos,
  inspeções);
- **transacional por item** — cada problema é aplicado em um `SAVEPOINT`
  (`Session.begin_nested()`); uma falha isolada é registrada em `resumo["erros"]`
  e não deixa registro parcial nem interrompe os demais;
- **commit único** ao final; em `--dry-run` é feito `rollback`;
- código de saída `1` se houver algum erro, para permitir uso em verificação
  automatizada;
- a atualização só ocorre quando a comparação de conteúdo (escalares + todas as
  listas, ordenadas) detecta diferença real — evitando `UPDATE` desnecessário e
  reescrita de filhos.

---

## 7. Reversão

### 7.1 Reverter apenas a carga (manter o esquema)

Os registros da seed são identificáveis pelo prefixo do código. Para removê-los
é preciso remover antes as linhas de `ss_problema` que os referenciem (a FK é
`RESTRICT`, decisão intencional para não apagar histórico de SS):

```sql
-- Backup antes de qualquer coisa
-- mysqldump manutencao problema_tipico sintoma_problema causa_problema \
--   metodo_deteccao_problema acao_recomendada alarme_problema \
--   palavra_chave_problema instrumento_problema ss_problema > backup_pt.sql

-- Identifique o que está em uso
SELECT sp.id_problema, COUNT(*) FROM ss_problema sp
  JOIN problema_tipico p ON p.id_problema = sp.id_problema
 WHERE p.codigo LIKE 'BDC-%' GROUP BY sp.id_problema;

-- Se não houver uso em SS, apague as filhas e depois os problemas
-- (a FK das filhas é ON DELETE CASCADE, então basta apagar o problema)
DELETE FROM problema_tipico WHERE codigo LIKE 'BDC-%';
```

> Se houver uso em SS, **não apague**: apenas desative
> (`UPDATE problema_tipico SET ativo = 0 WHERE codigo LIKE 'BDC-%'`), pois a
> remoção da FK bloquearia a exclusão.

### 7.2 Reverter o esquema (migração 017)

O script de reversão está em
`migrations/017_problemas_tipicos_base_conhecimento_down.sql`. Ele **dropa as
tabelas novas, os índices e as colunas adicionadas**, mas **não apaga linhas de
`problema_tipico`** — apenas os campos complementares deixam de existir.

Recomendação: fazer o backup indicado no cabeçalho do próprio arquivo antes de
executar. Em ambiente já migrado, reverter o esquema só faz sentido se a
aplicação também for revertida, pois o modelo ORM passa a esperar as colunas.

---

## 8. Relatório de validação (execução real)

Ambiente: MariaDB 11.7.2, banco `manutencao`.

### 8.1 Execuções

| Execução | Resultado |
| --- | --- |
| `--dry-run` | 70 inseridos, 0 erros, rollback ao final |
| 1ª carga real | **70 inseridos**, 4 tipos de ativo criados, 0 erros |
| 2ª execução | **0 inseridos, 0 atualizados, 70 inalterados**, 0 erros, 0 tipos criados |
| Testes unitários do catálogo | 10/10 OK |
| Testes de integração (banco) | 6/6 OK |

### 8.2 Distribuição por categoria (70 problemas)

| Qtd. | Categoria |
| ---: | --- |
| 12 | Proteção, Controle e Supervisão |
| 9 | Transformador de Potência e Reator |
| 8 | Disjuntor de Alta Tensão |
| 7 | Sistema CC 125 Vcc |
| 6 | Chave Seccionadora e de Aterramento |
| 5 | Barramentos, Conexões e Isoladores |
| 5 | Comunicação e Infraestrutura |
| 5 | Transformador de Corrente (TC) |
| 5 | Transformador de Potencial (TP/TPC) |
| 4 | Para-raios |
| 4 | Serviços Auxiliares em CA |

### 8.3 Classificação

| Criticidade | Qtd. | | Risco operacional | Qtd. |
| --- | ---: | --- | --- | ---: |
| CRITICA | 11 | | ALTO | 42 |
| ALTA | 40 | | MEDIO | 23 |
| MEDIA | 19 | | BAIXO | 5 |
| BAIXA | 0 | | | |

- `status_validacao = PENDENTE` em **70/70**;
- `origem_registro = REFERENCIA_TECNICA` em **70/70**;
- `alerta_seguranca` preenchido em **70/70**;
- `requer_equipe_especializada = true` em **44/70**;
- `requer_desligamento = true` em **29/70**;
- falhas de preenchimento (`modo_falha` / `efeito_falha` / `referencias_tecnicas`)
  : **0**;
- registros inativos: **0**.

### 8.4 Volumetria das listas estruturadas

| Lista | Registros |
| --- | ---: |
| `sintoma_problema` | 280 |
| `causa_problema` | 350 |
| `metodo_deteccao_problema` | 280 |
| `alarme_problema` | 186 |
| `palavra_chave_problema` | 341 |
| `instrumento_problema` | 207 |
| `acao_recomendada` | 350 |

Ações por tipo: `PREVENCAO` 140, `INSPECAO` 64, `CORRECAO` 62, `ENSAIO` 60,
`MONITORAMENTO` 14, `SUBSTITUICAO` 10.

### 8.5 Integridade e preservação

- **0 registros órfãos** em todas as 7 tabelas filhas;
- **0 problemas sem sintoma/causa/ação**;
- FK de `ss_problema` → `problema_tipico` é `RESTRICT` (confirmado por teste);
- registro anterior preservado: `#1 LEGADO-1 "Restritor de Arco"` — título,
  criticidade e filhos **inalterados**;
- acentuação gravada corretamente em `utf8mb4` (verificado com
  `"Pressão ou densidade de gás SF6..."`).

### 8.6 Cenários de idempotência testados

| Cenário | Resultado observado |
| --- | --- |
| Conteúdo alterado fora da seed | `atualizados = 1`, título restaurado pelo catálogo |
| Registro com `status_validacao = VALIDADO` alterado fora da seed | `preservados = 1`, conteúdo do especialista mantido |
| Registro reaberto para `PENDENTE` | volta a sincronizar (`atualizados = 1`) |
| `--sem-atualizar` com divergência | `ignorados_por_opcao = 1`, nada alterado |
| Reexecução sem mudanças | `inseridos = 0`, `atualizados = 0`, `inalterados = 70` |

### 8.7 API (smoke test)

| Verificação | Resultado |
| --- | --- |
| `GET /problemas-tipicos?categoria=Disjuntor de Alta Tensão` | 200, 8 itens |
| Campos novos presentes (`codigo`, `risco_operacional`, `condicao_intervencao`, `status_validacao`, `origem_registro`, `alerta_seguranca`) | OK |
| `GET /problemas-tipicos?busca=termografia` | 200, 5 resultados |
| `GET /problemas-tipicos?busca=bobina de trip` | 200, 3 resultados |
| `GET /problemas-tipicos?busca=BDC-SE-DJ-001` | 200, 1 resultado |
| `GET /problemas-tipicos?risco_operacional=ALTO&status_validacao=PENDENTE` | 200, 42 resultados |
| `GET /problemas-tipicos/opcoes` | 200, 7 sistemas e 12 categorias |
| `GET /problemas-tipicos/estatisticas` | 200, total 71 (70 seed + 1 legado) |
| `GET /problemas-tipicos/1` (registro legado) | 200, `LEGADO-1` |

---

## 9. Preparação para IA / RAG

A estrutura já foi pensada para uso futuro como apoio à decisão (a IA **não**
decide sozinha):

- **Busca textual** — `busca` cobre título, descrição, modo/efeito de falha,
  sintomas, causas, métodos, ações, categoria, sistema, especialidade, códigos
  e as listas novas (alarmes, palavras-chave, instrumentos).
- **Busca por tipo de equipamento** — filtro por `id_tipo_ativo` e por
  `categoria`/`sistema`.
- **Recuperação de problemas semelhantes** — o casamento por
  `palavra_chave_problema` e `alarme_problema` fornece o sinal lexical para
  similaridade.
- **Sugestão de causas/diagnóstico/ações** — as causas e os métodos vêm
  separados dos sintomas, permitindo sugerir hipóteses antes da confirmação.
- **Registro do diagnóstico confirmado** — `status_validacao`
  (`PENDENTE` → `EM_REVISAO` → `VALIDADO`/`REPROVADO`) com `validado_por` e
  `validado_em`; o campo `origem_registro` distingue referência técnica de
  ocorrência real, permitindo que a validação em campo alimente o aprendizado.
- **Indexação vetorial** — os campos textuais podem ser concatenados
  (`titulo + descricao + sintomas + causas + metodos`) em embeddings externos,
  sem alterar este modelo. `codigo` é o identificador estável a usar como
  referência nos índices.

Boas práticas já embutidas: nenhum ajuste de proteção ou limite de fabricante
hardcoded; todo texto que depende do equipamento remete ao manual/procedimento
aprovado.

---

## 10. Itens que exigem validação por especialista

Todos os 70 registros estão `PENDENTE` — por definição, **nenhum foi validado**.
Os itens abaixo têm prioridade de revisão, por serem críticos ou por
dependerem de dados do fabricante/projeto:

| Código | Título | Por que revisar |
| --- | --- | --- |
| BDC-SE-DJ-001 | Recusa de abertura do disjuntor por falha no circuito de comando ou no mecanismo | risco crítico à eliminação de falta |
| BDC-SE-DJ-003 | Pressão ou densidade de gás SF6 fora da faixa especificada | limites e manuseio de SF6 dependem do fabricante |
| BDC-SE-DJ-006 | Tempo de abertura ou fechamento fora do limite | valores de referência são do equipamento |
| BDC-SE-DJ-008 | Desgaste ou degradação dos contatos de interrupção | critério de substituição conforme fabricante |
| BDC-SE-SC-005 | Falha de intertravamento em chave seccionadora ou de aterramento | matriz de intertravamento específica da instalação |
| BDC-SE-TC-001 | Circuito secundário do TC aberto | risco elétrico grave; procedimento de curto do secundário |
| BDC-SE-TC-002 | Relação de transformação divergente | derivação e parametrização são do projeto |
| BDC-SE-TP-001 | Ausência ou desvio de tensão no secundário do TP/TPC | relação e fusíveis específicos |
| BDC-SE-PR-001 | Corrente de fuga elevada no para-raios | limiar depende do modelo do para-raios |
| BDC-SE-TR-001 | Atuação de proteção do transformador sem causa aparente | ajustes e análise de gases |
| BDC-SE-TR-005 | Anomalia em buchas do transformador | critério de substituição e ensaios |
| BDC-SE-TR-006 | Alteração relevante na análise de gases dissolvidos | interpretação de DGA exige especialista |
| BDC-SE-TR-008 | Anomalia no comutador de derivação em carga | manutenção do OLTC é do fabricante |
| BDC-SE-PC-002 | Perda de alimentação auxiliar de painel | define medida operacional compensatória |
| BDC-SE-PC-003 | Falha no circuito de trip da proteção | essencial à proteção |
| BDC-SE-PC-005 | Falha de disjuntor não detectada pela lógica 50BF | ajustes de 50BF são do projeto |
| BDC-SE-PC-008 | Falha em mensagens GOOSE entre IEDs | falha silenciosa; configuração SCL |
| BDC-SE-CC-004 | Autonomia reduzida do sistema CC | tempo de autonomia é definido em projeto |
| BDC-SE-CC-006 | Falha na supervisão de isolamento do sistema CC | setorização envolve cargas essenciais |
| BDC-SE-CA-001 | Perda de alimentação CA dos serviços auxiliares | plano de contingência da instalação |
| BDC-SE-COM-001 | Perda de comunicação com equipamentos de proteção | topologia e redundância da rede |
| BDC-SE-BC-003 | Descargas parciais ou evidências de efeito corona | critérios de aceitação dependem do equipamento |
| BDC-SE-BC-005 | Aterramento de estruturas com resistência elevada | projeto de aterramento e limites de toque/passo |

O fluxo previsto é: revisar → `EM_REVISAO` → `VALIDADO` (com `validado_por` e
`validado_em`), ou `REPROVADO`. Após isso, a seed **preserva** o registro e não
o sobrescreve mais.

---

## 11. Arquivos criados e alterados

### Backend — criados

| Arquivo | Conteúdo |
| --- | --- |
| `problemas_tipicos/catalogo.py` | catálogo dos 70 problemas |
| `problemas_tipicos/migracoes.py` | aplicador idempotente da migração |
| `migrations/017_problemas_tipicos_base_conhecimento.sql` | migração de esquema (up) |
| `migrations/017_problemas_tipicos_base_conhecimento_down.sql` | reversão |
| `scripts/seed_problemas_tipicos.py` | seed (substitui o script antigo) |
| `scripts/verificar_problemas_tipicos.py` | verificação somente leitura |
| `tests/test_problemas_tipicos_catalogo.py` | 10 testes do catálogo |
| `tests/test_problemas_tipicos_seed.py` | 6 testes de integração (opt-in) |
| `docs/problemas_tipicos_base_conhecimento.md` | este documento |

### Backend — alterados

| Arquivo | Alteração |
| --- | --- |
| `models/problemas_tipicos_models.py` | novas colunas, enums e 3 classes filhas |
| `problemas_tipicos/schemas.py` | campos novos e `OpcoesProblema`/`EstatisticasProblema` |
| `problemas_tipicos/service.py` | `gerar_codigo`, busca com `EXISTS`, `opcoes`, `estatisticas` |
| `problemas_tipicos/routes.py` | `/opcoes` e `/estatisticas` antes de `/{id_problema}` |
| `main.py` | aplica a migração de problemas típicos na subida |

### Frontend (`OP_FRONT/OPERACAO_MANUTENCAO`)

| Arquivo | Alteração |
| --- | --- |
| `src/types/problemaTipico.ts` | novos tipos/enums e campos opcionais; `TipoAcao` inclui `PREVENCAO` |
| `src/components/Layout.tsx` | remoção do link “Validar OS antigas” do menu |

### Corrigido no script antigo

O `scripts/seed_problemas_tipicos.py` anterior inseria registros **sem**
`codigo`, coluna que passou a ser `NOT NULL`, e por isso falhava. O script novo:

- define `codigo` a partir da chave natural do catálogo;
- separa inserir/atualizar/preservar com segurança transacional por item;
- cria os tipos de ativo ausentes de forma explícita e logada;
- é idempotente e retorna código de saída utilizável em automação.

---

## 12. Limitações e testes não executados

- **Validação técnica de conteúdo**: nenhum dos 70 registros foi revisado por
  especialista (todos `PENDENTE`). O texto é uma referência de apoio, não um
  procedimento liberado.
- **Valores de fabricante**: nenhum limite, código de alarme ou ajuste de
  proteção foi fixado no catálogo; a consulta ao manual/procedimento aprovado é
  obrigatória.
- **Testes não executados**: não foi executada a suíte completa do backend
  (`tests/` inteiro) nem testes de carga/estresse; não foi validado o consumo
  da nova `ProblemasTipicosPage` exibindo os campos novos (a página segue
  funcionando com o contrato anterior, e apenas os tipos foram estendidos).
- **Rota `/validacao-os-antigas`**: o link foi removido do menu, mas a rota e a
  página continuam acessíveis por URL direta (decisão pendente de confirmação).
- **Rollback de esquema**: o `_down.sql` foi escrito e revisado, mas **não foi
  executado** neste ambiente (destrutivo por natureza). Antes de usá-lo, faça o
  backup indicado no cabeçalho.
