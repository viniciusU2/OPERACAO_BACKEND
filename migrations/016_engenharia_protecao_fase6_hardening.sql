-- ENGVI - Engenharia de Proteção, Controle e Automação
-- Fase 6: segregação de funções, rollback e auditoria transversal.

ALTER TABLE solicitacao_alteracao
    ADD COLUMN IF NOT EXISTS id_usuario_implantador INT NULL AFTER id_usuario_aprovador,
    ADD COLUMN IF NOT EXISTS id_usuario_reversao INT NULL AFTER id_usuario_validador,
    ADD COLUMN IF NOT EXISTS id_configuracao_rollback INT NULL AFTER id_configuracao_resultante,
    ADD COLUMN IF NOT EXISTS data_reversao DATE NULL AFTER data_validacao,
    ADD COLUMN IF NOT EXISTS evidencia_implantacao TEXT NULL AFTER resultado_validacao;

ALTER TABLE solicitacao_alteracao
    ADD KEY IF NOT EXISTS ix_solicitacao_alteracao_implantador (id_usuario_implantador),
    ADD KEY IF NOT EXISTS ix_solicitacao_alteracao_reversao (id_usuario_reversao),
    ADD KEY IF NOT EXISTS ix_solicitacao_alteracao_config_rollback (id_configuracao_rollback);

ALTER TABLE solicitacao_alteracao
    DROP CONSTRAINT IF EXISTS ck_solicitacao_alteracao_status;

ALTER TABLE solicitacao_alteracao
    ADD CONSTRAINT ck_solicitacao_alteracao_status CHECK (
        status IN ('RASCUNHO','SUBMETIDA','EM_ANALISE','APROVADA','REJEITADA','IMPLANTADA',
                   'EM_VALIDACAO','VALIDADA','NAO_VALIDADA','CONCLUIDA','CANCELADA','REVERTIDA')
    );

ALTER TABLE solicitacao_alteracao
    ADD CONSTRAINT fk_solicitacao_alteracao_implantador
        FOREIGN KEY (id_usuario_implantador) REFERENCES usuarios (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_solicitacao_alteracao_reversao
        FOREIGN KEY (id_usuario_reversao) REFERENCES usuarios (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_solicitacao_alteracao_config_rollback
        FOREIGN KEY (id_configuracao_rollback) REFERENCES ied_configuracao (id_ied_configuracao) ON DELETE SET NULL;

ALTER TABLE alteracao_historico
    DROP CONSTRAINT IF EXISTS ck_alteracao_historico_acao;

ALTER TABLE alteracao_historico
    ADD CONSTRAINT ck_alteracao_historico_acao CHECK (
        acao IN ('CRIACAO','ATUALIZACAO','SUBMISSAO','ANALISE','APROVACAO','REJEICAO',
                 'IMPLANTACAO','INICIO_VALIDACAO','VALIDACAO','CONCLUSAO',
                 'REJEICAO_VALIDACAO','CANCELAMENTO','REVERSAO')
    );

CREATE TABLE IF NOT EXISTS engenharia_protecao_auditoria (
    id_engenharia_protecao_auditoria INT NOT NULL AUTO_INCREMENT,
    id_usuario INT NULL,
    acao VARCHAR(30) NOT NULL,
    metodo VARCHAR(10) NOT NULL,
    caminho VARCHAR(500) NOT NULL,
    recurso VARCHAR(100) NULL,
    id_recurso VARCHAR(100) NULL,
    status_http INT NOT NULL,
    endereco_ip VARCHAR(64) NULL,
    user_agent VARCHAR(300) NULL,
    detalhes TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_engenharia_protecao_auditoria),
    KEY ix_engenharia_protecao_auditoria_id_usuario (id_usuario),
    KEY ix_engenharia_protecao_auditoria_acao (acao),
    KEY ix_engenharia_protecao_auditoria_recurso_simples (recurso),
    KEY ix_engenharia_protecao_auditoria_status_http (status_http),
    KEY ix_eng_protecao_auditoria_data (criado_em),
    KEY ix_eng_protecao_auditoria_usuario_data (id_usuario, criado_em),
    KEY ix_eng_protecao_auditoria_recurso (recurso, id_recurso),
    CONSTRAINT fk_engenharia_protecao_auditoria_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
