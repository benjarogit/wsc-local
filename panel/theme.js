// Apply the saved preference before rendering the stylesheet to avoid a bright flash.
(() => {
  const key = 'wsc-color-mode';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (['system', 'light', 'dark'].includes(saved)) preference = saved; } catch (_) { /* Storage may be disabled. */ }
  function apply() {
    document.querySelectorAll('[data-color-mode]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.colorMode===preference)));
    document.documentElement.dataset.theme = preference === 'system' ? (system.matches ? 'dark' : 'light') : preference;
  }
  apply();
  system.addEventListener('change', () => { if (preference === 'system') apply(); });
  window.addEventListener('storage', (event) => {
    if (event.key !== key) return;
    preference = ['light', 'dark'].includes(event.newValue) ? event.newValue : 'system';
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-color-mode]').forEach(button=>button.addEventListener('click',()=>{
      preference=button.dataset.colorMode;
      try {localStorage.setItem(key,preference);} catch (_) { /* The current tab still works without storage. */ }
      apply();
    }));
    apply();
  }, { once: true });
})();
