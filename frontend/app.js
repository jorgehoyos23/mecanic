'use strict';
/* =====================================================================
 * Mecasolic · Frontend SPA (sin dependencias)
 * Consume los microservicios a través del API Gateway: /api/<servicio>/...
 * ===================================================================== */

// ------------------------------------------------------------------ estado
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* sin almacenamiento */ } },
};
const S = { token: store.get('token'), user: store.get('user'), unread: 0, poll: null, clock: null, health: {} };

const SVCS = ['auth', 'clientes', 'mecanicos', 'servicios', 'ordenes', 'inventario', 'facturacion', 'notificaciones'];
const SVC_LABEL = { auth: 'Autenticación', clientes: 'Clientes', mecanicos: 'Mecánicos', servicios: 'Servicios',
  ordenes: 'Órdenes', inventario: 'Inventario', facturacion: 'Facturación', notificaciones: 'Notificaciones' };

const STATUS = {
  SOLICITADA: { label: 'Solicitada', cls: 'gray', color: '#d1d5db' },
  EN_DIAGNOSTICO: { label: 'En diagnóstico', cls: 'blue', color: '#fed7aa' },
  COTIZADA: { label: 'Cotizada', cls: 'amber', color: '#fdba74' },
  APROBADA: { label: 'Aprobada', cls: 'teal', color: '#fb923c' },
  RECHAZADA: { label: 'Cotización rechazada', cls: 'red', color: '#9ca3af' },
  EN_REPARACION: { label: 'En reparación', cls: 'purple', color: '#f97316' },
  FINALIZADA: { label: 'Finalizada', cls: 'green', color: '#ea580c' },
  ENTREGADA: { label: 'Entregada', cls: 'green', color: '#9a3412' },
  CANCELADA: { label: 'Cancelada', cls: 'red', color: '#4b5563' },
};
const FLOW = ['SOLICITADA', 'EN_DIAGNOSTICO', 'COTIZADA', 'APROBADA', 'EN_REPARACION', 'FINALIZADA', 'ENTREGADA'];
const ACTIVE = ['SOLICITADA', 'EN_DIAGNOSTICO', 'COTIZADA', 'APROBADA', 'RECHAZADA', 'EN_REPARACION', 'FINALIZADA'];
const KIND = { MANO_OBRA: 'Mano de obra', REPUESTO: 'Repuesto', SERVICIO: 'Servicio' };
const CATEGORY = { MANTENIMIENTO: 'Mantenimiento', REPARACION: 'Reparación', DIAGNOSTICO: 'Diagnóstico' };
const INVOICE_CLS = { PENDIENTE: 'amber', PAGADA: 'green', ANULADA: 'red' };
const ROLE_LABEL = { cliente: 'Cliente', mecanico: 'Mecánico', admin: 'Administrador', sistema: 'Sistema' };

// iconos de línea (24×24)
const ICONS = {
  home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',
  gauge: 'M12 14l4-4M3 18a9 9 0 1 1 18 0M12 14a1 1 0 1 0 0 .01',
  car: 'M5 17h14M3 17v-4l2-5h14l2 5v4M7 17v2M17 17v2M6.5 13h.01M17.5 13h.01',
  plus: 'M12 7v10M7 12h10M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  clipboard: 'M9 3h6v3H9zM7 4.5H5V21h14V4.5h-2M9 11h6M9 15h4',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3',
  bell: 'M6 16v-5a6 6 0 1 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0',
  wrench: 'M15 4a5 5 0 0 0-5 6l-7 7 4 4 7-7a5 5 0 0 0 6-5l-3 3-3-1-1-3z',
  box: 'M3 7l9-4 9 4-9 4zM3 7v10l9 4 9-4V7M12 11v10',
  users: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21a7 7 0 0 1 14 0M16 3a4 4 0 0 1 0 8M22 21a7 7 0 0 0-4-6',
  layers: 'M12 3l9 5-9 5-9-5zM3 12.5l9 5 9-5M3 17l9 5 9-5',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11',
  mail: 'M3 6h18v12H3zM3 7l9 6 9-6',
  lock: 'M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0',
  phone: 'M5 4h4l2 5-3 2a11 11 0 0 0 5 5l2-3 5 2v4a2 2 0 0 1-2 2A17 17 0 0 1 3 6a2 2 0 0 1 2-2',
  money: 'M3 7h18v10H3zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 10v4M18 10v4',
  alert: 'M12 3l10 18H2zM12 10v5M12 18h.01',
  cpu: 'M7 7h10v10H7zM10 10h4v4h-4zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3',
  bolt: 'M13 2L4 14h7l-1 8 9-12h-7z',
  check: 'M5 12l5 5L20 7',
};
const ico = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICONS[n]}"/></svg>`;
const LOGO = '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M32 3 58 18v28L32 61 6 46V18z" fill="#f97316"/><path d="M20 42V22l12 12 12-12v20" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/></svg>';
const brand = (sub = 'Smart Workshop') => `<div class="logo">${LOGO}<div><b>MECASOLIC</b><small>${sub}</small></div></div>`;

const NAV = {
  cliente: [['inicio', 'Inicio', 'home'], ['vehiculos', 'Mis vehículos', 'car'], ['solicitar', 'Solicitar servicio', 'plus'],
    ['ordenes', 'Mis órdenes', 'clipboard'], ['facturas', 'Facturas', 'receipt'], ['notificaciones', 'Notificaciones', 'bell']],
  mecanico: [['inicio', 'Centro de control', 'gauge'], ['ordenes', 'Órdenes asignadas', 'clipboard'], ['inventario', 'Repuestos', 'box'],
    ['notificaciones', 'Notificaciones', 'bell']],
  admin: [['inicio', 'Centro de mando', 'gauge'], ['ordenes', 'Órdenes de trabajo', 'clipboard'], ['clientes', 'Clientes y vehículos', 'users'],
    ['mecanicos', 'Mecánicos', 'wrench'], ['catalogo', 'Servicios', 'layers'], ['inventario', 'Inventario', 'box'],
    ['facturas', 'Facturación', 'receipt'], ['notificaciones', 'Notificaciones', 'bell']],
};

// ------------------------------------------------------------------ utilidades
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = (n) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n || 0);
// las fechas sin zona horaria (p. ej. desde MySQL) están en UTC
const toDate = (s) => new Date(/Z$|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`);
const fdate = (d) => (d ? toDate(d).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' }) : '—');
const fday = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('es-CO', { dateStyle: 'medium' }) : '—');
const badge = (st) => `<span class="badge ${STATUS[st]?.cls || 'gray'}">${esc(STATUS[st]?.label || st)}</span>`;
const go = (path) => { location.hash = `#/${path}`; };
const role = () => S.user?.role;
const firstName = () => esc((S.user?.full_name || '').split(' ')[0]);
const progressOf = (st) => (st === 'CANCELADA' ? 0 : Math.round((Math.max(0, FLOW.indexOf(st === 'RECHAZADA' ? 'COTIZADA' : st)) / (FLOW.length - 1)) * 100));
const thumb = (svg, cls = '') => `<span class="thumb ${cls}">${svg}</span>`;
const orderArt = (o) => (o.service_name ? serviceArt({ name: o.service_name }) : o.kind === 'REPARACION' ? 'motor' : 'diagnostico');

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function formValues(form) {
  const out = {};
  for (const [k, v] of new FormData(form)) out[k] = typeof v === 'string' ? v.trim() : v;
  return out;
}
const numOrNull = (v) => (v === '' || v == null ? null : Number(v));

function errorText(data, status) {
  if (data && typeof data.detail === 'string') return data.detail;
  if (data && Array.isArray(data.detail)) return data.detail.map((e) => `${e.loc?.slice(-1)[0] ?? ''}: ${e.msg}`).join(' · ');
  return `Error ${status}`;
}

async function api(svc, path, { method, body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (S.token) headers.Authorization = `Bearer ${S.token}`;
  const res = await fetch(`/api/${svc}${path}`, {
    method: method || (body ? 'POST' : 'GET'), headers, body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* sin cuerpo */ }
  if (!res.ok) {
    if (res.status === 401 && S.token) logout();
    throw new Error(errorText(data, res.status));
  }
  return data;
}

async function fetchHealth(svc, timeout = 5000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeout);
  try {
    const r = await fetch(`/api/${svc}/health`, { signal: ctrl.signal });
    return r.ok ? await r.json() : null;
  } catch { return null; } finally { clearTimeout(t); }
}

async function refreshHealth() {
  const results = await Promise.all(SVCS.map(fetchHealth));
  SVCS.forEach((s, i) => { S.health[s] = results[i]; });
  updateSysPill();
  return S.health;
}

function dbEngine() {
  const h = Object.values(S.health).find((x) => x?.database);
  const names = { mysql: 'MySQL', postgresql: 'PostgreSQL', sqlite: 'SQLite' };
  return h ? names[h.database.engine] || h.database.engine : '—';
}

/** Anima los números con atributo data-count (y data-money para moneda). */
function countUp(root) {
  $$('[data-count]', root).forEach((el) => {
    const target = Number(el.dataset.count) || 0;
    const isMoney = 'money' in el.dataset;
    const t0 = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - t0) / 900);
      const v = target * (1 - (1 - p) ** 3);
      el.textContent = isMoney ? money(v) : Math.round(v).toLocaleString('es-CO');
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

function modal(title, body, { submit = 'Guardar', onSubmit, wide = false, onOpen } = {}) {
  const wrap = document.createElement('div');
  wrap.className = 'modal-backdrop';
  wrap.innerHTML = `<form class="modal ${wide ? 'wide' : ''}" novalidate>
      <header><h3>${esc(title)}</h3><button type="button" class="icon-btn" data-close aria-label="Cerrar">×</button></header>
      <div class="modal-body">${body}</div>
      ${onSubmit ? `<footer><button type="button" class="btn ghost" data-close>Cancelar</button>
        <button type="submit" class="btn primary">${esc(submit)}</button></footer>` : ''}
    </form>`;
  document.body.appendChild(wrap);
  const close = () => wrap.remove();
  wrap.addEventListener('mousedown', (e) => { if (e.target === wrap) close(); });
  $$('[data-close]', wrap).forEach((b) => b.addEventListener('click', close));
  const form = $('form', wrap);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!onSubmit || !form.reportValidity()) return;
    const btn = $('[type=submit]', form);
    btn.disabled = true;
    try { await onSubmit(formValues(form), form); close(); } catch (err) { toast(err.message, 'error'); } finally { btn.disabled = false; }
  });
  onOpen?.(form);
  $('input, select, textarea', form)?.focus();
  return { form, close };
}

/** Ejecuta una acción mostrando el resultado; devuelve true si tuvo éxito. */
async function act(fn, okMsg) {
  try { await fn(); if (okMsg) toast(okMsg, 'success'); return true; } catch (e) { toast(e.message, 'error'); return false; }
}

// ------------------------------------------------------------------ pantalla de carga 0 → 100 %
async function boot() {
  const el = $('#boot');
  if (!el) return;
  const num = $('#boot-num');
  const fill = $('#boot-fill');
  const msg = $('#boot-msg');
  const chips = $('#boot-chips');
  chips.innerHTML = SVCS.map((s) => `<span data-s="${s}">${s}</span>`).join('');

  let done = 0;
  SVCS.forEach((s) => fetchHealth(s).then((h) => {
    S.health[s] = h;
    $(`[data-s="${s}"]`, chips).classList.add(h && h.database?.status !== 'error' ? 'ok' : 'fail');
    done += 1;
  }));

  const MSGS = [[0, 'Iniciando núcleo Mecasolic…'], [14, 'Cargando interfaz…'], [30, 'Conectando microservicios…'],
    [55, 'Verificando conexión a la base de datos…'], [75, 'Sincronizando órdenes e inventario…'], [92, 'Calibrando sensores del taller…']];
  const t0 = performance.now();
  const DURATION = 2600;
  await new Promise((resolve) => {
    const frame = (now) => {
      const t = Math.min(1, (now - t0) / DURATION);
      const eased = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
      const cap = done === SVCS.length ? 100 : Math.min(97, 62 + done * 4);
      const pct = Math.min(cap, Math.floor(eased * 100));
      num.textContent = pct;
      fill.style.width = `${pct}%`;
      el.setAttribute('aria-valuenow', pct);
      const m = [...MSGS].reverse().find(([p]) => pct >= p);
      if (m && msg.textContent !== m[1]) msg.textContent = m[1];
      if (pct >= 100) return resolve();
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  });
  const ok = SVCS.filter((s) => S.health[s]).length;
  msg.textContent = ok === SVCS.length
    ? `✔ ${ok}/${SVCS.length} servicios en línea · Base de datos ${dbEngine()}`
    : `⚠ ${ok}/${SVCS.length} servicios en línea`;
  await new Promise((r) => setTimeout(r, 650));
  el.classList.add('done');
  setTimeout(() => el.remove(), 800);
  if (ok < SVCS.length) toast(`${SVCS.length - ok} servicio(s) no responden. Algunas funciones pueden fallar.`, 'error');
}

// ------------------------------------------------------------------ sesión
function saveSession(res) {
  S.token = res.access_token; S.user = res.user;
  store.set('token', S.token); store.set('user', S.user);
}

function logout() {
  S.token = null; S.user = null;
  store.del('token'); store.del('user');
  clearInterval(S.poll); S.poll = null;
  clearInterval(S.clock); S.clock = null;
  go('login');
}

// ------------------------------------------------------------------ router
const VIEWS = {};

async function router() {
  const [route, param] = location.hash.replace(/^#\/?/, '').split('/');
  if (!S.token) return route === 'registro' ? renderRegister() : renderLogin();
  const allowed = NAV[role()].map(([id]) => id).concat('orden');
  const r = allowed.includes(route) ? route : 'inicio';
  if (r !== route) return go(r);
  renderShell(r);
  const view = $('#view');
  view.innerHTML = '<div class="loading">Cargando datos…</div>';
  try {
    await VIEWS[r](view, param && decodeURIComponent(param));
    view.style.animation = 'none'; void view.offsetWidth; view.style.animation = '';
    countUp(view);
  } catch (e) {
    view.innerHTML = `<div class="card empty error">${esc(e.message)}</div>`;
  }
}

function updateSysPill() {
  const pill = $('.sys-pill');
  if (!pill) return;
  const ok = SVCS.filter((s) => S.health[s]).length;
  pill.classList.toggle('warn', ok < SVCS.length);
  pill.innerHTML = `<span class="dot"></span>${ok}/${SVCS.length} en línea · ${dbEngine()}`;
}

function renderShell(active) {
  if (!$('.shell')) {
    const initials = (S.user.full_name || '?').split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase();
    $('#app').innerHTML = `<div class="shell">
      <aside class="sidebar">
        ${brand()}
        <div class="nav-label">Navegación</div>
        <nav class="nav"></nav>
        <div class="who"><span class="avatar">${esc(initials)}</span>
          <div><b>${esc(S.user.full_name)}</b><span class="muted">${ROLE_LABEL[role()]}</span></div>
          <button class="btn sm ghost" id="logout">${ico('logout')} Cerrar sesión</button></div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="actions"><button class="icon-btn menu-btn" id="menu" aria-label="Menú">☰</button><h3 id="title"></h3></div>
          <div class="top-right"><span class="sys-pill"><span class="dot"></span>conectando…</span>
            <span class="clock" id="clock"></span>
            <a class="bell" href="#/notificaciones" title="Notificaciones">${ico('bell')}<span class="count" hidden></span></a></div>
        </header>
        <section class="view" id="view"></section>
      </div>
    </div>`;
    $('#logout').onclick = logout;
    $('#menu').onclick = () => $('.shell').classList.toggle('open');
    const tick = () => { const c = $('#clock'); if (c) c.textContent = new Date().toLocaleTimeString('es-CO', { hour12: false }); };
    tick();
    clearInterval(S.clock);
    S.clock = setInterval(tick, 1000);
    updateSysPill();
    if (!Object.keys(S.health).length) refreshHealth();
    startPolling();
  }
  $('.nav').innerHTML = NAV[role()].map(([id, label, icon]) =>
    `<a href="#/${id}" class="${id === active || (active === 'orden' && id === 'ordenes') ? 'active' : ''}">${ico(icon)}<span>${label}</span></a>`).join('');
  $('#title').textContent = (NAV[role()].find(([id]) => id === active) || [, 'Detalle de orden'])[1];
  $('.shell').classList.remove('open');
}

// ------------------------------------------------------------------ notificaciones (sondeo)
function startPolling() {
  clearInterval(S.poll);
  S.unread = -1;
  const tick = async () => {
    if (!S.token) return;
    try {
      const { unread } = await api('notificaciones', '/notifications/me/unread-count');
      const el = $('.bell .count');
      if (el) { el.hidden = !unread; el.textContent = unread > 99 ? '99+' : unread; }
      if (S.unread >= 0 && unread > S.unread) {
        const [latest] = await api('notificaciones', '/notifications/me?unread_only=true&limit=1');
        if (latest) {
          toast(`🔔 ${latest.title}`, latest.type === 'alerta' ? 'error' : 'success');
          const [route, id] = location.hash.replace(/^#\/?/, '').split('/');
          if (route === 'orden' && Number(id) === latest.order_id) router();
        }
      }
      S.unread = unread;
    } catch { /* silencioso */ }
  };
  tick();
  S.poll = setInterval(tick, 10000);
}

// ------------------------------------------------------------------ autenticación
function authLayout(inner) {
  $('#app').innerHTML = `<div class="auth">
    <section class="auth-hero">
      ${brand('Smart Workshop Platform')}
      <div class="hero-visual">
        <div class="car">${art('vehiculo')}</div>
        <div class="scan"></div>
        <div class="orbit o1">${art('motor')}</div>
        <div class="orbit o2">${art('disco')}</div>
        <div class="orbit o3">${art('bateria')}</div>
        <div class="orbit o4">${art('diagnostico')}</div>
      </div>
      <div class="hero-copy">
        <h1>Tu taller, <span>en modo futuro.</span></h1>
        <p>Registra tu vehículo, solicita servicios, aprueba cotizaciones y sigue cada reparación en tiempo real.</p>
        <div class="hero-feats">
          <div><b>8</b><span>microservicios conectados</span></div>
          <div><b>24/7</b><span>seguimiento de órdenes</span></div>
          <div><b>100%</b><span>notificaciones en vivo</span></div>
        </div>
      </div>
    </section>
    <section class="auth-side"><div class="card auth-card corner">${inner}</div></section>
  </div>`;
}

const field = (icon, input) => `<div class="input-icon">${ico(icon)}${input}</div>`;

function bindEye(root) {
  $$('.eye', root).forEach((b) => b.onclick = () => {
    const inp = b.parentElement.querySelector('input');
    inp.type = inp.type === 'password' ? 'text' : 'password';
    b.textContent = inp.type === 'password' ? 'VER' : 'OCULTAR';
  });
}

function renderLogin() {
  authLayout(`<h1>Acceso al sistema</h1>
    <p class="muted">Ingresa tus credenciales para continuar.</p>
    <form class="form" id="f">
      <label class="field">Correo electrónico${field('mail', '<input name="email" type="email" required autocomplete="username" placeholder="tu@correo.com">')}</label>
      <label class="field">Contraseña${field('lock', '<input name="password" type="password" required autocomplete="current-password" placeholder="••••••••"><button type="button" class="eye">VER</button>')}</label>
      <button class="btn primary block">${ico('bolt')} Ingresar</button>
    </form>
    <p class="auth-alt">¿No tienes cuenta? <a href="#/registro">Regístrate gratis</a></p>
    <div class="demo"><p>Acceso rápido de demostración</p><div class="demo-chips">
      <button type="button" data-u="admin@taller.com" data-p="admin123"><b>Administrador</b><span>admin@taller.com</span></button>
      <button type="button" data-u="mecanico@taller.com" data-p="mecanico123"><b>Mecánico</b><span>mecanico@taller.com</span></button>
    </div></div>`);
  const f = $('#f');
  bindEye(f);
  $$('.demo button').forEach((b) => b.onclick = () => { f.email.value = b.dataset.u; f.password.value = b.dataset.p; f.requestSubmit(); });
  f.onsubmit = async (e) => {
    e.preventDefault();
    const btn = $('button.primary', f);
    btn.disabled = true;
    await act(async () => { saveSession(await api('auth', '/login', { body: formValues(f) })); toast(`Bienvenido, ${firstName()}`, 'success'); go('inicio'); });
    btn.disabled = false;
  };
}

function renderRegister() {
  authLayout(`<h1>Crear cuenta</h1>
    <p class="muted">Únete a Mecasolic y gestiona tus vehículos.</p>
    <form class="form" id="f">
      <label class="field">Nombre completo${field('user', '<input name="full_name" required minlength="3" placeholder="Nombre y apellido">')}</label>
      <label class="field">Correo electrónico${field('mail', '<input name="email" type="email" required placeholder="tu@correo.com">')}</label>
      <label class="field">Teléfono${field('phone', '<input name="phone" placeholder="300 000 0000">')}</label>
      <label class="field">Contraseña${field('lock', '<input name="password" type="password" required minlength="6" placeholder="Mínimo 6 caracteres"><button type="button" class="eye">VER</button>')}</label>
      <button class="btn primary block">${ico('check')} Crear cuenta</button>
    </form>
    <p class="auth-alt">¿Ya tienes cuenta? <a href="#/login">Ingresa</a></p>`);
  const f = $('#f');
  bindEye(f);
  f.onsubmit = async (e) => {
    e.preventDefault();
    await act(async () => { saveSession(await api('auth', '/register', { body: formValues(f) })); go('vehiculos'); },
      '¡Bienvenido a Mecasolic! Registra tu primer vehículo.');
  };
}

// ------------------------------------------------------------------ componentes
const kpi = (label, value, icon, { tone = '', sub = '', href = '', isMoney = false } = {}) =>
  `<${href ? `a href="${href}"` : 'div'} class="card kpi ${tone}"><span class="l">${label}</span>
    <span class="n" data-count="${value}" ${isMoney ? 'data-money' : ''}>${isMoney ? money(value) : value}</span>
    <span class="ico">${ico(icon)}</span>${sub ? `<span class="s">${sub}</span>` : ''}</${href ? 'a' : 'div'}>`;

function ordersTable(orders, { showClient = true } = {}) {
  if (!orders.length) return '<div class="empty">No hay órdenes para mostrar.</div>';
  return `<div class="table-wrap"><table><thead><tr><th>Orden</th>${showClient ? '<th>Cliente</th>' : ''}<th>Vehículo</th>
    <th>Servicio</th><th>Mecánico</th><th>Estado</th><th>Actualizada</th></tr></thead><tbody>
    ${orders.map((o) => `<tr class="clickable" data-go="orden/${o.id}"><td><div class="cell-flex">${thumb(art(orderArt(o)), 'sm')}<b class="mono">${esc(o.code)}</b></div></td>
      ${showClient ? `<td>${esc(o.client_name)}</td>` : ''}<td>${esc(o.vehicle_label)}</td>
      <td>${esc(o.service_name || (o.kind === 'REPARACION' ? 'Reparación' : 'Mantenimiento'))}</td>
      <td>${esc(o.mechanic_name || '—')}</td><td>${badge(o.status)}</td><td class="small muted">${fdate(o.updated_at)}</td></tr>`).join('')}
    </tbody></table></div>`;
}

function miniOrders(orders) {
  if (!orders.length) return '<div class="empty">Sin órdenes en curso.</div>';
  return orders.map((o) => `<div class="mini-order" data-go="orden/${o.id}">${thumb(art(orderArt(o)), 'sm')}
    <div><b>${esc(o.code)}</b> <span class="muted small">· ${esc(o.vehicle_label)}</span>
      <div class="meter ${o.status === 'COTIZADA' ? 'hot' : ''}"><i style="width:${progressOf(o.status)}%"></i></div></div>
    ${badge(o.status)}</div>`).join('');
}

function bindRowLinks(root) {
  $$('[data-go]', root).forEach((el) => el.addEventListener('click', () => go(el.dataset.go)));
}

function donut(entries, centerLabel) {
  const total = entries.reduce((s, e) => s + e.value, 0);
  const R = 62;
  const C = 2 * Math.PI * R;
  let offset = 0;
  const arcs = total ? entries.filter((e) => e.value).map((e) => {
    const len = (e.value / total) * C;
    const seg = `<circle cx="80" cy="80" r="${R}" stroke="${e.color}" stroke-dasharray="${Math.max(len - 2, 0.1)} ${C}" stroke-dashoffset="${-offset}"/>`;
    offset += len;
    return seg;
  }).join('') : '';
  return `<div class="donut-wrap"><div class="donut-center">
      <svg class="donut" viewBox="0 0 160 160"><circle cx="80" cy="80" r="${R}" stroke="#f3f4f6"/>${arcs}</svg>
      <div class="c"><div><b data-count="${total}">${total}</b><span>${centerLabel}</span></div></div></div>
    <div class="legend">${entries.map((e) => `<div><i style="background:${e.color};color:${e.color}"></i><span>${e.label}</span><b>${e.value}</b></div>`).join('')}</div></div>`;
}

function stepper(status) {
  const idx = FLOW.indexOf(status === 'RECHAZADA' ? 'COTIZADA' : status);
  return `<div class="stepper">${FLOW.map((s, i) => {
    const cls = status === 'CANCELADA' ? '' : i < idx || (i === idx && status === 'ENTREGADA') ? 'done' : i === idx ? 'current' : '';
    return `<div class="step ${cls}"><span class="dot"></span>${STATUS[s].label}</div>`;
  }).join('')}</div>`;
}

const itemArt = (i) => (i.kind === 'REPUESTO' ? partArt({ sku: '', name: i.description, category: '' }) : i.kind === 'SERVICIO' ? serviceArt({ name: i.description }) : 'mantenimiento');

function itemsTable(items, { subtotal, tax, total, taxRate } = {}) {
  return `<div class="table-wrap"><table><thead><tr><th>Concepto</th><th class="right">Cant.</th>
    <th class="right">Precio</th><th class="right">Subtotal</th></tr></thead><tbody>
    ${items.map((i) => `<tr><td><div class="cell-flex">${thumb(art(itemArt(i)), 'sm')}<div><b>${esc(i.description)}</b>
      <div class="small muted">${KIND[i.kind] || esc(i.kind)}</div></div></div></td><td class="right mono">${i.quantity}</td>
      <td class="right mono">${money(i.unit_price)}</td><td class="right mono">${money(i.subtotal)}</td></tr>`).join('')}
    </tbody><tfoot>
    ${tax != null ? `<tr><td colspan="3" class="right">Subtotal</td><td class="right mono">${money(subtotal)}</td></tr>
      <tr><td colspan="3" class="right">IVA (${Math.round(taxRate * 100)}%)</td><td class="right mono">${money(tax)}</td></tr>` : ''}
    <tr><td colspan="3" class="right">Total</td><td class="right mono hot" style="font-size:16px">${money(total)}</td></tr>
    </tfoot></table></div>`;
}

function invoiceModal(inv, onChange) {
  const canPay = inv.status === 'PENDIENTE' && ['cliente', 'admin'].includes(role());
  const body = `<dl class="kv"><dt>Factura</dt><dd><span class="mono">${esc(inv.number)}</span> <span class="badge ${INVOICE_CLS[inv.status]}">${inv.status}</span></dd>
      <dt>Orden</dt><dd><a href="#/orden/${inv.order_id}">${esc(inv.order_code)}</a></dd>
      <dt>Cliente</dt><dd>${esc(inv.client_name)}</dd><dt>Vehículo</dt><dd>${esc(inv.vehicle_label)}</dd>
      <dt>Emitida</dt><dd>${fdate(inv.issued_at)}</dd>${inv.paid_at ? `<dt>Pagada</dt><dd>${fdate(inv.paid_at)}</dd>` : ''}</dl>
    <div class="mt">${itemsTable(inv.items, { subtotal: inv.subtotal, tax: inv.tax, total: inv.total, taxRate: inv.tax_rate })}</div>
    ${inv.payments.map((p) => `<p class="small muted">✔ Pago ${esc(p.method)} · ref. <span class="mono">${esc(p.reference)}</span> · ${fdate(p.created_at)} · ${esc(p.paid_by)}</p>`).join('')}
    ${canPay ? `<div class="form mt"><label class="field">Medio de pago
      <select name="method"><option value="TARJETA">Tarjeta</option><option value="TRANSFERENCIA">Transferencia</option>
      <option value="EFECTIVO">Efectivo</option></select></label></div>` : ''}`;
  modal(`Factura ${inv.number}`, body, {
    wide: true, submit: `Pagar ${money(inv.total)}`,
    onSubmit: canPay ? async (v) => {
      await api('facturacion', `/invoices/${inv.id}/pay`, { body: { method: v.method } });
      toast('Pago registrado correctamente', 'success');
      onChange?.();
    } : null,
  });
}

// ------------------------------------------------------------------ vistas: inicio / dashboards
VIEWS.inicio = async (view) => {
  if (role() === 'admin') return homeAdmin(view);
  if (role() === 'mecanico') return homeMechanic(view);
  return homeClient(view);
};

async function homeClient(view) {
  const [orders, vehicles, invoices] = await Promise.all([api('ordenes', '/orders'), api('clientes', '/vehicles'),
    api('facturacion', '/invoices?status=PENDIENTE')]);
  const active = orders.filter((o) => ACTIVE.includes(o.status));
  const pendingQuotes = orders.filter((o) => o.status === 'COTIZADA');
  view.innerHTML = `
    <div class="card hello corner"><div>
      <h1>Hola, <span>${firstName()}</span> 👋</h1>
      <p>${active.length ? `Tienes ${active.length} orden(es) en curso. Te avisaremos de cada avance.` : 'Todo en orden. ¿Necesitas un servicio para tu vehículo?'}</p>
      <div class="actions"><a class="btn primary" href="#/solicitar">${ico('plus')} Solicitar servicio</a>
        <a class="btn" href="#/vehiculos">${ico('car')} Mis vehículos</a></div></div>
      ${art('vehiculo')}</div>
    <div class="mt">
    ${pendingQuotes.map((o) => `<div class="banner amber">${ico('alert').replace('<svg', '<svg width="20" height="20"')} La orden <a href="#/orden/${o.id}"><b>${esc(o.code)}</b></a> tiene una cotización
      de ${money(o.quote_total)} esperando tu aprobación.</div>`).join('')}
    ${invoices.map((i) => `<div class="banner green">${ico('check').replace('<svg', '<svg width="20" height="20"')} Tu vehículo de la orden <a href="#/orden/${i.order_id}"><b>${esc(i.order_code)}</b></a>
      está listo. Factura ${esc(i.number)} pendiente por ${money(i.total)}.</div>`).join('')}</div>
    <div class="grid cols-3">
      ${kpi('Vehículos', vehicles.length, 'car', { href: '#/vehiculos', sub: 'registrados en tu garaje' })}
      ${kpi('Órdenes en curso', active.length, 'clipboard', { tone: 'violet', href: '#/ordenes', sub: `${orders.length} en total` })}
      ${kpi('Por pagar', invoices.reduce((s, i) => s + i.total, 0), 'money', { tone: 'hot', href: '#/facturas', isMoney: true, sub: `${invoices.length} factura(s) pendiente(s)` })}
    </div>
    <div class="grid span mt">
      <div class="card"><div class="card-head"><h2>Seguimiento en vivo</h2><a href="#/ordenes" class="small">Ver todas →</a></div>${miniOrders(active.slice(0, 6))}</div>
      <div class="card"><div class="card-head"><h2>Mi garaje</h2><a href="#/vehiculos" class="small">Gestionar →</a></div>
        ${vehicles.length ? vehicles.slice(0, 4).map((v) => `<div class="mini-order" data-go="solicitar/${v.id}">${thumb(art('vehiculo'), 'sm')}
          <div><b>${esc(v.brand)} ${esc(v.model)}</b> <span class="muted small">· ${v.year}</span><div class="small muted">${v.mileage.toLocaleString('es-CO')} km</div></div>
          <span class="plate sm">${esc(v.plate)}</span></div>`).join('') : '<div class="empty">Aún no registras vehículos.</div>'}</div>
    </div>`;
  bindRowLinks(view);
}

async function homeMechanic(view) {
  const orders = await api('ordenes', '/orders');
  const cols = [['EN_DIAGNOSTICO', 'Por diagnosticar', 'cpu'], ['COTIZADA', 'Esperando cliente', 'money'],
    ['APROBADA', 'Listas para reparar', 'check'], ['EN_REPARACION', 'En reparación', 'wrench']];
  const by = (st) => orders.filter((o) => o.status === st);
  view.innerHTML = `<div class="page-head"><div><h1>Centro de control</h1><div class="sub">Hola, ${firstName()} · tablero de trabajo del día</div></div></div>
    <div class="grid cols-4">${cols.map(([st, l, i], n) => kpi(l, by(st).length, i, { tone: ['', 'hot', 'green', 'violet'][n] })).join('')}</div>
    <div class="kanban mt">${cols.map(([st, l]) => `<div class="card col"><h2>${l} <b>${by(st).length}</b></h2>
      ${by(st).map((o) => `<div class="task" data-go="orden/${o.id}"><div class="cell-flex">${thumb(art(orderArt(o)), 'sm')}<b>${esc(o.code)}</b></div>
        <span>${esc(o.vehicle_label)}</span><small>${esc(o.description).slice(0, 80)}</small></div>`).join('') || '<div class="empty small" style="padding:20px 0">Vacío</div>'}
    </div>`).join('')}</div>`;
  bindRowLinks(view);
}

async function homeAdmin(view) {
  const [stats, orders, parts, invoices, mechs] = await Promise.all([
    api('ordenes', '/orders/stats'), api('ordenes', '/orders'), api('inventario', '/parts'),
    api('facturacion', '/invoices'), api('mecanicos', '/mechanics'), refreshHealth()]);
  const b = stats.by_status;
  const activeCount = ACTIVE.reduce((s, st) => s + (b[st] || 0), 0);
  const paid = invoices.filter((i) => i.status === 'PAGADA').reduce((s, i) => s + i.total, 0);
  const pending = invoices.filter((i) => i.status === 'PENDIENTE').reduce((s, i) => s + i.total, 0);
  const critical = [...parts].sort((x, y) => x.stock / Math.max(1, x.min_stock) - y.stock / Math.max(1, y.min_stock)).slice(0, 6);
  const maxLoad = Math.max(1, ...mechs.map((m) => m.active_assignments));
  const health = S.health;
  const dbName = (h) => h?.database?.name ? String(h.database.name).split(/[\\/]/).pop() : '';

  view.innerHTML = `<div class="page-head"><div><h1>Centro de mando</h1><div class="sub">Visión general del taller en tiempo real</div></div>
      <a class="btn primary" href="#/ordenes">${ico('clipboard')} Ver órdenes</a></div>
    <div class="grid cols-4">
      ${kpi('Órdenes activas', activeCount, 'clipboard', { href: '#/ordenes', sub: `${stats.total} órdenes registradas` })}
      ${kpi('Sin asignar', b.SOLICITADA, 'alert', { tone: 'hot', href: '#/ordenes', sub: 'esperando mecánico' })}
      ${kpi('Ingresos cobrados', paid, 'money', { tone: 'green', href: '#/facturas', isMoney: true, sub: 'facturas pagadas' })}
      ${kpi('Por cobrar', pending, 'receipt', { tone: 'violet', href: '#/facturas', isMoney: true, sub: `${invoices.filter((i) => i.status === 'PENDIENTE').length} factura(s)` })}
    </div>
    <div class="grid span mt">
      <div class="card corner"><h2>Órdenes por estado</h2>
        ${donut(Object.keys(STATUS).map((s) => ({ label: STATUS[s].label, value: b[s] || 0, color: STATUS[s].color })), 'órdenes')}</div>
      <div class="card"><div class="card-head"><h2>Estado del sistema</h2><span class="badge ${SVCS.every((s) => health[s]) ? 'green' : 'red'}">${dbEngine()}</span></div>
        <div class="health">${SVCS.map((s) => `<div class="${health[s] && health[s].database?.status !== 'error' ? '' : 'off'}"><i></i>${SVC_LABEL[s]}
          <small>${health[s] ? esc(dbName(health[s])) : 'sin respuesta'}</small></div>`).join('')}</div>
        <p class="small muted" style="margin:14px 0 0">Cada microservicio usa su propia base de datos (${dbEngine()}).</p></div>
    </div>
    <div class="grid cols-2 mt">
      <div class="card"><div class="card-head"><h2>Solicitudes sin asignar</h2><span class="badge gray">${b.SOLICITADA}</span></div>
        ${miniOrders(orders.filter((o) => o.status === 'SOLICITADA').slice(0, 6))}</div>
      <div class="card"><div class="card-head"><h2>Inventario crítico</h2><a href="#/inventario" class="small">Inventario →</a></div>
        <div class="bars">${critical.map((p) => `<div class="bar-row">${thumb(art(partArt(p)), 'sm')}<div>
          <div class="top"><span>${esc(p.name)}</span><span>${p.stock} / mín ${p.min_stock}</span></div>
          <div class="meter ${p.low_stock ? 'low' : ''}"><i style="width:${Math.min(100, (p.stock / Math.max(1, p.min_stock * 3)) * 100)}%"></i></div></div></div>`).join('')}</div></div>
    </div>
    <div class="grid cols-2 mt">
      <div class="card"><div class="card-head"><h2>Carga de mecánicos</h2><a href="#/mecanicos" class="small">Equipo →</a></div>
        <div class="bars">${mechs.map((m) => `<div class="bar-row"><span class="avatar" style="width:38px;height:38px;font-size:12px">${esc(m.full_name.split(' ').map((w) => w[0]).slice(0, 2).join(''))}</span><div>
          <div class="top"><span>${esc(m.full_name)} <span class="muted small">· ${esc(m.specialty)}</span></span><span>${m.active_assignments} activas</span></div>
          <div class="meter hot"><i style="width:${(m.active_assignments / maxLoad) * 100}%"></i></div></div></div>`).join('')}</div></div>
      <div class="card"><div class="card-head"><h2>Actividad reciente</h2></div>${miniOrders(orders.slice(0, 6))}</div>
    </div>`;
  bindRowLinks(view);
}

// ------------------------------------------------------------------ vistas: vehículos (cliente)
const vehicleForm = (extra = '') => `<div class="form">${extra}
  <div class="row"><label class="field">Placa<input name="plate" required maxlength="15" placeholder="ABC123"></label>
  <label class="field">Año<input name="year" type="number" required min="1950" max="2100"></label></div>
  <div class="row"><label class="field">Marca<input name="brand" required placeholder="Toyota"></label>
  <label class="field">Modelo<input name="model" required placeholder="Corolla"></label></div>
  <div class="row"><label class="field">Color<input name="color"></label>
  <label class="field">Kilometraje<input name="mileage" type="number" min="0" value="0"></label></div>
  <label class="field">VIN (opcional)<input name="vin"></label></div>`;

const vehicleBody = (v) => ({ ...v, year: Number(v.year), mileage: Number(v.mileage || 0), customer_id: numOrNull(v.customer_id) });

VIEWS.vehiculos = async (view) => {
  const vehicles = await api('clientes', '/vehicles');
  view.innerHTML = `<div class="page-head"><div><h1>Mi garaje</h1><div class="sub">${vehicles.length} vehículo(s) registrado(s)</div></div>
      <button class="btn primary" id="add">${ico('plus')} Registrar vehículo</button></div>
    ${vehicles.length ? `<div class="products">${vehicles.map((v) => `<div class="card product vehicle-card">
      <div class="pic">${art('vehiculo')}</div>
      <div class="meta"><span class="plate">${esc(v.plate)}</span><span>${v.year}</span></div>
      <h3>${esc(v.brand)} ${esc(v.model)}</h3>
      <div class="small muted">${esc(v.color || 'Sin color')} · ${v.mileage.toLocaleString('es-CO')} km</div>
      <div class="foot"><a class="btn sm primary" href="#/solicitar/${v.id}">Solicitar servicio</a>
      <a class="btn sm" href="#/ordenes/${v.id}">Historial</a></div></div>`).join('')}</div>`
    : `<div class="card empty"><div style="width:160px;margin:0 auto">${art('vehiculo')}</div>Aún no tienes vehículos registrados.</div>`}`;
  $('#add').onclick = () => modal('Registrar vehículo', vehicleForm(), {
    onSubmit: async (v) => { await api('clientes', '/vehicles', { body: vehicleBody(v) }); toast('Vehículo registrado', 'success'); router(); },
  });
};

// ------------------------------------------------------------------ vistas: solicitar servicio
VIEWS.solicitar = async (view, vehicleId) => {
  const [vehicles, catalog] = await Promise.all([api('clientes', '/vehicles'), api('servicios', '/catalog')]);
  if (!vehicles.length) {
    view.innerHTML = '<div class="card empty">Primero debes <a href="#/vehiculos">registrar un vehículo</a>.</div>';
    return;
  }
  view.innerHTML = `<div class="page-head"><div><h1>Solicitar servicio</h1><div class="sub">Elige el vehículo, el servicio y cuéntanos qué necesitas</div></div></div>
    <div class="card corner"><form class="form" id="f">
      <div class="row"><label class="field">Vehículo<select name="vehicle_id" required>${vehicles.map((v) =>
        `<option value="${v.id}" ${String(v.id) === vehicleId ? 'selected' : ''}>${esc(v.brand)} ${esc(v.model)} ${v.year} · ${esc(v.plate)}</option>`).join('')}</select></label>
        <label class="field">Kilometraje actual<input name="mileage" type="number" min="0" placeholder="Opcional"></label></div>
      <div class="field"><span>Tipo de servicio</span><div class="radio-group">
        <label><input type="radio" name="kind" value="MANTENIMIENTO" checked> Mantenimiento</label>
        <label><input type="radio" name="kind" value="REPARACION"> Reparación</label></div></div>
      <div class="field"><span>Servicio del catálogo</span><div class="svc-pick" id="svcs"></div></div>
      <label class="field">Describe el problema o lo que necesitas<textarea name="description" required minlength="5"
        placeholder="Ej.: Se escucha un chirrido al frenar y el pedal se siente esponjoso."></textarea></label>
      <div class="actions"><button class="btn primary">${ico('bolt')} Enviar solicitud</button></div>
    </form></div>`;
  const f = $('#f');
  const fill = () => {
    const kind = f.kind.value;
    const opts = catalog.filter((s) => s.category === kind || s.category === 'DIAGNOSTICO');
    $('#svcs').innerHTML = `<label><input type="radio" name="service_id" value="" checked>${thumb(art('diagnostico'))}
        <b>No estoy seguro</b><span class="small muted">Un mecánico revisará el vehículo y te dará un diagnóstico.</span></label>` +
      opts.map((s) => `<label><input type="radio" name="service_id" value="${s.id}">${thumb(art(serviceArt(s)))}
        <b>${esc(s.name)}</b><span class="price">desde ${money(s.base_price)}</span>
        <span class="small muted">${esc(s.description)} · ${s.estimated_hours} h</span></label>`).join('');
  };
  $$('input[name=kind]', f).forEach((r) => r.onchange = fill);
  fill();
  f.onsubmit = async (e) => {
    e.preventDefault();
    if (!f.reportValidity()) return;
    const v = formValues(f);
    await act(async () => {
      const o = await api('ordenes', '/orders', { body: { vehicle_id: Number(v.vehicle_id), kind: v.kind,
        service_id: numOrNull(v.service_id), mileage: numOrNull(v.mileage), description: v.description } });
      go(`orden/${o.id}`);
    }, 'Solicitud enviada. Te notificaremos cada avance.');
  };
};

// ------------------------------------------------------------------ vistas: órdenes
VIEWS.ordenes = async (view, vehicleId) => {
  const qs = vehicleId ? `?vehicle_id=${vehicleId}` : '';
  const orders = await api('ordenes', `/orders${qs}`);
  const titles = { cliente: 'Mis órdenes', mecanico: 'Órdenes asignadas', admin: 'Órdenes de trabajo' };
  view.innerHTML = `<div class="page-head"><div><h1>${titles[role()]}</h1><div class="sub">${vehicleId ? 'Historial del vehículo' : `${orders.length} orden(es)`}</div></div>
      <div class="actions"><select id="flt" style="width:auto"><option value="">Todos los estados</option>
      <option value="__active">Activas</option>${Object.entries(STATUS).map(([k, s]) => `<option value="${k}">${s.label}</option>`).join('')}</select>
      ${role() === 'admin' ? `<button class="btn primary" id="new">${ico('plus')} Nueva orden</button>` : ''}
      ${role() === 'cliente' ? `<a class="btn primary" href="#/solicitar">${ico('plus')} Solicitar servicio</a>` : ''}</div></div>
    <div class="card" id="list"></div>`;
  const draw = () => {
    const f = $('#flt').value;
    const list = f === '__active' ? orders.filter((o) => ACTIVE.includes(o.status)) : f ? orders.filter((o) => o.status === f) : orders;
    $('#list').innerHTML = ordersTable(list, { showClient: role() !== 'cliente' });
    bindRowLinks($('#list'));
  };
  $('#flt').onchange = draw;
  draw();
  $('#new')?.addEventListener('click', async () => {
    const [vehicles, catalog] = await Promise.all([api('clientes', '/vehicles'), api('servicios', '/catalog')]);
    modal('Nueva orden (cliente en mostrador)', `<div class="form">
      <label class="field">Vehículo<select name="vehicle_id" required>${vehicles.map((v) =>
        `<option value="${v.id}">${esc(v.plate)} · ${esc(v.brand)} ${esc(v.model)} · ${esc(v.owner_name)}</option>`).join('')}</select></label>
      <label class="field">Tipo<select name="kind"><option value="MANTENIMIENTO">Mantenimiento</option><option value="REPARACION">Reparación</option></select></label>
      <label class="field">Servicio<select name="service_id"><option value="">— Sin servicio específico —</option>
        ${catalog.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join('')}</select></label>
      <label class="field">Descripción<textarea name="description" required minlength="5"></textarea></label></div>`, {
      submit: 'Crear orden',
      onSubmit: async (v) => {
        const o = await api('ordenes', '/orders', { body: { vehicle_id: Number(v.vehicle_id), kind: v.kind,
          service_id: numOrNull(v.service_id), description: v.description } });
        go(`orden/${o.id}`);
      },
    });
  });
};

// ------------------------------------------------------------------ vista: detalle de orden
VIEWS.orden = async (view, id) => {
  const o = await api('ordenes', `/orders/${id}`);
  const r = role();
  const isStaff = r !== 'cliente';
  const q = o.quote;
  const inv = o.invoice;

  let banner = '';
  if (o.status === 'CANCELADA') banner = '<div class="banner red">Esta orden fue cancelada.</div>';
  else if (o.status === 'COTIZADA' && r === 'cliente') banner = '<div class="banner amber">El mecánico terminó el diagnóstico. Revisa la cotización y apruébala para iniciar la reparación.</div>';
  else if (o.status === 'RECHAZADA') banner = '<div class="banner red">La cotización fue rechazada. El mecánico puede proponer una nueva.</div>';
  else if (o.status === 'FINALIZADA') banner = `<div class="banner green">¡El servicio está terminado! ${inv?.status === 'PAGADA' ? 'Factura pagada; el vehículo está listo para entrega.' : 'Paga la factura para retirar el vehículo.'}</div>`;

  view.innerHTML = `<div class="page-head"><div class="order-hero">${thumb(art(orderArt(o)))}<div>
      <h1><span class="mono">${esc(o.code)}</span> ${badge(o.status)}</h1>
      <div class="sub">${esc(o.vehicle_label)} · creada ${fdate(o.created_at)}</div></div></div>
      <a class="btn ghost" href="#/ordenes">← Volver</a></div>
    ${banner}
    <div class="card corner"><div class="card-head"><h2>Progreso</h2><span class="mono hot">${progressOf(o.status)}%</span></div>${stepper(o.status)}</div>
    <div class="layout-detail mt">
      <div>
        <div class="card"><h2>Solicitud</h2><dl class="kv">
          <dt>Cliente</dt><dd>${esc(o.client_name)}</dd><dt>Vehículo</dt><dd>${esc(o.vehicle_label)}</dd>
          <dt>Tipo</dt><dd>${o.kind === 'REPARACION' ? 'Reparación' : 'Mantenimiento'}</dd>
          <dt>Servicio</dt><dd>${esc(o.service_name || 'Diagnóstico general')}</dd>
          ${o.mileage != null ? `<dt>Kilometraje</dt><dd>${o.mileage.toLocaleString('es-CO')} km</dd>` : ''}
          <dt>Mecánico</dt><dd>${esc(o.mechanic_name || 'Pendiente de asignación')}</dd>
          ${o.estimated_delivery ? `<dt>Entrega estimada</dt><dd>${fday(o.estimated_delivery)}</dd>` : ''}
          <dt>Descripción</dt><dd>${esc(o.description)}</dd></dl></div>
        ${o.diagnosis ? `<div class="card"><h2>Diagnóstico</h2><div class="diagnosis">${esc(o.diagnosis)}</div></div>` : ''}
        ${q ? `<div class="card"><div class="card-head"><h2>Cotización #${q.id}</h2>
            <span class="badge ${{ PENDIENTE: 'amber', APROBADA: 'green', RECHAZADA: 'red', REEMPLAZADA: 'gray' }[q.status]}">${q.status}</span></div>
          ${itemsTable(q.items, { total: q.total })}
          ${q.notes ? `<p class="muted">${esc(q.notes)}</p>` : ''}
          ${o.status === 'COTIZADA' && ['cliente', 'admin'].includes(r) ? `<div class="actions mt">
            <button class="btn success" id="approve">${ico('check')} Aprobar cotización</button><button class="btn danger" id="reject">Rechazar</button></div>` : ''}
          </div>` : ''}
        ${inv ? `<div class="card"><div class="card-head"><h2>Factura ${esc(inv.number)}</h2>
            <span class="badge ${INVOICE_CLS[inv.status]}">${inv.status}</span></div>
            <p style="margin:0">Total con IVA: <b class="hot">${money(inv.total)}</b></p>
            <div class="actions mt"><button class="btn ${inv.status === 'PENDIENTE' && r !== 'mecanico' ? 'primary' : ''}" id="inv">
            ${inv.status === 'PENDIENTE' && r !== 'mecanico' ? 'Ver y pagar factura' : 'Ver factura'}</button></div></div>` : ''}
        <div id="work"></div>
      </div>
      <div>
        <div class="card" id="actions-card"><h2>Acciones</h2><div class="actions" id="actions"></div></div>
        <div class="card"><h2>Seguimiento</h2><ul class="timeline">
          ${[...o.events].reverse().map((e) => `<li><span class="tl-dot"></span><div><div>${badge(e.status)}</div>
            <div style="margin-top:6px">${esc(e.note)}</div>
            <div class="tl-meta">${fdate(e.created_at)} · ${esc(e.author_name)} (${ROLE_LABEL[e.author_role] || e.author_role})</div></div></li>`).join('')}
        </ul></div>
      </div>
    </div>`;

  const reload = () => VIEWS.orden(view, id);
  const post = (path, body, msg) => act(async () => { await api('ordenes', `/orders/${o.id}${path}`, { body }); }, msg).then((ok) => ok && reload());
  const setStatus = (status, msg, note) => post('/status', { status, note }, msg);

  $('#approve')?.addEventListener('click', () => modal('Aprobar cotización', `<p>Se autorizará el trabajo por <b class="hot">${money(q.total)}</b>
      (+ IVA al facturar). Los repuestos se reservarán del inventario.</p>
      <label class="field">Comentario (opcional)<textarea name="comment"></textarea></label>`, {
    submit: 'Aprobar', onSubmit: async (v) => {
      await api('ordenes', `/orders/${o.id}/quote-decision`, { body: { approved: true, comment: v.comment || null } });
      toast('Cotización aprobada', 'success'); reload();
    },
  }));
  $('#reject')?.addEventListener('click', () => modal('Rechazar cotización', `<label class="field">Motivo
      <textarea name="comment" required placeholder="Ej.: El valor supera mi presupuesto"></textarea></label>`, {
    submit: 'Rechazar', onSubmit: async (v) => {
      await api('ordenes', `/orders/${o.id}/quote-decision`, { body: { approved: false, comment: v.comment } });
      toast('Cotización rechazada'); reload();
    },
  }));
  $('#inv')?.addEventListener('click', async () => invoiceModal(await api('facturacion', `/invoices/${inv.id}`), reload));

  const A = [];
  const st = o.status;
  if (r === 'admin' && !['FINALIZADA', 'ENTREGADA', 'CANCELADA'].includes(st)) A.push(['assign', o.mechanic_name ? 'Reasignar mecánico' : 'Asignar mecánico', 'primary']);
  if (isStaff && st === 'APROBADA') A.push(['start', 'Iniciar reparación', 'primary']);
  if (isStaff && st === 'EN_REPARACION') A.push(['finish', 'Finalizar trabajo', 'success']);
  if (r === 'admin' && st === 'FINALIZADA') A.push(['deliver', 'Registrar entrega', 'success']);
  if (isStaff && ['EN_DIAGNOSTICO', 'COTIZADA', 'APROBADA', 'EN_REPARACION', 'RECHAZADA'].includes(st)) A.push(['note', 'Reportar avance', 'cyan']);
  const cancellable = r === 'admin' ? ['SOLICITADA', 'EN_DIAGNOSTICO', 'COTIZADA', 'RECHAZADA', 'APROBADA', 'EN_REPARACION']
    : r === 'cliente' ? ['SOLICITADA', 'EN_DIAGNOSTICO', 'COTIZADA', 'RECHAZADA'] : [];
  if (cancellable.includes(st)) A.push(['cancel', 'Cancelar orden', 'danger']);
  $('#actions').innerHTML = A.length ? A.map(([k, l, c]) => `<button class="btn ${c}" data-a="${k}">${l}</button>`).join('')
    : '<span class="muted">No hay acciones disponibles en este estado.</span>';

  const handlers = {
    assign: async () => {
      const mechs = await api('mecanicos', '/mechanics?active=true');
      modal('Asignar mecánico', `<div class="form"><label class="field">Mecánico<select name="mechanic_id" required>
        ${mechs.map((m) => `<option value="${m.id}" ${m.id === o.mechanic_id ? 'selected' : ''}>${esc(m.full_name)} · ${esc(m.specialty)} · ${m.active_assignments} órdenes activas</option>`).join('')}
        </select></label><label class="field">Notas<input name="notes"></label></div>`, {
        submit: 'Asignar', onSubmit: async (v) => {
          await api('ordenes', `/orders/${o.id}/assign`, { body: { mechanic_id: Number(v.mechanic_id), notes: v.notes || null } });
          toast('Mecánico asignado', 'success'); reload();
        },
      });
    },
    start: () => setStatus('EN_REPARACION', 'Reparación iniciada'),
    finish: () => modal('Finalizar trabajo', `<p>Se generará la factura y se notificará al cliente que el vehículo está listo.</p>
      <label class="field">Nota final (opcional)<textarea name="note" placeholder="Trabajos realizados, recomendaciones…"></textarea></label>`, {
      submit: 'Finalizar', onSubmit: async (v) => {
        await api('ordenes', `/orders/${o.id}/status`, { body: { status: 'FINALIZADA', note: v.note || null } });
        toast('Orden finalizada y factura generada', 'success'); reload();
      },
    }),
    deliver: () => setStatus('ENTREGADA', 'Entrega registrada'),
    note: () => modal('Reportar avance', '<label class="field">Avance<textarea name="note" required minlength="3"></textarea></label>', {
      submit: 'Publicar', onSubmit: async (v) => {
        await api('ordenes', `/orders/${o.id}/notes`, { body: { note: v.note } });
        toast('Avance publicado; el cliente fue notificado', 'success'); reload();
      },
    }),
    cancel: () => modal('Cancelar orden', '<label class="field">Motivo<textarea name="note" required></textarea></label>', {
      submit: 'Cancelar orden', onSubmit: async (v) => {
        await api('ordenes', `/orders/${o.id}/status`, { body: { status: 'CANCELADA', note: v.note } });
        toast('Orden cancelada'); reload();
      },
    }),
  };
  $$('[data-a]', view).forEach((btn) => btn.addEventListener('click', handlers[btn.dataset.a]));

  if (isStaff && ['EN_DIAGNOSTICO', 'RECHAZADA', 'COTIZADA'].includes(st) && (r === 'admin' || o.mechanic_id)) {
    await renderDiagnosisForm($('#work'), o, reload);
  }
};

async function renderDiagnosisForm(container, o, done) {
  const [parts, service] = await Promise.all([
    api('inventario', '/parts'), o.service_id ? api('servicios', `/catalog/${o.service_id}`) : null]);
  const redo = o.status !== 'EN_DIAGNOSTICO';
  container.innerHTML = `<div class="card corner"><h2>${redo ? 'Nueva cotización' : 'Registrar diagnóstico y cotización'}</h2>
    <form class="form" id="diag">
      <label class="field">Diagnóstico<textarea name="diagnosis" required minlength="5"
        placeholder="Hallazgos de la inspección y trabajos recomendados">${esc(o.diagnosis || '')}</textarea></label>
      <div class="row"><label class="field">Entrega estimada<input type="date" name="estimated_delivery" value="${o.estimated_delivery || ''}"></label>
        <label class="field">Notas para el cliente<input name="quote_notes" placeholder="Garantía, condiciones…"></label></div>
      <div><span class="small muted" style="letter-spacing:.06em;text-transform:uppercase;font-weight:600">Ítems de la cotización</span>
        <div class="items" id="items" style="margin-top:8px"></div>
        <div class="actions" style="margin-top:10px"><button type="button" class="btn sm" data-add="MANO_OBRA">+ Mano de obra</button>
          <button type="button" class="btn sm" data-add="REPUESTO">+ Repuesto</button>
          <button type="button" class="btn sm" data-add="SERVICIO">+ Servicio</button></div>
        <div class="items-total">Total cotizado: <b id="tot">$0</b></div></div>
      <div class="actions"><button class="btn primary">${ico('bolt')} Enviar diagnóstico y cotización</button></div>
    </form></div>`;
  const items = $('#items', container);
  const recompute = () => {
    let total = 0;
    $$('.item-row', items).forEach((row) => {
      const sub = (Number(row.querySelector('[name=quantity]').value) || 0) * (Number(row.querySelector('[name=unit_price]').value) || 0);
      row.querySelector('.row-sub').textContent = money(sub);
      total += sub;
    });
    $('#tot', container).textContent = money(total);
  };
  const addRow = (it = { kind: 'MANO_OBRA' }) => {
    const row = document.createElement('div');
    row.className = 'item-row';
    row.dataset.kind = it.kind;
    row.innerHTML = `<select name="kind">${Object.entries(KIND).map(([k, l]) => `<option value="${k}" ${k === it.kind ? 'selected' : ''}>${l}</option>`).join('')}</select>
      <input name="description" placeholder="Descripción del trabajo" value="${esc(it.description || '')}">
      <select name="part_id" class="part-select"><option value="">— Seleccione repuesto —</option>
        ${parts.map((p) => `<option value="${p.id}" data-price="${p.unit_price}" ${p.stock <= 0 ? 'disabled' : ''}>${esc(p.name)} (${esc(p.sku)}) · stock ${p.stock}</option>`).join('')}</select>
      <input name="quantity" type="number" min="1" step="1" value="${it.quantity || 1}" title="Cantidad">
      <input name="unit_price" type="number" min="0" step="100" value="${it.unit_price ?? ''}" placeholder="Precio unit.">
      <span class="row-sub">$0</span>
      <button type="button" class="icon-btn" title="Quitar">×</button>`;
    row.querySelector('[name=kind]').onchange = (e) => { row.dataset.kind = e.target.value; };
    row.querySelector('[name=part_id]').onchange = (e) => {
      row.querySelector('[name=unit_price]').value = e.target.selectedOptions[0]?.dataset.price || '';
      recompute();
    };
    row.querySelector('.icon-btn').onclick = () => { row.remove(); recompute(); };
    row.addEventListener('input', recompute);
    items.appendChild(row);
    recompute();
  };
  $$('[data-add]', container).forEach((b) => b.onclick = () => addRow({ kind: b.dataset.add }));
  if (service) addRow({ kind: 'SERVICIO', description: service.name, unit_price: service.base_price });
  else addRow({ kind: 'MANO_OBRA', description: 'Diagnóstico general' });

  const form = $('#diag', container);
  form.onsubmit = async (e) => {
    e.preventDefault();
    const v = formValues(form);
    const rows = $$('.item-row', items).map((row) => {
      const kind = row.dataset.kind;
      const get = (n) => row.querySelector(`[name=${n}]`).value.trim();
      return {
        kind, description: kind === 'REPUESTO' ? null : get('description'),
        part_id: kind === 'REPUESTO' ? numOrNull(get('part_id')) : null,
        quantity: Number(get('quantity')) || 1, unit_price: numOrNull(get('unit_price')),
      };
    });
    if (!v.diagnosis || v.diagnosis.length < 5) return toast('Escribe el diagnóstico (mínimo 5 caracteres)', 'error');
    if (!rows.length) return toast('Agrega al menos un ítem a la cotización', 'error');
    if (rows.some((x) => x.kind === 'REPUESTO' && !x.part_id)) return toast('Selecciona el repuesto en cada ítem de tipo repuesto', 'error');
    if (rows.some((x) => x.kind !== 'REPUESTO' && !x.description)) return toast('Cada ítem necesita una descripción', 'error');
    const btn = $('button.primary', form);
    btn.disabled = true;
    const ok = await act(() => api('ordenes', `/orders/${o.id}/diagnosis`, { body: {
      diagnosis: v.diagnosis, estimated_delivery: v.estimated_delivery || null, quote_notes: v.quote_notes || null, items: rows } }),
    'Diagnóstico enviado. El cliente fue notificado.');
    btn.disabled = false;
    if (ok) done();
  };
}

// ------------------------------------------------------------------ vistas: facturas
VIEWS.facturas = async (view) => {
  const invoices = await api('facturacion', '/invoices');
  const sum = (st) => invoices.filter((i) => i.status === st).reduce((s, i) => s + i.total, 0);
  view.innerHTML = `<div class="page-head"><div><h1>${role() === 'admin' ? 'Facturación' : 'Mis facturas'}</h1><div class="sub">${invoices.length} factura(s)</div></div></div>
    <div class="grid cols-3">
      ${kpi('Pendiente', sum('PENDIENTE'), 'alert', { tone: 'hot', isMoney: true })}
      ${kpi('Pagado', sum('PAGADA'), 'check', { tone: 'green', isMoney: true })}
      ${kpi('Facturas', invoices.length, 'receipt', { tone: 'violet' })}
    </div>
    <div class="card mt">${invoices.length ? `<div class="table-wrap"><table><thead><tr><th>Factura</th><th>Orden</th>
      ${role() === 'admin' ? '<th>Cliente</th>' : ''}<th>Vehículo</th><th>Emitida</th><th class="right">Total</th><th>Estado</th></tr></thead><tbody>
      ${invoices.map((i) => `<tr class="clickable" data-id="${i.id}"><td><b class="mono">${esc(i.number)}</b></td><td class="mono">${esc(i.order_code)}</td>
        ${role() === 'admin' ? `<td>${esc(i.client_name)}</td>` : ''}<td>${esc(i.vehicle_label)}</td><td class="small">${fdate(i.issued_at)}</td>
        <td class="right mono">${money(i.total)}</td><td><span class="badge ${INVOICE_CLS[i.status]}">${i.status}</span></td></tr>`).join('')}
      </tbody></table></div>` : '<div class="empty">No hay facturas.</div>'}</div>`;
  $$('tr[data-id]', view).forEach((tr) => tr.onclick = () =>
    invoiceModal(invoices.find((i) => String(i.id) === tr.dataset.id), router));
};

// ------------------------------------------------------------------ vistas: notificaciones
VIEWS.notificaciones = async (view) => {
  const list = await api('notificaciones', '/notifications/me?limit=100');
  const icon = { info: 'ℹ️', exito: '✅', alerta: '⚠️' };
  view.innerHTML = `<div class="page-head"><div><h1>Notificaciones</h1><div class="sub">${list.filter((n) => !n.read).length} sin leer</div></div>
      <button class="btn" id="all">${ico('check')} Marcar todas como leídas</button></div>
    <div class="card">${list.length ? list.map((n) => `<div class="notif ${n.read ? '' : 'unread'}" data-id="${n.id}" data-order="${n.order_id || ''}">
      <span class="ic">${icon[n.type] || 'ℹ️'}</span><div><b class="type-${n.type}">${esc(n.title)}</b><div>${esc(n.message)}</div></div>
      <span class="small muted">${fdate(n.created_at)}</span></div>`).join('') : '<div class="empty">No tienes notificaciones.</div>'}</div>`;
  $('#all').onclick = () => act(() => api('notificaciones', '/notifications/me/read-all', { method: 'POST' })).then(() => { S.unread = 0; router(); });
  $$('.notif', view).forEach((el) => el.onclick = async () => {
    await api('notificaciones', `/notifications/${el.dataset.id}/read`, { method: 'POST' }).catch(() => {});
    if (el.dataset.order) go(`orden/${el.dataset.order}`); else router();
  });
};

// ------------------------------------------------------------------ vistas: admin — clientes
VIEWS.clientes = async (view) => {
  const [customers, vehicles] = await Promise.all([api('clientes', '/customers'), api('clientes', '/vehicles')]);
  view.innerHTML = `<div class="page-head"><div><h1>Clientes y vehículos</h1><div class="sub">${customers.length} clientes · ${vehicles.length} vehículos</div></div><div class="actions">
      <input id="q" placeholder="Buscar cliente o placa…" style="width:240px">
      <button class="btn" id="newc">${ico('user')} Cliente</button><button class="btn primary" id="newv">${ico('car')} Vehículo</button></div></div>
    <div class="card" id="list"></div>`;
  const draw = () => {
    const q = $('#q').value.toLowerCase();
    const match = (c) => !q || c.full_name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q) ||
      vehicles.some((v) => v.customer_id === c.id && v.plate.toLowerCase().includes(q));
    const rows = customers.filter(match);
    $('#list').innerHTML = rows.length ? `<div class="table-wrap"><table><thead><tr><th>Cliente</th><th>Contacto</th><th>Vehículos</th><th>Cuenta</th></tr></thead><tbody>
      ${rows.map((c) => `<tr><td><div class="cell-flex"><span class="avatar" style="width:36px;height:36px;font-size:12px">${esc(c.full_name.split(' ').map((w) => w[0]).slice(0, 2).join(''))}</span>
        <div><b>${esc(c.full_name)}</b><div class="small muted">${esc(c.document || '')}</div></div></div></td>
        <td>${esc(c.email)}<div class="small muted">${esc(c.phone || '')}</div></td>
        <td>${vehicles.filter((v) => v.customer_id === c.id).map((v) => `<div style="margin:2px 0"><span class="plate sm">${esc(v.plate)}</span>
          ${esc(v.brand)} ${esc(v.model)} ${v.year}</div>`).join('') || '<span class="muted">—</span>'}</td>
        <td>${c.user_id ? '<span class="badge green">En línea</span>' : '<span class="badge gray">Mostrador</span>'}</td></tr>`).join('')}
      </tbody></table></div>` : '<div class="empty">Sin resultados.</div>';
  };
  $('#q').oninput = draw;
  draw();
  $('#newc').onclick = () => modal('Nuevo cliente (mostrador)', `<div class="form">
      <label class="field">Nombre completo<input name="full_name" required minlength="3"></label>
      <div class="row"><label class="field">Correo<input name="email" type="email" required></label>
      <label class="field">Teléfono<input name="phone"></label></div>
      <div class="row"><label class="field">Documento<input name="document"></label>
      <label class="field">Dirección<input name="address"></label></div></div>`, {
    onSubmit: async (v) => { await api('clientes', '/customers', { body: v }); toast('Cliente creado', 'success'); router(); },
  });
  $('#newv').onclick = () => modal('Registrar vehículo', vehicleForm(`<label class="field">Cliente<select name="customer_id" required>
      ${customers.map((c) => `<option value="${c.id}">${esc(c.full_name)} · ${esc(c.email)}</option>`).join('')}</select></label>`), {
    onSubmit: async (v) => { await api('clientes', '/vehicles', { body: vehicleBody(v) }); toast('Vehículo registrado', 'success'); router(); },
  });
};

// ------------------------------------------------------------------ vistas: admin — mecánicos
VIEWS.mecanicos = async (view) => {
  const mechs = await api('mecanicos', '/mechanics');
  const maxLoad = Math.max(1, ...mechs.map((m) => m.active_assignments));
  view.innerHTML = `<div class="page-head"><div><h1>Equipo técnico</h1><div class="sub">${mechs.filter((m) => m.active).length} mecánicos activos</div></div>
      <button class="btn primary" id="add">${ico('plus')} Nuevo mecánico</button></div>
    <div class="products">${mechs.map((m) => `<div class="card product">
      <div class="cell-flex"><span class="avatar">${esc(m.full_name.split(' ').map((w) => w[0]).slice(0, 2).join(''))}</span>
        <div><h3>${esc(m.full_name)}</h3><div class="small muted">${esc(m.specialty)}</div></div></div>
      <div class="small">${esc(m.email)}<div class="muted">${esc(m.phone || '')}</div></div>
      <div><div class="meta"><span>Carga de trabajo</span><span class="mono">${m.active_assignments} activas</span></div>
        <div class="meter hot" style="margin-top:6px"><i style="width:${(m.active_assignments / maxLoad) * 100}%"></i></div></div>
      <div class="meta">${m.active ? '<span class="badge green">Activo</span>' : '<span class="badge gray">Inactivo</span>'}
        <button class="btn sm" data-edit="${m.id}">Editar</button></div></div>`).join('')}</div>`;
  $('#add').onclick = () => modal('Nuevo mecánico', `<div class="form">
      <label class="field">Nombre completo<input name="full_name" required minlength="3"></label>
      <div class="row"><label class="field">Correo (usuario de acceso)<input name="email" type="email" required></label>
      <label class="field">Contraseña inicial<input name="password" type="password" required minlength="6"></label></div>
      <div class="row"><label class="field">Teléfono<input name="phone"></label>
      <label class="field">Especialidad<input name="specialty" value="General"></label></div></div>`, {
    onSubmit: async (v) => { await api('mecanicos', '/mechanics', { body: v }); toast('Mecánico creado con acceso a la plataforma', 'success'); router(); },
  });
  $$('[data-edit]', view).forEach((b) => b.onclick = () => {
    const m = mechs.find((x) => String(x.id) === b.dataset.edit);
    modal(`Editar · ${m.full_name}`, `<div class="form">
      <label class="field">Especialidad<input name="specialty" value="${esc(m.specialty)}"></label>
      <label class="field">Teléfono<input name="phone" value="${esc(m.phone || '')}"></label>
      <label class="field">Estado<select name="active"><option value="true" ${m.active ? 'selected' : ''}>Activo</option>
        <option value="false" ${m.active ? '' : 'selected'}>Inactivo</option></select></label></div>`, {
      onSubmit: async (v) => {
        await api('mecanicos', `/mechanics/${m.id}`, { method: 'PUT', body: { ...v, active: v.active === 'true' } });
        toast('Mecánico actualizado', 'success'); router();
      },
    });
  });
};

// ------------------------------------------------------------------ vistas: admin — catálogo de servicios
VIEWS.catalogo = async (view) => {
  const list = await api('servicios', '/catalog?include_inactive=true');
  const form = (s = {}) => `<div class="form">
    <label class="field">Nombre<input name="name" required minlength="3" value="${esc(s.name || '')}"></label>
    <label class="field">Descripción<textarea name="description">${esc(s.description || '')}</textarea></label>
    <div class="row"><label class="field">Categoría<select name="category">${Object.entries(CATEGORY).map(([k, l]) =>
      `<option value="${k}" ${s.category === k ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <label class="field">Precio base<input name="base_price" type="number" min="0" step="1000" required value="${s.base_price ?? ''}"></label>
    <label class="field">Horas estimadas<input name="estimated_hours" type="number" min="0.5" step="0.5" value="${s.estimated_hours ?? 1}"></label></div>
    <label class="field">Estado<select name="active"><option value="true">Activo</option><option value="false" ${s.active === false ? 'selected' : ''}>Inactivo</option></select></label></div>`;
  const body = (v) => ({ ...v, base_price: Number(v.base_price), estimated_hours: Number(v.estimated_hours), active: v.active === 'true' });
  view.innerHTML = `<div class="page-head"><div><h1>Servicios del taller</h1><div class="sub">${list.length} servicios en el catálogo</div></div>
      <button class="btn primary" id="add">${ico('plus')} Nuevo servicio</button></div>
    <div class="products">${list.map((s) => `<div class="card product" style="${s.active ? '' : 'opacity:.55'}">
      <div class="pic">${art(serviceArt(s))}<span class="badge ${{ MANTENIMIENTO: 'blue', REPARACION: 'purple', DIAGNOSTICO: 'teal' }[s.category]}">${CATEGORY[s.category]}</span></div>
      <h3>${esc(s.name)}</h3><div class="small muted">${esc(s.description)}</div>
      <div class="meta"><span class="price">${money(s.base_price)}</span><span class="mono">${s.estimated_hours} h</span></div>
      <div class="meta">${s.active ? '<span class="badge green">Activo</span>' : '<span class="badge gray">Inactivo</span>'}
        <button class="btn sm" data-edit="${s.id}">Editar</button></div></div>`).join('')}</div>`;
  $('#add').onclick = () => modal('Nuevo servicio', form(), {
    onSubmit: async (v) => { await api('servicios', '/catalog', { body: body(v) }); toast('Servicio creado', 'success'); router(); },
  });
  $$('[data-edit]', view).forEach((b) => b.onclick = () => {
    const s = list.find((x) => String(x.id) === b.dataset.edit);
    modal('Editar servicio', form(s), {
      onSubmit: async (v) => { await api('servicios', `/catalog/${s.id}`, { method: 'PUT', body: body(v) }); toast('Servicio actualizado', 'success'); router(); },
    });
  });
};

// ------------------------------------------------------------------ vistas: inventario
VIEWS.inventario = async (view) => {
  const parts = await api('inventario', '/parts');
  const admin = role() === 'admin';
  const value = parts.reduce((s, p) => s + p.unit_price * p.stock, 0);
  view.innerHTML = `<div class="page-head"><div><h1>Inventario de repuestos</h1><div class="sub">${parts.length} referencias</div></div><div class="actions">
      <input id="q" placeholder="Buscar por nombre, SKU o marca…" style="width:260px">
      <div class="radio-group"><label><input type="checkbox" id="low"> Solo stock bajo</label></div>
      ${admin ? `<button class="btn primary" id="add">${ico('plus')} Nuevo repuesto</button>` : ''}</div></div>
    <div class="grid cols-3">
      ${kpi('Unidades en stock', parts.reduce((s, p) => s + p.stock, 0), 'box')}
      ${kpi('Valor del inventario', value, 'money', { tone: 'green', isMoney: true })}
      ${kpi('Stock bajo', parts.filter((p) => p.low_stock).length, 'alert', { tone: 'hot', sub: 'referencias por reponer' })}
    </div>
    <div class="products mt" id="list"></div>`;
  const draw = () => {
    const q = $('#q').value.toLowerCase();
    const rows = parts.filter((p) => (!$('#low').checked || p.low_stock) &&
      (!q || [p.name, p.sku, p.brand || ''].some((x) => x.toLowerCase().includes(q))));
    $('#list').innerHTML = rows.length ? rows.map((p) => `<div class="card product">
      <div class="pic">${art(partArt(p))}${p.low_stock ? '<span class="badge red">Stock bajo</span>' : `<span class="badge gray">${esc(p.category)}</span>`}</div>
      <span class="sku">${esc(p.sku)} · ${esc(p.brand || '')}</span>
      <h3>${esc(p.name)}</h3>
      <div class="meta"><span class="price">${money(p.unit_price)}</span><span class="mono">${p.stock} und.</span></div>
      <div><div class="meter ${p.low_stock ? 'low' : ''}"><i style="width:${Math.min(100, (p.stock / Math.max(1, p.min_stock * 3)) * 100)}%"></i></div>
        <div class="meta" style="margin-top:4px"><span>Mínimo ${p.min_stock}</span></div></div>
      ${admin ? `<div class="foot"><button class="btn sm cyan" data-stock="${p.id}">+ Stock</button> <button class="btn sm" data-mov="${p.id}">Movimientos</button></div>` : ''}
    </div>`).join('') : '<div class="card empty" style="grid-column:1/-1">Sin resultados.</div>';
    $$('[data-stock]', view).forEach((b) => b.onclick = () => {
      const p = parts.find((x) => String(x.id) === b.dataset.stock);
      modal(`Movimiento de stock · ${p.name}`, `<div class="form"><div class="cell-flex">${thumb(art(partArt(p)))}<p class="muted" style="margin:0">Stock actual: <b class="hot">${p.stock}</b></p></div>
        <div class="row"><label class="field">Tipo<select name="type"><option value="ENTRADA">Entrada (compra)</option><option value="AJUSTE">Ajuste (+/−)</option></select></label>
        <label class="field">Cantidad<input name="quantity" type="number" required step="1"></label></div>
        <label class="field">Nota<input name="note" placeholder="Factura proveedor, conteo físico…"></label></div>`, {
        onSubmit: async (v) => {
          await api('inventario', `/parts/${p.id}/stock`, { body: { ...v, quantity: Number(v.quantity) } });
          toast('Stock actualizado', 'success'); router();
        },
      });
    });
    $$('[data-mov]', view).forEach((b) => b.onclick = async () => {
      const p = parts.find((x) => String(x.id) === b.dataset.mov);
      const movs = await api('inventario', `/movements?part_id=${p.id}`);
      modal(`Movimientos · ${p.name}`, `<div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Tipo</th><th class="right">Cant.</th><th>Detalle</th></tr></thead><tbody>
        ${movs.map((m) => `<tr><td class="small">${fdate(m.created_at)}</td><td>${m.type}</td>
          <td class="right mono" style="color:var(--${m.quantity < 0 ? 'red' : 'green'})">${m.quantity > 0 ? '+' : ''}${m.quantity}</td>
          <td class="small">${esc(m.note || '')}${m.order_id ? ` · <a href="#/orden/${m.order_id}">orden</a>` : ''}</td></tr>`).join('')}
        </tbody></table></div>`, { wide: true });
    });
  };
  $('#q').oninput = draw;
  $('#low').onchange = draw;
  draw();
  $('#add')?.addEventListener('click', () => modal('Nuevo repuesto', `<div class="form">
      <div class="row"><label class="field">SKU<input name="sku" required></label><label class="field">Marca<input name="brand"></label></div>
      <label class="field">Nombre<input name="name" required></label>
      <div class="row"><label class="field">Categoría<input name="category" value="General" list="cats"></label>
      <label class="field">Precio unitario<input name="unit_price" type="number" min="0" step="100" required></label></div>
      <datalist id="cats">${[...new Set(parts.map((p) => p.category))].map((c) => `<option value="${esc(c)}">`).join('')}</datalist>
      <div class="row"><label class="field">Stock inicial<input name="stock" type="number" min="0" value="0"></label>
      <label class="field">Stock mínimo<input name="min_stock" type="number" min="0" value="0"></label></div></div>`, {
    onSubmit: async (v) => {
      await api('inventario', '/parts', { body: { ...v, unit_price: Number(v.unit_price), stock: Number(v.stock), min_stock: Number(v.min_stock) } });
      toast('Repuesto creado', 'success'); router();
    },
  }));
};

// ------------------------------------------------------------------ arranque
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', async () => {
  await boot();
  router();
});
