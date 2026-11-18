/* Top bar: when Site settings has more than one message, show them in turn every 5 seconds.
   Visitors with "reduce motion" turned on keep the first message. */
(function () {
  var bar = document.querySelector('.announcement-bar[data-rotate]'); if (!bar) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var msgs = bar.querySelectorAll('.announcement-msg'), current = 0, timer = null;
  function next() {
    msgs[current].classList.remove('is-active'); msgs[current].setAttribute('aria-hidden', 'true');
    current = (current + 1) % msgs.length;
    msgs[current].classList.add('is-active'); msgs[current].removeAttribute('aria-hidden');
  }
  function start() { clearInterval(timer); timer = setInterval(next, 5000); }
  document.addEventListener('visibilitychange', function () { if (document.hidden) clearInterval(timer); else start(); });
  start();
})();
