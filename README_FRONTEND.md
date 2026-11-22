# Interface da locadora

A interface é servida pelo Flask em `http://127.0.0.1:5000/app/`. Depois do login, use o menu para cadastrar um titular, registrar condutores, abrir uma locação e acompanhar a frota.

- **Clientes e Condutores** compartilham o CPF. A habilitação exige número e validade. O condutor pode ser registrado separadamente.
- **Locações** permite selecionar mais de um condutor. Use Ctrl no Windows ou Command no macOS para selecionar itens separados. Na edição de um contrato ativo, escolha **Finalizada** e informe a devolução efetiva. O botão **Cancelar** preserva o histórico.
- **Manutenções** registra a indisponibilidade e o custo do serviço. Use **Concluir** para registrar a data de término.
- **Multas** exige data da infração entre a retirada e a devolução, inclusive. Durante a locação usa a devolução prevista; depois da devolução usa a efetiva. O status começa como **Pendente**.
- **Pagamentos → Multa** permite selecionar a locação e uma multa pendente. O valor integral é preenchido e bloqueado para edição. Cada multa aceita um único pagamento vinculado e passa para **Acertada**. Excluir esse pagamento devolve o status para **Pendente**. Pagamentos do tipo **Locação** não alteram o status das multas.
- **Dashboard** mostra a lista de veículos disponíveis e os valores recebidos por modelo em locações finalizadas.

A API de locações aceita filtros `status`, `retirada_de` e `retirada_ate` no formato `AAAA-MM-DD`. O histórico de manutenções pode ser filtrado pelo parâmetro `placa`.
