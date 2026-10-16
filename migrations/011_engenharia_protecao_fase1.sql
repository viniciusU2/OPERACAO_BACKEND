-- ENGVI - Engenharia de Proteção, Controle e Automação
-- Fase 1: modelos, inventário, histórico de instalação, hardware e equipamentos protegidos.

CREATE TABLE IF NOT EXISTS modelo_ied (
    id_modelo_ied INT NOT NULL AUTO_INCREMENT,
    fabricante VARCHAR(100) NOT NULL,
    familia VARCHAR(100) NULL,
    modelo VARCHAR(100) NOT NULL,
    aplicacao VARCHAR(300) NULL,
    descricao TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_modelo_ied),
    UNIQUE KEY uq_modelo_ied_fabricante_modelo (fabricante, modelo),
    KEY ix_modelo_ied_fabricante (fabricante),
    KEY ix_modelo_ied_familia (familia),
    KEY ix_modelo_ied_modelo (modelo),
    KEY ix_modelo_ied_ativo (ativo),
    CONSTRAINT fk_modelo_ied_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_modelo_ied_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied (
    id_ied INT NOT NULL AUTO_INCREMENT,
    codigo_uuid VARCHAR(36) NOT NULL,
    tag_operacional VARCHAR(100) NOT NULL,
    id_ativo INT NOT NULL,
    id_modelo_ied INT NOT NULL,
    id_subestacao INT NOT NULL,
    id_funcao_operacao INT NULL,
    painel_instalacao VARCHAR(150) NOT NULL,
    numero_serie VARCHAR(150) NULL,
    codigo_produto VARCHAR(150) NULL,
    versao_hardware VARCHAR(100) NULL,
    versao_firmware VARCHAR(100) NULL,
    data_instalacao DATE NOT NULL,
    status_operacional VARCHAR(30) NOT NULL DEFAULT 'EM_OPERACAO',
    observacoes_tecnicas TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    versao INT NOT NULL DEFAULT 1,
    id_usuario_criacao INT NOT NULL,
    id_usuario_atualizacao INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied),
    UNIQUE KEY uq_ied_codigo_uuid (codigo_uuid),
    UNIQUE KEY uq_ied_tag_operacional (tag_operacional),
    UNIQUE KEY uq_ied_id_ativo (id_ativo),
    UNIQUE KEY uq_ied_numero_serie (numero_serie),
    KEY ix_ied_modelo (id_modelo_ied),
    KEY ix_ied_ativo_inventario (id_ativo),
    KEY ix_ied_subestacao (id_subestacao),
    KEY ix_ied_funcao_operacao (id_funcao_operacao),
    KEY ix_ied_localizacao (id_subestacao, id_funcao_operacao),
    KEY ix_ied_status (status_operacional),
    KEY ix_ied_firmware (versao_firmware),
    KEY ix_ied_ativo (ativo),
    CONSTRAINT fk_ied_modelo FOREIGN KEY (id_modelo_ied) REFERENCES modelo_ied (id_modelo_ied) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_ativo_inventario FOREIGN KEY (id_ativo) REFERENCES ativo (id_ativo) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_subestacao FOREIGN KEY (id_subestacao) REFERENCES subestacao (id_subestacao) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_funcao_operacao FOREIGN KEY (id_funcao_operacao) REFERENCES funcao_operacao (id_funcao_operacao) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_usuario_criacao FOREIGN KEY (id_usuario_criacao) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_usuario_atualizacao FOREIGN KEY (id_usuario_atualizacao) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_ied_status_operacional CHECK (status_operacional IN ('EM_OPERACAO','SOBRESSALENTE','EM_MANUTENCAO','RETIRADO','DESCARTADO'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_instalacao (
    id_ied_instalacao INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    id_subestacao INT NOT NULL,
    id_funcao_operacao INT NULL,
    painel_instalacao VARCHAR(150) NOT NULL,
    tipo_movimentacao VARCHAR(30) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NULL,
    motivo VARCHAR(300) NULL,
    observacoes TEXT NULL,
    id_usuario_registro INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_instalacao),
    KEY ix_ied_instalacao_ied (id_ied),
    KEY ix_ied_instalacao_subestacao (id_subestacao),
    KEY ix_ied_instalacao_funcao (id_funcao_operacao),
    KEY ix_ied_instalacao_periodo (id_ied, data_inicio, data_fim),
    CONSTRAINT fk_ied_instalacao_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ied_instalacao_subestacao FOREIGN KEY (id_subestacao) REFERENCES subestacao (id_subestacao) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_instalacao_funcao FOREIGN KEY (id_funcao_operacao) REFERENCES funcao_operacao (id_funcao_operacao) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_instalacao_usuario FOREIGN KEY (id_usuario_registro) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_ied_instalacao_tipo CHECK (tipo_movimentacao IN ('INSTALACAO','TRANSFERENCIA','SUBSTITUICAO','RETIRADA'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_modulo (
    id_ied_modulo INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    tipo_modulo VARCHAR(100) NOT NULL,
    slot VARCHAR(50) NULL,
    codigo_produto VARCHAR(150) NULL,
    numero_serie VARCHAR(150) NULL,
    versao_hardware VARCHAR(100) NULL,
    status_operacional VARCHAR(30) NOT NULL DEFAULT 'INSTALADO',
    data_instalacao DATE NULL,
    data_retirada DATE NULL,
    observacoes TEXT NULL,
    id_usuario_registro INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_modulo),
    KEY ix_ied_modulo_ied (id_ied),
    KEY ix_ied_modulo_numero_serie (numero_serie),
    KEY ix_ied_modulo_ied_slot (id_ied, slot),
    CONSTRAINT fk_ied_modulo_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ied_modulo_usuario FOREIGN KEY (id_usuario_registro) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_firmware_historico (
    id_ied_firmware_historico INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    versao_firmware VARCHAR(100) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NULL,
    motivo VARCHAR(300) NULL,
    id_os INT NULL,
    observacoes TEXT NULL,
    id_usuario_registro INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_firmware_historico),
    KEY ix_ied_firmware_ied (id_ied),
    KEY ix_ied_firmware_versao (versao_firmware),
    KEY ix_ied_firmware_os (id_os),
    KEY ix_ied_firmware_periodo (id_ied, data_inicio, data_fim),
    CONSTRAINT fk_ied_firmware_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ied_firmware_os FOREIGN KEY (id_os) REFERENCES ordem_servico (id_os) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_ied_firmware_usuario FOREIGN KEY (id_usuario_registro) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS ied_equipamento (
    id_ied_equipamento INT NOT NULL AUTO_INCREMENT,
    id_ied INT NOT NULL,
    id_ativo INT NOT NULL,
    principal BOOLEAN NOT NULL DEFAULT FALSE,
    data_inicio DATE NOT NULL,
    data_fim DATE NULL,
    observacoes TEXT NULL,
    id_usuario_registro INT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ied_equipamento),
    UNIQUE KEY uq_ied_equipamento_periodo (id_ied, id_ativo, data_inicio),
    KEY ix_ied_equipamento_ied (id_ied),
    KEY ix_ied_equipamento_ativo (id_ativo),
    KEY ix_ied_equipamento_ativo_periodo (id_ativo, data_inicio, data_fim),
    CONSTRAINT fk_ied_equipamento_ied FOREIGN KEY (id_ied) REFERENCES ied (id_ied) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ied_equipamento_ativo FOREIGN KEY (id_ativo) REFERENCES ativo (id_ativo) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ied_equipamento_usuario FOREIGN KEY (id_usuario_registro) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- Catálogo inicial solicitado. A inserção usa um usuário existente apenas para auditoria
-- e não cria registros se o banco ainda não possuir usuários.
INSERT INTO modelo_ied (fabricante, familia, modelo, aplicacao, descricao, ativo, id_usuario_criacao, id_usuario_atualizacao)
SELECT 'Siemens', 'SIPROTEC 5', seed.modelo, seed.aplicacao, 'Catálogo inicial da Engenharia de Proteção', TRUE, u.id, u.id
FROM (
    SELECT '7UT85' AS modelo, 'Proteção diferencial de transformadores' AS aplicacao UNION ALL
    SELECT '7SL87', 'Proteção diferencial e distância de linhas' UNION ALL
    SELECT '7VK87', 'Gerenciamento e proteção de disjuntores' UNION ALL
    SELECT '7KE85', 'Registro de perturbações e oscilografias' UNION ALL
    SELECT '7SJ85', 'Proteção de sobrecorrente e alimentadores'
) seed
JOIN (SELECT id FROM usuarios ORDER BY (role = 'admin') DESC, id LIMIT 1) u
LEFT JOIN modelo_ied existente ON existente.fabricante = 'Siemens' AND existente.modelo = seed.modelo
WHERE existente.id_modelo_ied IS NULL;

