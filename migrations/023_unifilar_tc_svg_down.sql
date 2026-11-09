-- Restaura as dimensoes anteriores do catalogo para o TC.
UPDATE unifilar_tipo_componente
SET largura = 40, altura = 72
WHERE tipo = 'TC';
