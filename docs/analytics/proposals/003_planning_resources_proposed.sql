-- PROPOSTA DA ETAPA 03 — NÃO EXECUTAR AUTOMATICAMENTE.
-- Proposta escrita para MySQL, que é o dialeto ativo identificado no backend.
-- Revisar nomes de schemas, tipos e convenções do ambiente antes da Etapa 04.
-- O script não inclui dados fictícios nem altera as tabelas atuais.

CREATE TABLE recurso (
    id_recurso INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(160) NOT NULL,
    categoria VARCHAR(30) NOT NULL,
    unidade VARCHAR(30) NOT NULL,
    quantidade_disponivel NUMERIC(12, 3),
    controla_disponibilidade BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_recurso_categoria CHECK (
        categoria IN ('MAO_DE_OBRA', 'INSTRUMENTO', 'VEICULO', 'EQUIPAMENTO', 'MATERIAL', 'EPI', 'EPC')
    ),
    CONSTRAINT ck_recurso_quantidade CHECK (
        quantidade_disponivel IS NULL OR quantidade_disponivel >= 0
    ),
    CONSTRAINT uq_recurso_categoria_nome UNIQUE (categoria, nome)
);

CREATE TABLE plano_estimativa (
    id_plano_manutencao INTEGER PRIMARY KEY,
    duracao_estimada_horas NUMERIC(8, 2),
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_plano_estimativa_plano FOREIGN KEY (id_plano_manutencao)
        REFERENCES plano_manutencao (id_plano_manutencao) ON DELETE CASCADE,
    CONSTRAINT ck_plano_estimativa_duracao CHECK (
        duracao_estimada_horas IS NULL OR duracao_estimada_horas > 0
    )
);

CREATE TABLE plano_recurso (
    id_plano_recurso INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_plano_manutencao INTEGER NOT NULL,
    id_recurso INTEGER NOT NULL,
    quantidade NUMERIC(12, 3) NOT NULL,
    horas_por_recurso NUMERIC(8, 2),
    consumivel BOOLEAN NOT NULL DEFAULT FALSE,
    obrigatorio BOOLEAN NOT NULL DEFAULT TRUE,
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_plano_recurso_plano FOREIGN KEY (id_plano_manutencao)
        REFERENCES plano_manutencao (id_plano_manutencao) ON DELETE CASCADE,
    CONSTRAINT fk_plano_recurso_recurso FOREIGN KEY (id_recurso)
        REFERENCES recurso (id_recurso),
    CONSTRAINT ck_plano_recurso_quantidade CHECK (quantidade > 0),
    CONSTRAINT ck_plano_recurso_horas CHECK (
        horas_por_recurso IS NULL OR horas_por_recurso > 0
    ),
    CONSTRAINT uq_plano_recurso UNIQUE (id_plano_manutencao, id_recurso)
);

CREATE TABLE plano_equipe (
    id_plano_equipe INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_plano_manutencao INTEGER NOT NULL,
    id_equipe INTEGER NOT NULL,
    prioridade INTEGER NOT NULL DEFAULT 1,
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_plano_equipe_plano FOREIGN KEY (id_plano_manutencao)
        REFERENCES plano_manutencao (id_plano_manutencao) ON DELETE CASCADE,
    CONSTRAINT fk_plano_equipe_equipe FOREIGN KEY (id_equipe)
        REFERENCES sobreaviso_equipe (id_equipe),
    CONSTRAINT ck_plano_equipe_prioridade CHECK (prioridade > 0),
    CONSTRAINT uq_plano_equipe UNIQUE (id_plano_manutencao, id_equipe)
);

CREATE TABLE equipe_capacidade (
    id_equipe_capacidade INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_equipe INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    horas_disponiveis NUMERIC(10, 2) NOT NULL,
    fonte VARCHAR(80),
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_equipe_capacidade_equipe FOREIGN KEY (id_equipe)
        REFERENCES sobreaviso_equipe (id_equipe) ON DELETE CASCADE,
    CONSTRAINT ck_equipe_capacidade_periodo CHECK (data_fim >= data_inicio),
    CONSTRAINT ck_equipe_capacidade_horas CHECK (horas_disponiveis >= 0),
    CONSTRAINT uq_equipe_capacidade_periodo UNIQUE (id_equipe, data_inicio, data_fim)
);

CREATE INDEX ix_plano_recurso_plano ON plano_recurso (id_plano_manutencao);
CREATE INDEX ix_plano_recurso_recurso ON plano_recurso (id_recurso);
CREATE INDEX ix_plano_equipe_plano ON plano_equipe (id_plano_manutencao);
CREATE INDEX ix_plano_equipe_equipe ON plano_equipe (id_equipe);
CREATE INDEX ix_equipe_capacidade_periodo ON equipe_capacidade (data_inicio, data_fim);

-- Não é proposta uma tabela de evento neste momento.
-- O evento futuro será agregado a partir de plano_execucao por plano, ativo/grupo,
-- data programada e periodicidade. Uma tabela persistente deverá ser introduzida
-- apenas quando houver remarcação, horário, equipe ou reserva por evento.

