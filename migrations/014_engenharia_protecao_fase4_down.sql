-- ENGVI - Engenharia de Proteção - Fase 4 (rollback)
-- Remove as tabelas da Fase 4 na ordem inversa de dependência.

DROP TABLE IF EXISTS ied_ensaio_arquivo;
DROP TABLE IF EXISTS ied_ensaio_item;
DROP TABLE IF EXISTS ied_ensaio;
DROP TABLE IF EXISTS ied_sinal;
DROP TABLE IF EXISTS ied_circuito;
DROP TABLE IF EXISTS ied_goose_controle;
DROP TABLE IF EXISTS ied_protocolo_comunicacao;
DROP TABLE IF EXISTS ied_interface_comunicacao;
