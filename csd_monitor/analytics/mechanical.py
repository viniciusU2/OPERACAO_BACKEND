"""Consultas de comparação calculado versus medido."""

MECHANICAL_COMPARISON_SQL = """
SELECT
    e.id_evento,
    e.archive_creation_date_utc AS data_evento,
    c.indice_canal AS canal,
    g.codigo AS grandeza,
    m.valor AS valor,
    CASE
        WHEN g.codigo LIKE 'calculated\\_%' THEN 'calculado'
        WHEN g.codigo LIKE 'measured\\_%' THEN 'medido'
    END AS tipo
FROM fato_medicao m
JOIN fato_evento e ON e.id_evento = m.id_evento
JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
LEFT JOIN dim_canal c ON c.id_canal = m.id_canal
WHERE g.codigo LIKE 'calculated\\_%' OR g.codigo LIKE 'measured\\_%'
"""

