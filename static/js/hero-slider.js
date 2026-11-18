/* Hero slider: moves every 5 seconds and keeps moving after clicks, taps and mouse hover (owner's request,
   18 Nov 2026: no pause button). It only waits while a keyboard user has tabbed into it, so a focused link
   can't slide away, and it doesn't move by itself for visitors who turned on "reduce motion". */
(function () {
  var root = document.querySelector('.hs'); if (!root) return;
  var track = root.querySelector('.hs-track'), slides = root.querySelectorAll('.hs-slide'),
      dots = root.querySelectorAll('.hs-dot'), current = 0, timer = null, keyboardInside = false,
      reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function show(i) {
    current = (i + slides.length) % slides.length;
    track.style.transform = 'translateX(' + (-100 * current) + '%)';
    slides.forEach(function (s, n) { var on = n === current; s.toggleAttribute('inert', !on); s.setAttribute('aria-hidden', on ? 'false' : 'true'); });
    dots.forEach(function (d, n) { d.setAttribute('aria-current', n === current ? 'true' : 'false'); });
  }
  function restart() { clearInterval(timer); if (!reduce && !keyboardInside) timer = setInterval(function () { show(current + 1); }, 5000); }
  root.querySelector('.hs-prev').addEventListener('click', function () { show(current - 1); restart(); });
  root.querySelector('.hs-next').addEventListener('click', function () { show(current + 1); restart(); });
  dots.forEach(function (d, n) { d.addEventListener('click', function () { show(n); restart(); }); });
  root.addEventListener('focusin', function (e) {
    var byKeyboard = false; try { byKeyboard = e.target.matches(':focus-visible'); } catch (err) { byKeyboard = false; }
    keyboardInside = byKeyboard; restart();
  });
  root.addEventListener('focusout', function (e) { if (!root.contains(e.relatedTarget)) { keyboardInside = false; restart(); } });
  var x0 = null;
  root.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  root.addEventListener('touchend', function (e) { if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) { show(current + (dx < 0 ? 1 : -1)); restart(); } x0 = null; });
  document.addEventListener('visibilitychange', function () { if (document.hidden) clearInterval(timer); else restart(); });
  show(0); restart();
})();
