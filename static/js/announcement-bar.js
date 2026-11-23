/* Top bar: when Site settings has more than one message, show them in turn every 5 seconds.
   Since 23 Nov 2026 the messages slide sideways like the hero slider (same 0.5 s movement and easing):
   the next message comes in from the right and pushes the current one out to the left.
   Visitors with "reduce motion" turned on keep the first message. */
(function () {
  var bar = document.querySelector('.announcement-bar[data-rotate]'); if (!bar) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var msgs = bar.querySelectorAll('.announcement-msg'), current = 0, timer = null;
  var SLIDE_MS = 500;

  function park(msg) {
    // Put a message back at the right-hand side without animating, ready to come in again
    msg.style.transition = 'none';
    msg.classList.remove('is-leaving');
    void msg.offsetWidth;
    msg.style.transition = '';
  }

  function next() {
    var old = msgs[current];
    current = (current + 1) % msgs.length;
    var incoming = msgs[current];
    park(incoming);
    old.classList.remove('is-active'); old.classList.add('is-leaving'); old.setAttribute('aria-hidden', 'true');
    incoming.classList.add('is-active'); incoming.removeAttribute('aria-hidden');
    setTimeout(function () { if (!old.classList.contains('is-active')) park(old); }, SLIDE_MS + 50);
  }
  function start() { clearInterval(timer); timer = setInterval(next, 5000); }
  document.addEventListener('visibilitychange', function () { if (document.hidden) clearInterval(timer); else start(); });
  start();
})();
