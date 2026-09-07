/* CricNetra — keeps a server-rendered list page fresh without a reload.
   Used by /live-matches and /t/{id}. (The match page /m/{id} has a real SSE
   stream via live.js; a directory would need one connection per match, so it
   polls one cheap HTML fetch instead.)

   Re-fetches this page and swaps the [data-live-region] block, restoring the
   open tab / active filter afterwards. site.js delegates its clicks from
   `document`, so swapped-in nodes stay wired. Polls faster while something is
   live, slower otherwise (so a match that starts later still shows up), and
   pauses entirely while the tab is hidden. */

(function () {
  "use strict";

  var region = document.querySelector("[data-live-region]");
  if (!region || !window.fetch || !window.DOMParser) return;  // no JS? page still reads fine

  var LIVE_MS = 12000;   // something is in play — keep it snappy
  var IDLE_MS = 30000;   // nothing live — just catch matches starting
  var timer = null, busy = false, every = 0;

  function anyLive() { return !!document.querySelector(".badge-live"); }

  function activeAttr(sel, attr) {
    var el = document.querySelector(sel + ".is-active");
    return el ? el.getAttribute(attr) : null;
  }

  // Re-click through site.js's delegated handler so the classes AND the card
  // filtering re-apply, rather than duplicating that logic here.
  function restore(tab, filter) {
    if (tab) {
      var t = document.querySelector('.tab[data-tab="' + tab + '"]');
      if (t && !t.classList.contains("is-active")) t.click();
    }
    if (filter) {
      var p = document.querySelector('.pill[data-filter="' + filter + '"]');
      if (p && !p.classList.contains("is-active")) p.click();
    }
  }

  function refresh() {
    if (busy || document.hidden) return;
    busy = true;
    var tab = activeAttr(".tab", "data-tab");
    var filter = activeAttr(".pill", "data-filter");
    fetch(location.href, { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        busy = false;
        if (!html) return;
        var doc = new DOMParser().parseFromString(html, "text/html");
        var fresh = doc.querySelector("[data-live-region]");
        if (fresh && fresh.innerHTML !== region.innerHTML) {
          region.innerHTML = fresh.innerHTML;
          restore(tab, filter);
        }
        // the "N live now" chip lives outside the region — keep it in step
        var chip = document.querySelector("[data-live-count]");
        var freshChip = doc.querySelector("[data-live-count]");
        if (chip && freshChip && chip.innerHTML !== freshChip.innerHTML) chip.innerHTML = freshChip.innerHTML;
        pace();
      })
      .catch(function () { busy = false; });
  }

  function pace() {
    var want = anyLive() ? LIVE_MS : IDLE_MS;
    if (want === every && timer) return;
    every = want;
    if (timer) window.clearInterval(timer);
    timer = window.setInterval(refresh, every);
  }

  function stop() { if (timer) { window.clearInterval(timer); timer = null; every = 0; } }

  pace();
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop();
    else { refresh(); pace(); }   // catch up on what was missed
  });
})();
