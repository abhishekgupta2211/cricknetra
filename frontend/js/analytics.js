/*!
 * CricNetra analytics — shared, dependency-free SVG renderers for the Wagon Wheel
 * and the Pitch Map. Exposes window.CricWagon and window.CricPitch so the SPA and the
 * server-rendered pages (overlay analysis scene, PDF, public match page) mount the SAME
 * component — one implementation, one theme. Pure SVG (no canvas, no libs); comfortably
 * handles 1000+ marks. Animations touch stroke-dashoffset / opacity only (GPU-friendly).
 *
 *   CricWagon.mount(el, shots, opts)   shots: [{x,y,runs,batter,bowler,over,ball,wicket,zone}]
 *   CricPitch.mount(el, marks, opts)   marks: [{x,y,runs,wicket,bowler,over,speed,length,line,outcome}]
 *   CricWagon.svg(shots,opts) / CricPitch.svg(marks,opts)  → static SVG string (print/PDF)
 *
 * opts: { filters:true, animate:true, batter, bowler, ppOvers, maxOvers }
 */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  // Self-contained styling — injected once so the component looks identical wherever
  // it mounts (SPA, overlay scene, PDF, public page). Semantic colours are fixed;
  // panels/tooltip use theme-neutral translucency that reads on light or dark.
  var CSS =
    ".cn-an-host{display:flex;flex-direction:column;gap:8px}" +
    ".cn-an-filters{display:flex;flex-wrap:wrap;gap:6px}" +
    ".cn-an-f{font:600 11px/1 system-ui,-apple-system,Segoe UI,sans-serif;letter-spacing:.02em;padding:5px 10px;" +
      "border-radius:999px;border:1px solid rgba(128,128,128,.32);background:rgba(128,128,128,.08);color:inherit;" +
      "cursor:pointer;opacity:.68;transition:opacity .12s,background .12s}" +
    ".cn-an-f:hover{opacity:.9}.cn-an-f.on{background:#0c9b54;border-color:#0c9b54;color:#fff;opacity:1}" +
    ".cn-an-wrap{position:relative;line-height:0}" +
    ".cn-an-wrap svg{display:block;width:100%;height:auto}" +
    ".cn-wagon-shot{opacity:.92;transition:stroke-width .12s,filter .12s}" +
    ".cn-wagon-shot.hot{stroke-width:3.4;opacity:1;filter:brightness(1.25) drop-shadow(0 0 2px rgba(0,0,0,.45))}" +
    ".cn-pitch-dot{cursor:pointer;transition:opacity .3s}" +
    ".cn-pitch-dot.pulse{animation:cnPulse 1s ease-in-out infinite;transform-box:fill-box;transform-origin:center}" +
    "@keyframes cnPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.55)}}" +
    ".cn-pitch-band{fill:rgba(255,255,255,.55);font:700 8px system-ui}" +
    ".cn-an-empty{fill:rgba(150,150,150,.75);font:600 12px system-ui}" +
    ".cn-an-tip{position:absolute;pointer-events:none;transform:translate(-50%,-125%);z-index:5;line-height:1.35;" +
      "background:rgba(12,16,14,.94);color:#fff;border:1px solid rgba(255,255,255,.16);border-radius:6px;" +
      "padding:5px 8px;font:600 11px system-ui;white-space:nowrap;box-shadow:0 4px 14px rgba(0,0,0,.4);transition:opacity .12s}" +
    "@media (prefers-reduced-motion:reduce){.cn-wagon-shot,.cn-pitch-dot{transition:none!important}.cn-pitch-dot.pulse{animation:none}}";
  function ensureCss() {
    if (document.getElementById("cn-an-css")) return;
    var st = document.createElement("style");
    st.id = "cn-an-css";
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  // Broadcast-standard, theme-independent semantic colours (per spec).
  var C6 = "#f5c518", C4 = "#22c55e", C3 = "#a855f7", C2 = "#06b6d4", C1 = "#3b82f6", C0 = "#9aa0a6", CW = "#ef4444";
  function wagonColor(s) {
    if (s.wicket) return CW;
    if (s.runs >= 6) return C6;
    if (s.runs >= 4) return C4;
    return { 0: C0, 1: C1, 2: C2, 3: C3 }[s.runs] || C1;
  }
  function pitchColor(m) {
    if (m.wicket || m.outcome === "wicket") return CW;
    if (m.outcome === "six" || m.runs >= 6) return C6;
    if (m.outcome === "four" || m.runs >= 4) return C4;
    if (m.outcome === "dot" || m.runs === 0) return C0;
    return C1;
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function overNo(s) {
    var v = parseInt(String(s.ball || s.over || "0").split(".")[0], 10);
    return isNaN(v) ? 0 : v;
  }
  function buildFilters(defs, onPick, activeLabel) {
    var bar = document.createElement("div");
    bar.className = "cn-an-filters";
    var activeIdx = 0;   // preserve a previously-picked filter across re-mounts (overlay refresh)
    if (activeLabel) for (var j = 0; j < defs.length; j++) if (defs[j].label === activeLabel) { activeIdx = j; break; }
    defs.forEach(function (d, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cn-an-f" + (i === activeIdx ? " on" : "");
      b.textContent = d.label;
      b.onclick = function () {
        bar.querySelectorAll(".cn-an-f").forEach(function (x) { x.classList.remove("on"); });
        b.classList.add("on");
        onPick(d.test);
      };
      bar.appendChild(b);
    });
    return bar;
  }
  // the test fn for a filter label (or null for "All"/unknown) — used for the initial draw
  function testFor(defs, label) {
    if (!label) return null;
    for (var i = 0; i < defs.length; i++) if (defs[i].label === label) return defs[i].test;
    return null;
  }
  function makeTip(wrap) {
    var t = document.createElement("div");
    t.className = "cn-an-tip";
    t.style.opacity = 0;
    wrap.appendChild(t);
    return {
      node: t,
      show: function (html, x, y) { t.innerHTML = html; t.style.left = x + "px"; t.style.top = y + "px"; t.style.opacity = 1; },
      hide: function () { t.style.opacity = 0; },
    };
  }
  // Insert an SVG string as the wrap's first child (HTML parser namespaces <svg> content
  // correctly — unlike setting innerHTML directly on an SVG node), keeping the tooltip on top.
  function paint(wrap, svgStr) {
    var old = wrap.querySelector("svg");
    if (old) old.remove();
    wrap.insertAdjacentHTML("afterbegin", svgStr);
    return wrap.querySelector("svg");
  }
  function staggerIn(node, i, n, prop, from, to, dur, total) {
    node.style[prop] = from;
    node.style.transition = prop.replace(/([A-Z])/g, "-$1").toLowerCase() + " " + dur + " ease";
    node.style.transitionDelay = Math.min(total, n ? (i / n) * total : 0) + "ms";
    requestAnimationFrame(function () { requestAnimationFrame(function () { node.style[prop] = to; }); });
    setTimeout(function () { node.style[prop] = to; }, 200 + total + 200);   // rAF-throttle fallback
  }

  /* =========================== WAGON WHEEL =========================== */
  function wagonField(S) {
    var c = S / 2, R = S * 0.47, inner = R * 0.56;
    return '<svg xmlns="' + NS + '" viewBox="0 0 ' + S + ' ' + S + '" class="cn-wagon-svg" preserveAspectRatio="xMidYMid meet">' +
      '<defs><radialGradient id="cnWagG" cx="50%" cy="42%" r="65%">' +
      '<stop offset="0%" stop-color="#1f7a48"/><stop offset="100%" stop-color="#12603a"/></radialGradient></defs>' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + R + '" fill="url(#cnWagG)" stroke="rgba(255,255,255,.5)" stroke-width="2"/>' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + inner.toFixed(1) + '" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1" stroke-dasharray="4 5"/>' +
      '<rect x="' + (c - S * 0.024) + '" y="' + (c - S * 0.075) + '" width="' + (S * 0.048) + '" height="' + (S * 0.15) + '" rx="2" fill="#cdae7a" opacity=".9"/>' +
      '<circle cx="' + c + '" cy="' + c + '" r="2.6" fill="#fff"/>';
  }
  function wagonLine(s, c, R, cls) {
    var x2 = c + s.x * R, y2 = c - s.y * R;
    return '<line class="cn-wagon-shot' + (cls || "") + '" x1="' + c + '" y1="' + c + '" x2="' + x2.toFixed(1) +
      '" y2="' + y2.toFixed(1) + '" stroke="' + wagonColor(s) + '" stroke-width="' + (s.runs >= 4 ? 2.4 : 1.8) +
      '" stroke-linecap="round"/>';
  }
  function runLabel(s) {
    if (s.wicket) return "Wicket";
    return { 0: "Dot", 1: "Single", 2: "Two", 3: "Three", 4: "FOUR", 6: "SIX" }[s.runs] || (s.runs + " runs");
  }
  var CricWagon = {
    colorOf: wagonColor,
    filtersFor: function (opts) {
      opts = opts || {};
      var f = [{ label: "All", test: null },
        { label: "4s", test: function (s) { return s.runs === 4 && !s.wicket; } },
        { label: "6s", test: function (s) { return s.runs >= 6; } },
        { label: "Boundaries", test: function (s) { return s.runs >= 4; } },
        { label: "Wickets", test: function (s) { return !!s.wicket; } }];
      if (opts.batter) f.splice(1, 0, { label: "Batter", test: function (s) { return s.batter === opts.batter; } });
      if (opts.ppOvers) f.push({ label: "Powerplay", test: function (s) { return overNo(s) < opts.ppOvers; } });
      if (opts.maxOvers) f.push({ label: "Death", test: function (s) { return overNo(s) >= opts.maxOvers - 5; } });
      return f;
    },
    svg: function (shots, opts) {
      opts = opts || {}; var S = opts.size || 300, c = S / 2, R = S * 0.47;
      return wagonField(S) + (shots || []).map(function (s) { return wagonLine(s, c, R); }).join("") + "</svg>";
    },
    mount: function (host, shots, opts) {
      opts = opts || {}; shots = shots || [];
      ensureCss();
      host.classList.add("cn-an-host"); host.innerHTML = "";
      var defs = this.filtersFor(opts);
      if (opts.filters !== false && shots.length) host.appendChild(buildFilters(defs, redraw, opts.activeFilter));
      var wrap = document.createElement("div"); wrap.className = "cn-an-wrap"; host.appendChild(wrap);
      var tip = makeTip(wrap), S = 300, c = S / 2, R = S * 0.47;
      function redraw(test) {
        var data = test ? shots.filter(test) : shots;
        var body = data.map(function (s) { return wagonLine(s, c, R); }).join("");
        if (!data.length) body += '<text x="' + c + '" y="' + c + '" class="cn-an-empty" text-anchor="middle">No shots yet</text>';
        var svg = paint(wrap, wagonField(S) + body + "</svg>");
        var lines = svg.querySelectorAll(".cn-wagon-shot");
        Array.prototype.forEach.call(lines, function (ln, i) {
          var s = data[i];
          if (opts.animate !== false) {
            var len = Math.hypot(s.x * R, s.y * R);
            ln.style.strokeDasharray = len;
            staggerIn(ln, i, data.length, "strokeDashoffset", len, 0, ".5s", 800);
          }
          ln.addEventListener("mouseenter", function () {
            ln.classList.add("hot");
            var rc = wrap.getBoundingClientRect();
            tip.show('<b>' + esc(s.ball || s.over) + "</b> · " + esc(runLabel(s)) +
              (s.zone ? "<br>" + esc(s.zone) : "") + (s.bowler ? "<br>b " + esc(s.bowler) : ""),
              ((c + s.x * R) / S) * rc.width, ((c - s.y * R) / S) * rc.height);
          });
          ln.addEventListener("mouseleave", function () { ln.classList.remove("hot"); tip.hide(); });
        });
      }
      redraw(testFor(defs, opts.activeFilter));   // honour a preserved filter on (re)mount
      return wrap;
    },
  };

  /* =========================== PITCH MAP =========================== */
  var LEN_BANDS = [
    { to: 0.12, label: "Yorker", tint: "rgba(245,197,24,.10)" },
    { to: 0.28, label: "Full", tint: "rgba(34,197,94,.09)" },
    { to: 0.52, label: "Good", tint: "rgba(255,255,255,.05)" },
    { to: 0.72, label: "Back", tint: "rgba(59,130,246,.08)" },
    { to: 0.90, label: "Short", tint: "rgba(239,68,68,.08)" },
    { to: 1.01, label: "Bouncer", tint: "rgba(239,68,68,.14)" },
  ];
  function pitchXY(m, W, H) {
    return { x: W / 2 + (m.x || 0) * (W * 0.15), y: H * 0.86 - (m.y || 0) * (H * 0.58) };
  }
  function pitchField(W, H) {
    var sX = W * 0.34, sW = W * 0.32, top = H * 0.06, bot = H * 0.94;
    var bands = LEN_BANDS.map(function (b, i) {
      var y0 = H * 0.86 - (i === 0 ? 0 : LEN_BANDS[i - 1].to) * H * 0.58;
      var y1 = H * 0.86 - b.to * H * 0.58;
      return '<rect x="' + sX + '" y="' + y1.toFixed(1) + '" width="' + sW + '" height="' + (y0 - y1).toFixed(1) +
        '" fill="' + b.tint + '"/><text x="' + (sX + sW + 4) + '" y="' + ((y0 + y1) / 2 + 3).toFixed(1) +
        '" class="cn-pitch-band">' + b.label + "</text>";
    }).join("");
    function stumps(y) {
      var m = W / 2;
      return '<g stroke="#e8e8e8" stroke-width="1.4">' +
        '<line x1="' + (m - 5) + '" y1="' + y + '" x2="' + (m - 5) + '" y2="' + (y + 9) + '"/>' +
        '<line x1="' + m + '" y1="' + y + '" x2="' + m + '" y2="' + (y + 9) + '"/>' +
        '<line x1="' + (m + 5) + '" y1="' + y + '" x2="' + (m + 5) + '" y2="' + (y + 9) + '"/></g>';
    }
    return '<svg xmlns="' + NS + '" viewBox="0 0 ' + W + ' ' + H + '" class="cn-pitch-svg" preserveAspectRatio="xMidYMid meet">' +
      '<rect x="0" y="0" width="' + W + '" height="' + H + '" rx="10" fill="#12603a"/>' +
      '<rect x="' + sX + '" y="' + top + '" width="' + sW + '" height="' + (bot - top) + '" rx="3" fill="#c9a86e"/>' +
      bands +
      '<line x1="' + sX + '" y1="' + (H * 0.86) + '" x2="' + (sX + sW) + '" y2="' + (H * 0.86) + '" stroke="rgba(255,255,255,.7)"/>' +
      stumps(H * 0.885) + stumps(top + 3);
  }
  function pOutcome(m) {
    if (m.wicket) return "WICKET";
    return { dot: "Dot", single: "Single", two: "Two", three: "Three", four: "FOUR", six: "SIX" }[m.outcome] ||
      (m.runs != null ? m.runs + " runs" : "");
  }
  var CricPitch = {
    colorOf: pitchColor,
    filtersFor: function (opts) {
      opts = opts || {};
      var f = [{ label: "All", test: null },
        { label: "Wickets", test: function (m) { return !!m.wicket; } },
        { label: "Dots", test: function (m) { return (m.outcome === "dot" || m.runs === 0) && !m.wicket; } },
        { label: "Boundaries", test: function (m) { return m.runs >= 4; } }];
      if (opts.bowler) f.splice(1, 0, { label: "Bowler", test: function (m) { return m.bowler === opts.bowler; } });
      if (opts.ppOvers) f.push({ label: "Powerplay", test: function (m) { return overNo(m) < opts.ppOvers; } });
      if (opts.maxOvers) f.push({ label: "Death", test: function (m) { return overNo(m) >= opts.maxOvers - 5; } });
      return f;
    },
    svg: function (marks, opts) {
      var W = 200, H = 300;
      return pitchField(W, H) + (marks || []).map(function (m) {
        var p = pitchXY(m, W, H);
        return '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="4.5" fill="' + pitchColor(m) +
          '" stroke="rgba(0,0,0,.25)" stroke-width=".5"/>';
      }).join("") + "</svg>";
    },
    mount: function (host, marks, opts) {
      opts = opts || {}; marks = marks || [];
      ensureCss();
      host.classList.add("cn-an-host"); host.innerHTML = "";
      var defs = this.filtersFor(opts);
      if (opts.filters !== false && marks.length) host.appendChild(buildFilters(defs, redraw, opts.activeFilter));
      var wrap = document.createElement("div"); wrap.className = "cn-an-wrap"; host.appendChild(wrap);
      var tip = makeTip(wrap), W = 200, H = 300;
      function redraw(test) {
        var data = test ? marks.filter(test) : marks;
        var body = data.map(function (m) {
          var p = pitchXY(m, W, H);
          return '<circle class="cn-pitch-dot" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="4.5" fill="' +
            pitchColor(m) + '" stroke="rgba(0,0,0,.25)" stroke-width=".5"/>';
        }).join("");
        if (!data.length) body += '<text x="' + (W / 2) + '" y="' + (H / 2) + '" class="cn-an-empty" text-anchor="middle">No deliveries yet</text>';
        var svg = paint(wrap, pitchField(W, H) + body + "</svg>");
        var dots = svg.querySelectorAll(".cn-pitch-dot");
        Array.prototype.forEach.call(dots, function (dot, i) {
          var m = data[i], p = pitchXY(m, W, H);
          if (opts.animate !== false) staggerIn(dot, i, data.length, "opacity", 0, 1, ".3s", 700);
          dot.addEventListener("mouseenter", function () {
            dot.classList.add("pulse");
            var rc = wrap.getBoundingClientRect();
            tip.show('<b>' + esc(m.over) + "</b> · " + esc(pOutcome(m)) +
              (m.length ? "<br>" + esc(m.length) + (m.line ? " · " + esc(m.line) : "") : "") +
              (m.bowler ? "<br>" + esc(m.bowler) : "") + (m.speed ? " · " + m.speed + " kph" : ""),
              (p.x / W) * rc.width, (p.y / H) * rc.height);
          });
          dot.addEventListener("mouseleave", function () { dot.classList.remove("pulse"); tip.hide(); });
        });
      }
      redraw(testFor(defs, opts.activeFilter));   // honour a preserved filter on (re)mount
      return wrap;
    },
  };

  window.CricWagon = CricWagon;
  window.CricPitch = CricPitch;
})();
