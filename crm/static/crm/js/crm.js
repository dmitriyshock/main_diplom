/* Shared CRM behaviours. Each initializer is guarded for pages that do not use it. */
(function () {
  'use strict';

  function applyPhoneMask(element) {
    function formatPhone(rawValue) {
      var digits = rawValue.replace(/\D/g, '');
      if (digits.charAt(0) === '8') digits = '7' + digits.slice(1);
      if (digits.length && digits.charAt(0) !== '7') digits = '7' + digits;
      digits = digits.slice(0, 11);

      var result = digits.length ? '+7' : '';
      if (digits.length >= 2) result += ' (' + digits.slice(1, Math.min(4, digits.length));
      if (digits.length >= 4) result += ') ' + digits.slice(4, Math.min(7, digits.length));
      if (digits.length >= 7) result += '-' + digits.slice(7, Math.min(9, digits.length));
      if (digits.length >= 9) result += '-' + digits.slice(9, 11);
      return result;
    }

    element.addEventListener('input', function () { this.value = formatPhone(this.value); });
    element.addEventListener('focus', function () { if (!this.value) this.value = '+7 ('; });
    element.addEventListener('blur', function () {
      if (this.value === '+7 (' || this.value === '+7') this.value = '';
    });
    element.addEventListener('keydown', function (event) {
      if (event.key === 'Backspace' && (this.value === '+7 (' || this.value === '+7')) {
        this.value = '';
        event.preventDefault();
      }
    });
  }

  function populateModels(brandId, modelSelect, emptyLabel) {
    modelSelect.innerHTML = '<option value="">' + emptyLabel + '</option>';
    if (!brandId) return;

    fetch('/api/models/' + encodeURIComponent(brandId) + '/')
      .then(function (response) { return response.ok ? response.json() : Promise.reject(response); })
      .then(function (data) {
        (data.models || []).forEach(function (model) {
          var option = document.createElement('option');
          option.value = model.id;
          option.textContent = model.name;
          modelSelect.appendChild(option);
        });
      })
      .catch(function () {
        /* Leave the safe empty choice when a temporary API failure occurs. */
      });
  }

  function initializeCascade(brandId, modelId, emptyLabel) {
    var brandSelect = document.getElementById(brandId);
    var modelSelect = document.getElementById(modelId);
    if (!brandSelect || !modelSelect) return;
    brandSelect.addEventListener('change', function () {
      populateModels(this.value, modelSelect, emptyLabel);
    });
  }

  function initializeAutoFill(selectId, fieldId) {
    var select = document.getElementById(selectId);
    var field = document.getElementById(fieldId);
    if (!select || !field) return;
    select.addEventListener('change', function () {
      var option = this.options[this.selectedIndex];
      if (option && option.dataset.price) field.value = option.dataset.price;
    });
  }

  function initializePage() {
    document.querySelectorAll('[data-phone]').forEach(applyPhoneMask);
    document.querySelectorAll('.toast').forEach(function (toast) {
      window.setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity .3s';
        window.setTimeout(function () { toast.remove(); }, 300);
      }, 4000);
    });
    document.querySelectorAll('[data-confirm]').forEach(function (element) {
      element.addEventListener('click', function (event) {
        if (!window.confirm(this.dataset.confirm)) event.preventDefault();
      });
    });

    initializeCascade('id_brand', 'id_phone_model', '— выберите модель —');
    initializeCascade('id_part_brand', 'id_part_model', '— все модели —');
    initializeAutoFill('service_select', 'service_price');
    initializeAutoFill('part_select', 'part_price');
  }

  document.body.addEventListener('htmx:configRequest', function (event) {
    if (window.crmCsrfToken) event.detail.headers['X-CSRFToken'] = window.crmCsrfToken;
  });
  document.addEventListener('DOMContentLoaded', initializePage);
}());
