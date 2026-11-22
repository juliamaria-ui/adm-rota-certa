CREATE VIEW vw_veiculos_disponiveis AS
SELECT placa, marca, modelo, ano, valor_diaria, status
FROM veiculos
WHERE status = 'DISPONIVEL';

CREATE VIEW vw_locacoes_detalhadas AS
SELECT l.id_locacao, l.status AS status_locacao, l.data_retirada,
       l.data_devolucao, l.data_devolucao_real,
       CASE WHEN l.status = 'CANCELADA' THEN 0
            ELSE l.valor_total + COALESCE(m.total_multas, 0) END AS valor_total,
       l.cpf_cliente, c.nome AS nome_cliente, c.telefone AS telefone_cliente,
       v.placa AS placa_veiculo, v.marca AS marca_veiculo, v.modelo AS modelo_veiculo,
       l.valor_diaria_contratada AS valor_diaria,
       f.id_funcionario, f.nome AS nome_funcionario,
       COALESCE(p.total_pago, 0) AS total_pago,
       COALESCE(m.total_multas, 0) AS total_multas,
       CASE WHEN l.status = 'CANCELADA' THEN 0
            ELSE GREATEST(l.valor_total + COALESCE(m.total_multas, 0) -
                          COALESCE(p.total_pago, 0), 0) END AS saldo
FROM locacoes l
JOIN pessoas c ON c.cpf = l.cpf_cliente
JOIN veiculos v ON v.placa = l.placa_veiculo
JOIN funcionarios f ON f.id_funcionario = l.id_funcionario
LEFT JOIN (SELECT id_locacao, SUM(valor) AS total_pago FROM pagamentos GROUP BY id_locacao) p
       ON p.id_locacao = l.id_locacao
LEFT JOIN (SELECT id_locacao, SUM(valor) AS total_multas FROM multas GROUP BY id_locacao) m
       ON m.id_locacao = l.id_locacao;

CREATE VIEW vw_faturamento_frota AS
SELECT marca_veiculo AS marca, modelo_veiculo AS modelo,
       COUNT(*) AS total_locacoes, SUM(total_pago) AS receita_total
FROM vw_locacoes_detalhadas
WHERE status_locacao = 'FINALIZADA'
GROUP BY marca_veiculo, modelo_veiculo;
