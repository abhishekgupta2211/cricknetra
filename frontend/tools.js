/* CricNetra — cricket tools: calculators, online toss, picker wheel.
   Pure client-side, no backend. Loaded only on /tools. */

(function () {
  "use strict";

  // ---- helpers --------------------------------------------------------------
  var $ = function (id) { return document.getElementById(id); };
  var num = function (id) { var v = parseFloat($(id) && $(id).value); return isNaN(v) ? null : v; };

  // Overs are entered as "overs.balls" (e.g. 12.3 = 12 overs 3 balls). Convert
  // to a decimal number of overs for arithmetic.
  function oversToDecimal(v) {
    if (v === null || v < 0) return null;
    var whole = Math.floor(v);
    var balls = Math.round((v - whole) * 10);
    if (balls > 5) { whole += 1; balls = 0; } // .6+ rolls to the next over
    return whole + balls / 6;
  }
  function oversToBalls(v) {
    var dec = oversToDecimal(v);
    return dec === null ? null : Math.round(dec * 6);
  }
  function setOut(id, text) { var el = $(id); if (el) el.textContent = text; }

  // ---- calculators ----------------------------------------------------------
  function calcRunRate() {
    var r = num("rr-runs"), o = oversToDecimal(num("rr-overs"));
    setOut("rr-out", (r !== null && o) ? (r / o).toFixed(2) : "—");
  }
  function calcRequiredRate() {
    var t = num("rrr-target"), s = num("rrr-score"), balls = oversToBalls(num("rrr-overs"));
    if (t === null || s === null || !balls) { setOut("rrr-out", "—"); setOut("rrr-note", ""); return; }
    var need = t - s;
    if (need <= 0) { setOut("rrr-out", "Won"); setOut("rrr-note", "Target already reached"); return; }
    setOut("rrr-out", ((need / balls) * 6).toFixed(2));
    setOut("rrr-note", "Need " + need + " off " + balls + (balls === 1 ? " ball" : " balls"));
  }
  function calcStrikeRate() {
    var r = num("sr-runs"), b = num("sr-balls");
    setOut("sr-out", (r !== null && b) ? ((r / b) * 100).toFixed(2) : "—");
  }
  function calcEconomy() {
    var r = num("eco-runs"), o = oversToDecimal(num("eco-overs"));
    setOut("eco-out", (r !== null && o) ? (r / o).toFixed(2) : "—");
  }
  function calcNRR() {
    var rf = num("nrr-rf"), of = oversToDecimal(num("nrr-of"));
    var ra = num("nrr-ra"), oa = oversToDecimal(num("nrr-oa"));
    if (rf === null || !of || ra === null || !oa) { setOut("nrr-out", "—"); return; }
    var nrr = (rf / of) - (ra / oa);
    setOut("nrr-out", (nrr >= 0 ? "+" : "") + nrr.toFixed(3));
  }

  function wire(ids, fn) {
    ids.forEach(function (id) {
      var el = $(id);
      if (el) el.addEventListener("input", fn);
    });
  }
  wire(["rr-runs", "rr-overs"], calcRunRate);
  wire(["rrr-target", "rrr-score", "rrr-overs"], calcRequiredRate);
  wire(["sr-runs", "sr-balls"], calcStrikeRate);
  wire(["eco-runs", "eco-overs"], calcEconomy);
  wire(["nrr-rf", "nrr-of", "nrr-ra", "nrr-oa"], calcNRR);

  // ---- online toss ----------------------------------------------------------
  var coin = $("coin"), tossBtn = $("tossBtn"), tossResult = $("tossResult");
  var tossSpin = 0, tossing = false;
  if (tossBtn) {
    tossBtn.addEventListener("click", function () {
      if (tossing) return;
      tossing = true;
      tossResult.textContent = "Flipping…";
      tossResult.className = "toss-result";
      var heads = Math.floor(Math.random() * 2) === 0;
      // Lots of half-turns, ending on the correct face (0deg = heads, 180 = tails).
      tossSpin += 360 * 5 + (heads ? 0 : 180);
      // normalise so it always lands clean on heads/tails
      tossSpin = Math.round(tossSpin / 180) * 180;
      coin.style.transform = "rotateY(" + tossSpin + "deg)";
      window.setTimeout(function () {
        tossResult.textContent = heads ? "Heads!" : "Tails!";
        tossResult.className = "toss-result show " + (heads ? "is-heads" : "is-tails");
        tossing = false;
      }, 1300);
    });
  }

  // ---- picker wheel ---------------------------------------------------------
  var canvas = $("wheelCanvas");
  if (canvas) {
    var ctx = canvas.getContext("2d");
    var SIZE = canvas.width, R = SIZE / 2;
    var PALETTE = ["#0e8a45", "#16a34a", "#0a6b34", "#22c55e", "#15803d", "#34d399",
                   "#047857", "#4ade80"];
    var options = [];
    var rotation = 0, spinning = false;
    var spinBtn = $("spinBtn"), wheelResult = $("wheelResult"), pendingWinner = null;

    function readOptions() {
      var raw = ($("wheelOptions").value || "").split("\n");
      options = raw.map(function (s) { return s.trim(); }).filter(Boolean).slice(0, 12);
      drawWheel();
      if (options.length < 2) wheelResult.textContent = "Add at least 2 options";
      else wheelResult.textContent = "Ready — press spin";
    }

    function drawWheel() {
      ctx.clearRect(0, 0, SIZE, SIZE);
      var n = options.length;
      if (n === 0) {
        ctx.fillStyle = "#e6ece8"; ctx.beginPath(); ctx.arc(R, R, R - 2, 0, 2 * Math.PI); ctx.fill();
        return;
      }
      var seg = (2 * Math.PI) / n;
      for (var i = 0; i < n; i++) {
        var a0 = i * seg, a1 = a0 + seg;
        ctx.beginPath(); ctx.moveTo(R, R); ctx.arc(R, R, R - 2, a0, a1); ctx.closePath();
        ctx.fillStyle = PALETTE[i % PALETTE.length]; ctx.fill();
        // label
        ctx.save();
        ctx.translate(R, R); ctx.rotate(a0 + seg / 2);
        ctx.textAlign = "right"; ctx.textBaseline = "middle";
        ctx.fillStyle = "#fff"; ctx.font = "700 14px Manrope, sans-serif";
        var label = options[i].length > 14 ? options[i].slice(0, 13) + "…" : options[i];
        ctx.fillText(label, R - 16, 0);
        ctx.restore();
      }
      // hub
      ctx.beginPath(); ctx.arc(R, R, 22, 0, 2 * Math.PI);
      ctx.fillStyle = "#fff"; ctx.fill();
      ctx.fillStyle = "#0e8a45"; ctx.font = "800 16px Manrope, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText("🏏", R, R + 1);
    }

    function settle() {
      if (pendingWinner === null) return; // already settled
      var w = pendingWinner;
      pendingWinner = null;
      spinning = false;
      wheelResult.innerHTML = "🎉 <b>" + escapeHtml(options[w]) + "</b>";
      wheelResult.className = "wheel-result show";
    }

    function spin() {
      var n = options.length;
      if (spinning || n < 2) return;
      spinning = true;
      wheelResult.textContent = "Spinning…";
      wheelResult.className = "wheel-result";
      var seg = 360 / n;
      var winner = Math.floor(Math.random() * n);
      pendingWinner = winner;
      // bring segment `winner` centre under the pointer at the top (270° in canvas
      // coords where 0°=right, +ve = clockwise). Add full turns for the spin.
      var target = 270 - (winner * seg + seg / 2);
      var base = Math.ceil(rotation / 360) * 360; // continue past current angle
      rotation = base + 360 * 6 + ((target % 360) + 360) % 360;
      canvas.style.transform = "rotate(" + rotation + "deg)";
      // Settle on transitionend, with a timer fallback in case the event is
      // missed (interrupted transition, or a renderer that doesn't fire it).
      window.setTimeout(settle, 4500);
    }

    // CSS transition is 4.2s; transitionend settles immediately when it fires.
    canvas.addEventListener("transitionend", settle);

    function escapeHtml(s) {
      return s.replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    }

    if (spinBtn) spinBtn.addEventListener("click", spin);
    var upd = $("wheelUpdate");
    if (upd) upd.addEventListener("click", readOptions);
    readOptions();
  }
})();
