-- Migração incremental para instalações onde relatorio_manutencao já existe.
-- Pode ser executada mais de uma vez com segurança.

DELIMITER $$

DROP PROCEDURE IF EXISTS add_relatorio_manutencao_column$$
CREATE PROCEDURE add_relatorio_manutencao_column(
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'relatorio_manutencao'
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT(
            'ALTER TABLE relatorio_manutencao ADD COLUMN `',
            REPLACE(p_column_name, '`', '``'),
            '` ', p_column_definition
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

CALL add_relatorio_manutencao_column('id_usuario_edicao', 'INT NULL')$$
CALL add_relatorio_manutencao_column('texto_introducao', 'TEXT NULL')$$
CALL add_relatorio_manutencao_column('corpo_tecnico_json', 'TEXT NULL')$$
CALL add_relatorio_manutencao_column('numero_os', 'VARCHAR(100) NULL')$$
CALL add_relatorio_manutencao_column('numero_apr', 'VARCHAR(100) NULL')$$
CALL add_relatorio_manutencao_column('periodo_capa', 'VARCHAR(100) NULL')$$
CALL add_relatorio_manutencao_column('concessao', 'VARCHAR(255) NULL')$$
CALL add_relatorio_manutencao_column('hora_inicio', 'VARCHAR(10) NULL')$$
CALL add_relatorio_manutencao_column('hora_fim', 'VARCHAR(10) NULL')$$
CALL add_relatorio_manutencao_column('temperatura_inicio', 'VARCHAR(20) NULL')$$
CALL add_relatorio_manutencao_column('temperatura_fim', 'VARCHAR(20) NULL')$$
CALL add_relatorio_manutencao_column('frequencia_inicio', 'VARCHAR(20) NULL')$$
CALL add_relatorio_manutencao_column('frequencia_fim', 'VARCHAR(20) NULL')$$
CALL add_relatorio_manutencao_column('tensao_inicio', 'VARCHAR(20) NULL')$$
CALL add_relatorio_manutencao_column('tensao_fim', 'VARCHAR(20) NULL')$$

DROP PROCEDURE add_relatorio_manutencao_column$$

DELIMITER ;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'relatorio_manutencao'
  AND COLUMN_NAME IN (
    'id_usuario_edicao', 'texto_introducao', 'corpo_tecnico_json',
    'numero_os', 'numero_apr', 'periodo_capa', 'concessao',
    'hora_inicio', 'hora_fim', 'temperatura_inicio', 'temperatura_fim',
    'frequencia_inicio', 'frequencia_fim', 'tensao_inicio', 'tensao_fim'
  )
ORDER BY ORDINAL_POSITION;
