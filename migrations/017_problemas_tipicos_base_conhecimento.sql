-- ENGVI - Base de conhecimento de problemas típicos de subestações
-- Fase 1: identificação estável, classificação técnica, rastreabilidade e
-- listas estruturadas (alarmes, palavras-chave e instrumentos).
--
-- Execução: idempotente. Pode ser aplicada mais de uma vez com segurança.
-- Requer que as tabelas de `003_problemas_tipicos.sql` já existam (o
-- `Base.metadata.create_all` do backend garante isso na subida).

-- ---------------------------------------------------------------------------
-- 1. Identificação estável do problema (chave natural da seed)
-- ---------------------------------------------------------------------------
ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS codigo VARCHAR(80) NULL AFTER id_problema;

-- Registros anteriores à base de conhecimento recebem um código legado
-- determinístico, sem colidir com os códigos da seed (prefixo BDC-).
UPDATE problema_tipico
   SET codigo = CONCAT('LEGADO-', id_problema)
 WHERE codigo IS NULL OR codigo = '';

ALTER TABLE problema_tipico
    MODIFY COLUMN codigo VARCHAR(80) NOT NULL;

ALTER TABLE problema_tipico
    ADD UNIQUE KEY IF NOT EXISTS uq_problema_codigo (codigo);

-- ---------------------------------------------------------------------------
-- 2. Classificação técnica, risco e rastreabilidade
-- ---------------------------------------------------------------------------
ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS risco_operacional ENUM('BAIXO','MEDIO','ALTO') NULL AFTER efeito_falha;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS condicao_intervencao ENUM('ENERGIZADO','DESENERGIZADO','INDIFERENTE') NULL AFTER requer_desligamento;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS requer_equipe_especializada BOOLEAN NOT NULL DEFAULT FALSE AFTER condicao_intervencao;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS alerta_seguranca TEXT NULL AFTER requer_equipe_especializada;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS referencias_tecnicas TEXT NULL AFTER alerta_seguranca;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS status_validacao ENUM('PENDENTE','EM_REVISAO','VALIDADO','REPROVADO')
        NOT NULL DEFAULT 'PENDENTE' AFTER referencias_tecnicas;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS origem_registro ENUM('REFERENCIA_TECNICA','OCORRENCIA_REAL')
        NOT NULL DEFAULT 'REFERENCIA_TECNICA' AFTER status_validacao;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS validado_por VARCHAR(150) NULL AFTER origem_registro;

ALTER TABLE problema_tipico
    ADD COLUMN IF NOT EXISTS validado_em DATETIME NULL AFTER validado_por;

ALTER TABLE problema_tipico
    ADD KEY IF NOT EXISTS ix_problema_status_validacao (status_validacao);

ALTER TABLE problema_tipico
    ADD KEY IF NOT EXISTS ix_problema_origem (origem_registro);

ALTER TABLE problema_tipico
    ADD KEY IF NOT EXISTS ix_problema_risco (risco_operacional);

-- ---------------------------------------------------------------------------
-- 3. Listas estruturadas complementares
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alarme_problema (
    id INT NOT NULL AUTO_INCREMENT,
    id_problema INT NOT NULL,
    alarme VARCHAR(300) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_alarme_problema_problema (id_problema),
    CONSTRAINT fk_alarme_problema_problema FOREIGN KEY (id_problema)
        REFERENCES problema_tipico (id_problema) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS palavra_chave_problema (
    id INT NOT NULL AUTO_INCREMENT,
    id_problema INT NOT NULL,
    palavra_chave VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_palavra_chave_problema_problema (id_problema),
    KEY ix_palavra_chave_problema_valor (palavra_chave),
    CONSTRAINT fk_palavra_chave_problema_problema FOREIGN KEY (id_problema)
        REFERENCES problema_tipico (id_problema) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS instrumento_problema (
    id INT NOT NULL AUTO_INCREMENT,
    id_problema INT NOT NULL,
    instrumento VARCHAR(150) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_instrumento_problema_problema (id_problema),
    CONSTRAINT fk_instrumento_problema_problema FOREIGN KEY (id_problema)
        REFERENCES problema_tipico (id_problema) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- ---------------------------------------------------------------------------
-- 4. Ações preventivas passam a ser registradas na mesma tabela de ações
-- ---------------------------------------------------------------------------
ALTER TABLE acao_recomendada
    MODIFY COLUMN tipo_acao ENUM('INSPECAO','ENSAIO','CORRECAO','SUBSTITUICAO','MONITORAMENTO','INVESTIGACAO','PREVENCAO')
        NOT NULL DEFAULT 'INVESTIGACAO';

-- ---------------------------------------------------------------------------
-- 5. Procedimentos de diagnóstico podem descrever passos completos
-- ---------------------------------------------------------------------------
ALTER TABLE metodo_deteccao_problema
    MODIFY COLUMN metodo VARCHAR(400) NOT NULL;
