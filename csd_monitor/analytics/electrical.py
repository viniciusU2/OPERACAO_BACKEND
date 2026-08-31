"""Consultas para grandezas elétricas."""

ELECTRICAL_SQL = """
SELECT * FROM vw_medicoes
WHERE categoria = 'ELECTRICAL'
ORDER BY archive_creation_date_utc, grandeza, indice_canal
"""

