-- ENGVI - Engenharia de Proteção, Controle e Automação
-- Fase 2: funções ANSI, parâmetros, grupos de ajuste, configurações/backups,
-- arquivos versionados (SHA-256) e validações de backup.
-- Idempotente: pode ser reaplicada com segurança.

CREATE TABLE IF NOT EXISTS funcao_ansi (
    id_funcao_ansi INT NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(20) NOT NULL,
    nome VARCHAR(150) NOT NULL,
    categoria VARCHAR(60) NULL,
    descricao TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_funcao_ansi),
    UNIQUE KEY uq_funcao_ansi_codigo (codigo),
    KEY ix_funcao_ansi_categoria (categoria),
    KEY ix_funcao_ansi_ativo (ativo),
    CONSTRAINT fk_funcao_ansi_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_funcao_ansi_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS parametro_definicao (
    id_parametro_definicao INT NOT NULL AUTO_INCREMENT,
    id_funcao_ansi INT NOT NULL,
    codigo VARCHAR(60) NOT NULL,
    nome VARCHAR(150) NOT NULL,
    unidade VARCHAR(30) NULL,
    tipo_dado VARCHAR(20) NOT NULL DEFAULT 'NUMERICO',
    identificador_fabricante VARCHAR(100) NULL,
    valor_minimo VARCHAR(60) NULL,
    valor_maximo VARCHAR(60) NULL,
    descricao TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_parametro_definicao),
    UNIQUE KEY uq_parametro_definicao_funcao_codigo (id_funcao_ansi, codigo),
    KEY ix_parametro_definicao_funcao (id_funcao_ansi),
    KEY ix_parametro_definicao_ativo (ativo),
    CONSTRAINT ck_parametro_definicao_tipo_dado CHECK (tipo_dado IN ('NUMERICO','TEMPO','BOOLEANO','TEXTO')),
    CONSTRAINT fk_parametro_definicao_funcao FOREIGN KEY (id_funcao_ansi) REFERENCES funcao_ansi (id_funcao_ansi) ON DELETE CASCADE,
    CONSTRAINT fk_parametro_definicao_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_parametro_definicao_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_funcao (
    id_ied_funcao INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    id_funcao_ansi INT NOT NULL,
    instancia INT NOT NULL DEFAULT 1,
    habilitada BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes TEXT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_funcao),
    UNIQUE KEY uq_ied_funcao_instancia (id_ied, id_funcao_ansi, instancia),
    KEY ix_ied_funcao_ied (id_ied),
    KEY ix_ied_funcao_funcao (id_funcao_ansi),
    CONSTRAINT fk_ied_funcao_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_funcao_funcao FOREIGN KEY (id_funcao_ansi) REFERENCES funcao_ansi (id_funcao_ansi) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_funcao_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_funcao_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_grupo_ajuste (
    id_ied_grupo_ajuste INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    numero INT NOT NULL,
    nome VARCHAR(100) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    descricao TEXT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_grupo_ajuste),
    UNIQUE KEY uq_ied_grupo_ajuste_numero (id_ied, numero),
    KEY ix_ied_grupo_ajuste_ied (id_ied),
    CONSTRAINT fk_ied_grupo_ajuste_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_grupo_ajuste_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_grupo_ajuste_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS config_parametro (
    id_config_parametro INT NOT NULL AUTO_INCREMENT,
    id_ied_grupo_ajuste INT NOT NULL,
    id_parametro_definicao INT NOT NULL,
    valor VARCHAR(255) NOT NULL,
    ajustado_em DATE NULL,
    observacoes TEXT NULL,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_config_parametro),
    UNIQUE KEY uq_config_parametro_grupo_parametro (id_ied_grupo_ajuste, id_parametro_definicao),
    KEY ix_config_parametro_grupo (id_ied_grupo_ajuste),
    KEY ix_config_parametro_parametro (id_parametro_definicao),
    CONSTRAINT fk_config_parametro_grupo FOREIGN KEY (id_ied_grupo_ajuste) REFERENCES ied_grupo_ajuste (id_ied_grupo_ajuste) ON DELETE CASCADE,
    CONSTRAINT fk_config_parametro_parametro FOREIGN KEY (id_parametro_definicao) REFERENCES parametro_definicao (id_parametro_definicao) ON DELETE CASCADE,
    CONSTRAINT fk_config_parametro_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_config_parametro_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS arquivo (
    id_arquivo INT NOT NULL AUTO_INCREMENT,
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    caminho VARCHAR(500) NOT NULL,
    tamanho_bytes INT NOT NULL,
    mime_type VARCHAR(150) NULL,
    extensao VARCHAR(20) NULL,
    sha256 VARCHAR(64) NOT NULL,
    categoria VARCHAR(40) NOT NULL DEFAULT 'OUTRO',
    descricao TEXT NULL,
    id_usuario_upload INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_arquivo),
    UNIQUE KEY uq_arquivo_nome_armazenado (nome_armazenado),
    KEY ix_arquivo_sha256 (sha256),
    KEY ix_arquivo_categoria (categoria),
    CONSTRAINT fk_arquivo_usuario_upload FOREIGN KEY (id_usuario_upload) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_configuracao (
    id_ied_configuracao INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    versao INT NOT NULL,
    rotulo VARCHAR(150) NOT NULL,
    motivo VARCHAR(40) NOT NULL DEFAULT 'OUTRO',
    status_validacao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    versao_digsi VARCHAR(60) NULL,
    versao_firmware VARCHAR(100) NULL,
    data_coleta DATE NOT NULL,
    id_grupo_ajuste INT NULL,
    id_os INT NULL,
    hash_configuracao VARCHAR(64) NULL,
    observacoes TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario_coleta INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_configuracao),
    UNIQUE KEY uq_ied_configuracao_versao (id_ied, versao),
    KEY ix_ied_configuracao_ied_data (id_ied, data_coleta),
    KEY ix_ied_configuracao_status (status_validacao),
    KEY ix_ied_configuracao_grupo (id_grupo_ajuste),
    KEY ix_ied_configuracao_os (id_os),
    CONSTRAINT ck_ied_configuracao_motivo CHECK (motivo IN ('BACKUP_PERIODICO','ALTERACAO_AJUSTE','PRE_MANUTENCAO','POS_MANUTENCAO','POS_FIRMWARE','OUTRO')),
    CONSTRAINT ck_ied_configuracao_status_validacao CHECK (status_validacao IN ('PENDENTE','VALIDADA','REJEITADA')),
    CONSTRAINT fk_ied_configuracao_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE,
    CONSTRAINT fk_ied_configuracao_grupo FOREIGN KEY (id_grupo_ajuste) REFERENCES ied_grupo_ajuste (id_ied_grupo_ajuste) ON DELETE SET NULL,
    CONSTRAINT fk_ied_configuracao_os FOREIGN KEY (id_os) REFERENCES ordem_servico (id_os) ON DELETE SET NULL,
    CONSTRAINT fk_ied_configuracao_usuario_coleta FOREIGN KEY (id_usuario_coleta) REFERENCES usuarios (id) ON DELETE RESTRICT,
    CONSTRAINT fk_ied_configuracao_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS configuracao_arquivo (
    id_configuracao_arquivo INT NOT NULL AUTO_INCREMENT,
    id_ied_configuracao INT NOT NULL,
    id_arquivo INT NOT NULL,
    papel VARCHAR(30) NOT NULL DEFAULT 'PRINCIPAL',
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_configuracao_arquivo),
    UNIQUE KEY uq_configuracao_arquivo (id_ied_configuracao, id_arquivo),
    KEY ix_configuracao_arquivo_config (id_ied_configuracao),
    KEY ix_configuracao_arquivo_arquivo (id_arquivo),
    CONSTRAINT ck_configuracao_arquivo_papel CHECK (papel IN ('PRINCIPAL','EXPORT_PARAMETROS','SCL','DOCUMENTO','COMPLEMENTAR')),
    CONSTRAINT fk_configuracao_arquivo_config FOREIGN KEY (id_ied_configuracao) REFERENCES ied_configuracao (id_ied_configuracao) ON DELETE CASCADE,
    CONSTRAINT fk_configuracao_arquivo_arquivo FOREIGN KEY (id_arquivo) REFERENCES arquivo (id_arquivo) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_backup_validacao (
    id_ied_backup_validacao INT NOT NULL AUTO_INCREMENT,
    id_ied_configuracao INT NOT NULL,
    resultado VARCHAR(20) NOT NULL,
    observacoes TEXT NULL,
    id_usuario_validacao INT NOT NULL,
    data_validacao DATE NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_backup_validacao),
    KEY ix_ied_backup_validacao_config (id_ied_configuracao),
    CONSTRAINT ck_ied_backup_validacao_resultado CHECK (resultado IN ('APROVADO','REPROVADO')),
    CONSTRAINT fk_ied_backup_validacao_config FOREIGN KEY (id_ied_configuracao) REFERENCES ied_configuracao (id_ied_configuracao) ON DELETE CASCADE,
    CONSTRAINT fk_ied_backup_validacao_usuario FOREIGN KEY (id_usuario_validacao) REFERENCES usuarios (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
