"""Consultas de chaveamento."""

SWITCHING_SQL = """
WITH pares AS (
    SELECT
        e.id_evento,
        e.archive_creation_date_utc AS data_evento,
        c.indice_canal AS canal,
        REPLACE(g.codigo, 'calculated_', '') AS codigo_base,
        'calculado' AS tipo,
        m.valor
    FROM fato_medicao m
    JOIN fato_evento e ON e.id_evento = m.id_evento
    JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
    LEFT JOIN dim_canal c ON c.id_canal = m.id_canal
    WHERE g.codigo LIKE 'calculated_meca_time%'
       OR g.codigo LIKE 'calculated_angle%'
       OR g.codigo LIKE 'calculated_arc_time%'
    UNION ALL
    SELECT
        e.id_evento,
        e.archive_creation_date_utc,
        c.indice_canal,
        REPLACE(g.codigo, 'measured_', '') AS codigo_base,
        'medido',
        m.valor
    FROM fato_medicao m
    JOIN fato_evento e ON e.id_evento = m.id_evento
    JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
    LEFT JOIN dim_canal c ON c.id_canal = m.id_canal
    WHERE g.codigo LIKE 'measured_meca_time%'
       OR g.codigo LIKE 'measured_angle%'
       OR g.codigo LIKE 'measured_arc_time%'
)
SELECT
    id_evento,
    data_evento,
    canal,
    codigo_base,
    MAX(CASE WHEN tipo = 'calculado' THEN valor END) AS calculado,
    MAX(CASE WHEN tipo = 'medido' THEN valor END) AS medido,
    ABS(MAX(CASE WHEN tipo = 'calculado' THEN valor END) - MAX(CASE WHEN tipo = 'medido' THEN valor END)) AS erro_absoluto,
    CASE WHEN MAX(CASE WHEN tipo = 'medido' THEN valor END) <> 0
         THEN ABS(MAX(CASE WHEN tipo = 'calculado' THEN valor END) - MAX(CASE WHEN tipo = 'medido' THEN valor END)) / ABS(MAX(CASE WHEN tipo = 'medido' THEN valor END)) * 100
    END AS erro_percentual
FROM pares
GROUP BY id_evento, data_evento, canal, codigo_base
ORDER BY data_evento, canal, codigo_base
"""

