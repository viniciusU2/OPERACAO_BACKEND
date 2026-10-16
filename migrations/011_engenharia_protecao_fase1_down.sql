-- REVERSÃO DE EMERGÊNCIA DA MIGRAÇÃO 011.
-- ATENÇÃO: destrutiva. Executar apenas com autorização, backup validado e sem dados que devam ser preservados.
DROP TABLE IF EXISTS ied_equipamento;
DROP TABLE IF EXISTS ied_firmware_historico;
DROP TABLE IF EXISTS ied_modulo;
DROP TABLE IF EXISTS ied_instalacao;
DROP TABLE IF EXISTS ied;
DROP TABLE IF EXISTS modelo_ied;
