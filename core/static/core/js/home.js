(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const menu = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('navigation');
  const closeMenu = () => {
    navigation.classList.remove('open');
    menu.setAttribute('aria-expanded', 'false');
  };
  menu.addEventListener('click', () => {
    const open = navigation.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && navigation.classList.contains('open')) { closeMenu(); menu.focus(); }
  });
  document.addEventListener('click', event => {
    if (!navigation.contains(event.target) && !menu.contains(event.target)) closeMenu();
  });
  const form = document.getElementById('bookingForm');
  const success = document.getElementById('formSuccess');
  const error = document.getElementById('formError');
  const submit = form.querySelector('[type="submit"]');
  const submitLabel = submit.querySelector('span');
  let sending = false;
  document.querySelectorAll('[data-device]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      if (sending) return;
      form.hidden = false; success.hidden = true;
      const selectedDevice = link.getAttribute('data-device') || '';
      const deviceInput = document.getElementById('booking-device');
      const problemInput = document.getElementById('booking-message');
      deviceInput.defaultValue = selectedDevice;
      deviceInput.value = selectedDevice;
      problemInput.value = link.getAttribute('data-problem') || '';
      document.getElementById('booking').scrollIntoView();
    });
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (sending || !form.reportValidity()) return;
    sending = true; submit.disabled = true; submitLabel.textContent = 'Отправляем…';
    form.setAttribute('aria-busy', 'true'); error.hidden = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form),
        headers: {'X-Requested-With': 'XMLHttpRequest'},
        credentials: 'same-origin', signal: controller.signal,
      });
      if (!(response.headers.get('content-type') || '').includes('application/json')) {
        throw new Error(response.status === 403
          ? 'Сессия формы истекла. Обновите страницу и попробуйте ещё раз.'
          : 'Не удалось получить ответ сервера. Попробуйте позже или позвоните нам.');
      }
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Не удалось отправить заявку. Проверьте данные и повторите попытку.');
      form.hidden = true; success.hidden = false; success.focus(); form.reset();
    } catch (failure) {
      error.textContent = failure.name === 'AbortError' || failure instanceof TypeError
        ? 'Связь прервалась. Заявка могла сохраниться — уточните по телефону перед повторной отправкой.'
        : failure.message;
      error.hidden = false; error.focus();
    } finally {
      clearTimeout(timeout); sending = false; submit.disabled = false;
      submitLabel.textContent = 'Отправить заявку'; form.removeAttribute('aria-busy');
    }
  });
  document.getElementById('newRequest').addEventListener('click', () => {
    success.hidden = true; form.hidden = false; error.hidden = true; form.elements.name.focus();
  });
})();
