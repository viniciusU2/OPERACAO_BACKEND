-- Normaliza o emissor das OS originadas de planos de manutencao.
--
-- Regras:
-- 1. Somente OS vinculadas por id_plano_manutencao sao consideradas.
-- 2. Emissores que ja comecam com "Plano #" permanecem inalterados.
-- 3. Quando o emissor atual identifica um colaborador e editado_por esta vazio,
--    o colaborador e preservado em editado_por.
-- 4. O emissor passa a identificar o plano no mesmo formato usado pela geracao
--    atual de OS: "Plano #ID - tipo do ativo".
-- 5. A tabela de backup torna a alteracao auditavel e reversivel.

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS backup_os_emissor_plano_20261002 (
    id_os INT NOT NULL,
    numero_os VARCHAR(30) NOT NULL,
    id_plano_manutencao INT NOT NULL,
    emissor_anterior TEXT NULL,
    editado_por_anterior TEXT NULL,
    emissor_normalizado TEXT NOT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_os)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

START TRANSACTION;

INSERT IGNORE INTO backup_os_emissor_plano_20261002 (
    id_os,
    numero_os,
    id_plano_manutencao,
    emissor_anterior,
    editado_por_anterior,
    emissor_normalizado
)
SELECT
    os.id_os,
    os.numero_os,
    os.id_plano_manutencao,
    os.emissor,
    os.editado_por,
    CONCAT(
        'Plano #',
        pm.id_plano_manutencao,
        ' - ',
        COALESCE(
            NULLIF(TRIM(ta.nome), ''),
            NULLIF(TRIM(pm.descricao_geral), ''),
            'Manutencao preventiva'
        )
    )
FROM ordem_servico AS os
INNER JOIN plano_manutencao AS pm
    ON pm.id_plano_manutencao = os.id_plano_manutencao
LEFT JOIN tipo_ativo AS ta
    ON ta.id_tipo_ativo = pm.id_tipo_ativo
WHERE os.id_plano_manutencao IS NOT NULL
  AND TRIM(COALESCE(os.emissor, '')) NOT LIKE 'Plano #%';

UPDATE ordem_servico AS os
INNER JOIN plano_manutencao AS pm
    ON pm.id_plano_manutencao = os.id_plano_manutencao
LEFT JOIN tipo_ativo AS ta
    ON ta.id_tipo_ativo = pm.id_tipo_ativo
SET
    os.editado_por = CASE
        WHEN NULLIF(TRIM(COALESCE(os.editado_por, '')), '') IS NULL
             AND NULLIF(TRIM(COALESCE(os.emissor, '')), '') IS NOT NULL
        THEN TRIM(os.emissor)
        ELSE os.editado_por
    END,
    os.emissor = CONCAT(
        'Plano #',
        pm.id_plano_manutencao,
        ' - ',
        COALESCE(
            NULLIF(TRIM(ta.nome), ''),
            NULLIF(TRIM(pm.descricao_geral), ''),
            'Manutencao preventiva'
        )
    )
WHERE os.id_plano_manutencao IS NOT NULL
  AND TRIM(COALESCE(os.emissor, '')) NOT LIKE 'Plano #%';

COMMIT;

-- Validacao esperada apos a execucao: zero registros.
SELECT
    os.id_os,
    os.numero_os,
    os.id_plano_manutencao,
    os.emissor,
    os.editado_por
FROM ordem_servico AS os
WHERE os.id_plano_manutencao IS NOT NULL
  AND TRIM(COALESCE(os.emissor, '')) NOT LIKE 'Plano #%'
ORDER BY os.id_os;
