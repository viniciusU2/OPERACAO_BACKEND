-- Rollback da fase 6. Preserva os registros e converte estados novos.

UPDATE solicitacao_alteracao SET status = 'SUBMETIDA' WHERE status = 'EM_ANALISE';
UPDATE solicitacao_alteracao SET status = 'IMPLANTADA' WHERE status = 'EM_VALIDACAO';
UPDATE solicitacao_alteracao SET status = 'VALIDADA' WHERE status = 'CONCLUIDA';
UPDATE solicitacao_alteracao SET status = 'CANCELADA' WHERE status = 'REVERTIDA';

DELETE FROM alteracao_historico
WHERE acao IN ('ANALISE','INICIO_VALIDACAO','CONCLUSAO','REVERSAO');

ALTER TABLE alteracao_historico
    DROP CONSTRAINT IF EXISTS ck_alteracao_historico_acao;

ALTER TABLE alteracao_historico
    ADD CONSTRAINT ck_alteracao_historico_acao CHECK (
        acao IN ('CRIACAO','ATUALIZACAO','SUBMISSAO','APROVACAO','REJEICAO','IMPLANTACAO',
                 'VALIDACAO','REJEICAO_VALIDACAO','CANCELAMENTO')
    );

DROP TABLE IF EXISTS engenharia_protecao_auditoria;

ALTER TABLE solicitacao_alteracao
    DROP CONSTRAINT IF EXISTS ck_solicitacao_alteracao_status,
    DROP FOREIGN KEY IF EXISTS fk_solicitacao_alteracao_implantador,
    DROP FOREIGN KEY IF EXISTS fk_solicitacao_alteracao_reversao,
    DROP FOREIGN KEY IF EXISTS fk_solicitacao_alteracao_config_rollback,
    DROP INDEX IF EXISTS ix_solicitacao_alteracao_implantador,
    DROP INDEX IF EXISTS ix_solicitacao_alteracao_reversao,
    DROP INDEX IF EXISTS ix_solicitacao_alteracao_config_rollback,
    DROP COLUMN IF EXISTS id_usuario_implantador,
    DROP COLUMN IF EXISTS id_usuario_reversao,
    DROP COLUMN IF EXISTS id_configuracao_rollback,
    DROP COLUMN IF EXISTS data_reversao,
    DROP COLUMN IF EXISTS evidencia_implantacao;

ALTER TABLE solicitacao_alteracao
    ADD CONSTRAINT ck_solicitacao_alteracao_status CHECK (
        status IN ('RASCUNHO','SUBMETIDA','APROVADA','REJEITADA','IMPLANTADA',
                   'VALIDADA','NAO_VALIDADA','CANCELADA')
    );
