/* CricNetra public detail pages — tabs, match filters, share.
   Loaded on /m/{id} and /t/{id}. Progressive: pages still read fine without JS.
   Uses event delegation on document, so it keeps working after live.js swaps in
   freshly-rendered match content. */

(function () {
  "use strict";

  document.addEventListener("click", function (e) {
    // ---- tabs (Live/Scorecard, Matches/Standings/Teams) ----
    var tab = e.target.closest && e.target.closest(".tab");
    if (tab) {
      var group = tab.closest(".tabs");
      var name = tab.dataset.tab;
      if (group) group.querySelectorAll(".tab").forEach(function (t) { t.classList.toggle("is-active", t === tab); });
      document.querySelectorAll("[data-panel]").forEach(function (p) {
        p.classList.toggle("is-active", p.dataset.panel === name);
      });
      return;
    }

    // ---- match filter pills (All/Live/Upcoming/Completed) ----
    var pill = e.target.closest && e.target.closest(".pill");
    if (pill) {
      var f = pill.dataset.filter;
      document.querySelectorAll(".pill").forEach(function (p) { p.classList.toggle("is-active", p === pill); });
      var shown = 0;
      document.querySelectorAll(".card-grid .match-card").forEach(function (card) {
        var match = f === "all" || card.dataset.status === f;
        card.style.display = match ? "" : "none";
        if (match) shown++;
      });
      var empty = document.getElementById("filterEmpty");
      if (empty) empty.style.display = shown ? "none" : "block";
      return;
    }

    // ---- share ----
    var share = e.target.closest && e.target.closest("[data-share]");
    if (share) {
      var url = location.href;
      if (navigator.share) {
        navigator.share({ title: document.title, url: url }).catch(function () {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(function () {
          var old = share.textContent;
          share.textContent = "✓";
          window.setTimeout(function () { share.textContent = old; }, 1500);
        }).catch(function () {});
      }
    }
  });
})();
