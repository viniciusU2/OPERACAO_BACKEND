-- ENGVI - Engenharia de Proteção, Controle e Automação
-- Fase 5: ocorrências e indicadores (eventos, oscilografias COMTRADE, relatórios e auditoria).
-- Idempotente: pode ser reaplicada com segurança.

-- --------------------------------------------------------------------------- --
-- Ocorrências (eventos) e auditoria
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS ied_ocorrencia (
    id_ied_ocorrencia INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    numero INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'ALARME',
    severidade VARCHAR(20) NOT NULL DEFAULT 'MEDIA',
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descricao TEXT NULL,
    causa_provavel TEXT NULL,
    acao_tomada TEXT NULL,
    id_os INT NULL,
    id_usuario_registro INT NULL,
    id_usuario_encerramento INT NULL,
    data_encerramento DATETIME NULL,
    observacoes TEXT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_ocorrencia),
    UNIQUE KEY uq_ied_ocorrencia_numero (id_ied, numero),
    KEY ix_ied_ocorrencia_ied (id_ied),
    KEY ix_ied_ocorrencia_tipo (tipo),
    KEY ix_ied_ocorrencia_severidade (severidade),
    KEY ix_ied_ocorrencia_status (status),
    KEY ix_ied_ocorrencia_os (id_os),
    KEY ix_ied_ocorrencia_registro (id_usuario_registro),
    KEY ix_ied_ocorrencia_encerramento (id_usuario_encerramento),
    CONSTRAINT ck_ied_ocorrencia_tipo CHECK (tipo IN ('DISPARO','REARME','ATUACAO_PROTECAO','ALARME','FALHA_COMUNICACAO','SOBRECORRENTE','SOBRETENSAO','SUBTENSAO','FALTA_ENERGIA','OSCILACAO','OUTRO')),
    CONSTRAINT ck_ied_ocorrencia_severidade CHECK (severidade IN ('BAIXA','MEDIA','ALTA','CRITICA')),
    CONSTRAINT ck_ied_ocorrencia_status CHECK (status IN ('ABERTA','EM_ANALISE','ENCERRADA','CANCELADA')),
    CONSTRAINT fk_ied_ocorrencia_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_ocorrencia_os FOREIGN KEY (id_os) REFERENCES ordem_servico (id_os) ON DELETE SET NULL,
    CONSTRAINT fk_ied_ocorrencia_registro FOREIGN KEY (id_usuario_registro) REFERENCES usuarios (id) ON DELETE SET NULL,
    CONSTRAINT fk_ied_ocorrencia_encerramento FOREIGN KEY (id_usuario_encerramento) REFERENCES usuarios (id) ON DELETE SET NULL,
    CONSTRAINT fk_ied_ocorrencia_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_ocorrencia_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_ocorrencia_arquivo (
    id_ied_ocorrencia_arquivo INT NOT NULL AUTO_INCREMENT,
    id_ied_ocorrencia INT NOT NULL,
    id_arquivo INT NOT NULL,
    descricao TEXT NULL,
    id_usuario_upload INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_ocorrencia_arquivo),
    UNIQUE KEY uq_ied_ocorrencia_arquivo (id_ied_ocorrencia, id_arquivo),
    KEY ix_ied_ocorrencia_arquivo_ocorrencia (id_ied_ocorrencia),
    KEY ix_ied_ocorrencia_arquivo_arquivo (id_arquivo),
    CONSTRAINT fk_ied_ocorrencia_arquivo_ocorrencia FOREIGN KEY (id_ied_ocorrencia) REFERENCES ied_ocorrencia (id_ied_ocorrencia) ON DELETE CASCADE,
    CONSTRAINT fk_ied_ocorrencia_arquivo_arquivo FOREIGN KEY (id_arquivo) REFERENCES arquivo (id_arquivo) ON DELETE CASCADE,
    CONSTRAINT fk_ied_ocorrencia_arquivo_usuario FOREIGN KEY (id_usuario_upload) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_ocorrencia_historico (
    id_ied_ocorrencia_historico INT NOT NULL AUTO_INCREMENT,
    id_ied_ocorrencia INT NOT NULL,
    id_ied INT NOT NULL,
    acao VARCHAR(30) NOT NULL,
    descricao TEXT NULL,
    id_usuario INT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_ocorrencia_historico),
    KEY ix_ied_ocorrencia_historico_ocorrencia (id_ied_ocorrencia),
    KEY ix_ied_ocorrencia_historico_ied (id_ied),
    KEY ix_ied_ocorrencia_historico_acao (acao),
    KEY ix_ied_ocorrencia_historico_usuario (id_usuario),
    CONSTRAINT ck_ied_ocorrencia_historico_acao CHECK (acao IN ('CRIACAO','ATUALIZACAO','ANEXO','REMOCAO_ARQUIVO','ENCERRAMENTO','CANCELAMENTO','REABERTURA','OSCILOGRAFIA','RELATORIO')),
    CONSTRAINT fk_ied_ocorrencia_historico_ocorrencia FOREIGN KEY (id_ied_ocorrencia) REFERENCES ied_ocorrencia (id_ied_ocorrencia) ON DELETE CASCADE,
    CONSTRAINT fk_ied_ocorrencia_historico_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_ocorrencia_historico_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- --------------------------------------------------------------------------- --
-- Oscilografias (COMTRADE)
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS ied_oscilografia (
    id_ied_oscilografia INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    id_ocorrencia INT NULL,
    numero INT NOT NULL,
    nome VARCHAR(150) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'OSCILOGRAFIA',
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duracao_ms INT NULL,
    frequencia_amostragem_hz INT NULL,
    numero_canais INT NULL,
    origem VARCHAR(150) NULL,
    observacoes TEXT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_oscilografia),
    UNIQUE KEY uq_ied_oscilografia_numero (id_ied, numero),
    KEY ix_ied_oscilografia_ied (id_ied),
    KEY ix_ied_oscilografia_ocorrencia (id_ocorrencia),
    KEY ix_ied_oscilografia_tipo (tipo),
    CONSTRAINT ck_ied_oscilografia_tipo CHECK (tipo IN ('OSCILOGRAFIA','PERTURBACAO','RELIGAMENTO','FALTA','OUTRO')),
    CONSTRAINT fk_ied_oscilografia_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_oscilografia_ocorrencia FOREIGN KEY (id_ocorrencia) REFERENCES ied_ocorrencia (id_ied_ocorrencia) ON DELETE SET NULL,
    CONSTRAINT fk_ied_oscilografia_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_oscilografia_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_oscilografia_arquivo (
    id_ied_oscilografia_arquivo INT NOT NULL AUTO_INCREMENT,
    id_ied_oscilografia INT NOT NULL,
    id_arquivo INT NOT NULL,
    descricao TEXT NULL,
    id_usuario_upload INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_oscilografia_arquivo),
    UNIQUE KEY uq_ied_oscilografia_arquivo (id_ied_oscilografia, id_arquivo),
    KEY ix_ied_oscilografia_arquivo_oscilografia (id_ied_oscilografia),
    KEY ix_ied_oscilografia_arquivo_arquivo (id_arquivo),
    CONSTRAINT fk_ied_oscilografia_arquivo_oscilografia FOREIGN KEY (id_ied_oscilografia) REFERENCES ied_oscilografia (id_ied_oscilografia) ON DELETE CASCADE,
    CONSTRAINT fk_ied_oscilografia_arquivo_arquivo FOREIGN KEY (id_arquivo) REFERENCES arquivo (id_arquivo) ON DELETE CASCADE,
    CONSTRAINT fk_ied_oscilografia_arquivo_usuario FOREIGN KEY (id_usuario_upload) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- --------------------------------------------------------------------------- --
-- Relatórios (documentos)
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS ied_relatorio (
    id_ied_relatorio INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    id_ocorrencia INT NULL,
    numero INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'OCORRENCIA',
    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
    data_emissao DATE NULL,
    periodo_inicio DATE NULL,
    periodo_fim DATE NULL,
    resumo TEXT NULL,
    observacoes TEXT NULL,
    id_usuario_emissao INT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_relatorio),
    UNIQUE KEY uq_ied_relatorio_numero (id_ied, numero),
    KEY ix_ied_relatorio_ied (id_ied),
    KEY ix_ied_relatorio_ocorrencia (id_ocorrencia),
    KEY ix_ied_relatorio_tipo (tipo),
    KEY ix_ied_relatorio_status (status),
    KEY ix_ied_relatorio_emissao (id_usuario_emissao),
    CONSTRAINT ck_ied_relatorio_tipo CHECK (tipo IN ('OCORRENCIA','INSPECAO','ENSAIO','MANUTENCAO','ANALISE','PERIODICO','OUTRO')),
    CONSTRAINT ck_ied_relatorio_status CHECK (status IN ('RASCUNHO','EMITIDO','APROVADO','CANCELADO')),
    CONSTRAINT fk_ied_relatorio_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_relatorio_ocorrencia FOREIGN KEY (id_ocorrencia) REFERENCES ied_ocorrencia (id_ied_ocorrencia) ON DELETE SET NULL,
    CONSTRAINT fk_ied_relatorio_emissao FOREIGN KEY (id_usuario_emissao) REFERENCES usuarios (id) ON DELETE SET NULL,
    CONSTRAINT fk_ied_relatorio_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_relatorio_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_relatorio_arquivo (
    id_ied_relatorio_arquivo INT NOT NULL AUTO_INCREMENT,
    id_ied_relatorio INT NOT NULL,
    id_arquivo INT NOT NULL,
    descricao TEXT NULL,
    id_usuario_upload INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_relatorio_arquivo),
    UNIQUE KEY uq_ied_relatorio_arquivo (id_ied_relatorio, id_arquivo),
    KEY ix_ied_relatorio_arquivo_relatorio (id_ied_relatorio),
    KEY ix_ied_relatorio_arquivo_arquivo (id_arquivo),
    CONSTRAINT fk_ied_relatorio_arquivo_relatorio FOREIGN KEY (id_ied_relatorio) REFERENCES ied_relatorio (id_ied_relatorio) ON DELETE CASCADE,
    CONSTRAINT fk_ied_relatorio_arquivo_arquivo FOREIGN KEY (id_arquivo) REFERENCES arquivo (id_arquivo) ON DELETE CASCADE,
    CONSTRAINT fk_ied_relatorio_arquivo_usuario FOREIGN KEY (id_usuario_upload) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
