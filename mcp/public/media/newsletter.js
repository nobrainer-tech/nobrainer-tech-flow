// Newsletter signup with the shared nobrainer.tech EmailOctopus form. The provider script is large, so
// it loads only after the page has loaded and the section nears the viewport. Its display copy (email
// label, consent wording, button, confirmation) comes from the section's data attributes, which the
// Polish page translates. EmailOctopus owns reCAPTCHA, submission and the result; the fallback link
// under the form stays visible in case the provider never loads.
(() => {
  const section = document.querySelector('[data-newsletter]');
  const box = section && section.querySelector('[data-eo-form]');
  if (!box) return;
  const text = section.dataset;
  const id = box.dataset.eoForm;
  const action = `https://eocampaign1.com/form/${id}`;
  let confirmed = false;

  // Runs on every change inside the box; each step writes only when the value differs, so its own
  // writes settle after one extra pass.
  const adapt = () => {
    const form = box.querySelector('form.emailoctopus-form');
    if (!form || form.action !== action) return;
    const consent = form.querySelector('.emailoctopus-form-row-consent input[type="checkbox"]');
    const label = form.querySelector('.emailoctopus-form-row-consent label');
    const submit = form.querySelector('[type="submit"]');
    if (!consent || !label || !submit) return;
    consent.required = true;
    if (label.textContent !== text.consent) label.textContent = text.consent;
    if (submit.value !== text.submit) submit.value = text.submit;
    const row = consent.closest('.emailoctopus-form-row-consent');
    if (row.nextElementSibling !== submit) submit.before(row);
    const email = form.querySelector('input[type="email"]');
    if (email && !form.querySelector(`label[for="${email.id}"]`)) {
      const name = document.createElement('label');
      name.htmlFor = email.id;
      name.textContent = text.emailLabel;
      email.before(name);
      email.removeAttribute('aria-label');
      email.removeAttribute('placeholder');
      email.autocomplete = 'email';
    }
    const success = box.querySelector('.emailoctopus-success-message');
    const error = box.querySelector('.emailoctopus-error-message');
    if (success && !success.hasAttribute('role')) success.setAttribute('role', 'status');
    if (error && !error.hasAttribute('role')) error.setAttribute('role', 'alert');
    if (confirmed && success && success.textContent && success.textContent !== text.confirmation) {
      success.textContent = text.confirmation;
      if (error && error.textContent) error.textContent = '';
    }
    section.dataset.formReady = 'true';
  };

  const load = () => {
    const script = document.createElement('script');
    script.async = true;
    script.src = box.dataset.eoSrc;
    // The provider finds its insertion point by this attribute and renders the form after the script.
    script.dataset.form = id;
    // Blocked or offline: drop the space reserved for the form so the fallback link sits under the copy.
    script.addEventListener('error', () => { box.hidden = true; });
    box.append(script);
  };

  document.addEventListener('emailoctopus:form.success', (event) => {
    if (!event.detail || event.detail.form_id !== id) return;
    confirmed = true;
    queueMicrotask(adapt);
  });
  new MutationObserver(adapt).observe(box, { childList: true, characterData: true, subtree: true });

  const watch = () => {
    if (!('IntersectionObserver' in window)) return load();
    const near = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      near.disconnect();
      load();
    }, { rootMargin: '600px 0px' });
    near.observe(section);
  };
  if (document.readyState === 'complete') watch();
  else window.addEventListener('load', watch, { once: true });
})();
