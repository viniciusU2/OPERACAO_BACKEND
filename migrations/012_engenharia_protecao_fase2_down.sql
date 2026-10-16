-- ENGVI - Engenharia de Proteção - Fase 2 (rollback)
-- Remove as tabelas da Fase 2 na ordem inversa de dependência.

DROP TABLE IF EXISTS ied_backup_validacao;
DROP TABLE IF EXISTS configuracao_arquivo;
DROP TABLE IF EXISTS ied_configuracao;
DROP TABLE IF EXISTS arquivo;
DROP TABLE IF EXISTS config_parametro;
DROP TABLE IF EXISTS ied_grupo_ajuste;
DROP TABLE IF EXISTS ied_funcao;
DROP TABLE IF EXISTS parametro_definicao;
DROP TABLE IF EXISTS funcao_ansi;
