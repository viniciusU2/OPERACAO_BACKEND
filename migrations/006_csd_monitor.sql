-- Modelo dimensional do CSD Monitor no mesmo banco do sistema de O&M.
-- Migração idempotente: não cria banco/schema separado e não inclui views.

CREATE TABLE IF NOT EXISTS dim_equipamento (
    id_equipamento BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_reference VARCHAR(100), order_reference VARCHAR(150),
    country VARCHAR(100), end_user VARCHAR(100), substation VARCHAR(150),
    voltage_level_kv DECIMAL(12,4), frequency_hz DECIMAL(10,4),
    bay_number VARCHAR(100), feeder_name VARCHAR(100), cb_model VARCHAR(100),
    cb1_sn VARCHAR(100), cb2_sn VARCHAR(100), csd_serial_number VARCHAR(100),
    csd_hostname VARCHAR(100), csd_ied_name VARCHAR(100), csd_software_version VARCHAR(50),
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_equipamento (csd_serial_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_canal (
    id_canal BIGINT AUTO_INCREMENT PRIMARY KEY,
    indice_canal INT NOT NULL, nome_canal VARCHAR(100), fase VARCHAR(20),
    disjuntor VARCHAR(50), descricao VARCHAR(255),
    UNIQUE KEY uk_canal (indice_canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_grandeza (
    id_grandeza BIGINT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(200) NOT NULL, nome VARCHAR(255), categoria VARCHAR(100),
    subcategoria VARCHAR(100), unidade VARCHAR(50),
    UNIQUE KEY uk_grandeza (codigo, unidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_tipo_alarme (
    id_tipo_alarme BIGINT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(200) NOT NULL UNIQUE, nome VARCHAR(255),
    categoria VARCHAR(100), severidade VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_configuracao (
    id_configuracao BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_equipamento BIGINT NOT NULL, parametro VARCHAR(255) NOT NULL,
    categoria VARCHAR(100), valor_original TEXT, valor_numerico DOUBLE NULL,
    unidade VARCHAR(50), source_file VARCHAR(255),
    data_importacao DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_config_equip FOREIGN KEY (id_equipamento)
        REFERENCES dim_equipamento(id_equipamento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_evento (
    id_evento BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_equipamento BIGINT NOT NULL, nome_arquivo VARCHAR(255), hash_arquivo CHAR(64) NOT NULL,
    archive_type VARCHAR(50), archive_creation_date_utc DATETIME(6),
    archive_creation_date_local DATETIME(6), switching_program VARCHAR(100),
    phase_ref_open VARCHAR(50), phase_ref_close VARCHAR(50),
    timestamp_open_order DATETIME(6), timestamp_close_order DATETIME(6),
    data_importacao DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_evento_equip FOREIGN KEY (id_equipamento)
        REFERENCES dim_equipamento(id_equipamento),
    UNIQUE KEY uk_hash_arquivo (hash_arquivo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_medicao (
    id_medicao BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_evento BIGINT NOT NULL, id_equipamento BIGINT NOT NULL, id_grandeza BIGINT NOT NULL,
    id_canal BIGINT NULL, valor DOUBLE, source_parameter VARCHAR(255),
    CONSTRAINT fk_med_evento FOREIGN KEY (id_evento) REFERENCES fato_evento(id_evento),
    CONSTRAINT fk_med_equip FOREIGN KEY (id_equipamento) REFERENCES dim_equipamento(id_equipamento),
    CONSTRAINT fk_med_grandeza FOREIGN KEY (id_grandeza) REFERENCES dim_grandeza(id_grandeza),
    CONSTRAINT fk_med_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal),
    UNIQUE KEY uk_medicao (id_evento, id_grandeza, id_canal, source_parameter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_alarme (
    id_alarme BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_evento BIGINT NOT NULL, id_equipamento BIGINT NOT NULL, id_tipo_alarme BIGINT NOT NULL,
    id_canal BIGINT NULL, estado_alarme BOOLEAN, timestamp_on DATETIME(6),
    timestamp_off DATETIME(6), duracao_segundos DOUBLE, source_parameter VARCHAR(255),
    CONSTRAINT fk_alarm_evento FOREIGN KEY (id_evento) REFERENCES fato_evento(id_evento),
    CONSTRAINT fk_alarm_equip FOREIGN KEY (id_equipamento) REFERENCES dim_equipamento(id_equipamento),
    CONSTRAINT fk_alarm_tipo FOREIGN KEY (id_tipo_alarme) REFERENCES dim_tipo_alarme(id_tipo_alarme),
    CONSTRAINT fk_alarm_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_estado (
    id_estado BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_evento BIGINT NOT NULL, id_equipamento BIGINT NOT NULL, id_canal BIGINT NULL,
    codigo_estado VARCHAR(200), valor_estado VARCHAR(255),
    CONSTRAINT fk_estado_evento FOREIGN KEY (id_evento) REFERENCES fato_evento(id_evento),
    CONSTRAINT fk_estado_equip FOREIGN KEY (id_equipamento) REFERENCES dim_equipamento(id_equipamento),
    CONSTRAINT fk_estado_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_contador (
    id_contador BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_evento BIGINT NOT NULL, id_equipamento BIGINT NOT NULL, id_grandeza BIGINT NOT NULL,
    id_canal BIGINT NULL, valor DOUBLE,
    CONSTRAINT fk_cont_evento FOREIGN KEY (id_evento) REFERENCES fato_evento(id_evento),
    CONSTRAINT fk_cont_equip FOREIGN KEY (id_equipamento) REFERENCES dim_equipamento(id_equipamento),
    CONSTRAINT fk_cont_grandeza FOREIGN KEY (id_grandeza) REFERENCES dim_grandeza(id_grandeza),
    CONSTRAINT fk_cont_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fato_timestamp (
    id_timestamp BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_evento BIGINT NOT NULL, id_equipamento BIGINT NOT NULL, id_canal BIGINT NULL,
    tipo_timestamp VARCHAR(200), timestamp_valor DATETIME(6), source_parameter VARCHAR(255),
    CONSTRAINT fk_ts_evento FOREIGN KEY (id_evento) REFERENCES fato_evento(id_evento),
    CONSTRAINT fk_ts_equip FOREIGN KEY (id_equipamento) REFERENCES dim_equipamento(id_equipamento),
    CONSTRAINT fk_ts_canal FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS etl_importacao (
    id_importacao BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome_arquivo VARCHAR(255), hash_arquivo CHAR(64), data_inicio DATETIME(6),
    data_fim DATETIME(6), status VARCHAR(20), linhas_xml INT,
    medicoes_inseridas INT, alarmes_inseridos INT, estados_inseridos INT,
    contadores_inseridos INT, timestamps_inseridos INT, mensagem_erro TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS etl_parametro_nao_classificado (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_importacao BIGINT NOT NULL, parametro VARCHAR(255) NOT NULL,
    valor_original TEXT, unidade VARCHAR(50),
    CONSTRAINT fk_nao_class_import FOREIGN KEY (id_importacao)
        REFERENCES etl_importacao(id_importacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
