const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function interfaceMultas() {
  const label = { hidden: true };
  const submit = { disabled: false };
  const pagamentos = {
    elements: {
      tipo: { value: 'MULTA' }, id_locacao: { value: '10' },
      id_multa: { value: '', closest: () => label },
      valor: { value: '', readOnly: false }
    },
    querySelector: () => submit
  };
  const multas = { elements: { id_locacao: { value: '10' }, data_multa: {} } };
  const context = vm.createContext({
    window: { location: { origin: 'http://localhost' } },
    document: {
      addEventListener() {},
      querySelector: selector => selector.includes('pagamentos') ? pagamentos : multas
    }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../frontend/script.js'), 'utf8'), context);
  const api = vm.runInContext('({ state, syncPagamentoForm, syncMultaForm })', context);
  api.state.multas = [
    { id_multa: 1, id_locacao: 10, status: 'PENDENTE', valor: 80, motivo: 'Infração' },
    { id_multa: 2, id_locacao: 10, status: 'ACERTADA', valor: 20, motivo: 'Já paga' },
    { id_multa: 3, id_locacao: 11, status: 'PENDENTE', valor: 30, motivo: 'Outro contrato' }
  ];
  return { ...api, pagamentos, multas, label, submit };
}

test('seleção filtra multas pendentes, preenche o integral e impede envio sem multa', () => {
  const ui = interfaceMultas();
  ui.syncPagamentoForm();
  const campos = ui.pagamentos.elements;
  assert.equal(ui.label.hidden, false);
  assert.equal(campos.id_multa.required, true);
  assert.match(campos.id_multa.innerHTML, /Infração/);
  assert.doesNotMatch(campos.id_multa.innerHTML, /Já paga|Outro contrato/);
  assert.equal(ui.submit.disabled, true);
  campos.id_multa.value = '1';
  ui.syncPagamentoForm();
  assert.equal(campos.valor.value, '80.00');
  assert.equal(campos.valor.readOnly, true);
  assert.equal(ui.submit.disabled, false);
  campos.id_locacao.value = '11';
  ui.syncPagamentoForm();
  assert.equal(campos.id_multa.value, '');
  assert.equal(campos.valor.value, '');
  assert.equal(ui.submit.disabled, true);
});

test('acerto remove opção e exclusão do pagamento devolve opção pendente', () => {
  const ui = interfaceMultas();
  ui.pagamentos.elements.id_multa.value = '1';
  ui.state.multas[0].status = 'ACERTADA';
  ui.syncPagamentoForm();
  assert.doesNotMatch(ui.pagamentos.elements.id_multa.innerHTML, /Infração/);
  assert.equal(ui.submit.disabled, true);
  ui.state.multas[0].status = 'PENDENTE';
  ui.syncPagamentoForm();
  assert.match(ui.pagamentos.elements.id_multa.innerHTML, /Infração/);
  ui.pagamentos.elements.tipo.value = 'LOCACAO';
  ui.syncPagamentoForm();
  assert.equal(ui.label.hidden, true);
  assert.equal(ui.pagamentos.elements.id_multa.disabled, true);
  assert.equal(ui.pagamentos.elements.valor.readOnly, false);
  assert.equal(ui.submit.disabled, false);
});

test('data da infração usa data prevista até existir devolução efetiva', () => {
  const ui = interfaceMultas();
  const contrato = { id_locacao: 10, data_retirada: '2026-11-20', data_devolucao_prevista: '2026-11-23' };
  ui.state.locacoes = [contrato];
  ui.syncMultaForm();
  assert.equal(ui.multas.elements.data_multa.min, '2026-11-20');
  assert.equal(ui.multas.elements.data_multa.max, '2026-11-23');
  contrato.data_devolucao_real = '2026-11-25';
  ui.syncMultaForm();
  assert.equal(ui.multas.elements.data_multa.max, '2026-11-25');
});
