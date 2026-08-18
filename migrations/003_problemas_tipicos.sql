CREATE TABLE IF NOT EXISTS problema_tipico (
 id_problema INT AUTO_INCREMENT PRIMARY KEY, id_tipo_ativo INT NOT NULL,
 sistema VARCHAR(50) NOT NULL, categoria VARCHAR(50) NOT NULL, titulo VARCHAR(150) NOT NULL,
 descricao TEXT NULL, criticidade_padrao ENUM('BAIXA','MEDIA','ALTA','CRITICA') NOT NULL,
 modo_falha TEXT NULL, efeito_falha TEXT NULL, detectabilidade ENUM('ALTA','MEDIA','BAIXA') NULL,
 especialidade VARCHAR(100) NULL, requer_desligamento BOOLEAN NOT NULL DEFAULT FALSE,
 ativo BOOLEAN NOT NULL DEFAULT TRUE, criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 CONSTRAINT fk_problema_tipo FOREIGN KEY(id_tipo_ativo) REFERENCES tipo_ativo(id_tipo_ativo) ON DELETE RESTRICT ON UPDATE CASCADE,
 CONSTRAINT uq_problema_tipo_titulo UNIQUE(id_tipo_ativo,titulo),
 INDEX ix_problema_tipo(id_tipo_ativo), INDEX ix_problema_filtros(sistema,categoria,criticidade_padrao,ativo), INDEX ix_problema_especialidade(especialidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS sintoma_problema (id INT AUTO_INCREMENT PRIMARY KEY,id_problema INT NOT NULL,sintoma VARCHAR(500) NOT NULL,INDEX(id_problema),FOREIGN KEY(id_problema) REFERENCES problema_tipico(id_problema) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS causa_problema (id INT AUTO_INCREMENT PRIMARY KEY,id_problema INT NOT NULL,causa VARCHAR(500) NOT NULL,INDEX(id_problema),FOREIGN KEY(id_problema) REFERENCES problema_tipico(id_problema) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS metodo_deteccao_problema (id INT AUTO_INCREMENT PRIMARY KEY,id_problema INT NOT NULL,metodo VARCHAR(150) NOT NULL,INDEX(id_problema),FOREIGN KEY(id_problema) REFERENCES problema_tipico(id_problema) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS acao_recomendada (id INT AUTO_INCREMENT PRIMARY KEY,id_problema INT NOT NULL,tipo_acao ENUM('INSPECAO','ENSAIO','CORRECAO','SUBSTITUICAO','MONITORAMENTO','INVESTIGACAO') NOT NULL DEFAULT 'INVESTIGACAO',descricao VARCHAR(500) NOT NULL,prioridade VARCHAR(30),prazo_recomendado VARCHAR(100),INDEX(id_problema),FOREIGN KEY(id_problema) REFERENCES problema_tipico(id_problema) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS ss_problema (id INT AUTO_INCREMENT PRIMARY KEY,id_ss INT NOT NULL,id_problema INT NOT NULL,observacao TEXT,criticidade_identificada ENUM('BAIXA','MEDIA','ALTA','CRITICA'),confirmado BOOLEAN NOT NULL DEFAULT FALSE,criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,CONSTRAINT uq_ss_problema UNIQUE(id_ss,id_problema),INDEX(id_ss),INDEX(id_problema),FOREIGN KEY(id_ss) REFERENCES solicitacao_servico(id) ON DELETE CASCADE,FOREIGN KEY(id_problema) REFERENCES problema_tipico(id_problema) ON DELETE RESTRICT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
