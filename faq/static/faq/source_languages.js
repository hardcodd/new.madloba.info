/* Source URLs/dates stay shared; names follow the native locale-picker buttons. */
(() => {
  function start() {
    const form = document.querySelector('form [id*="sources"]')?.closest('form');
    if (!form) return;
    let pending = false;
    function sync() {
      pending = false;
      const toggles = [...document.querySelectorAll('.locale-picker .locale-toggle')];
      if (!toggles.length) return;
      const selected = new Set(toggles.filter(button => button.classList.contains('showing-locale')).map(button => button.textContent.trim().replaceAll('-', '_')));
      form.querySelectorAll('[data-faq-source-language]').forEach(field => {
        field.hidden = !selected.has(field.dataset.faqSourceLanguage);
      });
    }
    function schedule() {
      if (!pending) { pending = true; requestAnimationFrame(sync); }
    }
    document.addEventListener('click', event => {
      if (event.target.closest('.locale-toggle')) schedule();
    });
    document.addEventListener('wagtail-modeltranslation:buildSets:done', schedule);
    new MutationObserver(schedule).observe(form, { childList: true, subtree: true });
    schedule();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
