"""Consultas analíticas para a página de operação do disjuntor."""

COUNTER_MATRIX_SQL = """
WITH por_evento AS (
    SELECT
        eq.id_equipamento,
        eq.substation,
        eq.bay_number,
        CASE
            WHEN g.codigo LIKE 'counter_closing_%' THEN 'Close'
            ELSE 'Open'
        END AS operacao,
        c.fase,
        CASE
            WHEN g.codigo IN ('counter_closing_controlled', 'counter_opening_controlled')
                THEN 'Operações controladas'
            WHEN g.codigo IN ('counter_closing_uncontrolled', 'counter_opening_uncontrolled')
                THEN 'Operações não controladas'
            WHEN g.codigo = 'counter_reignition'
                THEN 'Reignição controlada'
            WHEN g.codigo = 'counter_reignition_wo_csd'
                THEN 'Reignição não controlada'
        END AS contador,
        MAX(fc.valor) AS valor
    FROM fato_contador fc
    JOIN fato_evento e ON e.id_evento = fc.id_evento
    JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
    JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
    JOIN dim_canal c ON c.id_canal = fc.id_canal
    WHERE g.codigo IN (
        'counter_closing_controlled',
        'counter_closing_uncontrolled',
        'counter_opening_controlled',
        'counter_opening_uncontrolled',
        'counter_reignition',
        'counter_reignition_wo_csd'
    )
      AND c.fase IS NOT NULL
    GROUP BY eq.id_equipamento, eq.substation, eq.bay_number,
             operacao, c.fase, contador, e.id_evento
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

OPERATION_METRICS_SQL = """
SELECT
    eq.id_equipamento,
    eq.substation,
    eq.bay_number,
    e.id_evento,
    e.archive_creation_date_utc,
    e.archive_type,
    c.fase,
    g.codigo AS metrica,
    g.unidade,
    m.valor
FROM fato_medicao m
JOIN fato_evento e ON e.id_evento = m.id_evento
JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
JOIN dim_canal c ON c.id_canal = m.id_canal
WHERE g.codigo IN (
    'calculated_angle', 'measured_angle',
    'calculated_arc_time', 'measured_arc_time',
    'calculated_meca_time', 'measured_meca_time',
    'calculated_meca_time_compensation_udc',
    'calculated_break_time', 'calculated_make_time',
    'calculated_prearc_time', 'measured_prearc_time',
    'peak_current', 'voltage_dip'
)
  AND c.fase IS NOT NULL
ORDER BY e.archive_creation_date_utc DESC, e.id_evento DESC
"""

SENSOR_SUMMARY_SQL = """
SELECT
    eq.id_equipamento,
    eq.substation,
    eq.bay_number,
    e.id_evento,
    e.archive_creation_date_utc,
    c.fase,
    g.codigo AS sensor,
    g.unidade,
    m.valor
FROM fato_medicao m
JOIN fato_evento e ON e.id_evento = m.id_evento
JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
LEFT JOIN dim_canal c ON c.id_canal = m.id_canal
WHERE g.codigo IN (
    'ambient_temperature', 'cb_gas_pressure', 'hydraulic_pressure',
    'dc1_values', 'dc2_values', 'current_frequency_l1',
    'current_frequency_l2', 'current_frequency_l3',
    'rms_current_l1_primary', 'rms_current_l2_primary',
    'rms_current_l3_primary', 'rms_source_voltage_l1_primary',
    'rms_source_voltage_l2_primary', 'rms_source_voltage_l3_primary',
    'rms_load_voltage_l1_primary', 'rms_load_voltage_l2_primary',
    'rms_load_voltage_l3_primary'
)
ORDER BY e.archive_creation_date_utc DESC, e.id_evento DESC
"""

ALARM_MATRIX_SQL = """
SELECT
    eq.id_equipamento,
    eq.substation,
    eq.bay_number,
    COALESCE(ta.codigo, 'Sem código') AS alarme,
    COALESCE(c.fase, 'Geral') AS fase,
    COALESCE(a.estado_alarme, 'Desconhecido') AS estado_alarme,
    COUNT(*) AS ocorrencias
FROM fato_alarme a
JOIN fato_evento e ON e.id_evento = a.id_evento
JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
LEFT JOIN dim_tipo_alarme ta ON ta.id_tipo_alarme = a.id_tipo_alarme
LEFT JOIN dim_canal c ON c.id_canal = a.id_canal
GROUP BY eq.id_equipamento, eq.substation, eq.bay_number,
         alarme, fase, estado_alarme
ORDER BY ocorrencias DESC, alarme, fase
"""
