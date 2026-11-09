-- Ajusta as dimensoes do reator para manter a proporcao do SVG de referencia.
UPDATE unifilar_tipo_componente
SET largura = 44, altura = 110
WHERE tipo = 'REATOR';
