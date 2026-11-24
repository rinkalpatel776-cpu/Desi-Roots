/* Unsent enquiry keeper (21 Nov 2026).
 *
 * If a buyer's form expires, the page is closed by mistake or the connection drops, what they typed
 * is kept on their own device (localStorage "dr_enquiry_draft", never sent to our server) and put back
 * into the empty fields next time the form opens. Kept for 7 days at most and deleted as soon as the
 * enquiry is sent (the thank-you page clears it). The consent tick is never kept.
 */
(function () {
  "use strict";

  var KEY = "dr_enquiry_draft";
  var MAX_AGE = 7 * 24 * 60 * 60 * 1000;
  var FIELDS = ["name", "business_name", "business_type", "email", "phone", "postcode", "message"];

  function clear() {
    try { localStorage.removeItem(KEY); } catch (e) {}
  }

  function read() {
    try {
      var draft = JSON.parse(localStorage.getItem(KEY) || "null");
      if (!draft || !draft.values || Date.now() - draft.saved > MAX_AGE) {
        clear();
        return null;
      }
      return draft;
    } catch (e) {
      return null;
    }
  }

  // Thank-you page: the enquiry arrived, so nothing needs keeping any more
  if (document.querySelector("[data-enquiry-sent]")) {
    clear();
    return;
  }

  var form = document.querySelector("form[data-enquiry-draft]");
  if (!form) return;

  function field(name) {
    return form.elements[name] || null;
  }

  // Remember what the page itself filled in (e.g. the product message), so only the visitor's own
  // typing counts as a draft, and never overwrite anything already in a field
  var draft = read();
  var restored = false;
  FIELDS.forEach(function (name) {
    var el = field(name);
    if (!el) return;
    el.setAttribute("data-initial", el.value);
    if (draft && draft.values[name] && !el.value.trim()) {
      el.value = draft.values[name];
      restored = true;
    }
  });

  if (restored) {
    var note = document.createElement("div");
    note.className = "sp-draft-note";
    note.setAttribute("role", "status");
    var text = document.createElement("span");
    text.textContent = "We kept what you typed last time.";
    var reset = document.createElement("button");
    reset.type = "button";
    reset.className = "sp-draft-clear";
    reset.textContent = "Clear the form";
    reset.addEventListener("click", function () {
      FIELDS.forEach(function (name) {
        var el = field(name);
        if (el) el.value = el.getAttribute("data-initial") || "";
      });
      clear();
      note.remove();
    });
    note.appendChild(text);
    note.appendChild(reset);
    form.insertBefore(note, form.firstChild);
  }

  function save() {
    var values = {};
    var typed = false;
    FIELDS.forEach(function (name) {
      var el = field(name);
      if (!el) return;
      values[name] = el.value;
      if (el.value.trim() && el.value !== el.getAttribute("data-initial")) typed = true;
    });
    try {
      if (typed) {
        localStorage.setItem(KEY, JSON.stringify({ saved: Date.now(), values: values }));
      } else {
        localStorage.removeItem(KEY);
      }
    } catch (e) {}
  }

  var timer;
  form.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(save, 400);
  });
  // Keep it while sending too: if the form has expired, the text is still there to send again
  form.addEventListener("submit", save);
})();
