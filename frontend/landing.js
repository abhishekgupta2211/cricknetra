/* CricNetra landing page — make it feel alive:
   - reveal sections/cards as they scroll into view (staggered)
   - count the "in numbers" tiles up from 0
   - show a real "matches live now" pill from the API
   Robust by design: the hidden-initial state is only applied when scroll reveal
   is actually available, and a timed fallback guarantees nothing stays hidden. */

(function () {
  "use strict";
  var root = document.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var useAnim = !reduce && "IntersectionObserver" in window;
  var els = [].slice.call(document.querySelectorAll(".reveal"));

  function easeOutCubic(p) { return 1 - Math.pow(1 - p, 3); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function countUp(tile) {
    var el = tile.querySelector(".v") || tile;
    var target = parseFloat(tile.getAttribute("data-count"));
    if (isNaN(target)) return;
    var suffix = tile.getAttribute("data-suffix") || "";
    var t0 = null, dur = 1000;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1);
      el.textContent = Math.round(target * easeOutCubic(p)) + suffix;
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target + suffix;
    }
    requestAnimationFrame(step);
  }

  function reveal(el) {
    if (el.classList.contains("is-in")) return;
    el.classList.add("is-in");
    if (el.hasAttribute("data-count")) countUp(el);
  }

  if (useAnim) {
    root.classList.add("js-anim");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (el) { io.observe(el); });
    // safety net — never leave content hidden if the observer doesn't fire
    setTimeout(function () { els.forEach(reveal); }, 4000);
  }
  // (no useAnim → no .js-anim class, so everything is visible by default)

  // count a tile up to a real total (or set it now if it's already on screen)
  function setTile(id, value) {
    var tile = document.getElementById(id);
    if (!tile || value == null) return;
    tile.setAttribute("data-count", value);
    tile.removeAttribute("data-suffix");
    if (tile.classList.contains("is-in")) {
      var v = tile.querySelector(".v");
      if (v) v.textContent = value;
    }
  }

  function chipClass(s) {
    if (s === "4") return "dv-chip r4";
    if (s === "6") return "dv-chip r6";
    if (/w/i.test(s)) return "dv-chip w";
    return "dv-chip";
  }

  // standout player of one match: batting runs + wickets×20 across both innings
  function matchMvp(state) {
    var agg = {};
    (state.innings || []).forEach(function (inn) {
      (inn.batters || []).forEach(function (b) {
        (agg[b.name] = agg[b.name] || { runs: 0, wkts: 0 }).runs += b.runs || 0;
      });
      (inn.bowlers || []).forEach(function (w) {
        (agg[w.name] = agg[w.name] || { runs: 0, wkts: 0 }).wkts += w.wickets || 0;
      });
    });
    var best = null;
    Object.keys(agg).forEach(function (name) {
      var pts = agg[name].runs + agg[name].wkts * 20;
      if (pts > 0 && (!best || pts > best.pts)) best = { name: name, pts: pts };
    });
    return best;
  }

  // paint the hero "phone" with a real match, and rotate through live ones
  function fillHero(state) {
    var inn = state.innings && state.innings[(state.current_innings || 1) - 1];
    if (!inn || (inn.runs === 0 && inn.wickets === 0 && !(inn.this_over || []).length)) return;
    var set = function (id, txt) { var el = document.getElementById(id); if (el) el.textContent = txt; };
    set("dvTeam", inn.batting_team);
    set("dvScore", inn.runs + "/" + inn.wickets);
    var meta = document.getElementById("dvMeta");
    if (meta) {
      var right = inn.target ? "Target " + inn.target : "vs " + inn.bowling_team;
      meta.innerHTML = "<span>" + esc(inn.overs_str) + " ov</span><span>" + esc(right) + "</span>";
    }
    var atCrease = (inn.batters || []).filter(function (b) { return b.has_batted && !b.out; })
      .sort(function (a, b) { return (b.on_strike ? 1 : 0) - (a.on_strike ? 1 : 0); }).slice(0, 2);
    var batEl = document.getElementById("dvBat");
    if (batEl && atCrease.length) {
      batEl.innerHTML = atCrease.map(function (b) {
        return '<div class="dv-line"><span class="' + (b.on_strike ? "on" : "") + '">' +
          esc(b.name) + (b.on_strike ? " ★" : "") + "</span><b>" + b.runs + " (" + b.balls + ")</b></div>";
      }).join("");
    }
    var bowlers = inn.bowlers || [];
    var bw = bowlers.filter(function (w) { return w.name === inn.bowler; })[0] || bowlers[bowlers.length - 1];
    var bowlEl = document.getElementById("dvBowl");
    if (bowlEl && bw) {
      bowlEl.innerHTML = '<div class="dv-line"><span>' + esc(bw.name) + "</span><b>" +
        bw.wickets + "/" + bw.runs + " (" + esc(bw.overs) + ")</b></div>";
    }
    var overEl = document.getElementById("dvOver");
    if (overEl && (inn.this_over || []).length) {
      overEl.innerHTML = inn.this_over.map(function (s) {
        return '<span class="' + chipClass(s) + '">' + esc(s) + "</span>";
      }).join("");
    }
    // floating CRR / RRR pill — always show both (RRR is "—" until a chase begins)
    var rates = document.getElementById("floatRates");
    if (rates) {
      var crr = (inn.run_rate != null ? inn.run_rate : 0).toFixed(1);
      var rrr = inn.required_run_rate != null ? inn.required_run_rate.toFixed(1) : "—";
      rates.innerHTML = "CRR " + crr + "<small>RRR " + rrr + "</small>";
    }
    // floating MVP pill — the standout player of THIS match
    var mvp = matchMvp(state);
    var mvpEl = document.getElementById("floatMvp");
    if (mvpEl && mvp) mvpEl.textContent = mvp.name + " · " + mvp.pts + " pts";
  }

  // ---- live data: matches (live pill + hero card + a real "matches" total) ----
  // The match list is RE-POLLED, not fetched once: a match that starts after page
  // load still lights the pill and joins the hero rotation.
  var pool = [], idx = 0, heroTimer = null, heroEvery = 0;

  function showNext() {
    if (!pool.length) return;
    var m = pool[idx % pool.length];
    idx += 1;
    fetch("/api/v1/matches/" + m.id, { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (state) { if (state) fillHero(state); })
      .catch(function () {});
  }

  function paceHero(liveCount) {
    var every = liveCount > 1 ? 6000 : 15000;  // cycle several, or keep the one fresh
    if (every === heroEvery && heroTimer) return;
    heroEvery = every;
    if (heroTimer) clearInterval(heroTimer);
    heroTimer = setInterval(showNext, every);
  }

  function refreshLive() {
    if (document.hidden) return;
    fetch("/api/v1/matches", { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (matches) {
        if (!matches.length) return;
        setTile("numMatches", matches.length);
        var liveOnes = matches.filter(function (m) { return !m.result && m.status !== "complete"; });
        var pill = document.getElementById("heroLive"), n = document.getElementById("liveCount");
        if (pill && n) {
          n.textContent = liveOnes.length;
          pill.hidden = liveOnes.length === 0;
        }
        // hero phone: rotate through ALL live matches; if none live, show the latest
        var next = liveOnes.length ? liveOnes : [matches[matches.length - 1]];
        var changed = next.length !== pool.length || next.some(function (m, i) {
          return !pool[i] || String(pool[i].id) !== String(m.id);
        });
        pool = next;
        if (changed) { idx = 0; showNext(); }
        paceHero(liveOnes.length);
      })
      .catch(function () { /* offline — keep the sample card */ });
  }

  refreshLive();
  setInterval(refreshLive, 30000);  // pick up matches that start later
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refreshLive(); });

  // ---- real platform totals for the "in numbers" tiles ----
  fetch("/api/v1/players").then(function (r) { return r.ok ? r.json() : null; })
    .then(function (p) { if (p && p.length) setTile("numPlayers", p.length); }).catch(function () {});
  fetch("/api/v1/teams").then(function (r) { return r.ok ? r.json() : null; })
    .then(function (t) { if (t && t.length) setTile("numTeams", t.length); }).catch(function () {});

  // ---- MVP leaderboard: top all-rounders, straight from the match log ----
  fetch("/api/v1/leaderboards?limit=4", { headers: { Accept: "application/json" } })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var mvp = (data && data.mvp) || [];
      if (!mvp.length) return; // no scored matches yet — keep the sample board
      var board = document.getElementById("mvpBoard");
      if (!board) return;  // (the floating MVP pill is the *live match's* MVP, set in fillHero)
      var medal = ["g", "s", "b", ""];
      board.innerHTML = mvp.slice(0, 4).map(function (e, i) {
        var sub = e.detail ? ' <span class="mb-sub">· ' + esc(e.detail) + "</span>" : "";
        return '<div class="mb-rank"><span class="mb-medal ' + medal[i] + '">' + (i + 1) +
          '</span><span class="mb-name">' + esc(e.name) + sub +
          '</span><span class="mb-val">' + Math.round(e.value) + "</span></div>";
      }).join("");
    })
    .catch(function () { /* offline — keep the sample board */ });
})();
