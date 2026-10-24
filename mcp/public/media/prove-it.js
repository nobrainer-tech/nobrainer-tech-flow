// PROVE IT block: Flo points at the video until it plays, then shows OK while MC P dances;
// the cast also switches the page look.
// The page starts retro; MC P switches to classic with a CRT effect, Flo or playing the video
// switches back with a pixel circle. Nothing is stored, so a reload is retro again.
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
    root.dataset.vt = retro ? 'pixel' : 'crt';
    document.startViewTransition(apply).finished.finally(() => { delete root.dataset.vt; });
  };

  buttons.forEach((button) => button.addEventListener('click', () => setLook(button.dataset.look === 'retro', button)));

  const video = document.querySelector('[data-tv]');
  if (video) {
    const box = video.closest('.tv');
    // Follow the play state, not buffering: 'waiting' fires on every network stall of a streamed
    // file and made the cast stop and start at random. Stop only on pause, end, reset or error.
    video.addEventListener('play', () => box.classList.add('playing'));
    ['pause', 'ended', 'emptied'].forEach((e) => video.addEventListener(e, () => box.classList.remove('playing')));
    video.addEventListener('error', () => box.classList.remove('playing'), true);
    video.addEventListener('play', () => setLook(true, video));
    // Fetch MC P's dance sheet early so he does not blank out on the first play.
    new Image().src = '/media/mcp-dance.png';
  }
  sync();
});
