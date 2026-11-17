// Enquiry form: after the first click on "Send", ignore further clicks so a double click
// or an impatient second press can't send the same enquiry twice. (The server also
// ignores repeats; this just gives the visitor clear feedback.)
(function () {
  document.querySelectorAll("form[data-send-once]").forEach(function (form) {
    var button = form.querySelector("button[type=submit]");
    var label = button ? button.innerHTML : "";

    form.addEventListener("submit", function (event) {
      if (form.dataset.sending === "yes") {
        event.preventDefault();
        return;
      }
      form.dataset.sending = "yes";
      if (button) {
        button.setAttribute("aria-disabled", "true");
        button.classList.add("disabled");
        button.textContent = "Sending...";
      }
    });

    // Coming back with the browser's Back button shows the form ready to use again
    window.addEventListener("pageshow", function () {
      form.dataset.sending = "";
      if (button) {
        button.removeAttribute("aria-disabled");
        button.classList.remove("disabled");
        button.innerHTML = label;
      }
    });
  });
})();
