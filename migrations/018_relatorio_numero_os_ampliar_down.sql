-- ENGVI - Rollback da migração 018.
--
-- Volta numero_os/numero_apr para VARCHAR(100). Só execute depois de conferir
-- que nenhum registro tem valor acima de 100 caracteres:
--   SELECT id_relatorio_manutencao, CHAR_LENGTH(numero_os)
--   FROM relatorio_manutencao WHERE CHAR_LENGTH(numero_os) > 100;

ALTER TABLE relatorio_manutencao
    MODIFY COLUMN numero_os VARCHAR(100) NULL,
    MODIFY COLUMN numero_apr VARCHAR(100) NULL;
