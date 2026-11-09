-- Restaura as dimensoes anteriores do catalogo para o reator.
UPDATE unifilar_tipo_componente
SET largura = 44, altura = 80
WHERE tipo = 'REATOR';
