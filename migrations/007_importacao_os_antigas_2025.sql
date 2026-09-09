-- Migração das OS antigas de Gentio do Ouro - ano 2025
-- Banco alvo: MySQL/MariaDB
-- Fonte: OS_ANTIGAS_NORMALIZADAS.xlsx, aba OS
--
-- SEGURANÇA:
-- 1. O arquivo carrega 196 registros em uma tabela temporária de estágio.
-- 2. A carga definitiva fica DESATIVADA por padrão.
-- 3. Corrija as pendências indicadas abaixo e altere @executar_migracao para 1.
-- 4. A rotina aborta e executa ROLLBACK se qualquer validação falhar.

SET NAMES utf8mb4;
SET @lote_migracao = 'MIGRACAO_OS_GOR_2025_20260909';
SET @executar_migracao = 0;

DROP TEMPORARY TABLE IF EXISTS stg_os_antigas_2025;
CREATE TEMPORARY TABLE stg_os_antigas_2025 (
    linha_origem INT NOT NULL,
    numero_os VARCHAR(30) NOT NULL,
    numero_si VARCHAR(30) NULL,
    id_subestacao INT NULL,
    id_ativo INT NULL,
    id_grupo_ativo INT NULL,
    especie VARCHAR(100) NULL,
    numero_apr VARCHAR(50) NULL,
    localizacao VARCHAR(100) NULL,
    complemento VARCHAR(100) NULL,
    esquema_servicos VARCHAR(100) NULL,
    prioridade VARCHAR(20) NULL,
    responsavel VARCHAR(100) NULL,
    responsavel_manutencao VARCHAR(100) NULL,
    responsavel_operacao VARCHAR(100) NULL,
    substituto VARCHAR(100) NULL,
    data_inicio_programado DATETIME NULL,
    data_fim_programado DATETIME NULL,
    descricao_servicos TEXT NULL,
    emissor TEXT NULL,
    data_inicio_execucao DATETIME NULL,
    data_fim_execucao DATETIME NULL,
    centro_custos VARCHAR(50) NULL,
    status VARCHAR(30) NULL,
    PRIMARY KEY (numero_os),
    KEY idx_stg_os_ativo (id_ativo),
    KEY idx_stg_os_grupo (id_grupo_ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO stg_os_antigas_2025 (
    linha_origem, numero_os, numero_si, id_subestacao, id_ativo,
    id_grupo_ativo, especie, numero_apr, localizacao, complemento,
    esquema_servicos, prioridade, responsavel, responsavel_manutencao,
    responsavel_operacao, substituto, data_inicio_programado,
    data_fim_programado, descricao_servicos, emissor,
    data_inicio_execucao, data_fim_execucao, centro_custos, status
) VALUES
(2, 'OS-GOR-0001-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0001-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(3, 'OS-GOR-0002-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0002-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(4, 'OS-GOR-0003-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0003-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Evaldo Mendonça', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(5, 'OS-GOR-0004-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0004-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Evaldo Mendonça', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(6, 'OS-GOR-0005-2025', NULL, 2, 780, 162, 'RE_500KV_HITACHI', 'APR-GOR-0005-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Evaldo Mendonça', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(7, 'OS-GOR-0006-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0006-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Evaldo Mendonça', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-03-26 00:00:00', '2025-03-26 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e DGA antes da Energização', 'Marcio Oliveira', '2025-03-26 15:00:00', '2025-03-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(8, 'OS-GOR-0007-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0007-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(9, 'OS-GOR-0008-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0008-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(10, 'OS-GOR-0009-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0009-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(11, 'OS-GOR-0010-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0010-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(12, 'OS-GOR-0011-2025', NULL, 2, NULL, 82, 'RE_500KV_HITACHI', 'APR-GOR-0011-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(13, 'OS-GOR-0012-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0012-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-04-04 00:00:00', '2025-04-04 00:00:00', 'Coleta de óleo isolante para analise DGA 24 horas após energização', 'Marcio Oliveira', '2025-04-04 09:00:00', '2025-04-04 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(14, 'OS-GOR-0013-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0013-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(15, 'OS-GOR-0014-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0014-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(16, 'OS-GOR-0015-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0015-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(17, 'OS-GOR-0016-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0016-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(18, 'OS-GOR-0017-2025', NULL, 2, NULL, 82, 'RE_500KV_HITACHI', 'APR-GOR-0017-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(19, 'OS-GOR-0018-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0018-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir Pereira', 'Aldenir Pereira', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise DGA 48 horas após energização', 'Marcio Oliveira', '2025-04-05 09:00:00', '2025-04-05 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(20, 'OS-GOR-0019-2025', NULL, 2, 759, 148, 'PNL_125V_SIEMENS', 'APR-GOR-0019-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_1', 'Wilson Moreira Junior', 'Renato Delmanto / (38) 99982-7642', 'Marcio Oliveira/ (38) 99982-7642', 'Marcio Oliveira/ (38) 99982-7642', '2025-09-04 00:00:00', '2025-05-15 00:00:00', 'Ajustes nos paineis de telecominicações das subestações Bom Jesus da Lapa II e Gentio do Ouro II', 'Marcio Oliveira', '2025-05-09 07:00:00', '2025-05-09 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(21, 'OS-GOR-0020-2025', NULL, 2, 760, 149, 'PNL_125V_SIEMENS', 'APR-GOR-0020-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_1', 'Wilson Moreira Junior', 'Renato Delmanto / (38) 99982-7642', 'Marcio Oliveira/ (38) 99982-7642', 'Marcio Oliveira/ (38) 99982-7642', '2025-09-04 00:00:00', '2025-05-15 00:00:00', 'Ajustes nos paineis de telecominicações das subestações Bom Jesus da Lapa II e Gentio do Ouro II', 'Marcio Oliveira', '2025-05-09 07:00:00', '2025-05-09 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(22, 'OS-GOR-0021-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0021-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-11-04 00:00:00', '2025-11-04 00:00:00', 'Será realizado  teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-04-11 15:00:00', '2025-04-11 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(23, 'OS-GOR-0022-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0022-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(24, 'OS-GOR-0023-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0023-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica   após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(25, 'OS-GOR-0024-2025', NULL, 2, NULL, NULL, 'GERAL', 'APR-GOR-0024-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografica   após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(26, 'OS-GOR-0025-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0025-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografica   após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(27, 'OS-GOR-0026-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0026-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografica   após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(28, 'OS-GOR-0027-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0027-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-10-04 00:00:00', '2025-10-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 07 dias da energização', 'Wilson Moreira', '2025-04-10 10:00:00', '2025-04-10 12:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(29, 'OS-GOR-0028-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0028-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(30, 'OS-GOR-0029-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0029-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(31, 'OS-GOR-0030-2025', NULL, 2, 781, 163, 'RE_500KV_HITACHI', 'APR-GOR-0030-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(32, 'OS-GOR-0031-2025', NULL, 2, NULL, NULL, 'GERAL', 'APR-GOR-0031-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(33, 'OS-GOR-0032-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0032-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(34, 'OS-GOR-0033-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0033-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(35, 'OS-GOR-0034-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0034-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel', 'Rangel', '2025-04-14 00:00:00', '2025-10-06 00:00:00', 'Montagem e comissionamento do reator', 'Wilson Moreira', '2025-04-14 13:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(36, 'OS-GOR-0035-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0035-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Aldenir', 'Aldenir', '2025-03-04 00:00:00', '2025-03-04 00:00:00', 'Retirada do excesso de óleo no Reator', 'Wilson Moreira', '2025-04-03 10:00:00', '2025-04-03 21:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(37, 'OS-GOR-0036-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0036-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Rangel Vasconcelos', 'Rangel Vasconcelos', '2025-04-17 00:00:00', '2025-04-17 00:00:00', 'Será realizado teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-04-17 16:00:00', '2025-04-17 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(38, 'OS-GOR-0037-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0037-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_1', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Evaldo Mendonça', 'Evaldo Mendonça', '2025-04-22 00:00:00', '2025-04-25 00:00:00', 'Manutenção Preventiva em todos equipamentos de pátio da SE GDO II', 'Marcio Oliveira', '2025-04-22 08:00:00', '2025-04-25 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(39, 'OS-GOR-0038-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0038-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Evaldo Souza', 'Evaldo Souza', '2025-04-22 00:00:00', '2025-04-23 00:00:00', 'Limpeza no depósito da CC/SE', 'Wilson Moreira', '2025-04-24 09:00:00', '2025-04-24 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(40, 'OS-GOR-0039-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0039-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-04-24 00:00:00', '2025-04-24 00:00:00', 'Limpeza nos painéis da CC/SE', 'Wilson Moreira', '2025-05-02 14:00:00', '2025-05-02 15:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(41, 'OS-GOR-0040-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0040-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-02 00:00:00', '2025-05-02 00:00:00', 'Será realizado teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA');

INSERT INTO stg_os_antigas_2025 (
    linha_origem, numero_os, numero_si, id_subestacao, id_ativo,
    id_grupo_ativo, especie, numero_apr, localizacao, complemento,
    esquema_servicos, prioridade, responsavel, responsavel_manutencao,
    responsavel_operacao, substituto, data_inicio_programado,
    data_fim_programado, descricao_servicos, emissor,
    data_inicio_execucao, data_fim_execucao, centro_custos, status
) VALUES
(42, 'OS-GOR-0041-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0041-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(43, 'OS-GOR-0042-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0042-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(44, 'OS-GOR-0043-2025', NULL, 2, NULL, NULL, 'GERAL', 'APR-GOR-0043-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(45, 'OS-GOR-0044-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0044-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(46, 'OS-GOR-0045-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0045-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', '2025-05-05 08:00:00', '2025-05-05 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(47, 'OS-GOR-0046-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0046-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-04 00:00:00', '2025-05-04 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica e físico-química após 30 dias da energização', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(48, 'OS-GOR-0047-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0047-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-06 00:00:00', '2025-05-06 00:00:00', 'Realizar verificação de alimentação e de comutação dos servidores 1 e 2 do SAGE.', 'Edinei Rocha', '2025-09-05 08:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(49, 'OS-GOR-0048-2025', NULL, 2, NULL, 163, 'RE_500KV_HITACHI', 'APR-GOR-0048-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-09 00:00:00', '2025-05-02 00:00:00', 'Comissionamento dos reatores', 'Wilson Moreira', '2025-09-05 08:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(50, 'OS-GOR-0049-2025', NULL, 2, NULL, 163, 'RE_500KV_HITACHI', 'APR-GOR-0049-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-09 00:00:00', '2025-05-02 00:00:00', 'Conexoções dos cabos nos reatores', 'Wilson Moreira', '2025-11-05 08:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(51, 'OS-GOR-0050-2025', NULL, 2, NULL, 163, 'RE_500KV_HITACHI', 'APR-GOR-0050-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-11 00:00:00', '2025-05-12 00:00:00', 'Intervenção para teste de Proteções Intrínsecas do Reator de Barra 05E7. Parametrização, configuração e testes do sistema sincronizador.', 'Wilson Moreira', '2025-05-13 08:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(52, 'OS-GOR-0051-2025', NULL, 2, NULL, 83, 'RE_500KV_HITACHI', 'APR-GOR-0051-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-13 00:00:00', '2025-05-14 00:00:00', 'Intervenção para teste de Proteções Intrínsecas do Reator de Barra 05E9. Parametrização, configuração e testes do sistema sincronizador.', 'Wilson Moreira', '2025-05-14 08:00:00', NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(53, 'OS-GOR-0052-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0052-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-13 00:00:00', '2025-05-15 00:00:00', 'Finalizações de pedências da construção (montagem), e (elétrica)', 'Wilson Moreira', '2025-05-22 08:00:00', '2025-05-22 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(54, 'OS-GOR-0053-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0053-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-22 00:00:00', '2025-05-22 00:00:00', 'Será realizado teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-05-26 13:30:00', '2025-05-28 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(55, 'OS-GOR-0054-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0054-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-26 00:00:00', '2025-06-15 00:00:00', 'Manutenção Preventiva em todos equipamentos de pátio da SE GDO II', 'Wilson Moreira', '2025-05-22 08:00:00', '2025-05-22 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(56, 'OS-GOR-0055-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0055-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-05-29 00:00:00', 'Será realizado teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-06-01 07:00:00', '2025-06-01 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(57, 'OS-GOR-0056-2025', NULL, 2, 784, 164, 'RE_500KV_HITACHI', 'APR-GOR-0056-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(58, 'OS-GOR-0057-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0057-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(59, 'OS-GOR-0058-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0058-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(60, 'OS-GOR-0059-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0059-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(61, 'OS-GOR-0060-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0060-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(62, 'OS-GOR-0061-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0061-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-01 00:00:00', '2025-06-01 00:00:00', 'Coleta de óleo isolante para analise Físico e Quimica Cromarografia antes da Energização', 'Wilson Moreira', '2025-06-03 08:00:00', '2025-06-03 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(63, 'OS-GOR-0062-2025', NULL, 2, 610, 82, 'RE_500KV_HITACHI', 'APR-GOR-0062-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-06-01 07:00:00', '2025-06-01 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(64, 'OS-GOR-0063-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0063-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-06-04 07:00:00', '2025-10-03 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(65, 'OS-GOR-0064-2025', NULL, 2, NULL, NULL, 'GERAL', 'APR-GOR-0064-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-06-04 07:00:00', '2025-12-03 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(66, 'OS-GOR-0065-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0065-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-05-29 08:00:00', '2025-06-02 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(67, 'OS-GOR-0066-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0066-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-05-29 08:00:00', '2025-06-02 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(68, 'OS-GOR-0067-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0067-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2026-06-03 00:00:00', '2026-06-03 00:00:00', 'Coleta de óleo isolante para analise Cromatocrafica após 60 dias da energização', 'Wilson Moreira', '2025-05-29 08:00:00', '2025-06-02 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(69, 'OS-GOR-0068-2025', NULL, 2, 781, 163, 'RE_500KV_HITACHI', 'APR-GOR-0068-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-03 00:00:00', '2025-06-05 00:00:00', 'Comissionamento dos reator', 'Wilson Moreira', '2025-05-29 08:00:00', '2025-06-02 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(70, 'OS-GOR-0069-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0069-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-10-03 00:00:00', 'Acompanhar e verificar vazamento de óleo no radiador do reator', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(71, 'OS-GOR-0070-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0070-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-12-03 00:00:00', 'Acompanhar e verificar vazamento de óleo no (TC 303C) da bucha H1 do reator', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(72, 'OS-GOR-0071-2025', NULL, 2, 784, 164, 'RE_500KV_HITACHI', 'APR-GOR-0071-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(73, 'OS-GOR-0072-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0072-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(74, 'OS-GOR-0073-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0073-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(75, 'OS-GOR-0074-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0074-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-04 08:00:00', '2025-06-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(76, 'OS-GOR-0075-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0075-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(77, 'OS-GOR-0076-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0076-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-05-29 00:00:00', '2025-06-02 00:00:00', 'Coleta de óleo isolante para analise Físico Quimica e Cromatrografia antes da Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(78, 'OS-GOR-0077-2025', NULL, 2, 784, 164, 'RE_500KV_HITACHI', 'APR-GOR-0077-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(79, 'OS-GOR-0078-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0078-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(80, 'OS-GOR-0079-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0079-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(81, 'OS-GOR-0080-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0080-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-05 07:00:00', '2025-06-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA');

INSERT INTO stg_os_antigas_2025 (
    linha_origem, numero_os, numero_si, id_subestacao, id_ativo,
    id_grupo_ativo, especie, numero_apr, localizacao, complemento,
    esquema_servicos, prioridade, responsavel, responsavel_manutencao,
    responsavel_operacao, substituto, data_inicio_programado,
    data_fim_programado, descricao_servicos, emissor,
    data_inicio_execucao, data_fim_execucao, centro_custos, status
) VALUES
(82, 'OS-GOR-0081-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0081-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(83, 'OS-GOR-0082-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0082-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-04 00:00:00', '2025-06-04 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 24 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(84, 'OS-GOR-0083-2025', NULL, 2, 784, 164, 'RE_500KV_HITACHI', 'APR-GOR-0083-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(85, 'OS-GOR-0084-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0084-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(86, 'OS-GOR-0085-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0085-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(87, 'OS-GOR-0086-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0086-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(88, 'OS-GOR-0087-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0087-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-09 07:00:00', '2025-07-04 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(89, 'OS-GOR-0088-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0088-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-05 00:00:00', '2025-06-05 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após 48 horas de Energização', 'Wilson Moreira', '2025-06-12 07:00:00', '2025-06-12 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(90, 'OS-GOR-0089-2025', NULL, 2, 784, 164, 'RE_500KV_HITACHI', 'APR-GOR-0089-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Wilson', 'Wilson', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', '2025-06-19 07:00:00', '2025-06-23 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(91, 'OS-GOR-0090-2025', NULL, 2, 782, 163, 'RE_500KV_HITACHI', 'APR-GOR-0090-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', '2025-06-26 07:00:00', '2025-06-26 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(92, 'OS-GOR-0091-2025', NULL, 2, 783, 163, 'RE_500KV_HITACHI', 'APR-GOR-0091-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_5', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei', 'Edinei', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', '2025-06-25 07:00:00', '2025-07-30 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(93, 'OS-GOR-0092-2025', NULL, 2, 611, 83, 'RE_500KV_HITACHI', 'APR-GOR-0092-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', '2025-07-03 08:00:00', '2025-07-31 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(94, 'OS-GOR-0093-2025', NULL, 2, 612, 83, 'RE_500KV_HITACHI', 'APR-GOR-0093-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(95, 'OS-GOR-0094-2025', NULL, 2, 613, 83, 'RE_500KV_HITACHI', 'APR-GOR-0094-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Wilson Moreira', 'Wilson Moreira', '2025-06-10 00:00:00', '2025-06-10 00:00:00', 'Coleta de óleo isolante para analise Cromatografia após uma semana de Energização', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(96, 'OS-GOR-0095-2025', NULL, 2, 230, 69, 'GMG_380V_OLYMPIAN', 'APR-GOR-0095-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-09 00:00:00', '2025-07-04 00:00:00', 'Manutenção no GMG alternado', 'Wilson Moreira', '2024-01-07 08:00:00', '2025-07-31 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(97, 'OS-GOR-0096-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0096-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-12 00:00:00', '2025-06-12 00:00:00', 'Será realizado teste de funcionalidade no GMG- P.', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(98, 'OS-GOR-0097-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0097-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-19 00:00:00', '2025-06-23 00:00:00', 'Finalização da instalação da câmera', 'Wilson Moreira', '2025-07-16 08:00:00', '2025-07-21 18:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(99, 'OS-GOR-0098-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0098-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-19 00:00:00', '2025-06-26 00:00:00', 'Será realizado 4 vezes no mês referente, teste de funcionalidade no GMG- P.', 'Wilson Moreira', '2025-07-18 15:00:00', '2025-07-21 18:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(100, 'OS-GOR-0099-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0099-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Wsilson Moreira', 'Wsilson Moreira', '2025-06-25 00:00:00', '2025-06-30 00:00:00', 'CONSTRUÇÃO DO ARRUAMENTO E FINALIZAÇÃO DE PENDÊNCIAS DE OBRA (RIALMA CONSTRUÇÕES)', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(101, 'OS-GOR-0100-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0100-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-03 00:00:00', '2025-07-31 00:00:00', 'Será realizado 4 a 5 vezes no mês referente, teste de funcionalidade no GMG- P e GMA-P.', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(102, 'OS-GOR-0101-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0101-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-01 00:00:00', '2025-07-01 00:00:00', 'Realizar teste de perfomace dos gmg', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(103, 'OS-GOR-0102-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0102-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Wilson Moreira Junior', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-01 00:00:00', '2025-07-01 00:00:00', 'Realizar teste de perfomace dos gmg', 'Edinei Rocha', '2025-07-24 11:00:00', '2025-07-24 15:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(104, 'OS-GOR-0103-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0103-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-01 00:00:00', '2025-07-31 00:00:00', 'Manutenção Preventiva em todos equipamentos de pátio e CC/SE da SE GDO II', 'Wilson Moreira', '2025-07-28 11:00:00', '2025-10-03 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(105, 'OS-GOR-0104-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0104-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-06-27 00:00:00', '2025-06-27 00:00:00', 'Entrega técnica do GMG Stemac GMG-P', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(106, 'OS-GOR-0105-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0105-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-18 00:00:00', '2025-07-25 00:00:00', 'Verificação no circuito de iluminção, aquecimento, e tomada do vão G', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(107, 'OS-GOR-0106-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0106-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_1', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-18 00:00:00', '2025-07-21 00:00:00', 'Realizada reconexão de cabo solto na alimentação da resistência da SECC, que causava curto ao tocar a carcaça e abria o DJ do vão G Ilum, tom, e aquec', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(108, 'OS-GOR-0107-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0107-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-08-10 00:00:00', '2025-08-10 00:00:00', 'Realizar a troca da fase reserva do reator 05E8_R pela fase do reator 05E8_VM', 'Edinei Rocha', '2025-08-17 08:00:00', '2025-08-22 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(109, 'OS-GOR-0108-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0108-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_2', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-08-10 00:00:00', '2025-08-10 00:00:00', 'Realizar a troca da fase reserva do reator 05E8_R pela fase do reator 05E8_VM', 'Edinei Rocha', '2025-06-10 07:00:00', '2025-06-10 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(110, 'OS-GOR-0109-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0109-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_2', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-14 00:00:00', '2025-08-01 00:00:00', 'Realizar inspeção bimestral das chaves seccionadoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(111, 'OS-GOR-0110-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0110-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_4', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-24 00:00:00', '2025-07-24 00:00:00', 'Retirada do Mikrotik 1 e 2 do painel de Telecom (Servidor)', 'Wilson Moreira', '2025-01-08 09:00:00', '2025-08-28 16:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(112, 'OS-GOR-0111-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0111-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-07-28 00:00:00', '2025-10-03 00:00:00', 'Acompanhar e verificar vazamento de óleo no radiador do reator reserva de LT', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(113, 'OS-GOR-0112-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0112-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-08-09 00:00:00', '2025-08-09 00:00:00', 'REalizar instalação radiador 08 no reator 05E6_BR', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(114, 'OS-GOR-0113-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0113-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_2', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-08-04 00:00:00', '2025-08-29 00:00:00', 'Inspeção bimestral nos EAT (Reatores; Para-raios; TC''s; TP''s; Disjuntores)', 'Wilson Moreira', '2025-09-01 09:00:00', '2025-09-12 18:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(115, 'OS-GOR-0114-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0114-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_2', 'Edinei Rocha', 'Rangel Roger', 'Wilson Moreira', 'Wilson Moreira', '2025-08-14 00:00:00', '2025-08-16 00:00:00', 'Realizar troca da coluna do contato fixo e lamina contato móvel fase azul da chave 35C2-8', 'Edinei Rocha', '2025-09-01 13:00:00', '2025-09-05 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(116, 'OS-GOR-0115-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0115-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Edinei Rocha', 'Aldenir', 'Wilson Moreira', 'Wilson Moreira', '2025-08-17 00:00:00', '2025-08-22 00:00:00', 'Termovisão geral na subestação', 'Wilson Moreira', '2025-01-09 12:00:00', '2025-05-09 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(117, 'OS-GOR-0116-2025', NULL, 2, 609, 82, 'RE_500KV_HITACHI', 'APR-GOR-0116-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREDITIVA', 'NIVEL_2', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-08-17 00:00:00', '2025-08-18 00:00:00', 'Coleta de óleo cromatografia 1 semana após energizado 06E8 BR (2XBR62801)', 'Wilson Moreira', '2025-01-09 12:00:00', '2025-10-31 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(118, 'OS-GOR-0117-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0117-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-08-17 00:00:00', '2025-08-17 00:00:00', 'Intervenção SGI: 00.046.496-25 - Manobras: 35E8-8; 35C4-8; e 35C4-7', 'Wilson Moreira', '2025-01-09 08:00:00', '2025-09-30 17:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(119, 'OS-GOR-0118-2025', NULL, 2, 230, 69, 'GMG_380V_OLYMPIAN', 'APR-GOR-0118-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-08-01 00:00:00', '2025-08-29 00:00:00', 'Inspeção/teste de funcionalidade do GMG-P GMA-P', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(120, 'OS-GOR-0119-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0119-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-09-15 00:00:00', '2025-09-15 00:00:00', 'Realizar a troca da fase rerva pela fase azul do reator 05E7', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(121, 'OS-GOR-0120-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0120-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-09-15 00:00:00', '2025-09-15 00:00:00', 'Realizar a troca da fase rerva pela fase branca do reator 05E8', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA');

INSERT INTO stg_os_antigas_2025 (
    linha_origem, numero_os, numero_si, id_subestacao, id_ativo,
    id_grupo_ativo, especie, numero_apr, localizacao, complemento,
    esquema_servicos, prioridade, responsavel, responsavel_manutencao,
    responsavel_operacao, substituto, data_inicio_programado,
    data_fim_programado, descricao_servicos, emissor,
    data_inicio_execucao, data_fim_execucao, centro_custos, status
) VALUES
(122, 'OS-GOR-0121-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0121-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-09-01 00:00:00', '2025-09-12 00:00:00', 'Comissionamento do serviço auxiliar da subestação Gentio do Ouro II', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(123, 'OS-GOR-0122-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0122-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-09-01 00:00:00', '2025-09-05 00:00:00', 'Ajustes nas configurações dos relés UPCD1, UPCD2, UPCD3 e UPCD4 dos vãos G e H.', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(124, 'OS-GOR-0123-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0123-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-09-01 00:00:00', '2025-09-05 00:00:00', 'Inspeção visual com drone nas SECC', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(125, 'OS-GOR-0124-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0124-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-09-01 00:00:00', '2025-10-31 00:00:00', 'Inspeção bimestral nos EAT', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(126, 'OS-GOR-0125-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0125-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-09-01 00:00:00', '2025-09-30 00:00:00', 'Inspeção/teste de funcionalidade do GMG-P GMA-P', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(127, 'OS-GOR-0126-2025', NULL, 2, NULL, 111, 'SEC_500KV_WEG', 'APR-GOR-0126-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-09-26 00:00:00', '2025-09-26 00:00:00', 'Ajustes nos dedos do contato móvel da chave 35C4-8', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(128, 'OS-GOR-0127-2025', NULL, 2, 230, 69, 'GMG_380V_OLYMPIAN', 'APR-GOR-0127-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-08 00:00:00', 'Manutenção Preventiva semestral GMG-P', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(129, 'OS-GOR-0128-2025', NULL, 2, 718, 125, 'BAT_125V_HDS', 'APR-GOR-0128-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-07 00:00:00', 'Inspeção mensal Banco de Bateria 1', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(130, 'OS-GOR-0129-2025', NULL, 2, 719, 126, 'BAT_125V_HDS', 'APR-GOR-0129-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_6', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-07 00:00:00', 'Inspeção mensal Banco de Bateria 2', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(131, 'OS-GOR-0130-2025', NULL, 2, 720, 127, 'BAT_48V_HDS', 'APR-GOR-0130-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-01 00:00:00', '2025-10-07 00:00:00', 'Inspeção mensal Banco de Bateria 3', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-31 00:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(132, 'OS-GOR-0131-2025', NULL, 2, 721, 128, 'BAT_48V_HDS', 'APR-GOR-0131-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-01 00:00:00', '2025-10-07 00:00:00', 'Inspeção mensal Banco de Bateria 4', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-31 00:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(133, 'OS-GOR-0132-2025', NULL, 2, 777, 161, 'RE_500KV_HITACHI', 'APR-GOR-0132-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, semestral apos energizado.', 'Edinei Rocha', '2025-10-27 00:00:00', '2025-10-27 00:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(134, 'OS-GOR-0133-2025', NULL, 2, 778, 161, 'RE_500KV_HITACHI', 'APR-GOR-0133-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, semestral apos energizado.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(135, 'OS-GOR-0134-2025', NULL, 2, 779, 161, 'RE_500KV_HITACHI', 'APR-GOR-0134-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, semestral apos energizado.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(136, 'OS-GOR-0135-2025', NULL, 2, 608, 82, 'RE_500KV_HITACHI', 'APR-GOR-0135-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, semestral após  energizado.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(137, 'OS-GOR-0136-2025', NULL, 2, 609, 82, 'RE_500KV_HITACHI', 'APR-GOR-0136-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_2', 'Edinei Rocha', 'Rangel Roger', 'Marcio Oliveira', 'Marcio Oliveira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, Semestral após  energizado.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(138, 'OS-GOR-0137-2025', NULL, 2, NULL, 82, 'RE_500KV_HITACHI', 'APR-GOR-0137-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_2', 'Edinei Rocha', 'Rangel Roger', 'Marcio Oliveira', 'Marcio Oliveira', '2025-10-06 00:00:00', '2025-10-06 00:00:00', 'Coleta de óleo isolante para analise  DGA, semestral apos energizado.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(139, 'OS-GOR-0138-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0138-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira Junior', 'Edinei Rocha', 'Edinei Rocha', '2025-01-10 00:00:00', '2025-06-10 00:00:00', 'MP Preventiva Semestal da Subestação', 'Marcio Oliveira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(140, 'OS-GOR-0139-2025', NULL, 2, 230, 69, 'GMG_380V_OLYMPIAN', 'APR-GOR-0139-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_2', 'Edinei Rocha', 'Renato Mohamed', 'Edinei Rocha', 'Edinei Rocha', '2025-10-01 00:00:00', '2025-10-31 00:00:00', 'Inspeção/teste de funcionalidade do GMG-P GMA-P', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(141, 'OS-GOR-0140-2025', NULL, 2, 781, 163, 'RE_500KV_HITACHI', 'APR-GOR-0140-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Edinei Rocha', 'Wilson Moreira', 'Edinei Rocha', 'Edinei Rocha', '2025-10-27 00:00:00', '2025-10-27 00:00:00', 'Realizar coleta de óleo 30 dias após energização do reator 05E7_AZ', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(142, 'OS-GOR-0141-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0141-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Wilson Moreira', 'Wilson Moreira', '2025-11-05 00:00:00', '2025-11-05 00:00:00', 'Realizar manutenção pventiva mensal do GMG-P', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(143, 'OS-GOR-0142-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0142-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-11-10 00:00:00', '2025-11-10 00:00:00', 'Realizar manutenção prentiva mensal nos ar condicionado da sala de comando', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(144, 'OS-GOR-0143-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0143-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-11-11 00:00:00', '2025-11-11 00:00:00', 'Realizar instalação de disjuntor de falta fase no relé 27 no painel QSACA', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(145, 'OS-GOR-0144-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0144-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-11-26 00:00:00', '2025-11-26 00:00:00', 'Ajustes nas configurações dos sincronizadores dos vãos G.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(146, 'OS-GOR-0145-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0145-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-11-27 00:00:00', '2025-11-27 00:00:00', 'Ajustes nas configurações dos sincronizadores dos vãos  H.', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(147, 'OS-GOR-0146-2025', NULL, 2, NULL, 83, 'RE_500KV_HITACHI', 'APR-GOR-0146-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-11-12 00:00:00', '2025-11-14 00:00:00', 'Reaperto nos bujões superior dos reatores', 'Wilson Moreira', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(148, 'OS-GOR-0147-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0147-2025', 'Gentio do Ouro-BA', NULL, 'Atendimento Recomendação', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-11-12 00:00:00', '2025-11-13 00:00:00', 'Realizar ajustes fisico e configuração de farewell na rede de teleproteção, dado e Voz', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(149, 'OS-GOR-0148-2025', NULL, 2, 781, 163, 'RE_500KV_HITACHI', 'APR-GOR-0148-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO PREVENTIVA', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-11-26 00:00:00', '2025-11-27 00:00:00', 'Realizar coleta de óleo 60 dias após energização do reator 05E7_AZ', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(150, 'OS-GOR-0149-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0149-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA MENSAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-04 00:00:00', '2025-12-04 00:00:00', 'Realizar manutenção preventiva mensal do GMG-P', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(151, 'OS-GOR-0150-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0150-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-04 00:00:00', '2025-12-04 00:00:00', 'Inspeção Bimestral nos painéis CA e CC.', 'Edinei Rocha', '2026-05-13 08:00:00', '2026-05-13 08:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(152, 'OS-GOR-0151-2025', NULL, 2, 714, 121, 'RET_125V_CTRLTECH', 'APR-GOR-0151-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-04 00:00:00', '2025-12-05 00:00:00', 'Realizar manutenção preventiva bimestral nos retificadores 48 e 125Vcc', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(153, 'OS-GOR-0152-2025', NULL, 2, 718, 125, 'BAT_125V_HDS', 'APR-GOR-0152-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-04 00:00:00', '2025-12-05 00:00:00', 'Realizar manutenção preventiva bimestral nos banco bateria 48 e 125Vcc', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(154, 'OS-GOR-0153-2025', NULL, 2, NULL, 109, 'SEC_500KV_WEG', 'APR-GOR-0153-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(155, 'OS-GOR-0154-2025', NULL, 2, NULL, 107, 'SEC_500KV_WEG', 'APR-GOR-0154-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(156, 'OS-GOR-0155-2025', NULL, 2, NULL, 108, 'SEC_500KV_WEG', 'APR-GOR-0155-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(157, 'OS-GOR-0156-2025', NULL, 2, NULL, 105, 'SEC_500KV_WEG', 'APR-GOR-0156-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-05-13 08:00:00', '2026-05-13 09:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(158, 'OS-GOR-0157-2025', NULL, 2, NULL, 102, 'SEC_500KV_WEG', 'APR-GOR-0157-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-05-13 08:00:00', '2026-05-13 09:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(159, 'OS-GOR-0158-2025', NULL, 2, NULL, 103, 'SEC_500KV_WEG', 'APR-GOR-0158-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-05-13 08:00:00', '2026-05-13 09:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(160, 'OS-GOR-0159-2025', NULL, 2, NULL, 104, 'SEC_500KV_WEG', 'APR-GOR-0159-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-05-13 08:00:00', '2026-05-13 09:00:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(161, 'OS-GOR-0160-2025', NULL, 2, NULL, 101, 'SEC_500KV_WEG', 'APR-GOR-0160-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA');

INSERT INTO stg_os_antigas_2025 (
    linha_origem, numero_os, numero_si, id_subestacao, id_ativo,
    id_grupo_ativo, especie, numero_apr, localizacao, complemento,
    esquema_servicos, prioridade, responsavel, responsavel_manutencao,
    responsavel_operacao, substituto, data_inicio_programado,
    data_fim_programado, descricao_servicos, emissor,
    data_inicio_execucao, data_fim_execucao, centro_custos, status
) VALUES
(162, 'OS-GOR-0161-2025', NULL, 2, NULL, 100, 'SEC_500KV_WEG', 'APR-GOR-0161-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(163, 'OS-GOR-0162-2025', NULL, 2, NULL, 102, 'SEC_500KV_WEG', 'APR-GOR-0162-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(164, 'OS-GOR-0163-2025', NULL, 2, NULL, 120, 'SEC_500KV_WEG', 'APR-GOR-0163-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(165, 'OS-GOR-0164-2025', NULL, 2, NULL, 118, 'SEC_500KV_WEG', 'APR-GOR-0164-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(166, 'OS-GOR-0165-2025', NULL, 2, NULL, 119, 'SEC_500KV_WEG', 'APR-GOR-0165-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(167, 'OS-GOR-0166-2025', NULL, 2, NULL, 115, 'SEC_500KV_WEG', 'APR-GOR-0166-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(168, 'OS-GOR-0167-2025', NULL, 2, NULL, 117, 'SEC_500KV_WEG', 'APR-GOR-0167-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(169, 'OS-GOR-0168-2025', NULL, 2, NULL, 113, 'SEC_500KV_WEG', 'APR-GOR-0168-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(170, 'OS-GOR-0169-2025', NULL, 2, NULL, 114, 'SEC_500KV_WEG', 'APR-GOR-0169-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(171, 'OS-GOR-0170-2025', NULL, 2, NULL, 111, 'SEC_500KV_WEG', 'APR-GOR-0170-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(172, 'OS-GOR-0171-2025', NULL, 2, NULL, 110, 'SEC_500KV_WEG', 'APR-GOR-0171-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', NULL, NULL, 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(173, 'OS-GOR-0172-2025', NULL, 2, NULL, 112, 'SEC_500KV_WEG', 'APR-GOR-0172-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-05-27 15:00:00', '2026-06-04 16:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(174, 'OS-GOR-0173-2025', NULL, 2, NULL, 86, 'DJ_500KV_GE', 'APR-GOR-0173-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-08 00:00:00', '2025-12-12 00:00:00', 'Realizar mautenção preventiva bimestral das chaves Seccioandoras', 'Edinei Rocha', '2026-06-04 15:00:00', '2026-06-04 16:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(175, 'OS-GOR-0174-2025', NULL, 2, NULL, 91, 'DJ_500KV_GE', 'APR-GOR-0174-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-15 00:00:00', '2025-12-19 00:00:00', 'Realizar manutenção preventiva bimestral nos disjuntores', 'Edinei Rocha', '2026-05-27 15:00:00', '2026-05-27 16:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(176, 'OS-GOR-0175-2025', NULL, 2, NULL, 88, 'DJ_500KV_GE', 'APR-GOR-0175-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-15 00:00:00', '2025-12-19 00:00:00', 'Realizar manutenção preventiva bimestral nos disjuntores', 'Edinei Rocha', '2026-05-27 15:00:00', '2026-05-27 16:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(177, 'OS-GOR-0176-2025', NULL, 2, NULL, 89, 'DJ_500KV_GE', 'APR-GOR-0176-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-15 00:00:00', '2025-12-19 00:00:00', 'Realizar manutenção preventiva bimestral nos disjuntores', 'Edinei Rocha', '2026-05-28 09:00:00', '2026-05-28 10:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(178, 'OS-GOR-0177-2025', NULL, 2, NULL, 86, 'DJ_500KV_GE', 'APR-GOR-0177-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-15 00:00:00', '2025-12-19 00:00:00', 'Realizar manutenção preventiva bimestral nos disjuntores', 'Edinei Rocha', '2026-05-28 09:00:00', '2026-05-28 10:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(179, 'OS-GOR-0178-2025', NULL, 2, NULL, 87, 'DJ_500KV_GE', 'APR-GOR-0178-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-15 00:00:00', '2025-12-19 00:00:00', 'Realizar manutenção preventiva bimestral nos disjuntores', 'Edinei Rocha', '2026-05-28 09:00:00', '2026-05-28 10:30:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(180, 'OS-GOR-0179-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0179-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMANAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-11 00:00:00', '2025-12-11 00:00:00', 'Inspeção semanal preventiva do GMG-P sem carga', 'Edinei Rocha', '2026-06-16 13:42:00', '2026-06-16 15:39:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(181, 'OS-GOR-0180-2025', NULL, 2, NULL, 161, 'RE_500KV_HITACHI', 'APR-GOR-0180-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no banco de reator', 'Edinei Rocha', '2026-06-16 13:43:00', '2026-06-16 15:39:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(182, 'OS-GOR-0181-2025', NULL, 2, NULL, 163, 'RE_500KV_HITACHI', 'APR-GOR-0181-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no banco de reator', 'Edinei Rocha', '2026-06-16 13:44:00', '2026-06-16 15:39:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(183, 'OS-GOR-0182-2025', NULL, 2, NULL, 82, 'RE_500KV_HITACHI', 'APR-GOR-0182-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no banco de reator', 'Edinei Rocha', '2026-06-16 13:45:00', '2026-06-16 15:40:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(184, 'OS-GOR-0183-2025', NULL, 2, NULL, 83, 'RE_500KV_HITACHI', 'APR-GOR-0183-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no banco de reator', 'Edinei Rocha', '2026-06-16 14:52:00', '2026-06-16 15:41:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(185, 'OS-GOR-0184-2025', NULL, 2, NULL, 70, 'PR_500KV_BONOMI', 'APR-GOR-0184-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-16 14:54:00', '2026-06-16 15:41:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(186, 'OS-GOR-0185-2025', NULL, 2, NULL, 72, 'PR_500KV_BONOMI', 'APR-GOR-0185-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-16 14:53:00', '2026-06-16 15:42:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(187, 'OS-GOR-0186-2025', NULL, 2, NULL, 74, 'PR_500KV_BONOMI', 'APR-GOR-0186-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-16 14:55:00', '2026-06-16 15:42:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(188, 'OS-GOR-0187-2025', NULL, 2, NULL, 76, 'PR_500KV_BONOMI', 'APR-GOR-0187-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_6', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro Pereira', 'Alessandro Pereira', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:37:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(189, 'OS-GOR-0188-2025', NULL, 2, NULL, 76, 'PR_500KV_BONOMI', 'APR-GOR-0188-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:36:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(190, 'OS-GOR-0189-2025', NULL, 2, NULL, 71, 'PR_500KV_BONOMI', 'APR-GOR-0189-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:36:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(191, 'OS-GOR-0190-2025', NULL, 2, NULL, 73, 'PR_500KV_BONOMI', 'APR-GOR-0190-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:36:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(192, 'OS-GOR-0191-2025', NULL, 2, NULL, 75, 'PR_500KV_BONOMI', 'APR-GOR-0191-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:36:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(193, 'OS-GOR-0192-2025', NULL, 2, NULL, 77, 'PR_500KV_BONOMI', 'APR-GOR-0192-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:35:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(194, 'OS-GOR-0193-2025', NULL, 2, NULL, 77, 'PR_500KV_BONOMI', 'APR-GOR-0193-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA BIMESTRAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-22 00:00:00', '2025-12-26 00:00:00', 'Realizar manutenção preventiva bimestral no para raio', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:35:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(195, 'OS-GOR-0194-2025', NULL, 2, 776, 3486, 'GERAL', 'APR-GOR-0194-2025', 'Gentio do Ouro-BA', NULL, 'MANUTENÇÃO CORRETIVA', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-09 00:00:00', '2025-12-10 00:00:00', 'Realizar adequação de cabos de alimentação de falta CA', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:35:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(196, 'OS-GOR-0195-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0195-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMANAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-18 00:00:00', '2025-12-18 00:00:00', 'Inspeção semanal preventiva do GMG-P sem carga', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:34:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA'),
(197, 'OS-GOR-0196-2025', NULL, 2, 229, 68, 'GMG_380V_STEMAC', 'APR-GOR-0196-2025', 'Gentio do Ouro-BA', NULL, 'PREVENTIVA SEMANAL', 'NIVEL_3', 'Edinei Rocha', 'Edinei Rocha', 'Alessandro da Silva', 'Alessandro da Silva', '2025-12-30 00:00:00', '2025-12-30 00:00:00', 'Inspeção semanal preventiva do GMG-P sem carga', 'Edinei Rocha', '2026-06-02 09:00:00', '2026-06-05 13:34:00', 'RIALMA TRANSMISSORA V', 'ENCERRADA');

-- ---------------------------------------------------------------------------
-- AJUSTES OBRIGATÓRIOS ANTES DA EXECUÇÃO
-- ---------------------------------------------------------------------------
-- Estas OS não possuem id_ativo nem id_grupo_ativo. Informe a associação real.
-- UPDATE stg_os_antigas_2025 SET id_ativo = <ID>, id_grupo_ativo = <GRUPO>
-- WHERE numero_os = 'OS-GOR-0024-2025';
-- UPDATE stg_os_antigas_2025 SET id_ativo = <ID>, id_grupo_ativo = <GRUPO>
-- WHERE numero_os = 'OS-GOR-0031-2025';
-- UPDATE stg_os_antigas_2025 SET id_ativo = <ID>, id_grupo_ativo = <GRUPO>
-- WHERE numero_os = 'OS-GOR-0043-2025';
-- UPDATE stg_os_antigas_2025 SET id_ativo = <ID>, id_grupo_ativo = <GRUPO>
-- WHERE numero_os = 'OS-GOR-0064-2025';

-- Confirme e corrija as datas invertidas abaixo.
-- UPDATE stg_os_antigas_2025 SET data_inicio_programado = 'AAAA-MM-DD 00:00:00',
--     data_fim_programado = 'AAAA-MM-DD 00:00:00'
-- WHERE numero_os IN ('OS-GOR-0019-2025','OS-GOR-0020-2025',
--                     'OS-GOR-0048-2025','OS-GOR-0049-2025');
-- UPDATE stg_os_antigas_2025 SET data_inicio_execucao = 'AAAA-MM-DD HH:MM:SS',
--     data_fim_execucao = 'AAAA-MM-DD HH:MM:SS'
-- WHERE numero_os = 'OS-GOR-0021-2025';

-- Diagnóstico das pendências conhecidas e de qualquer nova inconsistência.
SELECT 'SEM_ATIVO_OU_GRUPO' AS tipo, numero_os,
       'Preencher id_ativo ou id_grupo_ativo' AS detalhe
FROM stg_os_antigas_2025
WHERE id_ativo IS NULL AND id_grupo_ativo IS NULL
UNION ALL
SELECT 'DATA_PROGRAMADA_INVERTIDA', numero_os,
       CONCAT(data_inicio_programado, ' > ', data_fim_programado)
FROM stg_os_antigas_2025
WHERE data_inicio_programado IS NOT NULL
  AND data_fim_programado IS NOT NULL
  AND data_inicio_programado > data_fim_programado
UNION ALL
SELECT 'DATA_EXECUCAO_INVERTIDA', numero_os,
       CONCAT(data_inicio_execucao, ' > ', data_fim_execucao)
FROM stg_os_antigas_2025
WHERE data_inicio_execucao IS NOT NULL
  AND data_fim_execucao IS NOT NULL
  AND data_inicio_execucao > data_fim_execucao
ORDER BY tipo, numero_os;

DROP PROCEDURE IF EXISTS executar_migracao_os_antigas_2025;
DELIMITER $$

CREATE PROCEDURE executar_migracao_os_antigas_2025(IN p_executar TINYINT)
migracao: BEGIN
    DECLARE v_qtd INT DEFAULT 0;
    DECLARE v_inseridos INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF COALESCE(p_executar, 0) <> 1 THEN
        SELECT
            'VALIDADO, NÃO EXECUTADO' AS resultado,
            'Corrija as pendências e altere @executar_migracao para 1.' AS proxima_acao;
        LEAVE migracao;
    END IF;

    SELECT COUNT(*) INTO v_qtd FROM stg_os_antigas_2025;
    IF v_qtd <> 196 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: a tabela de estágio deve conter 196 registros.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM (
        SELECT numero_os FROM stg_os_antigas_2025
        GROUP BY numero_os HAVING COUNT(*) > 1
    ) duplicadas;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: existem números de OS duplicados no estágio.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    JOIN ordem_servico o ON o.numero_os = s.numero_os;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: uma ou mais OS já existem em ordem_servico.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    JOIN ordem_servico o ON o.numero_apr = s.numero_apr
    WHERE s.numero_apr IS NOT NULL AND s.numero_apr <> '';
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: uma ou mais APR já existem em ordem_servico.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    LEFT JOIN subestacao se ON se.id_subestacao = s.id_subestacao
    WHERE se.id_subestacao IS NULL;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: há subestação inexistente.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    LEFT JOIN ativo a ON a.id_ativo = s.id_ativo
    WHERE s.id_ativo IS NOT NULL AND a.id_ativo IS NULL;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: há ativo inexistente.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    LEFT JOIN grupo_ativo g ON g.id_grupo_ativo = s.id_grupo_ativo
    WHERE s.id_grupo_ativo IS NOT NULL AND g.id_grupo_ativo IS NULL;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: há grupo de ativo inexistente.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025
    WHERE id_ativo IS NULL AND id_grupo_ativo IS NULL;
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: há OS sem ativo e sem grupo.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025 s
    LEFT JOIN ativo a ON a.id_ativo = s.id_ativo
    LEFT JOIN grupo_ativo g ON g.id_grupo_ativo = s.id_grupo_ativo
    WHERE (a.id_ativo IS NOT NULL AND a.id_subestacao <> s.id_subestacao)
       OR (g.id_grupo_ativo IS NOT NULL AND g.id_subestacao <> s.id_subestacao)
       OR (a.id_ativo IS NOT NULL AND s.id_grupo_ativo IS NOT NULL
           AND NOT (a.id_grupo_ativo <=> s.id_grupo_ativo));
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: ativo/grupo não pertence à subestação ou associação está divergente.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025
    WHERE prioridade IS NULL OR prioridade NOT REGEXP '^NIVEL_[1-6]$';
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: prioridade fora do padrão NIVEL_1 a NIVEL_6.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025
    WHERE esquema_servicos NOT IN (
        'MANUTENÇÃO PREVENTIVA', 'PREVENTIVA SEMANAL', 'PREVENTIVA MENSAL',
        'PREVENTIVA BIMESTRAL', 'PREVENTIVA TRIMESTRAL', 'PREVENTIVA SEMESTRAL',
        'PREVENTIVA ANUAL', 'PREVENTIVA BIANUAL', 'PREVENTIVA TRIANUAL',
        'PREVENTIVA A 5 ANOS', 'PREVENTIVA A 6 ANOS',
        'MANUTENÇÃO CORRETIVA', 'MANUTENÇÃO PREDITIVA',
        'Monitoramento', 'Atendimento Recomendação'
    );
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: esquema de serviços inválido.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025
    WHERE especie IS NULL OR TRIM(especie) = ''
       OR descricao_servicos IS NULL OR TRIM(descricao_servicos) = ''
       OR status <> 'ENCERRADA';
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: espécie, descrição ou status obrigatório está inválido.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM stg_os_antigas_2025
    WHERE (data_inicio_programado IS NOT NULL AND data_fim_programado IS NOT NULL
           AND data_inicio_programado > data_fim_programado)
       OR (data_inicio_execucao IS NOT NULL AND data_fim_execucao IS NOT NULL
           AND data_inicio_execucao > data_fim_execucao);
    IF v_qtd > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: existem datas iniciais posteriores às datas finais.';
    END IF;

    START TRANSACTION;

    INSERT INTO ordem_servico (
        numero_os, numero_si, id_subestacao, id_ativo, especie, numero_apr,
        localizacao, complemento, esquema_servicos, prioridade, responsavel,
        responsavel_manutencao, responsavel_operacao, substituto,
        data_inicio_programado, data_fim_programado, descricao_servicos,
        emissor, data_inicio_execucao, data_fim_execucao, centro_custos,
        status, criado_em, origem, id_grupo_ativo, id_funcao_operacao,
        escopo_ativo
    )
    SELECT
        s.numero_os, s.numero_si, s.id_subestacao, s.id_ativo,
        COALESCE(NULLIF(NULLIF(TRIM(a.especie), ''), 'NULL'), s.especie),
        s.numero_apr, s.localizacao, s.complemento, s.esquema_servicos,
        s.prioridade, s.responsavel, s.responsavel_manutencao,
        s.responsavel_operacao, s.substituto, s.data_inicio_programado,
        s.data_fim_programado, s.descricao_servicos, s.emissor,
        s.data_inicio_execucao, s.data_fim_execucao, s.centro_custos,
        s.status, CURRENT_TIMESTAMP, @lote_migracao, s.id_grupo_ativo,
        COALESCE(a.id_funcao_operacao, g.id_funcao_operacao),
        CASE WHEN s.id_ativo IS NOT NULL THEN 'FASE' ELSE 'GRUPO' END
    FROM stg_os_antigas_2025 s
    LEFT JOIN ativo a ON a.id_ativo = s.id_ativo
    LEFT JOIN grupo_ativo g ON g.id_grupo_ativo = s.id_grupo_ativo
    WHERE NOT EXISTS (
        SELECT 1 FROM ordem_servico o WHERE o.numero_os = s.numero_os
    );

    SET v_inseridos = ROW_COUNT();
    IF v_inseridos <> 196 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: quantidade inserida diferente de 196.';
    END IF;

    SELECT COUNT(*) INTO v_qtd
    FROM ordem_servico
    WHERE origem = @lote_migracao;
    IF v_qtd <> 196 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migração abortada: conferência final do lote diferente de 196.';
    END IF;

    COMMIT;

    SELECT @lote_migracao AS lote, v_inseridos AS registros_inseridos,
           'MIGRAÇÃO CONCLUÍDA' AS resultado;
END$$

DELIMITER ;

CALL executar_migracao_os_antigas_2025(@executar_migracao);
DROP PROCEDURE IF EXISTS executar_migracao_os_antigas_2025;

-- Conferência após uma execução bem-sucedida:
SELECT COUNT(*) AS total_lote,
       COUNT(DISTINCT numero_os) AS os_distintas,
       MIN(numero_os) AS primeira_os,
       MAX(numero_os) AS ultima_os
FROM ordem_servico
WHERE origem = @lote_migracao;

-- ROLLBACK APÓS COMMIT, se necessário. Execute conscientemente:
-- START TRANSACTION;
-- DELETE FROM ordem_servico WHERE origem = 'MIGRACAO_OS_GOR_2025_20260909';
-- SELECT ROW_COUNT() AS registros_removidos;
-- COMMIT;
