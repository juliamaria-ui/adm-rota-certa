DELIMITER //
CREATE PROCEDURE sp_finalizar_locacao(IN p_id INT, IN p_devolucao DATE)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_retirada DATE;
    SELECT status, data_retirada INTO v_status, v_retirada
    FROM locacoes WHERE id_locacao = p_id FOR UPDATE;

    IF v_status IS NULL OR v_status <> 'ATIVA' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A locação deve existir e estar ativa.';
    END IF;
    IF p_devolucao IS NULL OR p_devolucao < v_retirada THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Data efetiva da devolução inválida.';
    END IF;
    UPDATE locacoes
    SET status = 'FINALIZADA', data_devolucao_real = p_devolucao
    WHERE id_locacao = p_id;
END //
DELIMITER ;
