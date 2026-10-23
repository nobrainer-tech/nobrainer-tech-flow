// PROVE IT block: the cast dances while the video plays, and switches the page look.
// Playing the video or clicking Flo turns the retro look on; MC P turns it off.
// Nothing is stored, so a reload is classic again.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const buttons = document.querySelectorAll('[data-look]');
  const sync = () => buttons.forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.look === 'retro') === root.classList.contains('retro'))));

  const setLook = (retro, origin) => {
    if (retro === root.classList.contains('retro')) return;
    const apply = () => { root.classList.toggle('retro', retro); sync(); };
    if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) return apply();
    const r = origin.getBoundingClientRect();
    root.style.setProperty('--vt-x', `${r.left + r.width / 2}px`);
    root.style.setProperty('--vt-y', `${r.top + r.height / 2}px`);
    document.startViewTransition(apply);
  };

  buttons.forEach((button) => button.addEventListener('click', () => setLook(button.dataset.look === 'retro', button)));

  const video = document.querySelector('[data-tv]');
  if (video) {
    const box = video.closest('.tv');
    ['play', 'pause', 'ended'].forEach((e) => video.addEventListener(e, () => box.classList.toggle('playing', e === 'play')));
    video.addEventListener('play', () => setLook(true, video));
  }
  sync();
});
