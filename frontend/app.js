import * as api from './api.js';

// ── State ─────────────────────────────────────────────────────────
let currentUser = null;
let servicesCache = [];

// ── DOM helpers ───────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const setHtml = (id, html) => { $(id).innerHTML = html; };
const show = (id) => $(id)?.classList.remove('hidden');
const hide = (id) => $(id)?.classList.add('hidden');

function showAlert(id, msg, type = 'error') {
  const el = $(id);
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function showToast(msg, type = 'info') {
  let toast = $('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText =
      'position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;' +
      'font-size:.875rem;font-weight:500;z-index:999;transition:opacity .3s;max-width:320px;color:#fff';
    document.body.appendChild(toast);
  }
  toast.style.background = { success: '#16a34a', error: '#dc2626', info: '#2563eb' }[type] ?? '#2563eb';
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toast.style.opacity = '0'; }, 3000);
}

function esc(str) {
  return String(str).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
  );
}

function statusBadge(s) {
  const labels = {
    pending:   'Ожидает исполнителя',
    active:    'В работе',
    completed: 'Завершён',
    disputed:  'Спор',
    cancelled: 'Отменён',
  };
  return `<span class="status status-${s}">${labels[s] ?? s}</span>`;
}

// ── Auth ──────────────────────────────────────────────────────────
async function doLogin(email, password) {
  const data = await api.login(email, password);
  api.setToken(data.access_token);
  currentUser = await api.getMe();
  renderDashboard();
}

async function doRegister(email, password, role) {
  await api.register(email, password, role);
}

function logout() {
  api.setToken(null);
  currentUser = null;
  servicesCache = [];
  hide('screen-dashboard');
  show('screen-auth');
  hide('nav-user');
}

// ── Dashboard ─────────────────────────────────────────────────────
async function renderDashboard() {
  hide('screen-auth');
  show('screen-dashboard');
  renderNavUser();
  currentUser.role === 'executor' ? show('executor-create-section') : hide('executor-create-section');
  await loadServices();
}

function renderNavUser() {
  const el = $('nav-user');
  const role = currentUser.role;
  el.innerHTML = `
    <span>${esc(currentUser.email)}</span>
    <span class="badge badge-${role}">${role}</span>
    <span class="balance-chip" id="nav-balance">₽ ${parseFloat(currentUser.balance).toFixed(2)}</span>
    ${role === 'customer' ? `
      <div style="display:flex;gap:6px;align-items:center">
        <input id="topup-amount" type="number" min="1" placeholder="Пополнить"
               style="width:110px;padding:5px 8px;font-size:.8rem;border:1px solid var(--border);border-radius:6px;">
        <button class="btn btn-sm btn-primary" id="topup-btn">+</button>
      </div>` : ''}
    <button class="btn btn-ghost btn-sm" id="logout-btn">Выйти</button>
  `;
  el.classList.remove('hidden');

  $('logout-btn').addEventListener('click', logout);
  $('topup-btn')?.addEventListener('click', doTopup);
}

async function doTopup() {
  const amount = parseFloat($('topup-amount')?.value);
  if (!amount || amount <= 0) return;
  try {
    const data = await api.topup(amount);
    $('nav-balance').textContent = `₽ ${parseFloat(data.balance).toFixed(2)}`;
    $('topup-amount').value = '';
    showToast('Баланс пополнен', 'success');
  } catch (e) {
    showToast('Ошибка пополнения: ' + e.detail, 'error');
  }
}

// ── Tabs ──────────────────────────────────────────────────────────
function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));
  $(tabId).classList.add('active');
  $('pane-' + tabId.replace('tab-', '')).classList.add('active');
  if (tabId === 'tab-orders') loadOrders();
  if (tabId === 'tab-chain') loadChain();
}

// ── Services ─────────────────────────────────────────────────────
async function loadServices() {
  try {
    servicesCache = await api.listServices();
    renderServices(servicesCache);
  } catch (e) {
    setHtml('services-list', `<div class="empty">Ошибка загрузки: ${esc(e.detail ?? '')}</div>`);
  }
}

function renderServices(services) {
  if (!services.length) {
    setHtml('services-list', '<div class="empty">Нет доступных услуг</div>');
    return;
  }
  const isCustomer = currentUser.role === 'customer';
  const html = services.map((s) => `
    <div class="item-card">
      <div class="item-info">
        <div class="item-title">${esc(s.title)}</div>
        <div class="item-sub">${esc(s.description)}</div>
      </div>
      <div class="item-actions">
        <span class="price">₽ ${parseFloat(s.price).toFixed(2)}</span>
        ${isCustomer
          ? `<button class="btn btn-sm btn-primary" data-order="${s.id}" data-price="${s.price}">Заказать</button>`
          : ''}
      </div>
    </div>
  `).join('');
  setHtml('services-list', `<div class="item-grid">${html}</div>`);

  document.querySelectorAll('[data-order]').forEach((btn) => {
    btn.addEventListener('click', () => handleCreateOrder(btn.dataset.order, btn.dataset.price));
  });
}

async function handleCreateOrder(serviceId, price) {
  if (!confirm(`Создать заказ? ₽ ${parseFloat(price).toFixed(2)} будут заблокированы в эскроу.`)) return;
  try {
    await api.createOrder(serviceId);
    currentUser = await api.getMe();
    renderNavUser();
    switchTab('tab-orders');
    showToast('Заказ создан — средства заблокированы в эскроу', 'success');
  } catch (e) {
    const msg =
      e.status === 402 ? 'Недостаточно средств. Пополните баланс.' :
      e.status === 503 ? 'Платёжный сервис недоступен.' :
      e.detail ?? 'Ошибка';
    showToast(msg, 'error');
  }
}

// ── Orders ────────────────────────────────────────────────────────
async function loadOrders() {
  try {
    const orders = await api.listOrders();
    renderOrders(orders);
  } catch (e) {
    setHtml('orders-list', '<div class="empty">Ошибка загрузки заказов</div>');
  }
}

function renderOrders(orders) {
  if (!orders.length) {
    setHtml('orders-list', '<div class="empty">У вас пока нет заказов</div>');
    return;
  }
  const role = currentUser.role;

  const html = orders.map((o) => {
    const svc = servicesCache.find((s) => s.id === o.service_id);
    const svcTitle = svc ? svc.title : o.service_id.slice(0, 8) + '…';
    const escrowShort = o.escrow_tx_id ? o.escrow_tx_id.slice(0, 8) + '…' : '—';

    const actions = [];
    if (o.status === 'pending') {
      if (role === 'customer') actions.push(`<button class="btn btn-sm btn-danger"  data-id="${o.id}" data-action="cancel">Отменить</button>`);
      if (role === 'executor') actions.push(`<button class="btn btn-sm btn-success" data-id="${o.id}" data-action="accept">Принять</button>`);
    }
    if (o.status === 'active') {
      if (role === 'customer') actions.push(`<button class="btn btn-sm btn-primary" data-id="${o.id}" data-action="complete">Подтвердить выполнение</button>`);
      actions.push(`<button class="btn btn-sm btn-amber" data-id="${o.id}" data-action="dispute">Открыть спор</button>`);
    }

    return `
      <div class="item-card">
        <div class="item-info">
          <div class="item-title">${esc(svcTitle)}</div>
          <div class="item-sub">ID: ${o.id.slice(0, 8)}… · Escrow: ${escrowShort}</div>
        </div>
        <div class="item-actions">
          ${statusBadge(o.status)}
          ${actions.join('')}
        </div>
      </div>
    `;
  }).join('');

  setHtml('orders-list', `<div class="item-grid">${html}</div>`);

  const actionLabels = {
    accept:   'Принять заказ?',
    complete: 'Подтвердить выполнение? Средства перейдут исполнителю.',
    cancel:   'Отменить заказ? Средства вернутся на баланс.',
    dispute:  'Открыть спор?',
  };
  document.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm(actionLabels[btn.dataset.action])) return;
      try {
        await api.orderAction(btn.dataset.id, btn.dataset.action);
        currentUser = await api.getMe();
        renderNavUser();
        await loadOrders();
        showToast('Готово', 'success');
      } catch (e) {
        showToast(e.detail ?? 'Ошибка', 'error');
      }
    });
  });
}

// ── Blockchain ───────────────────────────────────────────────────
async function loadChain() {
  try {
    const chain = await api.getChain();
    $('verify-result').innerHTML = '';
    if (!chain.length) {
      setHtml('chain-content', '<div class="empty">Цепочка пуста — создайте заказ, чтобы появились записи</div>');
      return;
    }
    const rows = chain.map((tx, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${new Date(tx.timestamp).toLocaleString('ru')}</td>
        <td>${esc(tx.description ?? '—')}</td>
        <td class="hash" title="${esc(tx.from)}">${tx.from.slice(0, 12)}…</td>
        <td class="hash" title="${esc(tx.to)}">${tx.to.slice(0, 12)}…</td>
        <td>₽ ${tx.amount.toFixed(2)}</td>
        <td class="hash" title="${esc(tx.hash)}">${tx.hash.slice(0, 16)}…</td>
      </tr>
    `).join('');
    setHtml('chain-content', `
      <div style="overflow-x:auto">
        <table class="chain-table">
          <thead>
            <tr><th>#</th><th>Время</th><th>Операция</th><th>От</th><th>Кому</th><th>Сумма</th><th>Hash</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div style="margin-top:10px;font-size:.75rem;color:var(--muted)">
        Всего записей: ${chain.length} · Каждая запись включает prev_hash предыдущей транзакции
      </div>
    `);
  } catch (e) {
    setHtml('chain-content', `<div class="empty">Платёжный сервис недоступен (${e.detail ?? ''})</div>`);
  }
}

async function handleVerifyChain() {
  try {
    const data = await api.verifyChain();
    $('verify-result').innerHTML = data.valid
      ? `<div class="alert alert-success">✓ Цепочка целостна — все хэши корректны</div>`
      : `<div class="alert alert-error">✗ Повреждённые записи: ${(data.broken ?? []).join(', ')}</div>`;
  } catch (e) {
    $('verify-result').innerHTML = `<div class="alert alert-error">Ошибка верификации</div>`;
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────
function init() {
  // Login form
  $('form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('login-error').classList.add('hidden');
    const fd = new FormData(e.target);
    try {
      await doLogin(fd.get('email'), fd.get('password'));
    } catch (err) {
      showAlert('login-error', err.detail ?? 'Ошибка входа');
    }
  });

  // Register form
  $('form-register').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('reg-error').classList.add('hidden');
    $('reg-success').classList.add('hidden');
    const fd = new FormData(e.target);
    try {
      await doRegister(fd.get('email'), fd.get('password'), fd.get('role'));
      showAlert('reg-success', 'Аккаунт создан. Войдите в форме слева.', 'success');
      e.target.reset();
    } catch (err) {
      showAlert('reg-error', err.detail ?? 'Ошибка регистрации');
    }
  });

  // Create service form
  $('form-service').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('svc-error').classList.add('hidden');
    const fd = new FormData(e.target);
    try {
      await api.createService(fd.get('title'), fd.get('description'), parseFloat(fd.get('price')));
      e.target.reset();
      await loadServices();
      showToast('Услуга создана', 'success');
    } catch (err) {
      showAlert('svc-error', err.detail ?? 'Ошибка создания услуги');
    }
  });

  // Tab buttons
  $('tab-services').addEventListener('click', () => switchTab('tab-services'));
  $('tab-orders').addEventListener('click', () => switchTab('tab-orders'));
  $('tab-chain').addEventListener('click', () => switchTab('tab-chain'));

  // Chain buttons
  $('btn-refresh-chain').addEventListener('click', loadChain);
  $('btn-verify-chain').addEventListener('click', handleVerifyChain);
  $('btn-refresh-services').addEventListener('click', loadServices);
  $('btn-refresh-orders').addEventListener('click', loadOrders);
  $('link-to-chain').addEventListener('click', (e) => { e.preventDefault(); switchTab('tab-chain'); });
}

document.addEventListener('DOMContentLoaded', init);
