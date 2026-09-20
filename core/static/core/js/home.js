(() => {
  'use strict';

  const form = document.getElementById('bookingForm');
  const success = document.getElementById('formSuccess');
  const error = document.getElementById('formError');
  const newRequest = document.getElementById('newRequest');
  if (!form || !success || !error) return;

  const submit = form.querySelector('[type="submit"]');
  const submitLabel = submit?.querySelector('span');
  let sending = false;

  document.querySelectorAll('[data-device]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      if (sending) return;
      form.hidden = false;
      success.hidden = true;
      const deviceInput = document.getElementById('booking-device');
      const problemInput = document.getElementById('booking-message');
      if (deviceInput) deviceInput.value = link.getAttribute('data-device') || '';
      if (problemInput) problemInput.value = link.getAttribute('data-problem') || '';
      document.getElementById('booking')?.scrollIntoView({behavior: 'smooth'});
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (sending || !form.reportValidity() || !submit) return;
    sending = true;
    submit.disabled = true;
    if (submitLabel) submitLabel.textContent = 'Отправляем…';
    form.setAttribute('aria-busy', 'true');
    error.hidden = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {'X-Requested-With': 'XMLHttpRequest'},
        credentials: 'same-origin',
        signal: controller.signal,
      });
      if (!(response.headers.get('content-type') || '').includes('application/json')) {
        throw new Error(response.status === 403
          ? 'Сессия формы истекла. Обновите страницу и попробуйте ещё раз.'
          : 'Не удалось получить ответ сервера. Попробуйте позже или позвоните нам.');
      }
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || 'Не удалось отправить заявку. Проверьте данные и повторите попытку.');
      }
      form.hidden = true;
      success.hidden = false;
      success.focus();
      form.reset();
    } catch (failure) {
      error.textContent = failure.name === 'AbortError' || failure instanceof TypeError
        ? 'Связь прервалась. Заявка могла сохраниться — уточните по телефону перед повторной отправкой.'
        : failure.message;
      error.hidden = false;
      error.focus();
    } finally {
      window.clearTimeout(timeout);
      sending = false;
      submit.disabled = false;
      if (submitLabel) submitLabel.textContent = 'Отправить заявку';
      form.removeAttribute('aria-busy');
    }
  });

  newRequest?.addEventListener('click', () => {
    success.hidden = true;
    form.hidden = false;
    error.hidden = true;
    form.elements.name?.focus();
  });
})();
