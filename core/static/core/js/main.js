(() => {
  'use strict';

  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  const themeLabel = toggle?.querySelector('[data-theme-label]');
  const themeColor = document.getElementById('themeColor');
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  const readSavedTheme = () => {
    try { return localStorage.getItem('kayros-theme'); } catch (error) { return null; }
  };
  const saveTheme = (theme) => {
    try { localStorage.setItem('kayros-theme', theme); } catch (error) { /* Theme still works for this page. */ }
  };

  const applyTheme = (theme) => {
    const isDark = theme === 'dark';
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(isDark));
      toggle.setAttribute('aria-label', isDark ? 'Включить светлую тему' : 'Включить тёмную тему');
    }
    if (themeLabel) themeLabel.textContent = isDark ? 'Светлая' : 'Тёмная';
    if (themeColor) themeColor.setAttribute('content', isDark ? '#111411' : '#f6f5f0');
  };

  applyTheme(root.dataset.theme || (systemTheme.matches ? 'dark' : 'light'));

  toggle?.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    saveTheme(nextTheme);
    applyTheme(nextTheme);
  });

  systemTheme.addEventListener?.('change', (event) => {
    if (!readSavedTheme()) applyTheme(event.matches ? 'dark' : 'light');
  });

  const menu = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('navigation');
  const closeMenu = () => {
    if (!menu || !navigation) return;
    navigation.classList.remove('open');
    menu.setAttribute('aria-expanded', 'false');
    menu.setAttribute('aria-label', 'Открыть меню');
    document.body.classList.remove('menu-open');
  };

  if (menu && navigation) {
    menu.addEventListener('click', () => {
      const isOpen = navigation.classList.toggle('open');
      menu.setAttribute('aria-expanded', String(isOpen));
      menu.setAttribute('aria-label', isOpen ? 'Закрыть меню' : 'Открыть меню');
      document.body.classList.toggle('menu-open', isOpen);
    });
    navigation.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
    document.addEventListener('click', (event) => {
      if (!navigation.contains(event.target) && !menu.contains(event.target)) closeMenu();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && navigation.classList.contains('open')) {
        closeMenu();
        menu.focus();
      }
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth > 900) closeMenu();
    });
  }

  const applyPhoneMask = (input) => {
    const format = (raw) => {
      let digits = raw.replace(/\D/g, '');
      if (digits.charAt(0) === '8') digits = `7${digits.slice(1)}`;
      if (digits.length && digits.charAt(0) !== '7') digits = `7${digits}`;
      digits = digits.slice(0, 11);
      if (!digits.length) return '';
      let result = '+7';
      if (digits.length >= 2) result += ` (${digits.slice(1, Math.min(4, digits.length))}`;
      if (digits.length >= 4) result += `) ${digits.slice(4, Math.min(7, digits.length))}`;
      if (digits.length >= 7) result += `-${digits.slice(7, Math.min(9, digits.length))}`;
      if (digits.length >= 9) result += `-${digits.slice(9, 11)}`;
      return result;
    };
    input.addEventListener('input', () => { input.value = format(input.value); });
    input.addEventListener('focus', () => { if (!input.value) input.value = '+7 ('; });
    input.addEventListener('blur', () => { if (input.value === '+7 (' || input.value === '+7') input.value = ''; });
  };
  document.querySelectorAll('[data-phone]').forEach(applyPhoneMask);

  document.querySelectorAll('.message').forEach((message) => {
    window.setTimeout(() => message.classList.add('message-leaving'), 4200);
    window.setTimeout(() => message.remove(), 4700);
  });

  const cookieNotice = document.querySelector('[data-cookie-notice]');
  const cookieAccept = document.querySelector('[data-cookie-accept]');
  const cookieNoticeKey = 'kayros-cookie-notice';
  let cookieNoticeAccepted = false;
  try { cookieNoticeAccepted = localStorage.getItem(cookieNoticeKey) === 'accepted-v1'; } catch (error) { cookieNoticeAccepted = false; }
  if (cookieNotice && !cookieNoticeAccepted) cookieNotice.hidden = false;
  cookieAccept?.addEventListener('click', () => {
    try { localStorage.setItem(cookieNoticeKey, 'accepted-v1'); } catch (error) { /* Dismiss for this page when storage is unavailable. */ }
    if (cookieNotice) cookieNotice.hidden = true;
  });
})();
