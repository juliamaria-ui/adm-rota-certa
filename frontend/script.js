const API = window.location.origin;

const config = {
  funcionarios: {
    endpoint: '/funcionarios/',
    idField: 'id_funcionario',
    columns: ['id_funcionario', 'nome', 'cpf', 'email', 'telefone', 'cargo', 'usuario'],
    editable: true,
    buildPayload(form, isEdit) {
      const data = formToObject(form);
      if (isEdit) {
        delete data.id_funcionario;
        delete data.cpf;
        if (!data.senha) delete data.senha;
      }
      return data;
    }
  },
  clientes: {
    endpoint: '/clientes/',
    idField: 'cpf',
    columns: ['cpf', 'nome', 'telefone', 'email', 'cnh'],
    editable: true,
    buildPayload(form, isEdit) {
      const data = formToObject(form);
      if (isEdit) delete data.cpf;
      return data;
    }
  },
  veiculos: {
    endpoint: '/veiculos/',
    idField: 'placa',
    columns: ['placa', 'marca', 'modelo', 'ano', 'valor_diaria', 'status'],
    editable: true,
    buildPayload(form, isEdit) {
      const data = formToObject(form);
      data.placa = data.placa?.toUpperCase();
      data.ano = Number(data.ano);
      data.valor_diaria = Number(data.valor_diaria);
      if (isEdit) delete data.placa;
      return data;
    }
  },
  locacoes: {
    endpoint: '/locacoes/',
    idField: 'id_locacao',
    columns: ['id_locacao', 'cliente', 'veiculo', 'placa', 'funcionario', 'data_retirada', 'data_devolucao_prevista', 'data_devolucao_real', 'valor_total', 'saldo', 'status'],
    editable: true,
    buildPayload(form, isEdit) {
      const data = formToObject(form);
      if (!isEdit) data.condutores = new FormData(form).getAll('condutores');
      if (data.id_funcionario) data.id_funcionario = Number(data.id_funcionario);
      if (isEdit) {
        delete data.id_locacao;
        delete data.cpf_cliente;
        delete data.placa_veiculo;
        delete data.id_funcionario;
      }
      return data;
    }
  },
  condutores: {
    endpoint: '/condutores/',
    idField: 'cpf',
    columns: ['cpf', 'nome', 'cnh', 'validade_cnh'],
    editable: true,
    upsert: true,
    deletable: false,
    buildPayload: formToObject
  },
  manutencoes: {
    endpoint: '/manutencoes/',
    idField: 'id_manutencao',
    columns: ['id_manutencao', 'placa_veiculo', 'tipo', 'descricao', 'custo', 'data_inicio', 'data_fim'],
    editable: true,
    deletable: false,
    buildPayload: formToObject
  },
  pagamentos: {
    endpoint: '/pagamentos/',
    idField: 'id_pagamento',
    columns: ['id_pagamento', 'tipo', 'id_locacao', 'id_multa', 'valor', 'forma_pagamento', 'data_pagamento'],
    editable: false,
    buildPayload(form) {
      const data = formToObject(form);
      data.id_locacao = Number(data.id_locacao);
      if (data.id_multa) data.id_multa = Number(data.id_multa);
      data.valor = Number(data.valor);
      return data;
    }
  },
  multas: {
    endpoint: '/multas/',
    idField: 'id_multa',
    columns: ['id_multa', 'id_locacao', 'motivo', 'valor', 'data_multa', 'status'],
    editable: false,
    buildPayload(form) {
      const data = formToObject(form);
      data.id_locacao = Number(data.id_locacao);
      data.valor = Number(data.valor);
      return data;
    }
  }
};

const pageTitles = {
  dashboard: 'Visão geral',
  login: 'Login',
  funcionarios: 'Funcionários',
  clientes: 'Clientes',
  veiculos: 'Veículos',
  locacoes: 'Locações',
  condutores: 'Condutores',
  manutencoes: 'Manutenções',
  pagamentos: 'Pagamentos',
  multas: 'Multas'
};

const lockedFields = {
  funcionarios: ['cpf'],
  clientes: ['cpf'],
  veiculos: ['placa'],
  condutores: ['cpf'],
  manutencoes: ['placa_veiculo', 'tipo', 'descricao', 'data_inicio'],
  locacoes: ['cpf_cliente', 'placa_veiculo', 'id_funcionario', 'data_retirada']
};

const state = {
  user: null,
  dashboard: null,
  funcionarios: [],
  clientes: [],
  veiculos: [],
  locacoes: [],
  pagamentos: [],
  multas: [],
  editing: {}
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function showAlert(message, type = 'success') {
  const alert = document.getElementById('alert');
  alert.textContent = message;
  alert.className = `alert ${type}`;
  clearTimeout(showAlert.timeout);
  showAlert.timeout = setTimeout(() => alert.className = 'alert hidden', 4500);
}

function formToObject(form) {
  return Object.fromEntries([...new FormData(form).entries()].filter(([, value]) => value !== ''));
}

async function request(path, options = {}) {
  const response = await fetch(API + path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });

  let body = null;
  try { body = await response.json(); } catch (_) {}

  if (!response.ok) {
    const message = body?.error || body?.message || `Erro HTTP ${response.status}`;
    if (response.status === 401) handleUnauthorized(message);
    throw new Error(message);
  }
  return body;
}

function handleUnauthorized(message = 'Faça login para continuar.') {
  state.user = null;
  state.dashboard = null;
  Object.keys(config).forEach(resource => state[resource] = []);
  syncAuthLayout();
  showPage('login');
  showAlert(message, 'error');
}

function syncAuthLayout() {
  const logged = Boolean(state.user?.is_admin);
  document.body.classList.toggle('authenticated', logged);
  document.body.classList.toggle('not-authenticated', !logged);

  const topUser = document.getElementById('topUser');
  if (topUser) topUser.textContent = logged ? `${state.user.nome} (${state.user.usuario})` : '';

}

function showPage(pageName) {
  if (pageName !== 'login' && !state.user?.is_admin) {
    pageName = 'login';
  }

  document.querySelectorAll('#menuTabs button').forEach(button => {
    const active = button.dataset.page === pageName;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  document.querySelectorAll('.page').forEach(page => {
    page.classList.toggle('active', page.id === pageName);
  });
  document.getElementById('pageTitle').textContent = pageTitles[pageName];
}

function formatMoney(value) {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(value) {
  if (!value) return '-';
  const [year, month, day] = String(value).split('-');
  return year && month && day ? `${day}/${month}/${year}` : String(value);
}

function formatValue(key, value) {
  if (value === null || value === undefined || value === '') return '-';
  if (key.includes('valor') || ['saldo', 'custo'].includes(key)) return formatMoney(value);
  if (key.startsWith('data_') || key === 'validade_cnh') return escapeHtml(formatDate(value));
  if (key === 'status') {
    const text = String(value);
    const cls = ['DISPONIVEL', 'FINALIZADA', 'ACERTADA'].includes(text) ? 'ok' : text.includes('CANCELADA') || text.includes('MANUTENCAO') ? 'danger' : 'warn';
    const label = { PENDENTE: 'Pendente', ACERTADA: 'Acertada' }[text] || text;
    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
  }
  return escapeHtml(value);
}

function renderTable(resource) {
  const cfg = config[resource];
  const rows = state[resource] || [];
  const container = document.getElementById(`${resource}Table`);

  if (!container) return;
  if (!rows.length) {
    container.innerHTML = '<div class="empty">Nenhum registro encontrado.</div>';
    return;
  }

  const headers = cfg.columns.map(col => `<th>${escapeHtml(col.replaceAll('_', ' '))}</th>`).join('');
  const body = rows.map(row => {
    const id = row[cfg.idField];
    const safeId = escapeHtml(id);
    const cols = cfg.columns.map(col => `<td>${formatValue(col, row[col])}</td>`).join('');
    const editLabel = resource === 'manutencoes' ? 'Concluir' : 'Editar';
    const active = resource !== 'locacoes' || row.status === 'ATIVA';
    const editable = cfg.editable && active && !(resource === 'manutencoes' && row.data_fim);
    const editBtn = editable ? `<button type="button" data-action="edit" data-id="${safeId}">${editLabel}</button>` : '';
    const deleteLabel = resource === 'locacoes' ? 'Cancelar' : 'Excluir';
    const deleteBtn = cfg.deletable !== false && active && !(resource === 'multas' && row.status === 'ACERTADA')
      ? `<button type="button" class="danger" data-action="delete" data-id="${safeId}">${deleteLabel}</button>` : '';
    return `<tr>${cols}<td class="actions">${editBtn}${deleteBtn}</td></tr>`;
  }).join('');

  container.innerHTML = `<div class="table-wrap"><table><thead><tr>${headers}<th>Ações</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

async function loadResource(resource) {
  const container = document.getElementById(`${resource}Table`);
  try {
    state[resource] = await request(config[resource].endpoint);
    renderTable(resource);
  } catch (error) {
    if (container && state.user) container.innerHTML = `<div class="empty">Erro ao carregar dados: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadDashboard() {
  try {
    state.dashboard = await request('/dashboard/');
    renderDashboard();
  } catch (error) {
    updateStats();
  }
}

async function loadAll() {
  if (!state.user?.is_admin) return;
  await Promise.all(Object.keys(config).map(loadResource));
  updateSelects();
  await loadDashboard();
}

function updateStats() {
  const counts = state.dashboard?.counts || {};
  document.getElementById('statClientes').textContent = counts.clientes ?? state.clientes.length;
  document.getElementById('statVeiculos').textContent = counts.veiculos ?? state.veiculos.length;
  document.getElementById('statLocacoes').textContent = counts.locacoes ?? state.locacoes.length;
  document.getElementById('statFuncionarios').textContent = counts.funcionarios ?? state.funcionarios.length;
  document.getElementById('statPagamentos').textContent = counts.pagamentos ?? state.pagamentos.length;
  document.getElementById('statMultas').textContent = counts.multas ?? state.multas.length;
}

function renderMiniList(containerId, items, formatter) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!items?.length) {
    container.innerHTML = '<p>Nenhum registro.</p>';
    return;
  }

  container.innerHTML = items.map(item => {
    const content = formatter(item);
    return `<div class="mini-item"><b>${escapeHtml(content.title)}</b><small>${escapeHtml(content.subtitle)}</small></div>`;
  }).join('');
}

function renderDashboard() {
  updateStats();
  const latest = state.dashboard?.latest || {};

  renderMiniList('dashboardClientes', latest.clientes, item => ({
    title: item.nome,
    subtitle: `CPF ${item.cpf}`
  }));
  renderMiniList('dashboardVeiculos', latest.veiculos, item => ({
    title: `${item.marca} ${item.modelo}`,
    subtitle: `${item.placa} • ${item.status}`
  }));
  renderMiniList('dashboardLocacoes', latest.locacoes, item => ({
    title: `#${item.id_locacao} • ${item.cliente}`,
    subtitle: `${item.placa} • ${item.status}`
  }));
  renderMiniList('dashboardFuncionarios', latest.funcionarios, item => ({
    title: item.nome,
    subtitle: `${item.usuario} • ${item.cargo || '-'}`
  }));
  renderMiniList('dashboardPagamentos', latest.pagamentos, item => ({
    title: `Pagamento #${item.id_pagamento}`,
    subtitle: `${formatMoney(item.valor)} • ${formatDate(item.data_pagamento)}`
  }));
  const gerencial = state.dashboard?.views;
  renderMiniList('frotaDisponivel', gerencial?.veiculos_disponiveis, item => ({
    title: item.placa,
    subtitle: `${item.marca} ${item.modelo}`
  }));
  renderMiniList('receitaFrota', gerencial?.faturamento_frota, item => ({
    title: `${item.marca} ${item.modelo}`,
    subtitle: `${formatMoney(item.receita_total)} • ${item.total_locacoes} locação(ões)`
  }));
  renderMiniList('dashboardMultas', latest.multas, item => ({
    title: `Multa #${item.id_multa}`,
    subtitle: `${formatMoney(item.valor)} • ${formatDate(item.data_multa)}`
  }));
}

function optionData(selectName, item) {
  if (selectName === 'condutores') {
    return { value: item.cpf, label: `${item.nome} • CNH até ${formatDate(item.validade_cnh)}` };
  }
  if (selectName === 'clientes') {
    return { value: item.cpf, label: `${item.nome} - CPF ${item.cpf}` };
  }
  if (selectName === 'veiculos') {
    return { value: item.placa, label: `${item.placa} - ${item.marca} ${item.modelo} (${item.status})` };
  }
  if (selectName === 'funcionarios') {
    return { value: item.id_funcionario, label: `#${item.id_funcionario} - ${item.nome} (${item.cargo || 'sem cargo'})` };
  }
  if (selectName === 'locacoes') {
    return { value: item.id_locacao, label: `#${item.id_locacao} - ${item.cliente} / ${item.placa} (${item.status})` };
  }
  return { value: '', label: '' };
}

function placeholderForSelect(selectName) {
  const labels = {
    clientes: 'Selecione um cliente cadastrado',
    veiculos: 'Selecione um veículo cadastrado',
    funcionarios: 'Selecione um funcionário cadastrado',
    locacoes: 'Selecione uma locação cadastrada'
  };
  return labels[selectName] || 'Selecione um registro';
}

function updateSelects() {
  document.querySelectorAll('select[data-select]').forEach(select => {
    const selectName = select.dataset.select;
    const items = state[selectName] || [];
    const selection = [...select.selectedOptions].map(option => option.value);
    const currentValue = select.value;
    const options = [`<option value="">${escapeHtml(placeholderForSelect(selectName))}</option>`]
      .concat(items.map(item => {
        const option = optionData(selectName, item);
        return `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`;
      }));

    select.innerHTML = (select.multiple ? options.slice(1) : options).join('');
    if (select.multiple) {
      [...select.options].forEach(option => option.selected = selection.includes(option.value));
      return;
    }
    const hasCurrent = items.some(item => String(optionData(selectName, item).value) === String(currentValue));
    if (hasCurrent) {
      select.value = currentValue;
    } else if (select.name === 'id_funcionario' && state.user?.id_funcionario) {
      select.value = String(state.user.id_funcionario);
    } else {
      select.value = '';
    }
    select.disabled = items.length === 0;
  });

  Object.entries(state.editing).forEach(([resource, id]) => {
    if (id) applyFormLocks(resource, true);
  });
  syncPagamentoForm();
  syncMultaForm();
}

function syncPagamentoForm() {
  const form = document.querySelector('form[data-resource="pagamentos"]');
  const multa = form.elements.id_multa;
  const pagandoMulta = form.elements.tipo.value === 'MULTA';
  const selecionada = multa.value;
  const pendentes = state.multas.filter(item => item.status === 'PENDENTE' &&
    String(item.id_locacao) === form.elements.id_locacao.value);
  multa.innerHTML = '<option value="">Selecione uma multa pendente</option>' + pendentes.map(item =>
    `<option value="${escapeHtml(item.id_multa)}">#${escapeHtml(item.id_multa)} - ${escapeHtml(item.motivo)} (${escapeHtml(formatMoney(item.valor))})</option>`
  ).join('');
  multa.value = pendentes.some(item => String(item.id_multa) === selecionada) ? selecionada : '';
  multa.closest('label').hidden = !pagandoMulta;
  multa.disabled = !pagandoMulta;
  multa.required = pagandoMulta;
  const valor = form.elements.valor;
  if (pagandoMulta) {
    const item = pendentes.find(item => String(item.id_multa) === multa.value);
    valor.value = item ? Number(item.valor).toFixed(2) : '';
  } else if (valor.readOnly) {
    valor.value = '';
    multa.value = '';
  }
  valor.readOnly = pagandoMulta;
  form.querySelector('button[type="submit"]').disabled = pagandoMulta && !multa.value;
}

function syncMultaForm() {
  const form = document.querySelector('form[data-resource="multas"]');
  const locacao = state.locacoes.find(item => String(item.id_locacao) === form.elements.id_locacao.value);
  const data = form.elements.data_multa;
  data.min = locacao?.data_retirada || '';
  data.max = locacao?.data_devolucao_real || locacao?.data_devolucao_prevista || locacao?.data_devolucao || '';
}

function applyFormLocks(resource, disabled) {
  const form = document.querySelector(`form[data-resource="${resource}"]`);
  if (!form) return;
  (lockedFields[resource] || []).forEach(name => {
    const field = form.elements[name];
    if (field) field.disabled = disabled;
  });
}

function syncOperacaoForm(resource) {
  const form = document.querySelector(`form[data-resource="${resource}"]`);
  if (!form || !['locacoes', 'manutencoes'].includes(resource)) return;
  const editando = Boolean(state.editing[resource]);
  if (resource === 'locacoes') {
    const devolvendo = editando && form.elements.status.value === 'FINALIZADA';
    form.elements.status.disabled = !editando;
    form.elements.condutores.disabled = editando;
    form.elements.data_devolucao_real.closest('label').hidden = !devolvendo;
    form.elements.data_devolucao_real.disabled = !devolvendo;
    form.elements.data_devolucao_real.required = devolvendo;
  } else {
    form.elements.data_fim.closest('label').hidden = !editando;
    form.elements.data_fim.disabled = !editando;
    form.elements.data_fim.required = editando;
  }
}

function clearForm(resource) {
  const titleMap = { funcionarios: 'Cadastrar funcionário', clientes: 'Cadastrar cliente', veiculos: 'Cadastrar veículo', locacoes: 'Cadastrar locação' };
  const form = document.querySelector(`form[data-resource="${resource}"]`);
  if (!form) return;
  form.reset();
  state.editing[resource] = null;
  applyFormLocks(resource, false);
  updateSelects();
  syncOperacaoForm(resource);
  const title = document.getElementById(`${resource}FormTitle`);
  if (title) title.textContent = titleMap[resource] || 'Cadastrar registro';
}

async function editRecord(resource, id) {
  const cfg = config[resource];
  let record = state[resource].find(item => String(item[cfg.idField]) === String(id));
  if (!record) return;

  if (resource === 'locacoes') {
    try {
      record = await request(cfg.endpoint + encodeURIComponent(id));
    } catch (error) {
      showAlert(error.message, 'error');
      return;
    }
  }

  const form = document.querySelector(`form[data-resource="${resource}"]`);
  if (!form) return;

  state.editing[resource] = id;
  applyFormLocks(resource, false);
  form.reset();
  updateSelects();

  Object.entries(record).forEach(([key, value]) => {
    const field = form.elements[key];
    if (field && value !== null && value !== undefined) field.value = value;
  });

  if (resource === 'locacoes') {
    form.elements.id_locacao.value = record.id_locacao;
    form.elements.cpf_cliente.value = record.cpf_cliente || '';
    form.elements.placa_veiculo.value = record.placa || '';
    form.elements.id_funcionario.value = record.id_funcionario || '';
    [...form.elements.condutores.options].forEach(option => {
      option.selected = (record.condutores || []).includes(option.value);
    });
  }

  applyFormLocks(resource, true);
  syncOperacaoForm(resource);
  const title = document.getElementById(`${resource}FormTitle`);
  if (title) title.textContent = resource === 'manutencoes' ? 'Concluir manutenção' : 'Editar registro';
  showPage(resource);
}

async function deleteRecord(resource, id) {
  const cancelar = resource === 'locacoes';
  if (!confirm(cancelar ? 'Cancelar a locação e preservar o histórico?' : 'Excluir este registro?')) return;
  try {
    await request(config[resource].endpoint + encodeURIComponent(id), { method: 'DELETE' });
    showAlert(cancelar ? 'Locação cancelada.' : 'Registro excluído com sucesso.');
    await loadAll();
  } catch (error) {
    showAlert(error.message, 'error');
  }
}

async function submitResourceForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const resource = form.dataset.resource;
  const cfg = config[resource];
  const editingId = state.editing[resource];
  const isEdit = Boolean(editingId);

  try {
    const payload = cfg.buildPayload(form, isEdit);
    const update = isEdit && !cfg.upsert;
    if (isEdit && cfg.upsert) payload[cfg.idField] = editingId;
    const path = update ? cfg.endpoint + encodeURIComponent(editingId) : cfg.endpoint;
    await request(path, { method: update ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    showAlert(isEdit ? 'Registro atualizado com sucesso.' : 'Registro cadastrado com sucesso.');
    clearForm(resource);
    await loadAll();
  } catch (error) {
    showAlert(error.message, 'error');
  }
}

async function submitLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const data = formToObject(form);
    const user = await request('/funcionarios/login', { method: 'POST', body: JSON.stringify(data) });
    state.user = user;
    form.reset();
    syncAuthLayout();
    showPage('dashboard');
    showAlert(`Bem-vindo(a), ${user.nome}!`);
    await loadAll();
  } catch (error) {
    showAlert(error.message, 'error');
  }
}

async function logout() {
  try { await request('/funcionarios/logout', { method: 'POST', body: JSON.stringify({}) }); } catch (_) {}
  state.user = null;
  state.dashboard = null;
  Object.keys(config).forEach(resource => state[resource] = []);
  syncAuthLayout();
  showPage('login');
}

function setupTabs() {
  document.querySelectorAll('#menuTabs button').forEach(button => {
    button.addEventListener('click', () => showPage(button.dataset.page));
  });
  document.querySelectorAll('[data-open-page]').forEach(button => {
    button.addEventListener('click', () => showPage(button.dataset.openPage));
  });
}

function setupForms() {
  document.querySelectorAll('form[data-resource]').forEach(form => form.addEventListener('submit', submitResourceForm));
  Object.keys(config).forEach(resource => {
    document.getElementById(`${resource}Table`)?.addEventListener('click', event => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const action = button.dataset.action === 'edit' ? editRecord : deleteRecord;
      action(resource, button.dataset.id);
    });
  });
  const locacao = document.querySelector('form[data-resource="locacoes"]');
  locacao.elements.status.addEventListener('change', () => syncOperacaoForm('locacoes'));
  const pagamento = document.querySelector('form[data-resource="pagamentos"]');
  ['tipo', 'id_locacao', 'id_multa'].forEach(name => pagamento.elements[name].addEventListener('change', syncPagamentoForm));
  document.querySelector('form[data-resource="multas"]').elements.id_locacao.addEventListener('change', syncMultaForm);
  document.querySelectorAll('[data-clear]').forEach(button => button.addEventListener('click', () => clearForm(button.dataset.clear)));
  document.getElementById('loginForm').addEventListener('submit', submitLogin);
}

async function restoreSession() {
  try {
    const result = await request('/funcionarios/me');
    state.user = result.authenticated ? result.user : null;
  } catch (_) {
    state.user = null;
  }
  syncAuthLayout();
  if (state.user?.is_admin) {
    showPage('dashboard');
    await loadAll();
  } else {
    showPage('login');
  }
}

window.editRecord = editRecord;
window.deleteRecord = deleteRecord;

document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  setupForms();
  document.getElementById('refreshBtn').addEventListener('click', loadAll);
  document.getElementById('logoutBtn').addEventListener('click', logout);
  await restoreSession();
});
