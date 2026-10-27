-- ENGVI - Relatórios de manutenção
-- Amplia numero_os e numero_apr para 500 caracteres.
--
-- Motivo: um relatório pode reunir dezenas de OS/APR (ex.:
-- "BJD-1272, 1273, ... 1425-2026"), passando dos 100 caracteres atuais e
-- derrubando o upload com:
--   (1406, "Data too long for column 'numero_os' at row 1")

ALTER TABLE relatorio_manutencao
    MODIFY COLUMN numero_os VARCHAR(500) NULL,
    MODIFY COLUMN numero_apr VARCHAR(500) NULL;
