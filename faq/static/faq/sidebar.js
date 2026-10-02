/* Tall sidebars stay in document flow, avoiding nested scrolling and hidden links. */
(() => {
  const panels = [...document.querySelectorAll('.faq-sidebar')];
  if (!panels.length) return;
  const header = document.querySelector('.header');
  let pending = false;
  function update() {
    pending = false;
    const top = Math.ceil(header?.getBoundingClientRect().height || 64) + 24;
    for (const panel of panels) {
      panel.style.setProperty('--faq-sidebar-top', `${top}px`);
      panel.classList.toggle('faq-sidebar--sticky', panel.getBoundingClientRect().height <= window.innerHeight - top - 24);
    }
  }
  function schedule() {
    if (!pending) {
      pending = true;
      requestAnimationFrame(update);
    }
  }
  const observer = new ResizeObserver(schedule);
  panels.forEach(panel => observer.observe(panel));
  if (header) observer.observe(header);
  window.addEventListener('resize', schedule, { passive: true });
  update();
})();
