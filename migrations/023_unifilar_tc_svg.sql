-- 023: ajusta as dimensoes do TC para o SVG de referencia.
UPDATE unifilar_tipo_componente
SET largura = 32, altura = 108
WHERE tipo = 'TC';
