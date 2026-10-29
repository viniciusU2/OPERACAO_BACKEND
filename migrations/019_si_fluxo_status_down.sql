-- ENGVI - Rollback da migração 019.
--
-- CUIDADO: remove a trilha de auditoria do fluxo de SI. Exporte antes:
--   SELECT * FROM si_historico;

DROP TABLE IF EXISTS si_numero_liberado;
DROP TABLE IF EXISTS si_historico;

ALTER TABLE solicitacao_intervencao
    DROP INDEX ix_si_status,
    DROP COLUMN status;
