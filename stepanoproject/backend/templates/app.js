'use strict';



const state = {
  token: localStorage.getItem('groozer_token'),
  user:  JSON.parse(localStorage.getItem('groozer_user') || 'null'),
};

const API = '/api';

function _formatApiError(payload, fallback = 'Ошибка запроса') {
  if (!payload) return fallback;
  if (typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map(item => item?.msg || item?.message)
      .filter(Boolean)
      .join('; ') || fallback;
  }
  if (typeof payload.message === 'string') return payload.message;
  return fallback;
}

async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ошибка запроса' }));
    throw new Error(err.detail || 'Ошибка запроса');
  }
  return res.json();
}

function showToast(type, title, msg = '') {
  const toast = document.getElementById('toast');
  document.getElementById('toastTitle').textContent = title;
  document.getElementById('toastMsg').textContent   = msg;
  document.getElementById('toastIcon').textContent  = type === 'success' ? '✅' : '❌';
  toast.className = `toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 4000);
}

function openModal(tab = 'login', role = null) {
  document.getElementById('authModal').classList.add('open');
  switchTab(tab);
  if (role) {
    const el = document.getElementById(role === 'carrier' ? 'roleCarrier' : 'roleClient');
    if (el) selectRole(el);
  }
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('authModal').classList.remove('open');
  document.body.style.overflow = '';
}

function switchTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('tabLogin').classList.toggle('active', isLogin);
  document.getElementById('tabRegister').classList.toggle('active', !isLogin);
  document.getElementById('formLogin').style.display    = isLogin ? 'block' : 'none';
  document.getElementById('formRegister').style.display = isLogin ? 'none'  : 'block';
}

function selectRole(el) {
  document.querySelectorAll('.role-option').forEach(r => r.classList.remove('selected'));
  el.classList.add('selected');
}

async function submitLogin() {
  const username = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  if (!username || !password) { showToast('error', 'Заполните все поля'); return; }
  try {
    const body = new URLSearchParams({ username, password });
    const res  = await fetch(`${API}/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body,
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    const data = await res.json();
    _saveUser(data); closeModal(); updateNavForUser();
    showToast('success', 'Вы вошли в аккаунт', `Добро пожаловать, ${data.username}!`);
  } catch (e) { showToast('error', 'Ошибка входа', e.message); }
}

async function submitRegister() {
  const full_name = document.getElementById('regName').value.trim();
  const username  = document.getElementById('regUsername').value.trim();
  const email     = document.getElementById('regEmail').value.trim();
  const password  = document.getElementById('regPassword').value;
  const password2 = document.getElementById('regPassword2').value;
  const role      = document.querySelector('input[name="role"]:checked')?.value || 'client';
  if (!full_name || !username || !email || !password) { showToast('error', 'Заполните все поля'); return; }
  if (password !== password2) { showToast('error', 'Пароли не совпадают'); return; }
  try {
    const data = await apiFetch('/auth/register', {
      method: 'POST', body: JSON.stringify({ full_name, username, email, password, role }),
    });
    _saveUser(data); closeModal(); updateNavForUser();
    showToast('success', 'Регистрация прошла успешно!', `Добро пожаловать, ${data.username}!`);
  } catch (e) { showToast('error', 'Ошибка регистрации', e.message); }
}


apiFetch = async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(_formatApiError(err));
  }
  return res.json();
};

submitLogin = async function submitLogin() {
  const username = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  if (!username || !password) { showToast('error', 'Заполните все поля'); return; }

  try {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(_formatApiError(err, 'Ошибка входа'));
    }
    const data = await res.json();
    _saveUser(data);
    closeModal();
    updateNavForUser();
    showToast('success', 'Вы вошли в аккаунт', `Добро пожаловать, ${data.username}!`);
  } catch (e) {
    showToast('error', 'Ошибка входа', e.message);
  }
};

submitRegister = async function submitRegister() {
  const full_name = document.getElementById('regName').value.trim();
  const username  = document.getElementById('regUsername').value.trim();
  const email     = document.getElementById('regEmail').value.trim();
  const password  = document.getElementById('regPassword').value;
  const password2 = document.getElementById('regPassword2').value;
  const role      = document.querySelector('input[name="role"]:checked')?.value || 'client';

  if (!full_name || !username || !email || !password) {
    showToast('error', 'Заполните все поля');
    return;
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showToast('error', 'Некорректный email');
    return;
  }
  if (!/^[a-zA-Z0-9_]{3,30}$/.test(username)) {
    showToast('error', 'Некорректный логин', '3-30 символов: только буквы, цифры и _');
    return;
  }
  if (password !== password2) {
    showToast('error', 'Пароли не совпадают');
    return;
  }
  if (password.length < 8) {
    showToast('error', 'Слабый пароль', 'Минимум 8 символов');
    return;
  }
  if (!/[A-Z]/.test(password)) {
    showToast('error', 'Слабый пароль', 'Добавьте хотя бы одну заглавную букву');
    return;
  }
  if (!/\d/.test(password)) {
    showToast('error', 'Слабый пароль', 'Добавьте хотя бы одну цифру');
    return;
  }

  try {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, username, email, password, role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(_formatApiError(err, 'Ошибка регистрации'));
    }
    const data = await res.json();
    _saveUser(data);
    closeModal();
    updateNavForUser();
    showToast('success', 'Регистрация прошла успешно!', `Добро пожаловать, ${data.username}!`);
  } catch (e) {
    showToast('error', 'Ошибка регистрации', e.message);
  }
};

function logout() {
  state.token = null; state.user = null;
  localStorage.removeItem('groozer_token'); localStorage.removeItem('groozer_user');
  updateNavForUser(); showToast('success', 'Вы вышли из аккаунта');
}

function _saveUser(data) {
  state.token = data.access_token;
  state.user  = { id: data.user_id, username: data.username, role: data.role };
  localStorage.setItem('groozer_token', data.access_token);
  localStorage.setItem('groozer_user',  JSON.stringify(state.user));
}

function updateNavForUser() {
  [
    [document.getElementById('loginBtn'),       document.getElementById('registerBtn')],
    [document.getElementById('loginBtnMobile'), document.getElementById('registerBtnMobile')],
  ].forEach(([loginBtn, registerBtn]) => {
    if (!loginBtn || !registerBtn) return;
    if (state.user) {
      loginBtn.textContent    = state.user.username;
      loginBtn.onclick        = null;
      registerBtn.textContent = 'Выйти';
      registerBtn.className   = 'btn btn-ghost';
      registerBtn.onclick     = () => { logout(); closeMobileMenu(); };
    } else {
      loginBtn.textContent    = 'Войти';
      loginBtn.onclick        = () => { openModal('login'); closeMobileMenu(); };
      registerBtn.textContent = 'Начать →';
      registerBtn.className   = 'btn btn-primary';
      registerBtn.onclick     = () => { openModal('register'); closeMobileMenu(); };
    }
  });
}

function closeMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  const btn  = document.getElementById('hamburger');
  if (!menu || !btn) return;
  menu.classList.remove('open'); menu.style.display = '';
  btn.classList.remove('open'); btn.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
}

function toggleMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  const btn  = document.getElementById('hamburger');
  if (menu.classList.contains('open')) { closeMobileMenu(); return; }
  menu.style.display = 'flex';
  requestAnimationFrame(() => {
    menu.classList.add('open'); btn.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  });
}

function initReveal() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal:not(.visible)').forEach(el => observer.observe(el));
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}



const ROUTES = {
  '/':         '/partial/home',
  '/catalog':  '/partial/catalog',
  '/how':      '/partial/how',
  '/features': '/partial/features',
  '/carriers': '/partial/carriers',
};

const PAGE_TITLES = {
  '/':         'Groozer — Грузоперевозки нового поколения',
  '/catalog':  'Биржа заявок — Groozer',
  '/how':      'Как это работает — Groozer',
  '/features': 'Преимущества — Groozer',
  '/carriers': 'Перевозчикам — Groozer',
};

const _pageCache = {};

function _animateOut(app) {
  return new Promise(resolve => {
    app.style.transition = 'opacity 0.15s ease, transform 0.15s ease';
    app.style.opacity    = '0';
    app.style.transform  = 'translateY(8px)';
    setTimeout(resolve, 150);
  });
}

function _animateIn(app) {
  app.style.transition = 'none';
  app.style.opacity    = '0';
  app.style.transform  = 'translateY(8px)';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    app.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
    app.style.opacity    = '1';
    app.style.transform  = 'translateY(0)';
  }));
}

function _runPartialScripts(container) {
  container.querySelectorAll('script').forEach(old => {
    const s = document.createElement('script');

    if (old.src) {
      s.src = old.src;
      Array.from(old.attributes).forEach(attr => {
        if (attr.name !== 'src') s.setAttribute(attr.name, attr.value);
      });
    } else {
      s.textContent = `(function(){\n${old.textContent}\n})();`;
    }

    document.head.appendChild(s);
    if (!old.src) document.head.removeChild(s);
  });
}

async function navigateTo(path, pushState = true) {
  const route   = path.split('?')[0];
  const partial = ROUTES[route] || ROUTES['/'];
  const app     = document.getElementById('app');

  closeMobileMenu();

  await _animateOut(app);

  try {
    const query    = path.includes('?') ? path.split('?')[1] : '';
    const cacheKey = partial + (query ? '?' + query : '');
    let html;

    if (!query && _pageCache[partial]) {
      html = _pageCache[partial];
    } else {
      const res = await fetch(cacheKey);
      if (!res.ok) throw new Error('404');
      html = await res.text();
      if (!query) _pageCache[partial] = html;
    }

    if (pushState) history.pushState({ path }, '', path);


    app.innerHTML = html;
    document.title = PAGE_TITLES[route] || PAGE_TITLES['/'];


    _runPartialScripts(app);

    markActiveNav(route);
    window.scrollTo({ top: 0, behavior: 'instant' });
    setTimeout(initReveal, 50);
    _animateIn(app);

  } catch (err) {
    window.location.href = path;
  }
}

function markActiveNav(route) {
  const r = route || location.pathname;
  document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === r);
  });
}

function _interceptLinks() {
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href.startsWith('http') || href.startsWith('//') ||
        href.startsWith('#') || href.startsWith('mailto') ||
        href.startsWith('javascript') || a.target || a.download) return;

    const clean = href.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
    e.preventDefault();
    navigateTo(clean);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('hamburger')?.addEventListener('click', toggleMobileMenu);

  document.addEventListener('click', e => {
    const menu = document.getElementById('mobileMenu');
    const btn  = document.getElementById('hamburger');
    if (menu?.classList.contains('open')
        && !menu.contains(e.target) && !btn?.contains(e.target)) closeMobileMenu();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeMobileMenu();
  });

  document.getElementById('authModal')?.addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });

  document.querySelectorAll('.role-option').forEach(opt => {
    opt.addEventListener('click', () => selectRole(opt));
  });

  updateNavForUser();

  _interceptLinks();

  window.addEventListener('popstate', () => {
    navigateTo(location.pathname + location.search, false);
  });

  navigateTo(location.pathname + location.search, false);
});

ROUTES['/profile'] = '/partial/profile';
ROUTES['/admin'] = '/partial/admin';

PAGE_TITLES['/profile'] = 'Профиль — Groozer';
PAGE_TITLES['/admin'] = 'Админ-панель — Groozer';

const _baseNavigateTo = navigateTo;
const _baseLogout = logout;

function _accountRoute() {
  if (!state.user) return '/';
  return state.user.role === 'admin' ? '/admin' : '/profile';
}

function _redirectToRoute(path, pushState) {
  if (!pushState) history.replaceState({ path }, '', path);
  return _baseNavigateTo(path, pushState);
}

updateNavForUser = function updateNavForUser() {
  [
    [document.getElementById('loginBtn'), document.getElementById('registerBtn')],
    [document.getElementById('loginBtnMobile'), document.getElementById('registerBtnMobile')],
  ].forEach(([loginBtn, registerBtn]) => {
    if (!loginBtn || !registerBtn) return;

    if (state.user) {
      loginBtn.textContent = state.user.username;
      loginBtn.onclick = () => { navigateTo(_accountRoute()); closeMobileMenu(); };
      registerBtn.textContent = 'Выйти';
      registerBtn.className = 'btn btn-ghost';
      registerBtn.onclick = () => { logout(); closeMobileMenu(); };
    } else {
      loginBtn.textContent = 'Войти';
      loginBtn.className = 'btn btn-ghost';
      loginBtn.onclick = () => { openModal('login'); closeMobileMenu(); };
      registerBtn.textContent = 'Начать →';
      registerBtn.className = 'btn btn-primary';
      registerBtn.onclick = () => { openModal('register'); closeMobileMenu(); };
    }
  });

  if (typeof window.updateCatalogFab === 'function') {
    window.updateCatalogFab();
  }
};

logout = function logout() {
  _baseLogout();
  if (location.pathname === '/profile' || location.pathname === '/admin') {
    navigateTo('/', true);
  }
};

navigateTo = async function navigateTo(path, pushState = true) {
  const route = path.split('?')[0];

  if (route === '/profile' && !state.user) {
    showToast('error', 'Требуется вход', 'Авторизуйтесь, чтобы открыть профиль');
    openModal('login');
    if (location.pathname !== '/') {
      return _redirectToRoute('/', pushState);
    }
    return;
  }

  if (route === '/admin' && (!state.user || state.user.role !== 'admin')) {
    showToast('error', 'Доступ ограничен', 'Админ-панель доступна только администратору');
    if (!state.user) openModal('login');
    const fallback = state.user ? '/profile' : '/';
    if (location.pathname !== fallback) {
      return _redirectToRoute(fallback, pushState);
    }
    return;
  }

  return _baseNavigateTo(path, pushState);
};
