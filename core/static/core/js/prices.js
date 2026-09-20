(() => {
  'use strict';

  const catalog = document.querySelector('.price-catalog');
  if (!catalog) return;

  const brands = Array.from(catalog.querySelectorAll('.price-brand'));
  const models = Array.from(catalog.querySelectorAll('.price-model'));
  const links = Array.from(catalog.querySelectorAll('[data-price-brand]'));
  const expand = catalog.querySelector('[data-price-expand]');

  const markBrand = (id) => {
    links.forEach((link) => {
      if (link.dataset.priceBrand === id) {
        link.setAttribute('aria-current', 'location');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  };

  const updateExpand = () => {
    if (!expand) return;
    const allOpen = brands.every((brand) => brand.open) && models.every((model) => model.open);
    expand.setAttribute('aria-expanded', String(allOpen));
    expand.replaceChildren(
      document.createTextNode(allOpen ? 'Свернуть все модели ' : 'Развернуть все модели '),
    );
    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = allOpen ? '−' : '+';
    expand.append(icon);
  };

  if (expand && models.length) {
    expand.hidden = false;
    expand.addEventListener('click', () => {
      const open = !(brands.every((brand) => brand.open) && models.every((model) => model.open));
      models.forEach((model) => { model.open = open; });
      // Keep brand headings available when collapsing the model list.
      if (open) brands.forEach((brand) => { brand.open = true; });
      updateExpand();
    });
    [...brands, ...models].forEach((details) => details.addEventListener('toggle', updateExpand));
    updateExpand();
  }

  const revealHash = () => {
    const brand = brands.find((item) => `#${item.id}` === window.location.hash);
    if (brand) {
      brand.open = true;
      markBrand(brand.id);
    }
  };

  links.forEach((link) => {
    link.addEventListener('click', () => {
      const brand = brands.find((item) => item.id === link.dataset.priceBrand);
      if (brand) {
        brand.open = true;
        markBrand(brand.id);
      }
    });
  });
  window.addEventListener('hashchange', revealHash);
  revealHash();

  // Progressive enhancement: native anchors and details work without this API.
  if ('IntersectionObserver' in window) {
    const visibleBrands = new Set();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) visibleBrands.add(entry.target);
        else visibleBrands.delete(entry.target);
      });
      const active = brands.find((brand) => visibleBrands.has(brand));
      if (active) markBrand(active.id);
    }, { rootMargin: '-110px 0px -40% 0px', threshold: 0 });
    brands.forEach((brand) => observer.observe(brand));
  }
})();
