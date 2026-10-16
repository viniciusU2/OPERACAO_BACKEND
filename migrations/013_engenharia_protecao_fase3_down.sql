-- ENGVI - Engenharia de Proteção - Fase 3 (rollback)
-- Remove as tabelas da Fase 3 na ordem inversa de dependência.

DROP TABLE IF EXISTS alteracao_historico;
DROP TABLE IF EXISTS alteracao_item;
DROP TABLE IF EXISTS solicitacao_alteracao;
