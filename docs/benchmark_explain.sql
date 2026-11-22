-- Selecione o esquema revisado. Compare o campo key, rows e Extra.
EXPLAIN FORMAT=TRADITIONAL SELECT id_locacao, status, data_retirada
FROM locacoes WHERE status = 'FINALIZADA'
  AND data_retirada >= '2026-11-01' AND data_retirada < '2026-12-01'
ORDER BY data_retirada;
EXPLAIN FORMAT=TRADITIONAL SELECT id_locacao, status, data_retirada
FROM locacoes IGNORE INDEX (ix_locacoes_status_retirada)
WHERE status = 'FINALIZADA'
  AND data_retirada >= '2026-11-01' AND data_retirada < '2026-12-01'
ORDER BY data_retirada;

EXPLAIN FORMAT=TRADITIONAL SELECT id_manutencao, placa_veiculo, data_inicio
FROM manutencoes WHERE placa_veiculo = 'DEM0A01' ORDER BY data_inicio DESC;
EXPLAIN FORMAT=TRADITIONAL SELECT id_manutencao, placa_veiculo, data_inicio
FROM manutencoes IGNORE INDEX (ix_manutencoes_veiculo_inicio)
WHERE placa_veiculo = 'DEM0A01' ORDER BY data_inicio DESC;

EXPLAIN FORMAT=TRADITIONAL SELECT placa, marca, modelo
FROM veiculos WHERE status = 'DISPONIVEL' ORDER BY marca, modelo;
EXPLAIN FORMAT=TRADITIONAL SELECT placa, marca, modelo
FROM veiculos IGNORE INDEX (ix_veiculos_status_modelo)
WHERE status = 'DISPONIVEL' ORDER BY marca, modelo;
