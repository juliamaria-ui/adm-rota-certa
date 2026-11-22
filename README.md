# Locadora de veículos — Seminário II

Aplicação Flask com MySQL para registrar locações, condutores autorizados, devoluções, pagamentos, multas e manutenções.

## Executar no Windows

1. Inicie o MySQL local e abra um terminal PowerShell nesta pasta.
2. Na primeira execução, copie `.env.example` para `.env` e preencha as credenciais do MySQL. Mantenha `DB_DATABASE=locadora_bd2` para usar o esquema desta versão.
3. Crie o ambiente virtual e execute a aplicação com o Python desse ambiente.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

4. Abra [a locadora no navegador](http://127.0.0.1:5000/app/). As credenciais de demonstração configuradas no exemplo são `admin` e `admin123`.

A primeira execução cria as tabelas e instala os objetos SQL no esquema configurado. Para criar a estrutura pelo Workbench, selecione `locadora_bd2` e execute, uma vez e em ordem, os scripts `sql/01_schema.sql` até `sql/05_triggers.sql`. Em seguida, inicie a aplicação para criar o usuário e os veículos de demonstração.

## Demonstração do seminário

1. Em Clientes e Condutores, cadastre o titular e dois condutores, com CNH válida na data de retirada. O titular também pode ser condutor.
2. Abra uma locação e selecione os dois condutores. A frota passa a exibir o veículo como alugado.
3. Altere a tarifa vigente no cadastro do veículo e finalize a locação informando a devolução efetiva. A cobrança usa a tarifa contratada e o período efetivo, com mínimo de uma diária.
4. Registre um pagamento e uma multa. O painel usa as views para mostrar a disponibilidade, detalhes da locação e recebimentos por modelo.
5. Abra uma manutenção para o veículo devolvido. Tente alugá-lo e depois conclua a manutenção para verificar o retorno à disponibilidade.
6. Cancele uma locação ativa para verificar a preservação do contrato e dos vínculos.

Em `docs/seminario_ii.md` estão o resumo, as regras, o diagrama e as referências. O dicionário e as consultas de comparação de planos ficam em `docs/`. O arquivo `sql/06_demonstracao.sql` usa dados fictícios e serve como roteiro adicional no Workbench.

## Testes e base legada

Na inicialização, o projeto adiciona automaticamente `pagamentos.id_multa` às bases desta versão que ainda não possuem o campo, com chave estrangeira e unicidade. Os pagamentos existentes são preservados sem vínculo com multas. O status de cada multa é calculado pela existência do pagamento vinculado. A API aceita `tipo: "MULTA"` e `id_multa` para quitar uma multa da locação selecionada; o valor é obtido da multa, e um valor informado diferente do integral é rejeitado.

`python -m pytest -q` executa os testes com SQLite em memória. Para exercitar procedures e triggers reais, a variável `LOCADORA_TEST_DATABASE` pode apontar para um esquema **descartável** com o nome `locadora_teste`. Os testes recriam as tabelas desse esquema.

Uma base legada pode ter CPFs com pontuação, contratos sem diária histórica e devolução sem data efetiva registrada. A migração exige conferir esses dados com os contratos e completar as CNHs antes de transferir os registros. A aplicação identifica o esquema legado e informa como selecionar um esquema novo, sem inferir valores históricos.
