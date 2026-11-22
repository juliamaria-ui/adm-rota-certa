CREATE INDEX ix_locacoes_status_retirada ON locacoes (status, data_retirada);
CREATE INDEX ix_manutencoes_veiculo_inicio ON manutencoes (placa_veiculo, data_inicio);
CREATE INDEX ix_veiculos_status_modelo ON veiculos (status, marca, modelo);
