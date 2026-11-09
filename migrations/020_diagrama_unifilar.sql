-- 020: diagrama unifilar interativo por subestacao (Etapa 2 - persistencia)
-- Idempotente: CREATE IF NOT EXISTS + INSERT IGNORE com guarda.
-- Tabelas: catalogo de tipos, diagrama, componente, conexao e terminal.

CREATE TABLE IF NOT EXISTS unifilar_tipo_componente (
  tipo VARCHAR(40) NOT NULL PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  categoria VARCHAR(20) NOT NULL,
  aceita_ativo TINYINT(1) NOT NULL DEFAULT 0,
  max_por_terminal INT NOT NULL DEFAULT 1,
  largura FLOAT NOT NULL DEFAULT 40,
  altura FLOAT NOT NULL DEFAULT 72
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO unifilar_tipo_componente
  (tipo, nome, categoria, aceita_ativo, max_por_terminal, largura, altura)
VALUES
  ('BARRAMENTO', 'Barramento', 'estrutura', 0, 99, 200, 10),
  ('DISJUNTOR', 'Disjuntor', 'equipamento', 1, 1, 44, 72),
  ('SECCIONADORA', 'Seccionadora', 'equipamento', 1, 1, 40, 72),
  ('SECCIONADORA_ATERRAMENTO', 'Seccionadora de aterramento', 'equipamento', 1, 1, 40, 96),
  ('TC', 'Transformador de corrente (TC)', 'instrumento', 1, 1, 32, 108),
  ('TP', 'Transformador de potencial (TP)', 'instrumento', 1, 1, 44, 88),
  ('TPC', 'Transformador de potencial capacitivo (TPC)', 'instrumento', 1, 1, 44, 104),
  ('PARA_RAIOS', 'Para-raios', 'instrumento', 1, 1, 40, 96),
  ('REATOR', 'Reator', 'equipamento', 1, 1, 44, 110),
  ('TRANSFORMADOR', 'Transformador de potencia', 'equipamento', 1, 1, 64, 88),
  ('CONEXAO', 'Ponto de conexao', 'apoio', 0, 99, 16, 16),
  ('ETIQUETA_VAO', 'Identificacao de vao', 'apoio', 0, 99, 110, 26);

CREATE TABLE IF NOT EXISTS unifilar_diagrama (
  id_diagrama INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_subestacao INT NOT NULL,
  id_usuario_ultimo INT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_unifilar_diagrama_subestacao (id_subestacao),
  CONSTRAINT fk_unifilar_diagrama_subestacao FOREIGN KEY (id_subestacao)
    REFERENCES subestacao (id_subestacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS unifilar_componente (
  id_componente INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_diagrama INT NOT NULL,
  id_externo VARCHAR(160) NOT NULL,
  tipo VARCHAR(40) NOT NULL,
  codigo VARCHAR(64) NULL,
  nome VARCHAR(160) NULL,
  vao VARCHAR(64) NULL,
  rotacao SMALLINT NOT NULL DEFAULT 0,
  posicao_x FLOAT NOT NULL DEFAULT 0,
  posicao_y FLOAT NOT NULL DEFAULT 0,
  largura FLOAT NULL,
  altura FLOAT NULL,
  id_ativo INT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_unifilar_componente_externo (id_diagrama, id_externo),
  KEY ix_unifilar_componente_tipo (tipo),
  CONSTRAINT fk_unifilar_componente_diagrama FOREIGN KEY (id_diagrama)
    REFERENCES unifilar_diagrama (id_diagrama) ON DELETE CASCADE,
  CONSTRAINT fk_unifilar_componente_tipo FOREIGN KEY (tipo)
    REFERENCES unifilar_tipo_componente (tipo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS unifilar_conexao (
  id_conexao INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_diagrama INT NOT NULL,
  id_externo VARCHAR(160) NOT NULL,
  id_componente_origem INT NOT NULL,
  terminal_origem VARCHAR(8) NOT NULL,
  id_componente_destino INT NOT NULL,
  terminal_destino VARCHAR(8) NOT NULL,
  UNIQUE KEY uk_unifilar_conexao_externo (id_diagrama, id_externo),
  KEY ix_unifilar_conexao_origem (id_componente_origem, terminal_origem),
  KEY ix_unifilar_conexao_destino (id_componente_destino, terminal_destino),
  CONSTRAINT fk_unifilar_conexao_diagrama FOREIGN KEY (id_diagrama)
    REFERENCES unifilar_diagrama (id_diagrama) ON DELETE CASCADE,
  CONSTRAINT fk_unifilar_conexao_origem FOREIGN KEY (id_componente_origem)
    REFERENCES unifilar_componente (id_componente) ON DELETE CASCADE,
  CONSTRAINT fk_unifilar_conexao_destino FOREIGN KEY (id_componente_destino)
    REFERENCES unifilar_componente (id_componente) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS unifilar_terminal (
  id_terminal INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_componente INT NOT NULL,
  terminal VARCHAR(8) NOT NULL,
  UNIQUE KEY uk_unifilar_terminal (id_componente, terminal),
  CONSTRAINT fk_unifilar_terminal_componente FOREIGN KEY (id_componente)
    REFERENCES unifilar_componente (id_componente) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
