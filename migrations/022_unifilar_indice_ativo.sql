-- Indice da associacao de um componente do unifilar ao ativo real.
ALTER TABLE unifilar_componente
ADD INDEX ix_unifilar_componente_ativo (id_ativo);
