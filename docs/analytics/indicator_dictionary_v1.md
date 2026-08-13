# ENGVI — Dicionário Analítico de Manutenção v1

Status: proposta fechada da Etapa 2  
Base analisada: 13/08/2026  
Escopo: OS, ativos, funções operacionais, planos, execuções e inspeções.

## 1. Princípios

1. Todo KPI deve informar valor, período e cobertura dos dados.
2. Registros sem dimensão conhecida aparecem como `Não informado`; não são descartados.
3. O backend é a fonte única das fórmulas. O frontend apenas apresenta respostas analíticas.
4. Valores de cards, gráficos e drill-down devem usar a mesma consulta-base.
5. Datas inválidas não entram em indicadores temporais e são contabilizadas na cobertura.
6. Nenhum dado operacional será corrigido automaticamente pela camada analítica.

## 2. Fato analítico principal — OS

Granularidade: uma linha por `ordem_servico.id_os`.

### Datas canônicas

| Nome analítico | Fonte | Uso |
|---|---|---|
| `data_criacao` | `ordem_servico.criado_em` | entrada e idade do backlog |
| `data_programada_inicio` | `data_inicio_programado` | agenda e início planejado |
| `data_programada_fim` | `COALESCE(data_fim_programado, data_inicio_programado)` | prazo e atraso |
| `data_execucao_inicio` | `data_inicio_execucao` | duração real |
| `data_conclusao` | `data_fim_execucao` | produção e cumprimento |

Registros com fim anterior ao início são inválidos para métricas de duração.

### Status canônico

| Valor armazenado | Valor analítico |
|---|---|
| `ABERTA` | `ABERTA` |
| `PROGRAMADA` | `PROGRAMADA` |
| `EM_EXECUCAO`, `EM EXECUÇÃO`, `EM EXECUÇÃO` sem acento | `EM_EXECUCAO` |
| `ENCERRADA`, `CONCLUIDA`, `CONCLUÍDA` | `CONCLUIDA` |
| `CANCELADA` | `CANCELADA` |
| nulo ou desconhecido | `NAO_INFORMADO` |

Conjunto pendente: `ABERTA`, `PROGRAMADA`, `EM_EXECUCAO`.

### Classe de manutenção

Precedência sobre `esquema_servicos`:

1. contém `CORRET` → `CORRETIVA`;
2. contém `PREDIT` → `PREDITIVA`;
3. contém `PREVENT` → `PREVENTIVA`;
4. contém `MONITOR` → `MONITORAMENTO`;
5. contém `RECOMENDA` → `ATENDIMENTO_RECOMENDACAO`;
6. demais → `NAO_CLASSIFICADA`.

Periodicidade preventiva deve permanecer em dimensão separada: semanal, mensal, bimestral, trimestral, semestral, anual, três, cinco e seis anos.

### Prioridade canônica

Reutilizar a regra operacional já existente:

| Valor armazenado | Valor analítico |
|---|---|
| `ALTA` | `NIVEL_1` |
| `MEDIA` | `NIVEL_3` |
| `BAIXA` | `NIVEL_5` |
| `NIVEL_1` a `NIVEL_6` | mesmo valor |
| nulo ou desconhecido | `NAO_INFORMADA` |

O dashboard pode apresentar os textos completos da política de prioridade, mas filtros e agregações usam o código canônico.

### Função operacional derivada

Precedência:

```text
ordem_servico.id_funcao_operacao
→ ativo.id_funcao_operacao
→ grupo_ativo.id_funcao_operacao
→ Não informado
```

Não usar texto de instalação para inferir FO.

### Tipo de ativo derivado

Precedência:

```text
ativo.id_tipo_ativo
→ grupo_ativo.id_tipo_ativo
→ Não informado
```

## 3. Dimensões e filtros

Todos os endpoints analíticos de OS devem aceitar filtros combináveis:

- `data_inicio` e `data_fim`;
- `campo_data`: criação, programação ou conclusão;
- `id_subestacao`;
- `id_funcao_operacao` derivada;
- `id_ativo`;
- `id_grupo_ativo`;
- `id_tipo_ativo` derivado;
- `classe_manutencao`;
- `periodicidade`;
- `status_canonico`;
- `prioridade_canonica`;
- `responsavel`;
- `origem`;
- `id_plano_manutencao`.

Listas aceitam múltiplos valores. Datas usam intervalo semiaberto: `>= início` e `< dia seguinte ao fim`.

## 4. Dicionário de KPIs de OS

### OS abertas

- Objetivo: medir ordens ainda sem programação ou execução.
- Fórmula: `COUNT(DISTINCT id_os) WHERE status_canonico = ABERTA`.
- Data padrão: criação.
- Drill-down: número, subestação, FO, ativo, descrição, criação, prioridade e responsável.

### OS programadas

- Fórmula: `COUNT(DISTINCT id_os) WHERE status_canonico = PROGRAMADA`.
- Data padrão: programação.

### OS em execução

- Fórmula: `COUNT(DISTINCT id_os) WHERE status_canonico = EM_EXECUCAO`.
- Data padrão: início da execução.

### OS concluídas

- Fórmula: `COUNT(DISTINCT id_os) WHERE status_canonico = CONCLUIDA`.
- Data padrão: conclusão.
- Limitação: concluídas sem `data_fim_execucao` entram no total de status, mas não em séries por conclusão.

### Backlog total

- Objetivo: representar trabalho pendente conhecido.
- Fórmula: `COUNT(DISTINCT id_os) WHERE status_canonico IN (ABERTA, PROGRAMADA, EM_EXECUCAO)`.
- Filtros temporais: para fotografia atual, não restringir por criação; para análise histórica, usar snapshot reconstruído somente quando houver eventos de mudança de status. A base atual não possui histórico completo, portanto o backlog histórico será aproximação enquanto essa estrutura não existir.

### Idade do backlog

- Fórmula: `DATE(data_referencia) - DATE(data_criacao)`.
- `data_referencia`: agora para pendentes.
- Faixas: `0–7`, `8–30`, `31–60`, `61–90`, `>90 dias`.
- Sem data de criação: `Idade não calculável`.

### OS atrasadas

- Fórmula: pendente e `data_programada_fim < agora`.
- Sem data programada: não é classificada como atrasada; aparece como `Sem prazo programado`.
- Dias de atraso: `DATEDIFF(hoje, DATE(data_programada_fim))`, mínimo zero.

### Concluídas no prazo

- Numerador: concluídas com datas válidas e `data_conclusao <= data_programada_fim`.
- Denominador: concluídas com `data_conclusao` e `data_programada_fim` válidas.
- Resultado: `numerador / denominador × 100`.
- Obrigatório exibir cobertura: `denominador / total concluídas × 100`.

### Cumprimento da programação

- Nome exibido: `Concluídas no prazo` para evitar ambiguidade.
- A fórmula é a definida acima; não usar status encerrado isoladamente.

### Tempo médio de execução

- Fórmula: média de `data_conclusao - data_execucao_inicio` em horas.
- Exclusões: datas nulas, duração negativa e registros cancelados.
- Exibir mediana e percentil 90 junto da média para reduzir distorção por valores extremos.

### Tempo até início

- Fórmula: `data_execucao_inicio - data_criacao`.
- Mesmas regras de validade do tempo médio.

### Evolução mensal

- Abertas: agrupadas por mês de criação.
- Concluídas: agrupadas por mês de conclusão.
- Atrasadas: conclusão atrasada no mês ou pendência vencida atual. As duas séries não devem ser misturadas; nomes sugeridos: `Concluídas com atraso` e `Backlog vencido atual`.

### Mix de manutenção

- Fórmula por classe: `OS da classe / OS classificáveis no período × 100`.
- Exibir `Não classificada` separadamente; não removê-la do total sem informar cobertura.

### OS por ativo

- Contagem distinta de OS por ativo/grupo.
- Não interpretar volume alto automaticamente como baixa confiabilidade: pode refletir periodicidade ou granularidade do plano.

### OS por responsável

- Fonte preferencial: `responsavel_manutencao`, fallback `responsavel`.
- Limitação: nomes são textos livres e equipes aparecem combinadas no mesmo campo. Até haver vínculo por usuário/equipe, o KPI é descritivo e exige dimensão de aliases, sem alteração automática dos dados originais.

## 5. KPIs de inspeção

### Inspeções realizadas

- Fórmula: contagem distinta de `id_inspecao` por `data_inspecao`.

### Inspeções NOK

- Fórmula: inspeções cujo `status_geral = NOK`.
- Percentual NOK: `inspeções NOK / inspeções realizadas × 100`.

### Itens NOK

- Fórmula: resultados cujo `status_item = NOK`.
- Não confundir quantidade de itens NOK com quantidade de inspeções NOK.

### Cobertura de inspeção

- Fórmula: `ativos distintos inspecionados / ativos elegíveis × 100`.
- Elegibilidade inicial: ativos operantes do filtro e período. A regra deverá ser refinada por plano e periodicidade na Etapa 3.

## 6. Planejamento

Fato futuro: `plano_execucao`, granularidade de um item do plano para um ativo.

### Execuções próximas

- Fórmula: contagem distinta de `id_execucao` com `proxima_execucao` entre agora e o limite.
- Janelas: 7, 15, 30, 60, 90 dias e personalizada.
- Não nomear como “manutenções” antes do agrupamento operacional.

### Execuções atrasadas do plano

- Fórmula inicial: `proxima_execucao < agora` e item/execução ativos.
- Necessário considerar se já existe OS do mesmo ciclo. O serviço analítico deverá usar a regra vigente de geração de OS para evitar falso atraso.

### Evento de manutenção planejada

Para calendário e carga, agrupar execuções por:

```text
id_plano_manutencao
+ id_ativo ou id_grupo
+ data programada
+ periodicidade
```

O evento mantém a lista dos itens internos. Essa regra reduz 18.723 itens a mobilizações operacionais sem perder o detalhamento.

### Previsão de próxima execução

Fonte prioritária: `plano_execucao.proxima_execucao`, calculada pela regra atual.

Não recalcular meses ou anos como quantidade fixa de dias. A camada analítica reutilizará a mesma função de periodicidade do domínio.

## 7. KPIs bloqueados por falta de dados

| KPI | Situação | Estrutura necessária |
|---|---|---|
| MTBF | indisponível | evento de falha, início/fim e horas operacionais |
| MTTR | indisponível | início da indisponibilidade e restabelecimento |
| Disponibilidade | indisponível | tempo operacional e indisponibilidade |
| Homem-hora | indisponível | duração estimada e quantidade de profissionais por função |
| Capacidade x demanda | indisponível | capacidade por equipe/período e ausências |
| Conflito de recursos | indisponível | recurso estruturado, quantidade disponível e reservas |
| Custo | indisponível | custos de mão de obra, material e serviço |
| Criticidade | indisponível | classificação rastreável e regra aprovada |

## 8. Qualidade e cobertura obrigatórias na API

Cada resposta de KPI deve conter:

```json
{
  "valor": 95.5,
  "numerador": 942,
  "denominador": 986,
  "total_relevante": 1186,
  "cobertura_percentual": 83.1,
  "atualizado_em": "2026-08-13T...",
  "regra_versao": "1.0"
}
```

Alertas de qualidade mínimos:

- data final sem data inicial;
- data final anterior à inicial;
- conclusão anterior à criação;
- conclusão futura;
- OS sem ativo/grupo;
- OS sem FO derivável;
- concluída sem data final;
- número de OS duplicado;
- referência órfã.

## 9. Drill-down

Todos os KPIs contáveis devem retornar um `drilldown_key` e aceitar paginação no endpoint de detalhes.

Colunas-padrão:

```text
OS | Status | Subestação | FO | Ativo/Grupo | Tipo de ativo
Classe | Prioridade | Atividade | Data programada | Data conclusão
Dias de atraso | Responsável
```

Exportação e tela devem reutilizar o mesmo filtro serializado do card/gráfico.

## 10. Contratos propostos para a Etapa 4

Sem implementação nesta etapa:

```text
GET /analytics/filters
GET /analytics/executive-summary
GET /analytics/os/timeline
GET /analytics/os/status
GET /analytics/os/backlog-aging
GET /analytics/os/distribution
GET /analytics/inspections/summary
GET /analytics/planning/upcoming
GET /analytics/details/{drilldown_key}
GET /analytics/data-quality
```

Todas as rotas serão protegidas pelas permissões existentes, sem autenticação paralela.

## 11. Validação

Para cada endpoint será criada consulta SQL de referência. Teste obrigatório:

```text
resultado do serviço = resultado SQL direto
```

Linha de base de 13/08/2026:

- OS totais: 1.506;
- backlog atual: 320;
- atrasadas: 138;
- concluídas no mês: 153;
- concluídas no prazo avaliáveis: 942 de 986;
- OS com FO derivável: 1.463 de 1.506.

Esses números são referência de regressão, não valores fixos do produto.

## 12. Decisões para a Etapa 3

1. Criar modelagem estruturada de recurso sem remover os textos atuais do plano.
2. Definir duração estimada por evento ou item.
3. Definir mão de obra por função e quantidade.
4. Definir disponibilidade e quantidade de instrumentos/veículos.
5. Definir capacidade de equipe por calendário.
6. Definir regra rastreável de criticidade.
7. Manter o dashboard atual intacto; o dashboard analítico será criado em rota paralela de teste.
