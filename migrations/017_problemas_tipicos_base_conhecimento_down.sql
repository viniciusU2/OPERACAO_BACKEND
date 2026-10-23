-- ENGVI - Reversão da migração 017 (base de conhecimento de problemas típicos).
--
-- ATENÇÃO: remove as colunas de classificação/rastreabilidade e as listas
-- estruturadas. Os registros de `problema_tipico` NÃO são apagados; apenas
-- perdem os campos complementares.
--
-- Antes de executar, exporte a base:
--   mysqldump manutencao problema_tipico sintoma_problema causa_problema \
--     metodo_deteccao_problema acao_recomendada alarme_problema \
--     palavra_chave_problema instrumento_problema > backup_problemas_tipicos.sql

DROP TABLE IF EXISTS instrumento_problema;
DROP TABLE IF EXISTS palavra_chave_problema;
DROP TABLE IF EXISTS alarme_problema;

ALTER TABLE problema_tipico
    DROP INDEX IF EXISTS uq_problema_codigo,
    DROP INDEX IF EXISTS ix_problema_status_validacao,
    DROP INDEX IF EXISTS ix_problema_origem,
    DROP INDEX IF EXISTS ix_problema_risco;

ALTER TABLE problema_tipico
    DROP COLUMN IF EXISTS codigo,
    DROP COLUMN IF EXISTS risco_operacional,
    DROP COLUMN IF EXISTS condicao_intervencao,
    DROP COLUMN IF EXISTS requer_equipe_especializada,
    DROP COLUMN IF EXISTS alerta_seguranca,
    DROP COLUMN IF EXISTS referencias_tecnicas,
    DROP COLUMN IF EXISTS status_validacao,
    DROP COLUMN IF EXISTS origem_registro,
    DROP COLUMN IF EXISTS validado_por,
    DROP COLUMN IF EXISTS validado_em;

ALTER TABLE acao_recomendada
    MODIFY COLUMN tipo_acao ENUM('INSPECAO','ENSAIO','CORRECAO','SUBSTITUICAO','MONITORAMENTO','INVESTIGACAO')
        NOT NULL DEFAULT 'INVESTIGACAO';

ALTER TABLE metodo_deteccao_problema
    MODIFY COLUMN metodo VARCHAR(150) NOT NULL;
