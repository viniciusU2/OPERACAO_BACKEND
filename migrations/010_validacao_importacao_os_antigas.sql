-- Fila de validação das OS históricas antes do cadastro/ajuste definitivo.
-- Os 146 registros iniciais são carregados de forma idempotente pela API.

CREATE TABLE IF NOT EXISTS os_validacao_importacao (
    id_validacao INT NOT NULL AUTO_INCREMENT,
    chave_origem VARCHAR(190) NOT NULL,
    tipo_registro VARCHAR(30) NOT NULL,
    fonte VARCHAR(80) NULL,
    linha_controle INT NULL,
    numero_os VARCHAR(30) NOT NULL,
    id_os_destino INT NULL,
    bloqueios LONGTEXT NOT NULL,
    avisos LONGTEXT NOT NULL,
    contexto LONGTEXT NOT NULL,
    dados_os LONGTEXT NOT NULL,
    status_validacao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    observacao_validacao TEXT NULL,
    validado_por VARCHAR(120) NULL,
    erro_envio TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    validado_em DATETIME NULL,
    enviado_em DATETIME NULL,
    PRIMARY KEY (id_validacao),
    UNIQUE KEY uq_os_validacao_chave_origem (chave_origem),
    KEY idx_os_validacao_status (status_validacao),
    KEY idx_os_validacao_numero (numero_os),
    KEY idx_os_validacao_tipo (tipo_registro),
    KEY idx_os_validacao_destino (id_os_destino)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
