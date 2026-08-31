"""Consultas do dashboard principal."""

EQUIPMENT_COUNTERS_SQL = """
WITH por_evento AS (
    SELECT
        e.id_evento,
        e.id_equipamento,
        eq.substation,
        eq.bay_number,
        eq.csd_serial_number,
        e.archive_creation_date_utc,
        MAX(CASE WHEN g.codigo = 'counter_opening_controlled' THEN fc.valor END) AS abertura_controlada,
        MAX(CASE WHEN g.codigo = 'counter_opening_uncontrolled' THEN fc.valor END) AS abertura_nao_controlada
    FROM fato_contador fc
    JOIN fato_evento e ON e.id_evento = fc.id_evento
    JOIN dim_equipamento eq ON eq.id_equipamento = fc.id_equipamento
    JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
    WHERE g.codigo IN ('counter_opening_controlled', 'counter_opening_uncontrolled')
    GROUP BY e.id_evento, e.id_equipamento, eq.substation, eq.bay_number,
             eq.csd_serial_number, e.archive_creation_date_utc
)
SELECT
    id_equipamento,
    substation,
    bay_number,
    csd_serial_number,
    MAX(abertura_controlada) AS abertura_controlada,
    MAX(abertura_nao_controlada) AS abertura_nao_controlada,
    MAX(archive_creation_date_utc) AS ultimo_evento
FROM por_evento
GROUP BY id_equipamento, substation, bay_number, csd_serial_number
ORDER BY substation, bay_number
"""

COUNTER_TIMELINE_SQL = """
SELECT
    e.archive_creation_date_utc AS data_evento,
    eq.bay_number,
    eq.substation,
    MAX(CASE WHEN g.codigo = 'counter_opening_controlled' THEN fc.valor END) AS abertura_controlada,
    MAX(CASE WHEN g.codigo = 'counter_opening_uncontrolled' THEN fc.valor END) AS abertura_nao_controlada
FROM fato_contador fc
JOIN fato_evento e ON e.id_evento = fc.id_evento
JOIN dim_equipamento eq ON eq.id_equipamento = fc.id_equipamento
JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
WHERE g.codigo IN ('counter_opening_controlled', 'counter_opening_uncontrolled')
GROUP BY e.id_evento, e.archive_creation_date_utc, eq.bay_number, eq.substation
ORDER BY data_evento
"""

ALARM_SUMMARY_SQL = """
SELECT
    eq.id_equipamento,
    eq.substation,
    eq.bay_number,
    eq.csd_serial_number,
    ta.codigo AS alarme,
    COUNT(*) AS ocorrencias,
    SUM(CASE WHEN a.estado_alarme = 1 THEN 1 ELSE 0 END) AS ativas,
    MAX(a.timestamp_on) AS ultima_ativacao
FROM fato_alarme a
JOIN fato_evento e ON e.id_evento = a.id_evento
JOIN dim_equipamento eq ON eq.id_equipamento = a.id_equipamento
JOIN dim_tipo_alarme ta ON ta.id_tipo_alarme = a.id_tipo_alarme
GROUP BY eq.id_equipamento, eq.substation, eq.bay_number,
         eq.csd_serial_number, ta.codigo
ORDER BY ocorrencias DESC, alarme
"""

COUNTER_MATRIX_SQL = """
WITH por_evento AS (
    SELECT
        e.id_evento,
        eq.id_equipamento,
        eq.substation,
        eq.bay_number,
        CASE
            WHEN g.codigo LIKE 'counter_closing_%' THEN 'Close'
            ELSE 'Open'
        END AS operacao,
        c.fase,
        CASE
            WHEN g.codigo = 'counter_closing_controlled' OR g.codigo = 'counter_opening_controlled' THEN 'Operações controladas'
            WHEN g.codigo = 'counter_closing_uncontrolled' OR g.codigo = 'counter_opening_uncontrolled' THEN 'Operações não controladas'
            WHEN g.codigo = 'counter_reignition' THEN 'Reignição controlada'
            WHEN g.codigo = 'counter_reignition_wo_csd' THEN 'Reignição não controlada'
        END AS contador,
        MAX(fc.valor) AS valor
    FROM fato_contador fc
    JOIN fato_evento e ON e.id_evento = fc.id_evento
    JOIN dim_equipamento eq ON eq.id_equipamento = fc.id_equipamento
    JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
    LEFT JOIN dim_canal c ON c.id_canal = fc.id_canal
    WHERE g.codigo IN (
        'counter_closing_controlled',
        'counter_closing_uncontrolled',
        'counter_opening_controlled',
        'counter_opening_uncontrolled',
        'counter_reignition',
        'counter_reignition_wo_csd'
    )
      AND c.fase IS NOT NULL
    GROUP BY e.id_evento, eq.id_equipamento, eq.substation, eq.bay_number,
             operacao, c.fase, contador
)
SELECT
    id_equipamento,
    substation,
    bay_number,
    operacao,
    fase,
    contador,
    MAX(valor) AS valor
FROM por_evento
GROUP BY id_equipamento, substation, bay_number, operacao, fase, contador
ORDER BY bay_number, operacao, fase, contador
"""
