-- ENGVI - Migração 019: fluxo de status das Solicitações de Intervenção (SI).
--
-- Cria a coluna `status` (rito novo) e a trilha de auditoria `si_historico`.
-- As SIs existentes são migradas para PROGRAMADA/CONCLUIDA/ENCERRADA,
-- preservando o que já estava registrado. Nenhuma vira RASCUNHO.
--
-- Status usados a partir de agora:
--   RASCUNHO | ENVIADA | REJEITADA | APROVADA | CANCELADA
--   PROGRAMADA | CONCLUIDA | ENCERRADA   (herdados, somente leitura)

ALTER TABLE solicitacao_intervencao
    ADD COLUMN status VARCHAR(30) NULL,
    ADD INDEX ix_si_status (status);

CREATE TABLE IF NOT EXISTS si_historico (
    id_historico INT AUTO_INCREMENT PRIMARY KEY,
    id_si INT NOT NULL,
    acao VARCHAR(30) NOT NULL,
    status_anterior VARCHAR(30) NULL,
    status_novo VARCHAR(30) NOT NULL,
    observacao TEXT NULL,
    usuario_id INT NULL,
    usuario_nome VARCHAR(200) NOT NULL,
    usuario_perfil VARCHAR(30) NULL,
    criado_em DATETIME NOT NULL,
    INDEX idx_si_historico_si (id_si),
    CONSTRAINT fk_si_historico_si
        FOREIGN KEY (id_si) REFERENCES solicitacao_intervencao(id_si)
        ON DELETE CASCADE,
    CONSTRAINT fk_si_historico_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE SET NULL
);

-- Números devolvidos por exclusão de SI: o próximo cadastro da sigla
-- reaproveita o menor número livre em vez de pular para o final.
CREATE TABLE IF NOT EXISTS si_numero_liberado (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sigla VARCHAR(30) NOT NULL,
    ano INT NOT NULL,
    numero INT NOT NULL,
    liberado_em DATETIME NOT NULL,
    UNIQUE KEY uq_si_numero_liberado (sigla, ano, numero)
);

-- Migra o status das SIs que já existiam.
UPDATE solicitacao_intervencao
   SET status = CASE
         WHEN UPPER(COALESCE(status_operacao, '')) IN ('CONCLUIDA', 'ENCERRADA')
              THEN UPPER(status_operacao)
         WHEN UPPER(COALESCE(status_manutencao, '')) IN ('CONCLUIDA', 'ENCERRADA')
              THEN UPPER(status_manutencao)
         WHEN UPPER(COALESCE(status_operacao, '')) = 'PROGRAMADA'
              OR UPPER(COALESCE(status_manutencao, '')) = 'PROGRAMADA'
              THEN 'PROGRAMADA'
         ELSE 'RASCUNHO'
       END
 WHERE status IS NULL OR TRIM(status) = '';

-- Registra a origem das SIs migradas.
INSERT INTO si_historico
    (id_si, acao, status_anterior, status_novo, observacao,
     usuario_id, usuario_nome, usuario_perfil, criado_em)
SELECT s.id_si, 'MIGRACAO', NULL, s.status,
       'SI registrada no sistema.',
       NULL, COALESCE(NULLIF(s.emissor, ''), 'Sistema'), NULL, COALESCE(s.criado_em, NOW())
  FROM solicitacao_intervencao s
 WHERE NOT EXISTS (SELECT 1 FROM si_historico h WHERE h.id_si = s.id_si);
