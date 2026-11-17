/* Hero slider: moves every 5 seconds; pauses on hover, keyboard focus or the pause button; no auto-move for reduced-motion users */
(function () {
  var root = document.querySelector('.hs'); if (!root) return;
  var track = root.querySelector('.hs-track'), slides = root.querySelectorAll('.hs-slide'),
      dots = root.querySelectorAll('.hs-dot'), pauseBtn = root.querySelector('.hs-pause'),
      current = 0, timer = null, paused = false, hovering = false, focused = false,
      reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { paused = true; }
  function show(i) {
    current = (i + slides.length) % slides.length;
    track.style.transform = 'translateX(' + (-100 * current) + '%)';
    slides.forEach(function (s, n) { var on = n === current; s.toggleAttribute('inert', !on); s.setAttribute('aria-hidden', on ? 'false' : 'true'); });
    dots.forEach(function (d, n) { d.setAttribute('aria-current', n === current ? 'true' : 'false'); });
  }
  function setPauseIcon() {
    pauseBtn.innerHTML = paused ? '<i class="bi bi-play-fill" aria-hidden="true"></i>' : '<i class="bi bi-pause-fill" aria-hidden="true"></i>';
    pauseBtn.setAttribute('aria-label', paused ? 'Play slides' : 'Pause slides');
  }
  function restart() { clearInterval(timer); if (!paused && !hovering && !focused) timer = setInterval(function () { show(current + 1); }, 5000); }
  root.querySelector('.hs-prev').addEventListener('click', function () { show(current - 1); restart(); });
  root.querySelector('.hs-next').addEventListener('click', function () { show(current + 1); restart(); });
  dots.forEach(function (d, n) { d.addEventListener('click', function () { show(n); restart(); }); });
  pauseBtn.addEventListener('click', function () { paused = !paused; setPauseIcon(); restart(); });
  root.addEventListener('mouseenter', function () { hovering = true; restart(); });
  root.addEventListener('mouseleave', function () { hovering = false; restart(); });
  root.addEventListener('focusin', function () { focused = true; restart(); });
  root.addEventListener('focusout', function () { focused = false; restart(); });
  var x0 = null;
  root.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  root.addEventListener('touchend', function (e) { if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) { show(current + (dx < 0 ? 1 : -1)); restart(); } x0 = null; });
  document.addEventListener('visibilitychange', function () { if (document.hidden) clearInterval(timer); else restart(); });
  show(0); setPauseIcon(); restart();
})();
