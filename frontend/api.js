const API_BASE = 'http://localhost:8000';
const PAY_BASE = 'http://localhost:8001';

let _token = null;

export const setToken = (t) => { _token = t; };
export const getToken = () => _token;

async function request(base, path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;
  Object.assign(headers, options.headers ?? {});

  const res = await fetch(base + path, { ...options, headers });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) throw { status: res.status, detail: data.detail ?? JSON.stringify(data) };
  return data;
}

const back = (path, opts) => request(API_BASE, path, opts);
const pay  = (path, opts) => request(PAY_BASE, path, opts);

// ── Auth ──────────────────────────────────────────────────────────
export const register = (email, password, role) =>
  back('/register', { method: 'POST', body: JSON.stringify({ email, password, role }) });

export const login = (email, password) =>
  back('/login', { method: 'POST', body: JSON.stringify({ email, password }) });

export const getMe = () => back('/me');

// ── Balance ───────────────────────────────────────────────────────
export const topup = (amount) =>
  back('/balance/topup', { method: 'POST', body: JSON.stringify({ amount }) });

// ── Services ──────────────────────────────────────────────────────
export const listServices = () => back('/services');

export const createService = (title, description, price) =>
  back('/services', { method: 'POST', body: JSON.stringify({ title, description, price }) });

// ── Orders ────────────────────────────────────────────────────────
export const createOrder = (serviceId) =>
  back('/orders', { method: 'POST', body: JSON.stringify({ service_id: serviceId }) });

export const listOrders = () => back('/orders');

export const orderAction = (id, action) =>
  back(`/orders/${id}/${action}`, { method: 'POST' });

// ── Blockchain ────────────────────────────────────────────────────
export const getChain  = () => pay('/chain');
export const verifyChain = () => pay('/chain/verify');
