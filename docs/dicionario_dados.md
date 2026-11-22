# Dicionário de dados

PK indica chave primária. FK indica chave estrangeira. AI indica incremento automático. NULL indica um campo que pode ficar sem preenchimento.

## funcionarios

**Descrição** — Responsáveis pelo atendimento e pelo acesso à aplicação.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_funcionario` | Identificador do funcionário | INTEGER | — | PK, AI |
| `nome` | Nome completo | VARCHAR | 100 | NOT NULL |
| `cpf` | Identificação da pessoa | VARCHAR | 14 | NOT NULL, UNIQUE |
| `email` | Endereço eletrônico | VARCHAR | 100 | NOT NULL, UNIQUE |
| `senha_hash` | Hash da senha de acesso | VARCHAR | 255 | NULL |
| `telefone` | Contato telefônico | VARCHAR | 20 | NULL |
| `cargo` | Função do funcionário | VARCHAR | 50 | NULL |
| `usuario` | Identificador de login | VARCHAR | 50 | NOT NULL, UNIQUE |

## pessoas

**Descrição** — Dados cadastrais compartilhados por clientes e condutores.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `cpf` | Identificação da pessoa | VARCHAR | 11 | PK |
| `nome` | Nome completo | VARCHAR | 100 | NOT NULL |
| `telefone` | Contato telefônico | VARCHAR | 20 | NULL |
| `email` | Endereço eletrônico | VARCHAR | 100 | NULL |

## veiculos

**Descrição** — Cadastro da frota, tarifa vigente e estado controlado pelas rotinas SQL.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `placa` | Placa do veículo | VARCHAR | 10 | PK |
| `marca` | Fabricante do veículo | VARCHAR | 50 | NOT NULL |
| `modelo` | Modelo comercial | VARCHAR | 50 | NOT NULL |
| `ano` | Ano de fabricação | INTEGER | — | NOT NULL |
| `valor_diaria` | Tarifa vigente por dia | NUMERIC | 10, 2 | NOT NULL |
| `status` | Estado operacional | VARCHAR | 20 | NOT NULL |

**Observações** — Restrições adicionais

- `status in ('DISPONIVEL', 'ALUGADO', 'MANUTENCAO')`
- `valor_diaria > 0`

## clientes

**Descrição** — Pessoas que podem contratar locações.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `cpf` | Identificação da pessoa | VARCHAR | 11 | PK, FK para pessoas.cpf |

## condutores

**Descrição** — Pessoas habilitadas a dirigir com CNH e vencimento.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `cpf` | Identificação da pessoa | VARCHAR | 11 | PK, FK para pessoas.cpf |
| `cnh` | Número da habilitação | VARCHAR | 20 | NOT NULL, UNIQUE |
| `validade_cnh` | Vencimento da habilitação | DATE | — | NOT NULL |

## manutencoes

**Descrição** — Eventos de manutenção por veículo.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_manutencao` | Identificador do serviço | INTEGER | — | PK, AI |
| `placa_veiculo` | Placa do veículo da operação | VARCHAR | 10 | NOT NULL, FK para veiculos.placa |
| `tipo` | Classificação preventiva ou corretiva | VARCHAR | 10 | NOT NULL |
| `descricao` | Serviço realizado | VARCHAR | 255 | NOT NULL |
| `custo` | Custo registrado para a manutenção | NUMERIC | 10, 2 | NOT NULL |
| `data_inicio` | Data de início do serviço | DATE | — | NOT NULL |
| `data_fim` | Data de encerramento do serviço | DATE | — | NULL |

**Observações** — Restrições adicionais

- `custo >= 0`
- `data_fim is null or data_fim >= data_inicio`
- `tipo in ('PREVENTIVA', 'CORRETIVA')`

## locacoes

**Descrição** — Histórico de contratos, diária pactuada e situação da devolução.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_locacao` | Identificador da locação | INTEGER | — | PK, AI |
| `cpf_cliente` | CPF do titular do contrato | VARCHAR | 11 | NOT NULL, FK para clientes.cpf |
| `placa_veiculo` | Placa do veículo da operação | VARCHAR | 10 | NOT NULL, FK para veiculos.placa |
| `id_funcionario` | Identificador do funcionário | INTEGER | — | NOT NULL, FK para funcionarios.id_funcionario |
| `data_retirada` | Data de retirada | DATE | — | NOT NULL |
| `data_devolucao` | Data prevista de devolução | DATE | — | NOT NULL |
| `data_devolucao_real` | Data efetiva de devolução | DATE | — | NULL |
| `valor_diaria_contratada` | Tarifa por dia contratada | NUMERIC | 10, 2 | NOT NULL |
| `valor_total` | Valor das diárias, antes de multas e pagamentos | NUMERIC | 10, 2 | NOT NULL |
| `status` | Estado operacional | VARCHAR | 20 | NOT NULL |

**Observações** — Restrições adicionais

- `(status = 'FINALIZADA' AND data_devolucao_real IS NOT NULL AND data_devolucao_real >= data_retirada) OR (status IN ('ATIVA','CANCELADA') AND data_devolucao_real IS NULL)`
- `data_devolucao >= data_retirada`
- `status in ('ATIVA', 'FINALIZADA', 'CANCELADA')`
- `valor_total >= 0 and valor_diaria_contratada > 0`

## locacao_condutor

**Descrição** — Autorizações por contrato sem duplicação do par locação e condutor.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_locacao` | Identificador da locação | INTEGER | — | PK, FK para locacoes.id_locacao |
| `cpf_condutor` | CPF do condutor autorizado | VARCHAR | 11 | PK, FK para condutores.cpf |

## multas

**Descrição** — Multas ou cobranças adicionais associadas ao contrato.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_multa` | Identificador da multa | INTEGER | — | PK, AI |
| `id_locacao` | Identificador da locação | INTEGER | — | NOT NULL, FK para locacoes.id_locacao |
| `motivo` | Motivo da cobrança | VARCHAR | 255 | NOT NULL |
| `valor` | Valor em reais | NUMERIC | 10, 2 | NOT NULL |
| `data_multa` | Data da ocorrência | DATE | — | NOT NULL |

A API exige `data_retirada <= data_multa <= COALESCE(data_devolucao_real, data_devolucao)`. O campo `status` retornado pela API é calculado: `PENDENTE` sem pagamento vinculado, `ACERTADA` quando existe esse pagamento. A exclusão do pagamento restaura o estado pendente.

## pagamentos

**Descrição** — Recebimentos vinculados ao contrato.

| Nome | Descrição | Tipo de dado | Tamanho | Restrições de domínio |
| --- | --- | --- | --- | --- |
| `id_pagamento` | Identificador do recebimento | INTEGER | — | PK, AI |
| `id_multa` | Multa quitada integralmente; nulo para pagamentos da locação | INTEGER | — | NULL, UNIQUE, FK para multas.id_multa |
| `id_locacao` | Identificador da locação | INTEGER | — | NOT NULL, FK para locacoes.id_locacao |
| `valor` | Valor em reais | NUMERIC | 10, 2 | NOT NULL |
| `forma_pagamento` | Meio usado no pagamento | VARCHAR | 30 | NOT NULL |
| `data_pagamento` | Data do recebimento | DATE | — | NOT NULL |
