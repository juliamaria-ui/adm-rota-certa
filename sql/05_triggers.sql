DELIMITER //
CREATE TRIGGER trg_locacao_abertura BEFORE INSERT ON locacoes
FOR EACH ROW
BEGIN
    IF NEW.status <> 'ATIVA' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A locação deve iniciar como ativa.';
    END IF;
    UPDATE veiculos SET status = 'ALUGADO'
    WHERE placa = NEW.placa_veiculo AND status = 'DISPONIVEL';
    IF ROW_COUNT() <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Veículo indisponível para locação.';
    END IF;
    SET NEW.valor_diaria_contratada = (SELECT valor_diaria FROM veiculos WHERE placa = NEW.placa_veiculo);
    SET NEW.valor_total = NEW.valor_diaria_contratada *
        GREATEST(DATEDIFF(NEW.data_devolucao, NEW.data_retirada), 1);
END //

CREATE TRIGGER trg_locacao_transicao BEFORE UPDATE ON locacoes
FOR EACH ROW
BEGIN
    IF OLD.status <> 'ATIVA' OR NEW.placa_veiculo <> OLD.placa_veiculo
       OR NEW.cpf_cliente <> OLD.cpf_cliente OR NEW.id_funcionario <> OLD.id_funcionario
       OR NEW.data_retirada <> OLD.data_retirada
       OR NEW.valor_diaria_contratada <> OLD.valor_diaria_contratada THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Contrato encerrado ou alteração de dados contratuais protegidos.';
    END IF;
    IF NEW.status = 'FINALIZADA' THEN
        SET NEW.valor_total = NEW.valor_diaria_contratada *
            GREATEST(DATEDIFF(NEW.data_devolucao_real, NEW.data_retirada), 1);
    ELSEIF NEW.status = 'ATIVA' THEN
        SET NEW.valor_total = NEW.valor_diaria_contratada *
            GREATEST(DATEDIFF(NEW.data_devolucao, NEW.data_retirada), 1);
    END IF;
    IF NEW.status IN ('FINALIZADA', 'CANCELADA') THEN
        UPDATE veiculos SET status = 'DISPONIVEL'
        WHERE placa = OLD.placa_veiculo AND status = 'ALUGADO';
    END IF;
END //

CREATE TRIGGER trg_locacao_preservar BEFORE DELETE ON locacoes
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Preserve o contrato no histórico usando o cancelamento.';
END //

CREATE TRIGGER trg_cnh_autorizacao BEFORE INSERT ON locacao_condutor
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM condutores c JOIN locacoes l ON l.id_locacao = NEW.id_locacao
        WHERE c.cpf = NEW.cpf_condutor AND l.status = 'ATIVA'
          AND c.validade_cnh >= l.data_retirada
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Locação inativa ou CNH inválida na retirada.';
    END IF;
END //

CREATE TRIGGER trg_manutencao_abertura BEFORE INSERT ON manutencoes
FOR EACH ROW
BEGIN
    IF NEW.data_fim IS NOT NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A manutenção deve iniciar sem data de fim.';
    END IF;
    UPDATE veiculos SET status = 'MANUTENCAO'
    WHERE placa = NEW.placa_veiculo AND status = 'DISPONIVEL';
    IF ROW_COUNT() <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Veículo indisponível para manutenção.';
    END IF;
END //

CREATE TRIGGER trg_manutencao_conclusao BEFORE UPDATE ON manutencoes
FOR EACH ROW
BEGIN
    IF OLD.data_fim IS NOT NULL OR NEW.placa_veiculo <> OLD.placa_veiculo
       OR NEW.data_inicio <> OLD.data_inicio THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Manutenção concluída ou dados iniciais protegidos.';
    END IF;
    IF NEW.data_fim IS NOT NULL THEN
        UPDATE veiculos SET status = 'DISPONIVEL'
        WHERE placa = OLD.placa_veiculo AND status = 'MANUTENCAO';
    END IF;
END //

CREATE TRIGGER trg_manutencao_preservar BEFORE DELETE ON manutencoes
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'O histórico de manutenção deve ser preservado.';
END //
DELIMITER ;
