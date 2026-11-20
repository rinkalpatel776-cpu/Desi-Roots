/* Privacy pop-up and Google Analytics consent (20 Nov 2026).
 *
 * - Essential cookies are always on.
 * - Google Analytics loads ONLY after the visitor presses "Accept All" or switches it on and
 *   saves. Before that, no Google script is requested and no Google cookie is set.
 * - "Reject All" keeps it off. "Cookie settings" in the footer reopens the pop-up; switching
 *   Analytics off later stops it and deletes its cookies.
 * - The choice is kept on the visitor's own device (localStorage key "dr_cookie_consent":
 *   "granted" or "denied"). It is never sent to our server, so cached pages stay identical.
 */
(function () {
  "use strict";

  var KEY = "dr_cookie_consent";
  var OLD_KEY = "sp_cookie_notice_ok"; // pop-up seen before Analytics existed (no consent to Analytics)

  var notice = document.getElementById("cookieNotice");
  if (!notice) return;

  var gaId = notice.getAttribute("data-ga-id") || "";
  var details = document.getElementById("cookieNoticeDetails");
  var customize = document.getElementById("cookieNoticeCustomize");
  var toggle = document.getElementById("cookieAnalyticsToggle");
  var save = document.getElementById("cookieNoticeSave");
  var loaded = false;

  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(value) {
    try { localStorage.setItem(KEY, value); } catch (e) {}
  }

  function loadAnalytics() {
    if (!gaId || loaded) return;
    loaded = true;
    window["ga-disable-" + gaId] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", gaId);
    // Pages can ask for one event, e.g. the enquiry thank-you page counts a lead
    var marker = document.querySelector("[data-analytics-event]");
    if (marker) window.gtag("event", marker.getAttribute("data-analytics-event"));
    var script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    document.head.appendChild(script);
  }

  function stopAnalytics() {
    if (gaId) window["ga-disable-" + gaId] = true;
    // Delete Google Analytics cookies (_ga, _ga_<id>, _gid) for this site and its parent domain
    var host = location.hostname.replace(/^www\./, "");
    document.cookie.split(";").forEach(function (part) {
      var name = part.split("=")[0].trim();
      if (name === "_ga" || name === "_gid" || name.indexOf("_ga_") === 0) {
        ["", "; domain=" + host, "; domain=." + host].forEach(function (domain) {
          document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + domain;
        });
      }
    });
  }

  function open() {
    var choice = read(KEY);
    if (toggle) toggle.checked = choice === "granted";
    notice.hidden = false;
    document.body.classList.add("sp-cookie-notice-open");
  }

  function close() {
    notice.hidden = true;
    details.hidden = true;
    customize.setAttribute("aria-expanded", "false");
    document.body.classList.remove("sp-cookie-notice-open");
  }

  function choose(value) {
    write(value);
    close();
    if (value === "granted") {
      loadAnalytics();
    } else {
      stopAnalytics();
    }
  }

  customize.addEventListener("click", function () {
    details.hidden = !details.hidden;
    customize.setAttribute("aria-expanded", String(!details.hidden));
  });

  notice.querySelectorAll("[data-cookie-choice]").forEach(function (button) {
    button.addEventListener("click", function () {
      choose(button.getAttribute("data-cookie-choice"));
    });
  });

  if (save && toggle) {
    save.addEventListener("click", function () {
      choose(toggle.checked ? "granted" : "denied");
    });
  }

  document.querySelectorAll("[data-cookie-settings]").forEach(function (link) {
    link.addEventListener("click", function () {
      open();
      details.hidden = false;
      customize.setAttribute("aria-expanded", "true");
      (toggle || customize).focus();
    });
  });

  var choice = read(KEY);
  if (choice === "granted") {
    loadAnalytics();
  } else if (choice === "denied") {
    // keep Analytics off; nothing to show
  } else if (!gaId && read(OLD_KEY)) {
    // Analytics is not set up and the visitor already closed the old pop-up
  } else {
    open();
  }
})();
