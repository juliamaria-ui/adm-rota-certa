-- Execute em um esquema de demonstração recém-criado, já selecionado.
INSERT INTO pessoas(cpf, nome) VALUES
('90000000001', 'Cliente fictício'), ('90000000002', 'Condutor fictício');
INSERT INTO clientes(cpf) VALUES ('90000000001');
INSERT INTO condutores(cpf, cnh, validade_cnh) VALUES
('90000000001', 'DEMO01', '2030-01-01'), ('90000000002', 'DEMO02', '2030-01-01');
INSERT INTO funcionarios(cpf, nome, email, usuario)
VALUES ('90000000003', 'Funcionário fictício', 'demo@example.org', 'demo');
SET @funcionario = LAST_INSERT_ID();
INSERT INTO veiculos(placa, marca, modelo, ano, valor_diaria, status)
VALUES ('DEM0A01', 'Fiat', 'Argo', 2024, 150.00, 'DISPONIVEL');

START TRANSACTION;
INSERT INTO locacoes(cpf_cliente, placa_veiculo, id_funcionario, data_retirada,
                     data_devolucao, valor_diaria_contratada, valor_total, status)
VALUES ('90000000001', 'DEM0A01', @funcionario, '2026-11-20', '2026-11-22', 150, 300, 'ATIVA');
SET @locacao = LAST_INSERT_ID();
INSERT INTO locacao_condutor(id_locacao, cpf_condutor)
VALUES (@locacao, '90000000001'), (@locacao, '90000000002');
COMMIT;
SELECT placa, status FROM veiculos WHERE placa = 'DEM0A01';

UPDATE veiculos SET valor_diaria = 180.00 WHERE placa = 'DEM0A01';
START TRANSACTION;
CALL sp_finalizar_locacao(@locacao, '2026-11-23');
COMMIT;
INSERT INTO multas(id_locacao, motivo, valor, data_multa)
VALUES (@locacao, 'Combustível', 30, '2026-11-23');
INSERT INTO pagamentos(id_locacao, valor, forma_pagamento, data_pagamento)
VALUES (@locacao, 480, 'PIX', '2026-11-23');

SELECT id_locacao, nome_cliente, valor_diaria, valor_total, saldo, status_locacao
FROM vw_locacoes_detalhadas WHERE id_locacao = @locacao;
SELECT p.nome, c.cnh FROM locacao_condutor lc
JOIN condutores c ON c.cpf = lc.cpf_condutor JOIN pessoas p ON p.cpf = c.cpf
WHERE lc.id_locacao = @locacao;

INSERT INTO manutencoes(placa_veiculo, tipo, descricao, custo, data_inicio)
VALUES ('DEM0A01', 'PREVENTIVA', 'Troca de óleo', 160, '2026-11-23');
SET @manutencao = LAST_INSERT_ID();
SELECT placa, status FROM veiculos WHERE placa = 'DEM0A01';
UPDATE manutencoes SET data_fim = '2026-11-24' WHERE id_manutencao = @manutencao;
SELECT placa, status FROM vw_veiculos_disponiveis WHERE placa = 'DEM0A01';

INSERT INTO pessoas(cpf, nome) VALUES ('90000000004', 'Cadastro temporário');
DELETE FROM pessoas WHERE cpf = '90000000004';
