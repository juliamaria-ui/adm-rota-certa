-- Selecione o esquema de destino antes de executar.

CREATE TABLE funcionarios (
	id_funcionario INTEGER NOT NULL AUTO_INCREMENT, 
	nome VARCHAR(100) NOT NULL, 
	cpf VARCHAR(14) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	senha_hash VARCHAR(255), 
	telefone VARCHAR(20), 
	cargo VARCHAR(50), 
	usuario VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id_funcionario), 
	UNIQUE (cpf), 
	UNIQUE (email), 
	UNIQUE (usuario)
);

CREATE TABLE pessoas (
	cpf VARCHAR(11) NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	telefone VARCHAR(20), 
	email VARCHAR(100), 
	PRIMARY KEY (cpf)
);

CREATE TABLE veiculos (
	placa VARCHAR(10) NOT NULL, 
	marca VARCHAR(50) NOT NULL, 
	modelo VARCHAR(50) NOT NULL, 
	ano INTEGER NOT NULL, 
	valor_diaria NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (placa), 
	CONSTRAINT ck_veiculo_status CHECK (status in ('DISPONIVEL', 'ALUGADO', 'MANUTENCAO')), 
	CONSTRAINT ck_veiculo_diaria CHECK (valor_diaria > 0)
);

CREATE TABLE clientes (
	cpf VARCHAR(11) NOT NULL, 
	PRIMARY KEY (cpf), 
	FOREIGN KEY(cpf) REFERENCES pessoas (cpf)
);

CREATE TABLE condutores (
	cpf VARCHAR(11) NOT NULL, 
	cnh VARCHAR(20) NOT NULL, 
	validade_cnh DATE NOT NULL, 
	PRIMARY KEY (cpf), 
	FOREIGN KEY(cpf) REFERENCES pessoas (cpf), 
	UNIQUE (cnh)
);

CREATE TABLE manutencoes (
	id_manutencao INTEGER NOT NULL AUTO_INCREMENT, 
	placa_veiculo VARCHAR(10) NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	descricao VARCHAR(255) NOT NULL, 
	custo NUMERIC(10, 2) NOT NULL, 
	data_inicio DATE NOT NULL, 
	data_fim DATE, 
	PRIMARY KEY (id_manutencao), 
	CONSTRAINT ck_manutencao_tipo CHECK (tipo in ('PREVENTIVA', 'CORRETIVA')), 
	CONSTRAINT ck_manutencao_datas CHECK (data_fim is null or data_fim >= data_inicio), 
	CONSTRAINT ck_manutencao_custo CHECK (custo >= 0), 
	FOREIGN KEY(placa_veiculo) REFERENCES veiculos (placa)
);

CREATE TABLE locacoes (
	id_locacao INTEGER NOT NULL AUTO_INCREMENT, 
	cpf_cliente VARCHAR(11) NOT NULL, 
	placa_veiculo VARCHAR(10) NOT NULL, 
	id_funcionario INTEGER NOT NULL, 
	data_retirada DATE NOT NULL, 
	data_devolucao DATE NOT NULL, 
	data_devolucao_real DATE, 
	valor_diaria_contratada NUMERIC(10, 2) NOT NULL, 
	valor_total NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_locacao), 
	CONSTRAINT ck_locacao_status CHECK (status in ('ATIVA', 'FINALIZADA', 'CANCELADA')), 
	CONSTRAINT ck_locacao_prevista CHECK (data_devolucao >= data_retirada), 
	CONSTRAINT ck_locacao_real CHECK ((status = 'FINALIZADA' AND data_devolucao_real IS NOT NULL AND data_devolucao_real >= data_retirada) OR (status IN ('ATIVA','CANCELADA') AND data_devolucao_real IS NULL)), 
	CONSTRAINT ck_locacao_valores CHECK (valor_total >= 0 and valor_diaria_contratada > 0), 
	FOREIGN KEY(cpf_cliente) REFERENCES clientes (cpf), 
	FOREIGN KEY(placa_veiculo) REFERENCES veiculos (placa), 
	FOREIGN KEY(id_funcionario) REFERENCES funcionarios (id_funcionario)
);

CREATE TABLE locacao_condutor (
	id_locacao INTEGER NOT NULL, 
	cpf_condutor VARCHAR(11) NOT NULL, 
	PRIMARY KEY (id_locacao, cpf_condutor), 
	FOREIGN KEY(id_locacao) REFERENCES locacoes (id_locacao), 
	FOREIGN KEY(cpf_condutor) REFERENCES condutores (cpf)
);

CREATE TABLE multas (
	id_multa INTEGER NOT NULL AUTO_INCREMENT, 
	id_locacao INTEGER NOT NULL, 
	motivo VARCHAR(255) NOT NULL, 
	valor NUMERIC(10, 2) NOT NULL, 
	data_multa DATE NOT NULL, 
	PRIMARY KEY (id_multa), 
	FOREIGN KEY(id_locacao) REFERENCES locacoes (id_locacao)
);

CREATE TABLE pagamentos (
	id_pagamento INTEGER NOT NULL AUTO_INCREMENT, 
	id_locacao INTEGER NOT NULL, 
	id_multa INTEGER NULL,
	valor NUMERIC(10, 2) NOT NULL, 
	forma_pagamento VARCHAR(30) NOT NULL, 
	data_pagamento DATE NOT NULL, 
	PRIMARY KEY (id_pagamento), 
	FOREIGN KEY(id_locacao) REFERENCES locacoes (id_locacao),
	CONSTRAINT uq_pagamentos_multa UNIQUE (id_multa),
	CONSTRAINT fk_pagamentos_multa FOREIGN KEY(id_multa) REFERENCES multas (id_multa)
);
