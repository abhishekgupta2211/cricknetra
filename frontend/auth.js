/* CricNetra — standalone /login and /register pages.
   Calls the JSON API, stores the JWT under the same key the app reads
   (localStorage 'cn_token'), then redirects into the app. */

(function () {
  "use strict";
  var API = "/api/v1";
  var TOKEN_KEY = "cn_token";
  var REFRESH_KEY = "cn_refresh";
  var next = new URLSearchParams(location.search).get("next") || "/app";

  function val(id) { var el = document.getElementById(id); return el ? el.value : ""; }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function saveTokens(r) {
    if (r && r.access_token) localStorage.setItem(TOKEN_KEY, r.access_token);
    if (r && r.refresh_token) localStorage.setItem(REFRESH_KEY, r.refresh_token);
  }

  function msg(text, ok) {
    var el = document.getElementById("authMsg");
    if (!el) return;
    el.textContent = text;
    el.className = "auth-msg " + (ok ? "ok" : "err");
  }

  var FIELD_LABELS = {
    full_name: "Full name", username: "Username", mobile_no: "Mobile number",
    email: "Email", password: "Password", role: "Role", identifier: "Mobile or username",
  };
  // Turn a FastAPI error body into one readable sentence. `detail` is either a
  // string (our HTTPExceptions) or the 422 validation array [{loc,msg,…}] — which
  // must never be shown raw.
  function humanError(data, fallback) {
    var d = data ? (data.detail !== undefined ? data.detail : data.message) : null;
    if (typeof d === "string" && d) return d;
    if (Array.isArray(d) && d.length) {
      var parts = d.map(function (e) {
        var field = e && e.loc && e.loc[e.loc.length - 1];
        var label = FIELD_LABELS[field];
        var m = (e && e.msg) || "";
        if (/^Value error,/i.test(m)) return m.replace(/^Value error,\s*/i, "");  // custom: already names the field
        return label ? m.replace(/^String /, label + " ") : m;                     // built-in: name the field
      }).filter(Boolean);
      if (parts.length) return parts.join(". ");
    }
    if (d && d.msg) return String(d.msg).replace(/^Value error,\s*/i, "");
    return fallback || "Something went wrong — please try again.";
  }

  async function post(path, body) {
    var res = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    var data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw new Error(humanError(data, res.statusText));
    return data;
  }

  // ---- login ----
  var loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var btn = loginForm.querySelector("button");
      btn.disabled = true;
      try {
        var r = await post("/auth/login", { identifier: val("identifier").trim(), password: val("password") });
        saveTokens(r);
        location.href = next;
      } catch (err) { msg(err.message); btn.disabled = false; }
    });
  }

  // ---- password reset (login page) ----
  var loginPanel = document.getElementById("loginPanel");
  var resetPanel = document.getElementById("resetPanel");

  function clearMsg() {
    var el = document.getElementById("authMsg");
    if (el) { el.textContent = ""; el.className = "auth-msg"; }
  }
  function showReset(show) {
    if (loginPanel) loginPanel.hidden = show;
    if (resetPanel) resetPanel.hidden = !show;
    clearMsg();
  }
  var forgotLink = document.getElementById("forgotLink");
  if (forgotLink) forgotLink.addEventListener("click", function (e) { e.preventDefault(); showReset(true); });
  var backToLogin = document.getElementById("backToLogin");
  if (backToLogin) backToLogin.addEventListener("click", function (e) { e.preventDefault(); showReset(false); });

  var forgotForm = document.getElementById("forgotForm");
  if (forgotForm) {
    forgotForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var btn = forgotForm.querySelector("button");
      btn.disabled = true;
      try {
        var r = await post("/auth/password/forgot", { identifier: val("resetId").trim() });
        document.getElementById("resetForm").hidden = false;
        if (r && r.dev_token) {
          document.getElementById("resetToken").value = r.dev_token;
          msg("Reset code generated (dev) — it's pre-filled. Set a new password below.", true);
        } else {
          msg("If that account exists, a reset code has been sent. Enter it below.", true);
        }
      } catch (err) { msg(err.message); }
      finally { btn.disabled = false; }
    });
  }

  var resetForm = document.getElementById("resetForm");
  if (resetForm) {
    resetForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var btn = resetForm.querySelector("button");
      btn.disabled = true;
      try {
        await post("/auth/password/reset", { token: val("resetToken").trim(), new_password: val("resetPass") });
        showReset(false);
        msg("Password updated — sign in with your new password.", true);
      } catch (err) { msg(err.message); btn.disabled = false; }
    });
  }

  // ---- register (then auto-login) ----
  var registerForm = document.getElementById("registerForm");
  var APPROVAL_ROLES = ["team_owner", "organizer", "umpire", "commentator"];
  var roleSel = document.getElementById("role");
  var roleNote = document.getElementById("roleNote");
  if (roleSel && roleNote) {
    var syncNote = function () { roleNote.hidden = APPROVAL_ROLES.indexOf(roleSel.value) === -1; };
    roleSel.addEventListener("change", syncNote);
    syncNote();
  }
  if (registerForm) {
    registerForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var btn = registerForm.querySelector("button");
      btn.disabled = true;
      try {
        var reg = await post("/auth/register", {
          full_name: val("full_name").trim(),
          username: val("username").trim(),
          mobile_no: val("mobile_no").trim(),
          email: val("email").trim(),
          password: val("password"),
          role: val("role"),
        });
        var r = await post("/auth/login", { identifier: val("username").trim(), password: val("password") });
        saveTokens(r);
        if (reg && reg.role_pending) {
          var label = (reg.requested_role || "role").replace(/_/g, " ");
          msg("Account created! Your " + label + " access is awaiting admin approval — you're signed in as a general user for now.", true);
          setTimeout(function () { location.href = next; }, 2400);
        } else {
          location.href = next;
        }
      } catch (err) { msg(err.message); btn.disabled = false; }
    });
  }
})();
