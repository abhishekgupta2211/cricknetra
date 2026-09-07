/* CricNetra — real-time live updates for a public match page (/m/{id}).
   Subscribes to the server's SSE stream; on each change it re-fetches the page
   and swaps in the freshly server-rendered scorecard (so all the rendering lives
   in one place — the Jinja template). Falls back to polling if SSE is missing.
   Only runs while the match is live; tears down once a result is in. */

(function () {
  "use strict";

  var main = document.querySelector(".match-main");
  if (!main) return;
  var idMatch = location.pathname.match(/\/m\/([^\/?#]+)/);
  if (!idMatch) return;
  var id = idMatch[1];

  function isLive() { return !!main.querySelector(".badge-live"); }
  if (!isLive()) return; // already finished — nothing to stream

  var es = null, poll = null, busy = false;

  function teardown() {
    if (es) { es.close(); es = null; }
    if (poll) { clearInterval(poll); poll = null; }
  }

  function refresh() {
    if (busy) return;
    busy = true;
    fetch(location.pathname, { cache: "no-store", headers: { Accept: "text/html" } })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        busy = false;
        if (!html) return;
        var fresh = new DOMParser().parseFromString(html, "text/html").querySelector(".match-main");
        if (!fresh) return;
        // remember which tab the viewer was on, then swap in the fresh render
        var openTab = main.querySelector(".tab.is-active");
        openTab = openTab ? openTab.dataset.tab : null;
        main.innerHTML = fresh.innerHTML;
        if (openTab && openTab !== "live") {
          var t = main.querySelector('.tab[data-tab="' + openTab + '"]');
          if (t) t.click(); // re-apply via site.js's delegated handler
        }
        flash();
        if (!isLive()) teardown(); // match just ended
      })
      .catch(function () { busy = false; });
  }

  // brief highlight on the live badge so a watcher notices the update
  function flash() {
    var b = main.querySelector(".badge-live");
    if (!b) return;
    b.classList.remove("just-updated");
    void b.offsetWidth; // restart the animation
    b.classList.add("just-updated");
  }

  function startPolling() { if (!poll) poll = setInterval(refresh, 5000); }

  if (window.EventSource) {
    try {
      es = new EventSource("/api/v1/matches/" + id + "/stream");
      es.onmessage = function () { refresh(); };
      es.addEventListener("gone", teardown);
      es.onerror = function () {
        // a finished stream closes itself; otherwise drop to polling
        if (es && es.readyState === EventSource.CLOSED) { es = null; if (isLive()) startPolling(); }
      };
    } catch (e) { startPolling(); }
  } else {
    startPolling();
  }

  window.addEventListener("beforeunload", teardown);
})();
