// Newsletter signup with the shared nobrainer.tech EmailOctopus form. The provider script (about 90 KB
// gzipped, plus reCAPTCHA) stays off the critical path: it loads after the window load event, once the
// section is within 600px of the viewport. The section sits under the video, so on most screens that
// is right after load. The display copy (email label, consent wording, button, confirmation, errors)
// comes from the section's data attributes, which the Polish page translates. EmailOctopus owns
// reCAPTCHA, submission and the result; the fallback link under the form stays visible throughout.
(() => {
  const section = document.querySelector('[data-newsletter]');
  const box = section && section.querySelector('[data-eo-form]');
  if (!box) return;
  const text = section.dataset;
  const id = box.dataset.eoForm;
  const action = `https://eocampaign1.com/form/${id}`;
  // The provider's English error wording, mapped to the section's (translated) texts; any other error,
  // such as a failed request or a bot check, gets the generic text that points to the fallback link.
  const errorKey = {
    'Your email address is required.': 'errorEmail',
    'Your email address looks incorrect, please try again.': 'errorEmail',
    'Please check the checkbox to indicate your consent.': 'errorConsent',
  };
  const ownErrors = () => [text.errorEmail, text.errorConsent, text.errorOther];
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
    if (error && error.textContent && !ownErrors().includes(error.textContent)) {
      error.textContent = text[errorKey[error.textContent] || 'errorOther'];
    }
    if (confirmed && success && success.textContent && success.textContent !== text.confirmation) {
      success.textContent = text.confirmation;
      if (error && error.textContent) error.textContent = '';
      // The provider hides the form under the focused button; keep keyboard focus on the result.
      success.tabIndex = -1;
      success.focus({ preventScroll: true });
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
