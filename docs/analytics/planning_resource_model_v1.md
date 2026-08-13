# Modelo de planejamento e recursos — Etapa 03

Status: proposta de modelagem. Esta etapa não altera o banco, a API ou o dashboard atual.

## Objetivo

Transformar as execuções futuras dos planos de manutenção em uma visão operacional capaz de estimar demanda de pessoas, horas, equipamentos, instrumentos, veículos, materiais, EPI e EPC, sem inventar capacidades ou quantidades ainda não cadastradas.

## Evento futuro de manutenção

A fonte permanece `plano_execucao`. Cada registro representa a previsão de execução de um item do plano para um ativo ou grupo de ativos; ele não deve ser interpretado isoladamente como uma mobilização completa.

Para calendário e previsão, os registros devem ser agrupados por:

- plano de manutenção;
- ativo ou grupo de ativos;
- data programada;
- periodicidade do item.

O agrupamento forma um `evento_planejado` calculado. Itens de ativos diferentes não são agrupados. Periodicidades diferentes permanecem separadas, mesmo quando caem na mesma data. O identificador pode ser determinístico, composto pelos campos acima, para permitir drill-down sem criar tabela nova.

Persistir uma tabela de eventos só será necessário quando o sistema permitir remarcação, atribuição manual de equipe ou bloqueio de recursos em um evento específico. Até lá, a agregação dinâmica evita duplicar a agenda já existente.

## Catálogo de recursos

### `recurso`

Catálogo único com as categorias:

- `MAO_DE_OBRA`;
- `INSTRUMENTO`;
- `VEICULO`;
- `EQUIPAMENTO`;
- `MATERIAL`;
- `EPI`;
- `EPC`.

Campos principais: nome, categoria, unidade, quantidade disponível, controle de disponibilidade, ativo e observação. A disponibilidade pode ser nula: isso significa “não informada”, e nunca zero.

### `plano_recurso`

Relaciona o plano ao recurso e registra quantidade, horas de utilização e se o item é consumível. Recursos do tipo mão de obra usam quantidade de profissionais e horas por profissional.

As descrições textuais já existentes em materiais, procedimentos e segurança permanecem válidas. A nova associação é incremental e serve para cálculos estruturados; nenhuma informação antiga deve ser removida automaticamente.

## Duração, equipe e capacidade

### `plano_estimativa`

Registra uma estimativa padrão de duração do evento em horas. Fica em tabela separada para não tornar obrigatória uma alteração invasiva na tabela atual de planos.

### `plano_equipe`

Associa um plano a uma ou mais equipes existentes em `sobreaviso_equipe`. A prioridade define qual equipe é preferencial. Não deve ser criada outra tabela de cadastro de equipes.

### `equipe_capacidade`

Registra horas disponíveis por equipe e período. A capacidade é informada explicitamente pelo usuário ou integração. Na ausência dela, os indicadores exibem “dados insuficientes”.

## Cálculos

### Homem-hora previsto

Para cada recurso de `MAO_DE_OBRA`:

`HH previsto = quantidade de profissionais × horas por profissional`

Se as horas do recurso não estiverem preenchidas, pode ser usada a duração estimada do plano. Sem ambas, o HH não é calculável e deve aparecer como pendência cadastral.

### Demanda de recursos reutilizáveis

Para instrumentos, veículos, equipamentos, EPI e EPC controlados:

`demanda simultânea = soma das quantidades dos eventos com horários sobrepostos`

Enquanto os eventos tiverem apenas data e duração, o início padrão deve ser configurável e claramente identificado como estimativa. Sem horário ou regra configurada, a análise deve ser diária, não horária.

### Materiais consumíveis

Materiais consumíveis geram previsão de consumo por período. Eles não usam a regra de simultaneidade:

`consumo previsto = soma da quantidade × número de eventos`

Essa previsão não equivale a estoque reservado. Uma futura integração com almoxarifado poderá comparar saldo e demanda.

### Utilização de equipe

`utilização = HH atribuída à equipe / horas disponíveis da equipe × 100`

O indicador só é válido quando existem associação da equipe e capacidade cadastrada para o período. Valores acima de 100% representam sobrecarga.

## Detecção de conflitos

Um conflito deve possuir tipo, severidade, período, eventos envolvidos, recurso ou equipe e excesso calculado.

Regras iniciais:

1. recurso reutilizável: demanda simultânea maior que a quantidade disponível;
2. equipe: HH planejada maior que a capacidade do período;
3. material: consumo previsto maior que saldo, apenas quando houver integração de estoque;
4. cadastro incompleto: evento sem duração, equipe ou recursos necessários — exibido como alerta de dados, não como conflito confirmado;
5. agenda: eventos atribuídos à mesma equipe com sobreposição de horário, apenas após existir horário de início confiável.

Disponibilidade nula desativa a validação daquele recurso e gera alerta de cobertura. Nunca deve ser tratada como disponibilidade ilimitada nem como zero.

## Indicadores possíveis

- eventos previstos por período, subestação, plano e periodicidade;
- HH previsto e HH sem dados suficientes;
- utilização de equipe;
- recursos mais demandados;
- consumo previsto de materiais;
- conflitos confirmados e alertas de cadastro;
- cobertura de duração, recursos, equipe e capacidade;
- carga futura por subestação e família de equipamento.

Todos devem oferecer drill-down até os eventos e registros de `plano_execucao` que formaram o resultado.

## APIs propostas para a Etapa 04

- `GET /analytics/planning/events`
- `GET /analytics/planning/workload`
- `GET /analytics/planning/resources-demand`
- `GET /analytics/planning/conflicts`
- `GET /analytics/planning/data-coverage`
- CRUD administrativo de `/recursos`
- CRUD de recursos, estimativa e equipes vinculados ao plano
- CRUD de `/equipes/{id}/capacidades`

Filtros comuns: intervalo de datas, subestação, plano, periodicidade, tipo de equipamento, recurso e equipe.

## Ordem segura de implantação

1. aplicar as tabelas propostas após revisão e backup;
2. cadastrar recursos reais, sem carga fictícia;
3. cadastrar duração e recursos dos planos prioritários;
4. associar equipes e informar capacidades;
5. publicar os endpoints analíticos com cobertura explícita;
6. validar os resultados com a operação;
7. somente depois adicionar o novo dashboard de teste em `/dashboard-analitico`.

## Decisões de segurança

- nenhuma quantidade, duração ou capacidade será inferida silenciosamente;
- o modelo reutiliza as equipes existentes;
- o dashboard atual não será modificado;
- a proposta SQL não deve ser executada automaticamente;
- eventos permanecem calculados até existir necessidade operacional de persistência.
