// PROVE IT block. The page starts retro; MC P switches to classic with a CRT effect, Flo or playing
// the video switches back with a pixel circle. Clicking Flo also counts a quick 3-2-1 over the video and plays
// it; Flo points at the video while it is not playing, shows OK when it starts, then dances.
// Nothing is stored, so a reload is retro again.
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
    const count = box.querySelector('.countdown');
    let timers = [];
    const clear = () => { timers.forEach(clearTimeout); timers = []; };
    const stopCount = () => { clear(); if (count) count.classList.remove('on'); };
    // Follow the play state, not buffering: 'waiting' fires on every network stall of a streamed
    // file and made the cast stop and start at random. Stop only on pause, end, reset or error.
    video.addEventListener('play', () => {
      stopCount();
      box.classList.add('playing');
      timers.push(setTimeout(() => box.classList.add('dancing'), 1600));
      setLook(true, video);
    });
    const stop = () => { stopCount(); box.classList.remove('playing', 'dancing'); };
    ['pause', 'ended', 'emptied'].forEach((e) => video.addEventListener(e, stop));
    video.addEventListener('error', stop, true);
    const flo = box.querySelector('.flo');
    if (flo && count) flo.addEventListener('click', () => {
      if (!video.paused) return;
      stopCount();
      count.classList.add('on');
      const STEP = 450;
      [3, 2, 1].forEach((n, i) => timers.push(setTimeout(() => { count.innerHTML = `<span>${n}</span>`; }, i * STEP)));
      // The click still counts as a user gesture this soon after in current browsers;
      // if sound is refused, start muted rather than not at all.
      timers.push(setTimeout(() => { stopCount(); video.play().catch(() => { video.muted = true; return video.play(); }).catch(() => {}); }, 3 * STEP));
    });
    // Fetch the dance sheets early so the cast does not blank out on the first play.
    ['/media/flo-dance.png', '/media/mcp-dance.png'].forEach((src) => { new Image().src = src; });
  }
  sync();
});
