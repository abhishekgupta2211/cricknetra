import { api } from "/js/api.js?v=97";

const view = document.getElementById("view");
const toastEl = document.getElementById("toast");
const backBtn = document.getElementById("backBtn");

const h = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
const nav = (hash) => (location.hash = hash);
// stable roster code from a player id (mirrors the backend "P00012"); a fallback
// for any cached data that predates the API `code` field.
const pcode = (id) => "P" + String(id).padStart(5, "0");

// ---- inline SVG icon set (Lucide-style line icons; replace ugly emojis) ----
const ICONS = {
  stumps: '<path d="M7 21V8"/><path d="M12 21V7.5"/><path d="M17 21V8"/><path d="M6.5 7.5h5"/><path d="M12.5 6.8h5"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  chart: '<path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="6" rx="1"/><rect x="12" y="7" width="3" height="10" rx="1"/><rect x="17" y="13" width="3" height="4" rx="1"/>',
  network: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  gavel: '<path d="m14.5 12.5-8 8a2.12 2.12 0 1 1-3-3l8-8"/><path d="m16 16 6-6"/><path d="m8 8 6-6"/><path d="m9 7 8 8"/><path d="m21 11-8-8"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>',
  phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.18 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z"/>',
  message: '<path d="M21 11.5a8.38 8.38 0 0 1-9 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.2A8.5 8.5 0 0 1 12 3a8.38 8.38 0 0 1 9 8.5Z"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
  cap: '<path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12v5c3 2.5 9 2.5 12 0v-5"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  search: '<circle cx="11" cy="11" r="7.5"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  swap: '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="M16 21l4-4-4-4"/><path d="M20 17H4"/>',
  star: '<polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V4s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="4"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  umbrella: '<path d="M12 2a10 10 0 0 1 10 10H2A10 10 0 0 1 12 2Z"/><path d="M12 12v7a2 2 0 0 0 4 0"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
  radio: '<circle cx="12" cy="12" r="2"/><path d="M4.9 19.1a10 10 0 0 1 0-14.2"/><path d="M7.8 16.2a6 6 0 0 1 0-8.4"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4"/><path d="M19.1 4.9a10 10 0 0 1 0 14.2"/>',
  share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  palette: '<circle cx="13.5" cy="6.5" r="1.3"/><circle cx="17.5" cy="10.5" r="1.3"/><circle cx="8.5" cy="7.5" r="1.3"/><circle cx="6.5" cy="12.5" r="1.3"/><path d="M12 2a10 10 0 0 0 0 20 2.5 2.5 0 0 0 2.5-2.5c0-.6-.2-1.1-.6-1.5a2.5 2.5 0 0 1 1.8-4.2H18a4 4 0 0 0 4-4A10 10 0 0 0 12 2z"/>',
};
function icon(name, cls) {
  return '<svg class="ico' + (cls ? " " + cls : "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || "") + "</svg>";
}

let toastTimer;
function toast(msg, kind) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  toastEl.style.background = kind === "error" ? "#c0303a" : "#1c2a24";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toastEl.hidden = true), 2800);
}

backBtn.addEventListener("click", () =>
  history.length > 1 ? history.back() : nav("#/")
);

// Mobile nav drawer — the desktop sidebar slides in from the ☰ button, so phones
// reach every section (Players, Venues, Rules, Leaderboards, Highlights, …) too.
const menuBtn = document.getElementById("menuBtn");
const navScrim = document.getElementById("navScrim");
function setNav(open) {
  document.body.classList.toggle("nav-open", open);
  if (menuBtn) menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
}
const closeNav = () => setNav(false);
if (menuBtn) menuBtn.addEventListener("click", () => setNav(!document.body.classList.contains("nav-open")));
if (navScrim) navScrim.addEventListener("click", closeNav);
// tapping any drawer link navigates — close behind it
document.getElementById("sidebar")?.addEventListener("click", (e) => {
  if (e.target.closest("a")) closeNav();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && document.body.classList.contains("nav-open")) closeNav();
});

const DISMISSALS = {
  bowled: "Bowled", caught: "Caught", caught_behind: "Caught behind",
  caught_and_bowled: "Caught & bowled", lbw: "LBW", run_out: "Run out",
  stumped: "Stumped", hit_wicket: "Hit wicket", retired_out: "Retired out",
  retired_hurt: "Retired hurt", obstructing_field: "Obstructing field",
  hit_ball_twice: "Hit ball twice", timed_out: "Timed out",
};

// colored initials avatar (consistent per name)
function avatar(name, cls = "") {
  const s = String(name || "?").trim();
  const initials = (s.split(/\s+/).map((w) => w[0]).join("").slice(0, 2) || "?").toUpperCase();
  let hash = 0;
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) % 360;
  const h2 = (hash + 38) % 360;
  return `<span class="avatar ${cls}" style="background:linear-gradient(135deg,hsl(${hash},58%,52%),hsl(${h2},58%,42%))">${h(initials)}</span>`;
}

// Bumped after any upload/remove so cached <img>s refresh on the next render.
let photoBust = Date.now();

// An avatar that shows the uploaded picture when one exists, else the initials.
// `hasPhoto` comes from the DTO; the onerror is a safety net (e.g. just-deleted).
function photoAvatar(kind, id, name, cls = "", hasPhoto = false) {
  if (!hasPhoto || id == null) return avatar(name, cls);
  const fb = avatar(name, cls).replace(/'/g, "&#39;");
  return `<img class="avatar avt-img ${cls}" src="${h(api.photoSrc(kind, id, photoBust))}" alt="${h(name)}"
    onerror="this.outerHTML=this.getAttribute('data-fb')" data-fb='${fb}'>`;
}

// highlight the active bottom-nav tab + hide the nav on the scoring screen
const NAV_TABS = [
  [/^#\/tournament/, "tournaments"],
  [/^#\/(teams|team\/)/, "teams"],
  [/^#\/(leaderboards|players|player\/)/, "stats"],
];
// Desktop sidebar has finer-grained items than the 4-tab bottom bar.
const SIDE_TABS = [
  [/^#\/(tournaments|tournament\/)/, "tournaments"],
  [/^#\/(teams|team\/)/, "teams"],
  [/^#\/(players|player\/)/, "players"],
  [/^#\/venues/, "venues"],
  [/^#\/rules/, "rules"],
  [/^#\/(leaderboards|compare)/, "leaderboards"],
  [/^#\/highlights/, "highlights"],
  [/^#\/feed/, "feed"],
  [/^#\/network/, "network"],
  [/^#\/search/, "search"],
  [/^#\/settings/, "settings"],
  [/^#\/admin/, "admin"],
];
function setChrome(hash) {
  closeNav();  // never leave the mobile drawer open across a route change
  const tab = (NAV_TABS.find(([re]) => re.test(hash)) || [null, "home"])[1];
  document.querySelectorAll(".navitem").forEach((n) => n.classList.toggle("active", n.dataset.tab === tab));
  const side = (SIDE_TABS.find(([re]) => re.test(hash)) || [null, "home"])[1];
  document.querySelectorAll(".side-link").forEach((a) => a.classList.toggle("active", a.dataset.side === side));
  document.body.classList.toggle("no-nav", /^#\/match\//.test(hash));
  document.body.classList.remove("narrow");  // new + rules now use a wide two-panel layout
}

// share a public, server-rendered page (native share sheet, or copy link)
async function share(path, title) {
  const url = location.origin + path;
  try {
    if (navigator.share) await navigator.share({ title, url });
    else { await navigator.clipboard.writeText(url); toast("Link copied ✓"); }
  } catch (e) { /* user dismissed the share sheet */ }
}

// --------------------------------------------------------------------------
// Auth state + login / register / account
// --------------------------------------------------------------------------
const auth = { user: null };
const PUBLIC_ROLES = [
  ["general_user", "General user"], ["player", "Player"], ["team_owner", "Team owner"],
  ["organizer", "Organizer"], ["umpire", "Umpire"], ["commentator", "Commentator"],
];
const CAP_LABEL = {
  "match.create": "Score matches", "match.score": "Officiate any match",
  "team.create": "Manage teams & players", "tournament.create": "Organize tournaments",
  "rules.manage": "Build rule templates",
};
const isAuthed = () => !!auth.user;
const can = (cap) => !!(auth.user && (auth.user.capabilities || []).includes(cap));

async function loadAuth() {
  if (!api.isAuthed()) { auth.user = null; return; }
  try { auth.user = await api.me(); } catch (e) { auth.user = null; api.logout(); }
}

function renderAuthChip() {
  const isAdmin = !!(auth.user && auth.user.role === "admin");
  document.querySelectorAll(".js-admin-link").forEach((el) => (el.hidden = !isAdmin));
  // A viewer can't start a match, so don't offer the shortcut into a screen
  // that would only show them a lock.
  const canScore = can("match.create");
  document.querySelectorAll(".navfab, .side-new").forEach((el) => (el.hidden = !canScore));
  document.querySelectorAll(".js-authchip").forEach((el) => {
    if (auth.user) {
      el.innerHTML = `${photoAvatar("user", auth.user.id, auth.user.full_name || auth.user.username, "avatar--sm", auth.user.has_photo)}<span class="ac-name">${h(auth.user.username)}</span>`;
      el.setAttribute("href", "#/account");
      el.classList.add("is-in");
    } else {
      el.innerHTML = "Sign in";
      el.setAttribute("href", "/login");  // the standalone split-screen auth page
      el.classList.remove("is-in");
    }
  });
}

// gate a create view: returns false (and renders a prompt) if not allowed
function gate(cap, what) {
  if (!isAuthed()) {
    view.innerHTML = `<div class="card empty"><span class="empty-ico">${icon("lock")}</span>Sign in to ${h(what)}.
      <div class="spacer"></div>
      <a class="btn btn--sm" href="/login">Sign in</a>
      <a class="btn btn--ghost btn--sm" href="/register" style="margin-left:8px">Create account</a></div>`;
    return false;
  }
  if (!can(cap)) {
    view.innerHTML = `<div class="card empty"><span class="empty-ico">${icon("ban")}</span>Your role (<b>${h(auth.user.role.replace(/_/g, " "))}</b>) can't ${h(what)}.<br>
      <span class="tiny muted">Ask an organizer or admin — or sign up with a different role.</span></div>`;
    return false;
  }
  return true;
}

const vv = (id) => (document.getElementById(id)?.value || "").trim();

// Login & register are the standalone /login and /register pages — a single auth
// experience. The router redirects the old #/login and #/register hashes there.

function profileForm(p) {
  p = p || {};
  return `
    <label>Address</label><input id="pf_address" value="${h(p.address || "")}" placeholder="House / street">
    <div class="row">
      <div><label>City</label><input id="pf_city" value="${h(p.city || "")}"></div>
      <div><label>Pincode</label><input id="pf_pincode" value="${h(p.pincode || "")}" inputmode="numeric" placeholder="6 digits"></div>
    </div>
    <div class="row">
      <div><label>District</label><input id="pf_district" value="${h(p.district || "")}"></div>
      <div><label>State</label><input id="pf_state" value="${h(p.state || "")}"></div>
    </div>
    <label>Region</label><input id="pf_region" value="${h(p.region || "")}" placeholder="e.g. North / South / East / West">`;
}

function profilePayload() {
  return {
    address: val("pf_address"), pincode: val("pf_pincode"), city: val("pf_city"),
    district: val("pf_district"), state: val("pf_state"), region: val("pf_region"),
  };
}

// Reusable picture uploader: a preview + "Upload/Change" + "Remove".
// For an existing entity (id known) it uploads immediately; for a not-yet-created
// one (id null) it previews locally and hands the File back via onLocalFile.
function photoEditorHtml({ kind, id, name, hasPhoto }) {
  const prev = hasPhoto && id != null
    ? `<img class="pe-img" src="${h(api.photoSrc(kind, id, photoBust))}" alt="">`
    : avatar(name || "?", "avatar--lg");
  return `<div class="photo-edit">
    <div class="pe-prev">${prev}</div>
    <div class="pe-actions">
      <button type="button" class="btn btn--ghost btn--sm pe-pick">${hasPhoto ? "Change photo" : "Upload photo"}</button>
      <button type="button" class="btn btn--ghost btn--sm pe-rm"${hasPhoto ? "" : " hidden"}>Remove</button>
      <span class="pe-hint">JPG, PNG, WEBP or GIF · up to 4 MB</span>
    </div>
    <input type="file" accept="image/*" class="pe-file" hidden>
  </div>`;
}

function bindPhotoEditor(root, { kind, name, getId, onLocalFile, onChanged }) {
  if (!root) return;
  const fileInp = root.querySelector(".pe-file");
  const pickBtn = root.querySelector(".pe-pick");
  const rmBtn = root.querySelector(".pe-rm");
  const prev = root.querySelector(".pe-prev");
  pickBtn.onclick = () => fileInp.click();
  fileInp.onchange = async () => {
    const f = fileInp.files && fileInp.files[0];
    if (!f) return;
    if (!/^image\//.test(f.type)) return toast("Please choose an image file", "error");
    if (f.size > 4 * 1024 * 1024) return toast("Image too large — keep it under 4 MB", "error");
    prev.innerHTML = `<img class="pe-img" src="${URL.createObjectURL(f)}" alt="">`;  // instant preview
    pickBtn.textContent = "Change photo";
    rmBtn.hidden = false;
    const id = getId && getId();
    if (id != null) {
      try { await api.uploadPhoto(kind, id, f); photoBust = Date.now(); toast("Photo updated ✓"); onChanged && onChanged(true); }
      catch (e) { toast(e.message, "error"); }
    } else {
      onLocalFile && onLocalFile(f);  // defer until the entity is created
    }
  };
  if (rmBtn) rmBtn.onclick = async () => {
    const id = getId && getId();
    if (id != null) {
      try { await api.deletePhoto(kind, id); photoBust = Date.now(); toast("Photo removed"); onChanged && onChanged(false); }
      catch (e) { return toast(e.message, "error"); }
    }
    fileInp.value = "";
    prev.innerHTML = avatar(name || "?", "avatar--lg");
    pickBtn.textContent = "Upload photo";
    rmBtn.hidden = true;
    onLocalFile && onLocalFile(null);
  };
}

async function renderAccount() {
  if (!auth.user) { location.href = "/login"; return; }
  const u = auth.user;
  const caps = (u.capabilities || []).map((c) => `<span class="cap-chip">✓ ${h(CAP_LABEL[c] || c)}</span>`).join("");
  const r = u.records || {};
  view.innerHTML = `
    <h2>My account</h2>
    <div id="officReqs"></div>
    ${u.role_pending ? `<div class="card prof-todo"><b>⏳ ${h((u.requested_role || "").replace(/_/g, " "))} role pending</b>
      <div class="tiny muted" style="margin-top:2px">An admin needs to approve this. Until then you're a general user (view-only).</div></div>` : ""}
    ${!u.is_verified ? `<div class="card prof-todo" id="verifyCard">
      <b>${icon("phone")} Verify your mobile</b>
      <div class="tiny muted" style="margin-top:2px">Confirm your number to secure your account.</div>
      <div class="spacer"></div>
      <div id="verifyBody"><button class="btn btn--sm" id="vSend">Send code</button></div>
    </div>` : ""}
    <div class="card">
      <div class="acct"><span id="acctHero">${photoAvatar("user", u.id, u.full_name || u.username, "avatar--lg", u.has_photo)}</span>
        <div><b>${h(u.full_name)}</b>
          <div class="tiny muted">@${h(u.username)} · ${h(u.role.replace(/_/g, " "))}</div>
          <div class="tiny muted">${h(u.user_code)} · ${icon("phone", "rec-ico")}${h(u.mobile_no)}</div></div></div>
      <div class="section-title" style="margin-top:16px">Email <span class="tiny muted">· where your codes are sent</span></div>
      <div class="addrow"><input id="emailInput" type="email" autocomplete="email" placeholder="you@example.com" value="${h(u.email || "")}"><button class="btn btn--sm" id="emailSave">Save</button></div>
      <div class="tiny muted" id="emailHint" style="margin-top:6px">${u.email ? "Verification &amp; reset codes go to your email." : "Add an email to get codes by email instead of SMS."}</div>
      <div class="section-title" style="margin-top:16px">Profile picture</div>
      ${photoEditorHtml({ kind: "user", id: u.id, name: u.full_name || u.username, hasPhoto: u.has_photo })}
      <div class="section-title" style="margin-top:16px">My records</div>
      <div class="record">
        <div class="stat"><div class="stat__v">${r.matches_scored || 0}</div><div class="stat__k">Matches</div></div>
        <div class="stat"><div class="stat__v">${r.matches_umpired || 0}</div><div class="stat__k">Umpired</div></div>
        <div class="stat"><div class="stat__v">${r.matches_commentated || 0}</div><div class="stat__k">Commentated</div></div>
        <div class="stat"><div class="stat__v">${r.tournaments_organized || 0}</div><div class="stat__k">Cups</div></div>
        <div class="stat"><div class="stat__v">${r.teams_owned || 0}</div><div class="stat__k">Teams</div></div>
      </div>
      <div class="section-title" style="margin-top:16px">What your role can do</div>
      <div class="caps">${caps || '<span class="tiny muted">View-only access — you can browse everything.</span>'}</div>
      <div class="spacer"></div>
      <a class="btn btn--ghost" href="#/settings" style="margin-bottom:8px">${icon("settings")} Settings &amp; theme</a>
      <button class="btn btn--ghost" id="logoutBtn">Log out</button>
    </div>
    <div id="claimBox"></div>
    <div id="profileBox"><div class="card"><div class="empty">Loading profile…</div></div></div>`;
  document.getElementById("logoutBtn").onclick = () => {
    api.logout(); auth.user = null; stopNotifStream(); clearNotifCache(); setUnreadBadge(0);
    renderAuthChip(); toast("Logged out"); nav("#/");
  };
  bindPhotoEditor(view.querySelector(".photo-edit"), {
    kind: "user", name: u.full_name || u.username, getId: () => u.id,
    onChanged: (has) => {
      u.has_photo = has;
      if (auth.user) auth.user.has_photo = has;
      const hero = document.getElementById("acctHero");
      if (hero) hero.innerHTML = photoAvatar("user", u.id, u.full_name || u.username, "avatar--lg", has);
      renderAuthChip();  // reflect the new picture in the top-bar account chip
    },
  });

  const emailSave = document.getElementById("emailSave");
  if (emailSave) emailSave.onclick = async () => {
    const email = val("emailInput");
    if (!email) { toast("Enter an email", "error"); return; }
    emailSave.disabled = true;
    try {
      const updated = await api.setEmail(email);
      u.email = updated.email;
      if (auth.user) auth.user.email = updated.email;
      const hint = document.getElementById("emailHint");
      if (hint) hint.textContent = "Verification & reset codes go to your email.";
      toast("Email saved ✓");
    } catch (e) { toast(e.message, "error"); }
    emailSave.disabled = false;
  };

  const vSend = document.getElementById("vSend");
  if (vSend) vSend.onclick = async () => {
    vSend.disabled = true;
    try {
      const r = await api.requestVerify();
      const body = document.getElementById("verifyBody");
      body.innerHTML = `<div class="addrow"><input id="vCode" inputmode="numeric" maxlength="6" placeholder="6-digit code"><button class="btn btn--sm" id="vConfirm">Confirm</button></div>
        <div class="tiny muted" style="margin-top:6px">${r.dev_code ? `Dev code: <b>${h(r.dev_code)}</b> (no SMS provider wired yet)` : "Code sent to your mobile."}</div>`;
      document.getElementById("vConfirm").onclick = async () => {
        try {
          await api.confirmVerify(val("vCode"));
          toast("Mobile verified ✓");
          u.is_verified = true;
          if (auth.user) auth.user.is_verified = true;
          renderAccount();
        } catch (e) { toast(e.message, "error"); }
      };
      document.getElementById("vCode").focus();
    } catch (e) { toast(e.message, "error"); vSend.disabled = false; }
  };

  const profile = await api.myProfile().catch(() => null);  // 404 → not completed yet
  paintProfile(profile, !profile);
  loadClaim();
  loadOfficiatingRequests("officReqs");

  // claimed roster players + claimable suggestions (the unverified-stub → account model)
  async function loadClaim() {
    const box = document.getElementById("claimBox");
    if (!box) return;
    let mine = [], claimable = [];
    try { [mine, claimable] = await Promise.all([api.myPlayers(), api.claimablePlayers().catch(() => [])]); }
    catch (e) { box.innerHTML = ""; return; }
    if (!mine.length && !claimable.length) { box.innerHTML = ""; return; }
    const row = (p, claimed) => `<div class="matchitem">${photoAvatar("player", p.id, p.name, "", p.has_photo)}
      <a class="mi-main" href="#/player/${h(p.id)}"><b>${h(p.name)}</b><div class="tiny muted">${h(p.code)}${p.batting_style ? " · " + h(p.batting_style) : ""}</div></a>
      ${claimed ? `<span class="badge">✓ yours</span>` : `<button class="btn btn--sm claim-btn" data-id="${h(p.id)}">Claim</button>`}</div>`;
    box.innerHTML = `<div class="section-title">${icon("stumps")} Your cricket profiles</div><div class="card">
      ${mine.map((p) => row(p, true)).join("")}
      ${claimable.length ? `<div class="tiny muted" style="margin:${mine.length ? "10px" : "0"} 4px 6px">These roster profiles match your number — claim the ones that are you:</div>
        ${u.is_verified ? claimable.map((p) => row(p, false)).join("") : `<div class="tiny muted">Verify your mobile (above) to claim them.</div>`}` : ""}
      ${!mine.length && !claimable.length ? `<div class="empty tiny">No linked player profiles yet.</div>` : ""}</div>`;
    box.querySelectorAll(".claim-btn").forEach((b) => (b.onclick = async () => {
      b.disabled = true;
      try { await api.claimPlayer(b.dataset.id); toast("Profile claimed ✓"); loadClaim(); }
      catch (e) { toast(e.message, "error"); b.disabled = false; }
    }));
  }

  function paintProfile(p, editing) {
    const box = document.getElementById("profileBox");
    if (!box) return;
    if (p && !editing) {
      const cell = (k, v) => `<div><span class="tiny muted">${k}</span><div>${h(v || "—")}</div></div>`;
      box.innerHTML = `<div class="card">
        <div class="between"><div class="section-title" style="margin:0">Profile</div><span class="badge">✓ complete</span></div>
        <div class="prof-grid">
          ${cell("Address", p.address)}${cell("City", p.city)}${cell("Pincode", p.pincode)}
          ${cell("District", p.district)}${cell("State", p.state)}${cell("Region", p.region)}
        </div>
        <div class="spacer"></div>
        <button class="btn btn--ghost btn--sm" id="pfEdit">Edit profile</button>
      </div>`;
      document.getElementById("pfEdit").onclick = () => paintProfile(p, true);
    } else {
      box.innerHTML = `<div class="card${p ? "" : " prof-todo"}">
        <div class="section-title" style="margin-top:0">${p ? "Edit profile" : icon("alert") + " Complete your profile"}</div>
        ${p ? "" : `<p class="tiny muted" style="margin:-6px 0 4px">Add your location so teammates and organizers can find you.</p>`}
        ${profileForm(p)}
        <div class="spacer"></div>
        <button class="btn" id="pfSave">${p ? "Save changes" : "Save profile"}</button>
        ${p ? `<button class="btn btn--ghost btn--sm" id="pfCancel" style="margin-top:8px">Cancel</button>` : ""}
      </div>`;
      const cancel = document.getElementById("pfCancel");
      if (cancel) cancel.onclick = () => paintProfile(p, false);
      document.getElementById("pfSave").onclick = async (ev) => {
        const body = profilePayload();
        if (Object.values(body).some((v) => !v)) return toast("Please fill in every field", "error");
        ev.target.disabled = true;
        try {
          const saved = p ? await api.updateProfile(body) : await api.completeProfile(body);
          toast("Profile saved ✓");
          paintProfile(saved, false);
        } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
      };
    }
  }
}

// --------------------------------------------------------------------------
// Network directory — members by role + teams
// --------------------------------------------------------------------------
const NET_TABS = [
  ["player", "Players"], ["umpire", "Umpires"], ["commentator", "Commentators"],
  ["organizer", "Organizers"], ["team_owner", "Team owners"], ["__teams", "Teams"],
];

// the record most relevant to a member's role (their "states")
function recordLine(u) {
  const r = u.records || {};
  switch (u.role) {
    case "umpire": return `${icon("gavel", "rec-ico")}${r.matches_umpired || 0} matches officiated`;
    case "commentator": return `${icon("mic", "rec-ico")}${r.matches_commentated || 0} commentated`;
    case "organizer": return `${icon("trophy", "rec-ico")}${r.tournaments_organized || 0} tournaments organized`;
    case "team_owner": return `${icon("users", "rec-ico")}${r.teams_owned || 0} teams`;
    default: return `${icon("stumps", "rec-ico")}${r.matches_scored || 0} matches scored`;
  }
}

async function renderNetwork() {
  if (!isAuthed()) {
    view.innerHTML = `<h2>Network</h2>
      <div class="card empty"><span class="empty-ico">${icon("lock")}</span>Sign in to browse players, umpires, commentators &amp; teams.
        <div class="spacer"></div>
        <a class="btn btn--sm" href="/login">Sign in</a>
        <a class="btn btn--ghost btn--sm" href="/register" style="margin-left:8px">Create account</a></div>`;
    return;
  }
  view.innerHTML = `
    <h2>Network</h2>
    <div class="net-actions">
      <a class="btn btn--ghost btn--sm" href="#/looking-for">${icon("megaphone")} Looking For board</a>
      <a class="btn btn--ghost btn--sm" href="#/messages">${icon("message")} Messages</a>
    </div>
    <div class="netseg" id="netSeg">
      ${NET_TABS.map(([r, l], i) => `<button data-r="${r}"${i === 0 ? ' class="active"' : ""}>${l}</button>`).join("")}
    </div>
    <div class="card" id="netList"><div class="empty">Loading…</div></div>`;
  const seg = document.getElementById("netSeg");
  const listEl = document.getElementById("netList");
  const labelFor = (r) => (NET_TABS.find(([rr]) => rr === r) || [, "members"])[1];
  let following = new Set();  // who the viewer already follows (to label buttons)

  let loadSeq = 0;
  async function load(r) {
    const seq = ++loadSeq; // ignore a stale response if a newer tab was clicked
    listEl.innerHTML = `<div class="empty">Loading…</div>`;
    try {
      let html;
      if (r === "__teams") {
        const teams = await api.teams();
        html = teams.length
          ? teams.map((t) => `<a class="matchitem" href="#/team/${h(t.id)}">${photoAvatar("team", t.id, t.name, "", t.has_photo)}
              <div class="mi-main"><b>${h(t.name)}</b><div class="tiny muted">${t.members.length} player${t.members.length === 1 ? "" : "s"}${t.location ? " · " + h(t.location) : ""}</div></div>
              <span class="badge badge--grey">open ›</span></a>`).join("")
          : `<div class="empty">No teams yet.</div>`;
      } else {
        const users = await api.users(r);
        html = users.length
          ? users.map((u) => `<div class="matchitem">${photoAvatar("user", u.id, u.full_name || u.username, "", u.has_photo)}
              <div class="mi-main"><b>${h(u.full_name)}</b>${u.is_verified ? ` <span class="verified" title="Verified">✓</span>` : ""}
                <div class="tiny muted">@${h(u.username)}${u.location ? " · " + h(u.location) : ""}</div>
                <div class="net-rec">${recordLine(u)}</div></div>
              ${String(u.id) !== String((auth.user || {}).id) ? `<button class="btn btn--sm follow-btn${following.has(String(u.id)) ? " is-following" : ""}" data-uid="${h(u.id)}">${following.has(String(u.id)) ? "Following" : "Follow"}</button>` : ""}
              ${String(u.id) !== String((auth.user || {}).id) ? `<a class="badge net-msg" href="#/messages/${h(u.id)}" title="Message ${h(u.full_name)}">${icon("message")}</a>` : ""}
              ${u.mobile_no ? `<a class="badge net-call" href="tel:${h(u.mobile_no)}" title="Call ${h(u.full_name)}">${icon("phone")}</a>` : ""}</div>`).join("")
          : `<div class="empty">No ${h(labelFor(r).toLowerCase())} registered yet.</div>`;
      }
      if (seq === loadSeq) {
        listEl.innerHTML = html;
        listEl.querySelectorAll(".follow-btn").forEach((b) => (b.onclick = async () => {
          const uid = b.dataset.uid, add = !following.has(String(uid));
          b.disabled = true;
          try {
            if (add) { await api.follow(uid); following.add(String(uid)); }
            else { await api.unfollow(uid); following.delete(String(uid)); }
            b.classList.toggle("is-following", add);
            b.textContent = add ? "Following" : "Follow";
          } catch (e) { toast(e.message, "error"); }
          finally { b.disabled = false; }
        }));
      }
    } catch (e) {
      if (seq === loadSeq) listEl.innerHTML = `<div class="empty">${h(e.message)}</div>`;
    }
  }
  seg.querySelectorAll("button").forEach((b) => (b.onclick = () => {
    seg.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
    load(b.dataset.r);
  }));
  try { following = new Set((await api.myFollowing()).map(String)); } catch (e) { /* not signed in */ }
  load("player");
}

// --------------------------------------------------------------------------
// Community / social — feed + notifications
// --------------------------------------------------------------------------
const ACT_ICO = { match: icon("stumps"), tournament: icon("trophy"), team: icon("users") };

function timeago(iso) {
  const t = Date.parse(iso);
  if (isNaN(t)) return "";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}

function signInCard(what) {
  return `<div class="card empty"><span class="empty-ico">${icon("lock")}</span>Sign in to ${h(what)}.
    <div class="spacer"></div><a class="btn btn--sm" href="/login">Sign in</a></div>`;
}

function setUnreadBadge(n) {
  document.querySelectorAll(".js-notif-badge").forEach((b) => {
    b.textContent = n > 99 ? "99+" : n;
    b.hidden = !n;
  });
}

// Realtime notification badge — a per-user SSE stream pushes the unread count the
// instant a notification lands (falls back to a 20s poll where EventSource is absent).
let notifES = null, notifPoll = null;
let notifPrefsCache = null;             // cached prefs for the sound / quiet-hours gate
let _lastUnread = 0, _notifPrimed = false;
// Handle a fresh (unread, latest) tick from the SSE gate: chime on an increase.
function onNotifTick(unread) {
  if (typeof unread !== "number") return;
  if (_notifPrimed && unread > _lastUnread) maybeChime();
  _lastUnread = unread; _notifPrimed = true;
  setUnreadBadge(unread);
}
function startNotifStream() {
  stopNotifStream();
  if (!isAuthed()) return;
  _notifPrimed = false;
  api.notifPrefs().then((p) => { notifPrefsCache = p; }).catch(() => {});
  api.unreadCount().then((r) => { _lastUnread = r.count; _notifPrimed = true; setUnreadBadge(r.count); }).catch(() => {});
  if (window.EventSource) {
    try {
      notifES = new EventSource(api.notifStreamUrl());
      notifES.onmessage = (e) => {
        try { const d = JSON.parse(e.data); onNotifTick(d.unread); } catch (_) {}
      };
      notifES.onerror = () => {
        if (notifES) { notifES.close(); notifES = null; }
        if (isAuthed()) setTimeout(startNotifStream, 5000);   // controlled reconnect (fresh token)
      };
      return;
    } catch (_) { notifES = null; }
  }
  notifPoll = setInterval(() => {
    if (!isAuthed()) return stopNotifStream();
    api.unreadCount().then((r) => onNotifTick(r.count)).catch(() => {});
  }, 20000);
}
function stopNotifStream() {
  if (notifES) { notifES.close(); notifES = null; }
  if (notifPoll) { clearInterval(notifPoll); notifPoll = null; }
}
// Drop the offline-cached notifications list (so it can't leak across a user switch).
function clearNotifCache() {
  notifPrefsCache = null; _lastUnread = 0; _notifPrimed = false;
  if (!("caches" in window)) return;
  caches.keys().then((keys) => keys.forEach((k) =>
    caches.open(k).then((c) => c.delete("/api/v1/social/notifications")).catch(() => {}))).catch(() => {});
}

// ---- notification sound (a short WebAudio chime; no asset needed) ----
let _audioCtx = null, _lastChime = 0;
function clientInQuietHours(p) {
  if (!p) return false;
  const qs = p.quiet_start, qe = p.quiet_end;
  if (qs == null || qe == null || qs === qe) return false;
  const hr = new Date().getHours();     // the browser already knows local time
  return qs < qe ? (hr >= qs && hr < qe) : (hr >= qs || hr < qe);
}
function maybeChime() {
  const p = notifPrefsCache;
  if (p && p.sound === false) return;                       // muted by preference
  if (clientInQuietHours(p)) return;                        // do not disturb
  if (location.hash.startsWith("#/notifications")) return;  // you're already looking at them
  const now = Date.now();
  if (now - _lastChime < 4000) return;                      // throttle bursts
  _lastChime = now;
  playNotifChime();
}
function playNotifChime() {
  try {
    _audioCtx = _audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (_audioCtx.state === "suspended") _audioCtx.resume();
    const t = _audioCtx.currentTime;
    const o = _audioCtx.createOscillator(), g = _audioCtx.createGain();
    o.type = "sine";
    o.frequency.setValueAtTime(880, t);          // a two-note "ding-ding"
    o.frequency.setValueAtTime(1175, t + 0.09);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.14, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.33);
    o.connect(g).connect(_audioCtx.destination);
    o.start(t); o.stop(t + 0.35);
  } catch (_) { /* audio not available */ }
}

// ---- Web Push --------------------------------------------------------------
function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}
// VAPID app-server key is base64url; PushManager wants a Uint8Array.
function urlB64ToUint8Array(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}
// Ask permission (if needed), subscribe this browser, register it server-side.
// Throws with a user-friendly message so the caller can revert the toggle.
async function subscribeToPush() {
  if (!pushSupported()) throw new Error("This browser doesn't support push notifications");
  let perm = Notification.permission;
  if (perm === "default") perm = await Notification.requestPermission();
  if (perm !== "granted") throw new Error("Notifications are blocked — allow them in your browser settings");
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    const { key, available } = await api.vapidKey();
    if (!available || !key) throw new Error("Push isn't configured on the server yet");
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(key) });
  }
  const j = sub.toJSON();
  await api.pushSubscribe({ endpoint: sub.endpoint, keys: { p256dh: j.keys.p256dh, auth: j.keys.auth }, platform: "web" });
  return true;
}
// Drop this browser's subscription (locally + server-side). Best-effort.
async function unsubscribeFromPush() {
  if (!pushSupported()) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await api.pushUnsubscribe(sub.endpoint).catch(() => {});
      await sub.unsubscribe().catch(() => {});
    }
  } catch (_) { /* best-effort */ }
}
// Boot: if the user wants push and already granted permission, silently make sure
// this device is registered (cheap upsert — covers new devices / rotated endpoints).
async function syncPushOnBoot() {
  if (!isAuthed() || !pushSupported() || Notification.permission !== "granted") return;
  try {
    const prefs = await api.notifPrefs();
    if (prefs.push_enabled) await subscribeToPush();
  } catch (_) { /* non-fatal */ }
}

// Follow button for a non-user entity (team|player|tournament|match). Renders a
// placeholder that bindFollowBtns() fills once the current follow-state is known.
function followBtnHtml(type, id) {
  return `<button class="btn btn--sm js-follow-ent" data-etype="${h(type)}" data-eid="${h(id)}" hidden>Follow</button>`;
}
function paintFollow(btn, following) {
  btn.dataset.following = following ? "1" : "0";
  btn.textContent = following ? "✓ Following" : "＋ Follow";
  btn.classList.toggle("btn--ghost", following);
}
async function bindFollowBtns(root) {
  const btns = [...(root || document).querySelectorAll(".js-follow-ent:not([data-bound])")];
  for (const btn of btns) {
    btn.dataset.bound = "1";
    if (!isAuthed()) { btn.hidden = true; continue; }
    const type = btn.dataset.etype, id = btn.dataset.eid;
    try {
      paintFollow(btn, (await api.entityFollowState(type, id)).is_following);
      btn.hidden = false;
    } catch (_) { btn.hidden = true; continue; }
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        const st = btn.dataset.following === "1"
          ? await api.unfollowEntity(type, id) : await api.followEntity(type, id);
        paintFollow(btn, st.is_following);
        toast(st.is_following ? "You'll get updates" : "Unfollowed");
      } catch (e) { toast(e.message || "Couldn't update", "error"); }
      btn.disabled = false;
    };
  }
}

async function renderFeed() {
  if (!isAuthed()) { view.innerHTML = `<h2>Feed</h2>${signInCard("see your feed")}`; return; }
  view.innerHTML = `<h2>Feed</h2><p class="tiny muted" style="margin:-8px 0 12px">Matches, tournaments &amp; teams from the people you follow.</p>
    <div class="card" id="feedList"><div class="empty">Loading…</div></div>`;
  const row = (a) => {
    const body = `${avatar(a.actor_name)}<div class="mi-main"><div><b>${h(a.actor_name)}</b> ${h(a.text)}</div>
      <div class="tiny muted">${ACT_ICO[a.kind] || "•"} ${h(timeago(a.when))}</div></div>`;
    return a.link ? `<a class="matchitem" href="${h(a.link)}">${body}</a>` : `<div class="matchitem">${body}</div>`;
  };
  try {
    const items = await api.feed();
    document.getElementById("feedList").innerHTML = items.length
      ? items.map(row).join("")
      : `<div class="empty">Your feed is quiet.<br><a href="#/network">Follow players & organizers</a> to see their cricket here.</div>`;
  } catch (e) { document.getElementById("feedList").innerHTML = `<div class="empty">${h(e.message)}</div>`; }
}

// Notifications: delete with a 5-second deferred-commit undo. We don't hit the
// API until the window passes (or the user leaves the page — see
// flushNotifDeletes), so "Undo" is instant and never touches the server.
const pendingNotifDeletes = new Map();  // id -> timeout handle
let notifById = {};                     // id -> notification, to rebuild a row on undo

// Notification categories → an emoji + label, used for per-row icons and the
// grouped notification center. Keeps in sync with the backend category set.
const NOTIF_CATS = [
  ["match", "🏏", "Matches"], ["tournament", "🏆", "Tournaments"], ["team", "🛡️", "Teams"],
  ["player", "🧢", "Players"], ["social", "👥", "Social"], ["achievement", "🏅", "Achievements"],
  ["system", "⚙️", "System"], ["admin", "🛠️", "Admin"], ["marketing", "📣", "Tips & offers"],
];
const NOTIF_CAT_BY = Object.fromEntries(NOTIF_CATS.map(([k, e, l]) => [k, { emoji: e, label: l }]));
function notifCat(cat) { return NOTIF_CAT_BY[cat] || { emoji: "🔔", label: "Other" }; }

function notifRowInner(n) {
  const c = notifCat(n.category);
  const cnt = n.count > 1 ? `<span class="ntf-count" title="${n.count} updates">×${n.count}</span>` : "";
  const inner = `<div class="ntf-ico${n.is_read ? "" : " unread"}" aria-hidden="true">${c.emoji}</div>
    <div class="mi-main"><div>${h(n.text)}${cnt}</div><div class="tiny muted">${h(timeago(n.when))}</div></div>`;
  const link = n.link
    ? `<a class="ntf-link" href="${h(n.link)}">${inner}</a>`
    : `<div class="ntf-link">${inner}</div>`;
  return `${link}<button class="ntf-del" data-del="${h(n.id)}" title="Delete notification" aria-label="Delete notification">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg></button>`;
}

function notifRowHtml(n) {
  return `<div class="matchitem ntf-row" data-id="${h(n.id)}">${notifRowInner(n)}</div>`;
}

// Group notifications by category under labelled headers (unread count per group).
function groupedNotifsHtml(items) {
  const by = new Map();
  items.forEach((n) => {
    const k = NOTIF_CAT_BY[n.category] ? n.category : "other";
    (by.get(k) || by.set(k, []).get(k)).push(n);
  });
  const order = [...NOTIF_CATS.map((c) => c[0]), "other"].filter((k) => by.has(k));
  return order.map((k) => {
    const rows = by.get(k), c = notifCat(k);
    const unread = rows.filter((r) => !r.is_read).length;
    return `<div class="ntf-group"><div class="ntf-group-h"><span>${c.emoji} ${h(c.label)}</span>${
      unread ? `<span class="ntf-group-n">${unread}</span>` : ""}</div>${rows.map(notifRowHtml).join("")}</div>`;
  }).join("");
}

// ---- Category filter chips (shared by the bell dropdown + the notification centre) ----
function catKey(n) { return NOTIF_CAT_BY[n.category] ? n.category : "other"; }
function catChipsHtml(items, active) {
  const present = new Set(items.map(catKey));
  const chips = [["all", "🔔", "All"], ...NOTIF_CATS.filter((c) => present.has(c[0]))];
  if (present.has("other")) chips.push(["other", "🔔", "Other"]);
  return chips.map(([k, e, l]) => {
    const n = k === "all" ? items.length : items.filter((x) => catKey(x) === k).length;
    return `<button class="cat-chip${active === k ? " active" : ""}" data-cat="${h(k)}">${e} ${h(l)}${n ? ` <span class="cat-chip__n">${n}</span>` : ""}</button>`;
  }).join("");
}
function filterByCat(items, cat) { return cat === "all" ? items : items.filter((n) => catKey(n) === cat); }

// ---- Bell dropdown: a quick popover of recent notifications with a category filter ----
let _npItems = [], _npFilter = "all";
function npRowHtml(n) {
  const c = notifCat(n.category);
  const cnt = n.count > 1 ? `<span class="ntf-count">×${n.count}</span>` : "";
  const inner = `<div class="ntf-ico${n.is_read ? "" : " unread"}" aria-hidden="true">${c.emoji}</div>
    <div class="mi-main"><div>${n.title ? `<b>${h(n.title)}</b> ` : ""}${h(n.text)}${cnt}</div>
      <div class="tiny muted">${h(timeago(n.when))}</div></div>`;
  return n.link
    ? `<a class="matchitem np-row" data-id="${h(n.id)}" href="${h(n.link)}">${inner}</a>`
    : `<div class="matchitem np-row" data-id="${h(n.id)}">${inner}</div>`;
}
function ensureNotifPop() {
  if (document.getElementById("notifPop")) return;
  const bk = document.createElement("div");
  bk.className = "notif-pop__bk"; bk.id = "notifPopBk"; bk.hidden = true; bk.onclick = closeNotifPop;
  const pop = document.createElement("div");
  pop.className = "notif-pop"; pop.id = "notifPop"; pop.hidden = true;
  pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Notifications");
  pop.innerHTML = `<div class="notif-pop__head"><b>Notifications</b><a class="tiny np-all" href="#/notifications">See all →</a></div>
    <div class="cat-chips" id="npFilters"></div>
    <div class="notif-pop__list" id="npList"><div class="empty">Loading…</div></div>`;
  document.body.append(bk, pop);
  document.getElementById("npFilters").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-cat]");
    if (chip) { _npFilter = chip.dataset.cat; renderNpList(); }
  });
  document.getElementById("npList").addEventListener("click", (e) => {
    const row = e.target.closest("a.np-row");    // record the click for CTR; hashchange closes the pop
    if (row && row.dataset.id) api.markNotifClicked(row.dataset.id).catch(() => {});
  });
  window.addEventListener("hashchange", closeNotifPop);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeNotifPop(); });
}
function renderNpList() {
  document.getElementById("npFilters").innerHTML = catChipsHtml(_npItems, _npFilter);
  const items = filterByCat(_npItems, _npFilter);
  document.getElementById("npList").innerHTML = items.length
    ? items.map(npRowHtml).join("") : `<div class="empty">Nothing here.</div>`;
}
async function openNotifPop() {
  ensureNotifPop();
  document.getElementById("notifPopBk").hidden = false;
  document.getElementById("notifPop").hidden = false;
  _npFilter = "all";
  document.getElementById("npList").innerHTML = `<div class="empty">Loading…</div>`;
  try { _npItems = await api.notifications(); } catch (_) { _npItems = []; }
  renderNpList();
  api.markNotifsRead().then(() => setUnreadBadge(0)).catch(() => {});  // opening clears the badge
}
function closeNotifPop() {
  const pop = document.getElementById("notifPop"), bk = document.getElementById("notifPopBk");
  if (pop) pop.hidden = true;
  if (bk) bk.hidden = true;
}
function toggleNotifPop() {
  const pop = document.getElementById("notifPop");
  if (pop && !pop.hidden) closeNotifPop(); else openNotifPop();
}
// the header bells open the popover for signed-in users (else fall through to the page)
document.addEventListener("click", (e) => {
  const bell = e.target.closest(".js-notif-bell");
  if (bell && isAuthed()) { e.preventDefault(); toggleNotifPop(); }
});

function notifRow(id) {
  const list = document.getElementById("notifList");
  return list && list.querySelector(`.ntf-row[data-id="${CSS.escape(String(id))}"]`);
}

function startNotifUndo(id) {
  const rowEl = notifRow(id);
  if (!rowEl) return;
  rowEl.classList.add("is-undo");
  rowEl.innerHTML = `<div class="ntf-undo-main"><span>Notification deleted</span><span class="ntf-bar"></span></div>
    <button class="btn-undo" data-undo="${h(id)}">Undo</button>`;
  pendingNotifDeletes.set(String(id), setTimeout(() => commitNotifDelete(id), 5000));
}

function commitNotifDelete(id) {
  const key = String(id);
  if (pendingNotifDeletes.has(key)) { clearTimeout(pendingNotifDeletes.get(key)); pendingNotifDeletes.delete(key); }
  delete notifById[key];
  api.deleteNotification(id).catch(() => {});
  const rowEl = notifRow(id);
  if (rowEl) {
    const grp = rowEl.closest(".ntf-group");
    rowEl.remove();
    if (grp && !grp.querySelector(".ntf-row")) grp.remove();  // drop the header once its group empties
  }
  const list = document.getElementById("notifList");
  if (list && !list.querySelector(".ntf-row")) list.innerHTML = `<div class="empty">No notifications yet.</div>`;
}

function cancelNotifUndo(id) {
  const key = String(id);
  if (pendingNotifDeletes.has(key)) { clearTimeout(pendingNotifDeletes.get(key)); pendingNotifDeletes.delete(key); }
  const rowEl = notifRow(id), n = notifById[key];
  if (rowEl && n) { rowEl.classList.remove("is-undo"); rowEl.innerHTML = notifRowInner(n); }
}

// Commit any deletes still inside their 5s window (the user navigated away).
// `beacon` uses a keepalive fetch so it survives a full page unload.
function flushNotifDeletes(beacon) {
  pendingNotifDeletes.forEach((t, id) => {
    clearTimeout(t);
    if (beacon) api.deleteNotificationBeacon(id);
    else api.deleteNotification(id).catch(() => {});
  });
  pendingNotifDeletes.clear();
}
window.addEventListener("pagehide", () => flushNotifDeletes(true));

async function renderNotifications() {
  if (!isAuthed()) { view.innerHTML = `<h2>Notifications</h2>${signInCard("see your notifications")}`; return; }
  view.innerHTML = `<h2>Notifications</h2>
    <p class="tiny muted" style="margin:-8px 0 12px">Tap a notification to open it, or ${icon("trash", "rec-ico")} to remove — you'll get 5 seconds to undo.</p>
    <div class="cat-chips" id="notifFilters" style="margin-bottom:10px"></div>
    <div class="card" id="notifList"><div class="empty">Loading…</div></div>`;
  const list = document.getElementById("notifList");
  const filters = document.getElementById("notifFilters");
  let items = [], filter = "all";
  const paint = () => {
    filters.innerHTML = catChipsHtml(items, filter);
    const shown = filterByCat(items, filter);
    list.innerHTML = shown.length ? groupedNotifsHtml(shown) : `<div class="empty">Nothing here.</div>`;
  };
  try {
    items = await api.notifications();
    notifById = {};
    items.forEach((n) => (notifById[String(n.id)] = n));
    if (!items.length) { list.innerHTML = `<div class="empty">No notifications yet.</div>`; return; }
    paint();
    api.markNotifsRead().then(() => setUnreadBadge(0)).catch(() => {});  // viewing clears the badge
    filters.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-cat]");
      if (chip) { filter = chip.dataset.cat; paint(); }
    });
    list.addEventListener("click", (e) => {
      const del = e.target.closest("[data-del]");
      if (del) { e.preventDefault(); startNotifUndo(del.getAttribute("data-del")); return; }
      const undo = e.target.closest("[data-undo]");
      if (undo) { e.preventDefault(); cancelNotifUndo(undo.getAttribute("data-undo")); return; }
      const link = e.target.closest("a.ntf-link");   // opening a real link → record the click (CTR)
      if (link) {
        const row = link.closest(".ntf-row");
        if (row && row.dataset.id) api.markNotifClicked(row.dataset.id).catch(() => {});
        // no preventDefault — the <a href> still navigates
      }
    });
  } catch (e) { list.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
}

// --------------------------------------------------------------------------
// Admin — elevated-role approval queue
// --------------------------------------------------------------------------
// Admin "Manage & delete content": one row per entity with a Delete button.
// Deleting is admin-only server-side, so this whole panel is gated to admins.
const ADMIN_MANAGE = [
  ["matches", "Matches", () => api.matches(), (m) => admRow(m.id, `${m.team_a} vs ${m.team_b}`, m.result || (m.status === "in_progress" ? "In progress" : (m.status || "match")), "match")],
  ["tournaments", "Tournaments", () => api.tournaments(), (t) => admRow(t.id, t.name, `${t.format === "knockout" ? "Knockout" : "League"} · ${(t.teams || []).length} team${(t.teams || []).length === 1 ? "" : "s"}`, "tournament")],
  ["teams", "Teams", () => api.teams(), (t) => admRow(t.id, t.name, `${(t.members || []).length} player${(t.members || []).length === 1 ? "" : "s"}${t.location ? " · " + t.location : ""}`, "team")],
  ["players", "Players", () => api.players(), (p) => admRow(p.id, p.name, [p.code, p.batting_style, p.bowling_style].filter(Boolean).join(" · ") || "player", "player")],
];
const ADMIN_DELETE = {
  match: (id) => api.deleteMatch(id), tournament: (id) => api.deleteTournament(id),
  team: (id) => api.deleteTeam(id), player: (id) => api.deletePlayer(id),
};

function admRow(id, title, sub, kind) {
  return `<div class="matchitem" data-row="${h(id)}">
    <div class="mi-main"><b>${h(title)}</b><div class="tiny muted">${h(sub)}</div></div>
    <button class="btn btn--ghost btn--sm adm-del" data-id="${h(id)}" data-kind="${kind}" data-label="${h(title)}">${icon("trash")} Delete</button>
  </div>`;
}

const pct = (x) => Math.round((x || 0) * 100) + "%";
function annStatsHtml(rows) {
  if (!rows.length) return `<div class="empty">No announcements sent yet.</div>`;
  return rows.map((r) => `<div class="matchitem">
    <div class="mi-main"><b>${h(r.title)}</b>
      <div class="tiny muted">${h(r.category)} · sent ${r.delivered} · opened ${r.opened} (${pct(r.open_rate)}) · clicked ${r.clicked}</div></div>
    <div style="text-align:right;min-width:52px"><b style="font-size:1.15em">${pct(r.ctr)}</b><div class="tiny muted">CTR</div></div>
  </div>`).join("");
}

// Admin is four sub-routes behind one tab bar — #/admin, #/admin/organizers,
// #/admin/roles and #/admin/audit. The router sends every "#/admin…" hash to
// renderAdmin(), so a tab is just one more branch here (and one `nav()` away).
const ADMIN_TABS = [["", "Overview"], ["organizers", "Organizers"], ["roles", "Roles"], ["audit", "Audit"]];
const adminTabsHtml = (current) =>
  `<div class="netseg" id="admTabs">${ADMIN_TABS.map(([k, l]) =>
    `<button data-go="#/admin${k ? "/" + k : ""}"${k === current ? ' class="active"' : ""}>${h(l)}</button>`).join("")}</div>`;
function bindAdminTabs() {
  document.querySelectorAll("#admTabs button").forEach((b) => (b.onclick = () => nav(b.dataset.go)));
}

async function renderAdmin() {
  if (!isAuthed()) { view.innerHTML = `<h2>Admin</h2>${signInCard("manage role requests")}`; return; }
  if (auth.user.role !== "admin") {
    view.innerHTML = `<h2>Admin</h2><div class="card empty"><span class="empty-ico">${icon("ban")}</span>Admins only.</div>`;
    return;
  }
  const sub = (location.hash.match(/^#\/admin\/([a-z]+)/) || ["", ""])[1];
  if (sub === "organizers") return await renderAdminOrganizers();
  if (sub === "roles") return await renderAdminRoles();
  if (sub === "audit") return await renderAdminAudit();
  return await renderAdminOverview();
}

async function renderAdminOverview() {
  view.innerHTML = `
    <h2>Admin</h2>
    ${adminTabsHtml("")}
    <div class="section-title">${icon("gavel")} Role requests</div>
    <p class="tiny muted" style="margin:-4px 0 10px">Members who signed up for an elevated role — approve to grant it, or decline.</p>
    <div class="card" id="rrList"><div class="empty">Loading…</div></div>

    <div class="section-title" style="margin-top:22px">📣 Broadcast announcement</div>
    <p class="tiny muted" style="margin:-4px 0 10px">Notify everyone at once. <b>System</b> reaches all users; <b>Marketing</b> reaches only those who opted in.</p>
    <div class="card">
      <label>Title</label>
      <input id="annTitle" maxlength="120" placeholder="e.g. Scheduled maintenance tonight">
      <label>Message</label>
      <textarea id="annText" rows="2" maxlength="255" placeholder="What do you want everyone to know?"></textarea>
      <div class="row">
        <div><label>Type</label><select id="annCat"><option value="system">System — all users</option><option value="marketing">Marketing — opted-in only</option></select></div>
        <div><label>Link (optional)</label><input id="annLink" placeholder="#/tournaments/5"></div>
      </div>
      <div class="spacer"></div>
      <button class="btn" id="annSend">📣 Broadcast to everyone</button>
    </div>
    <div class="section-title" style="margin-top:22px">📊 Announcement analytics</div>
    <p class="tiny muted" style="margin:-4px 0 10px">Delivered → opened → clicked for each broadcast.</p>
    <div class="card" id="annStats"><div class="empty">Loading…</div></div>

    <div class="section-title" style="margin-top:22px">${icon("trash")} Manage &amp; delete content</div>
    <p class="tiny muted" style="margin:-4px 0 10px">Remove any match, tournament, team or player across CricNetra. Deleting can't be undone.</p>
    <div class="netseg" id="admSeg">${ADMIN_MANAGE.map(([k, l], i) => `<button data-k="${h(k)}"${i === 0 ? ' class="active"' : ""}>${h(l)}</button>`).join("")}</div>
    <div class="card" id="admList"><div class="empty">Loading…</div></div>`;

  // ---- role requests ----
  const rrList = document.getElementById("rrList");
  async function refreshRR() {
    try {
      const reqs = await api.roleRequests();
      rrList.innerHTML = reqs.length
        ? reqs.map((r) => `<div class="matchitem">${avatar(r.full_name || r.username)}
            <div class="mi-main"><b>${h(r.full_name)}</b><div class="tiny muted">@${h(r.username)} · wants <b>${h(r.requested_role.replace(/_/g, " "))}</b></div></div>
            <span class="rr-actions"><button class="btn btn--sm rr-ok" data-uid="${h(r.user_id)}">Approve</button>
            <button class="btn btn--ghost btn--sm rr-no" data-uid="${h(r.user_id)}">Decline</button></span></div>`).join("")
        : `<div class="empty">No pending requests.</div>`;
    } catch (e) { rrList.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  rrList.addEventListener("click", async (e) => {
    const btn = e.target.closest(".rr-ok, .rr-no");
    if (!btn) return;
    const uid = btn.getAttribute("data-uid"), approve = btn.classList.contains("rr-ok");
    btn.disabled = true;
    try {
      if (approve) { await api.approveRole(uid); toast("Role approved ✓"); }
      else { await api.rejectRole(uid); toast("Request declined"); }
      refreshRR();
    } catch (err) { toast(err.message, "error"); btn.disabled = false; }
  });
  refreshRR();

  // ---- broadcast announcements + analytics ----
  const annStats = document.getElementById("annStats");
  async function loadAnnStats() {
    try { annStats.innerHTML = annStatsHtml(await api.announcementAnalytics()); }
    catch (e) { annStats.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  document.getElementById("annSend").onclick = async () => {
    const title = document.getElementById("annTitle").value.trim();
    const text = document.getElementById("annText").value.trim();
    if (!title || !text) { toast("Title and message are required", "error"); return; }
    const category = document.getElementById("annCat").value;
    const link = document.getElementById("annLink").value.trim();
    const btn = document.getElementById("annSend");
    btn.disabled = true;
    try {
      const r = await api.sendAnnouncement({ title, text, category, link });
      toast(`Broadcast to ${r.recipients} user${r.recipients === 1 ? "" : "s"} ✓`);
      document.getElementById("annTitle").value = "";
      document.getElementById("annText").value = "";
      document.getElementById("annLink").value = "";
      loadAnnStats();
    } catch (e) { toast(e.message || "Couldn't broadcast", "error"); }
    finally { btn.disabled = false; }
  };
  loadAnnStats();

  // ---- manage & delete content ----
  const seg = document.getElementById("admSeg");
  const admList = document.getElementById("admList");
  let loadSeq = 0;
  async function loadContent(kind) {
    const seq = ++loadSeq;
    admList.innerHTML = `<div class="empty">Loading…</div>`;
    const entry = ADMIN_MANAGE.find(([k]) => k === kind);
    try {
      const items = await entry[2]();
      if (seq !== loadSeq) return;  // a newer tab was clicked
      admList.innerHTML = items.length ? items.map(entry[3]).join("") : `<div class="empty">Nothing here.</div>`;
    } catch (e) { if (seq === loadSeq) admList.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  admList.addEventListener("click", async (e) => {
    const btn = e.target.closest(".adm-del");
    if (!btn) return;
    const { id, kind, label } = btn.dataset;
    if (!confirm(`Delete this ${kind}?\n\n${label}\n\nThis can't be undone.`)) return;
    btn.disabled = true;
    try {
      await ADMIN_DELETE[kind](id);
      toast(`${kind.charAt(0).toUpperCase() + kind.slice(1)} deleted`);
      const row = btn.closest("[data-row]"); if (row) row.remove();
      if (!admList.querySelector("[data-row]")) admList.innerHTML = `<div class="empty">Nothing here.</div>`;
    } catch (err) { toast(err.message, "error"); btn.disabled = false; }
  });
  seg.querySelectorAll("button").forEach((b) => (b.onclick = () => {
    seg.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
    loadContent(b.dataset.k);
  }));
  loadContent("matches");
  bindAdminTabs();
}

// --------------------------------------------------------------------------
// Admin → Organizers: areas, organizations, and the people who run competitions
// --------------------------------------------------------------------------
// The roles an admin may hand out. Mirrors the backend's assignable set — a role
// outside it is refused server-side, so the picker never offers one.
const ASSIGNABLE_ROLES = [
  ["general_user", "General user"], ["player", "Player"], ["team_owner", "Team owner"],
  ["umpire", "Umpire"], ["commentator", "Commentator"], ["organizer", "Organizer"], ["admin", "Admin"],
];
const roleLabel = (r) => (ASSIGNABLE_ROLES.find(([k]) => k === r) || [, String(r || "").replace(/_/g, " ")])[1];

// "CN000004 - Sunil Umpire" on the left, their current role on the right — the
// same shape the squad pickers use, so an admin sees who they're about to change.
function userPickerOptions(users, { skip = () => false, reason = () => "" } = {}) {
  const opts = [], blocked = [];
  users.forEach((u) => {
    const left = `${u.user_code || "@" + u.username} - ${u.full_name || u.username}`;
    if (skip(u)) blocked.push({ value: u.id, disabled: true, left, right: reason(u) });
    else opts.push({ value: u.id, left, right: roleLabel(u.role) });
  });
  if (blocked.length) { opts.push({ group: "Not available" }); blocked.forEach((o) => opts.push(o)); }
  return opts;
}

// One <select> of areas / organizations, with the current posting preselected.
function refSelect(id, rows, selected, placeholder) {
  return `<select id="${h(id)}"><option value="">${h(placeholder)}</option>${rows.map((r) =>
    `<option value="${h(r.id)}"${String(r.id) === String(selected || "") ? " selected" : ""}>${h(r.name)}</option>`).join("")}</select>`;
}

function organizerRowHtml(o, areas, orgs) {
  const posting = [o.area_name, o.organization_name].filter(Boolean).map(h).join(" · ") || "No posting yet";
  return `<div class="adm-org" data-row="${h(o.user_id)}">
    <div class="matchitem">${avatar(o.full_name || o.username)}
      <div class="mi-main"><b>${h(o.full_name || o.username)}</b>
        <div class="tiny muted">@${h(o.username)} · ${posting}</div>
        <div class="tiny muted">${o.tournaments} tournament${o.tournaments === 1 ? "" : "s"} · ${h(roleLabel(o.role))}</div></div>
      <span class="badge ${o.is_active ? "" : "badge--grey"}">${o.is_active ? "active" : "suspended"}</span></div>
    <div class="rr-actions adm-acts">
      <button class="btn btn--ghost btn--sm og-edit" data-uid="${h(o.user_id)}">Edit posting</button>
      <button class="btn btn--ghost btn--sm og-susp" data-uid="${h(o.user_id)}" data-to="${o.is_active ? "0" : "1"}">${o.is_active ? "Suspend" : "Restore"}</button>
      <button class="btn btn--ghost btn--sm og-rm" data-uid="${h(o.user_id)}" data-label="${h(o.full_name || o.username)}">Stand down</button>
    </div>
    <div class="adm-edit" data-edit="${h(o.user_id)}" hidden>
      <div class="row">
        <div><label>Area</label>${refSelect("oe_area_" + o.user_id, areas, o.area_id, "— no area —")}</div>
        <div><label>Organization</label>${refSelect("oe_org_" + o.user_id, orgs, o.organization_id, "— none —")}</div>
      </div>
      <div class="spacer"></div>
      <button class="btn btn--sm og-save" data-uid="${h(o.user_id)}">Save posting</button>
    </div>
  </div>`;
}

async function renderAdminOrganizers() {
  view.innerHTML = `<h2>Admin</h2>${adminTabsHtml("organizers")}<div class="card"><div class="empty">Loading…</div></div>`;
  bindAdminTabs();
  const [organizers, areas, orgs, users] = await Promise.all([
    api.organizers(), api.areas(), api.organizations(), api.users().catch(() => []),
  ]);
  const areaRows = areas.map((a) => ({ id: a.id, name: a.state ? `${a.name} (${a.state})` : a.name }));
  const orgRows = orgs.map((o) => ({ id: o.id, name: o.area_name ? `${o.name} — ${o.area_name}` : o.name }));
  const isOrganizer = new Set(organizers.map((o) => String(o.user_id)));

  view.innerHTML = `
    <h2>Admin</h2>
    ${adminTabsHtml("organizers")}
    <div class="section-title">${icon("shield")} Organizers</div>
    <p class="tiny muted" style="margin:-4px 0 10px">An organizer is an existing account promoted to run competitions — this never creates a login.
      <b>Suspend</b> stops them acting but keeps the role; <b>stand down</b> drops the account to general user and leaves their tournaments alone.</p>
    <div class="card" id="ogList">${organizers.length
      ? organizers.map((o) => organizerRowHtml(o, areaRows, orgRows)).join("")
      : `<div class="empty">No organizers yet. Appoint one below.</div>`}</div>

    <div class="section-title" style="margin-top:22px">${icon("user")} Appoint an organizer</div>
    <div class="card">
      <label>Member</label>
      <div class="cdd" id="ogPick"></div>
      <p class="tiny muted" style="margin:8px 0 0">Only somebody who already signed up can be appointed. Existing organizers aren't listed.</p>
      <div class="row" style="margin-top:10px">
        <div><label>Area</label>${refSelect("og_area", areaRows, "", "— no area —")}</div>
        <div><label>Organization</label>${refSelect("og_org", orgRows, "", "— none —")}</div>
      </div>
      <div class="spacer"></div>
      <button class="btn" id="ogAdd">Make organizer</button>
    </div>

    <div class="section-title" style="margin-top:22px">${icon("pin")} Areas</div>
    <p class="tiny muted" style="margin:-4px 0 10px">A place competitions are run in. Add these before posting an organizer to one.</p>
    <div class="card">
      <div class="row">
        <div><label>Name</label><input id="ar_name" placeholder="e.g. Prayagraj" maxlength="120"></div>
        <div><label>State (optional)</label><input id="ar_state" placeholder="e.g. Uttar Pradesh" maxlength="80"></div>
      </div>
      <div class="spacer"></div>
      <button class="btn btn--sm" id="arAdd">Add area</button>
    </div>
    <div class="card" id="arList">${areas.length ? areas.map((a) => `<div class="matchitem" data-row="${h(a.id)}">
      <div class="mi-main"><b>${h(a.name)}</b><div class="tiny muted">${[a.state, `${a.organizers} organizer${a.organizers === 1 ? "" : "s"}`, `${a.tournaments} tournament${a.tournaments === 1 ? "" : "s"}`].filter(Boolean).map(h).join(" · ")}</div></div>
      <button class="btn btn--ghost btn--sm ar-del" data-id="${h(a.id)}" data-label="${h(a.name)}">${icon("trash")}</button></div>`).join("")
      : `<div class="empty">No areas yet.</div>`}</div>

    <div class="section-title" style="margin-top:22px">${icon("users")} Organizations</div>
    <p class="tiny muted" style="margin:-4px 0 10px">The body that runs cricket in an area — a club, a board, a league office.</p>
    <div class="card">
      <div class="row">
        <div><label>Name</label><input id="or_name" placeholder="e.g. XYZ Sports" maxlength="140"></div>
        <div><label>Area</label>${refSelect("or_area", areaRows, "", "— no area —")}</div>
      </div>
      <div class="spacer"></div>
      <button class="btn btn--sm" id="orAdd">Add organization</button>
    </div>
    <div class="card" id="orList">${orgs.length ? orgs.map((o) => `<div class="matchitem" data-row="${h(o.id)}">
      <div class="mi-main"><b>${h(o.name)}</b><div class="tiny muted">${h(o.area_name || "No area")}</div></div>
      <button class="btn btn--ghost btn--sm or-del" data-id="${h(o.id)}" data-label="${h(o.name)}">${icon("trash")}</button></div>`).join("")
      : `<div class="empty">No organizations yet.</div>`}</div>`;
  bindAdminTabs();

  const pick = document.getElementById("ogPick");
  cdd(pick, userPickerOptions(users, {
    skip: (u) => isOrganizer.has(String(u.id)),
    reason: () => "already an organizer",
  }), users.length ? "Pick a member…" : "No members yet");

  const reload = () => renderAdminOrganizers();
  const guard = async (btn, fn, okMsg) => {   // one place for "disable → call → toast → reload"
    btn.disabled = true;
    try { await fn(); toast(okMsg); reload(); }
    catch (e) { toast(e.message, "error"); btn.disabled = false; }
  };

  document.getElementById("ogAdd").onclick = (e) => {
    const uid = pick.dataset.value;
    if (!uid) return toast("Pick the member to appoint", "error");
    guard(e.target, () => api.createOrganizer({
      user_id: uid, area_id: val("og_area") || null, organization_id: val("og_org") || null,
    }), "Organizer appointed ✓");
  };
  document.getElementById("arAdd").onclick = (e) => {
    if (!val("ar_name")) return toast("Name the area", "error");
    guard(e.target, () => api.createArea({ name: val("ar_name"), state: val("ar_state") || null }), "Area added ✓");
  };
  document.getElementById("orAdd").onclick = (e) => {
    if (!val("or_name")) return toast("Name the organization", "error");
    guard(e.target, () => api.createOrganization({ name: val("or_name"), area_id: val("or_area") || null }), "Organization added ✓");
  };
  document.getElementById("arList").addEventListener("click", (e) => {
    const btn = e.target.closest(".ar-del");
    if (!btn || !confirm(`Delete the area "${btn.dataset.label}"?`)) return;
    guard(btn, () => api.deleteArea(btn.dataset.id), "Area deleted");
  });
  document.getElementById("orList").addEventListener("click", (e) => {
    const btn = e.target.closest(".or-del");
    if (!btn || !confirm(`Delete the organization "${btn.dataset.label}"?`)) return;
    guard(btn, () => api.deleteOrganization(btn.dataset.id), "Organization deleted");
  });
  document.getElementById("ogList").addEventListener("click", (e) => {
    const btn = e.target.closest(".og-edit, .og-save, .og-susp, .og-rm");
    if (!btn) return;
    const uid = btn.dataset.uid;
    if (btn.classList.contains("og-edit")) {
      const panel = view.querySelector(`[data-edit="${uid}"]`);
      if (panel) panel.hidden = !panel.hidden;
      return;
    }
    if (btn.classList.contains("og-save")) {
      return guard(btn, () => api.updateOrganizer(uid, {
        area_id: val("oe_area_" + uid) || null, organization_id: val("oe_org_" + uid) || null,
      }), "Posting updated ✓");
    }
    if (btn.classList.contains("og-susp")) {
      const on = btn.dataset.to === "1";
      return guard(btn, () => api.updateOrganizer(uid, { is_active: on }), on ? "Organizer restored ✓" : "Organizer suspended");
    }
    if (!confirm(`Stand ${btn.dataset.label} down?\n\nTheir account drops to general user. Their tournaments are kept.`)) return;
    guard(btn, () => api.standDownOrganizer(uid), "Organizer stood down");
  });
}

// --------------------------------------------------------------------------
// Admin → Roles: the one place an account's role is set
// --------------------------------------------------------------------------
async function renderAdminRoles() {
  view.innerHTML = `<h2>Admin</h2>${adminTabsHtml("roles")}<div class="card"><div class="empty">Loading…</div></div>`;
  bindAdminTabs();
  const [users, recent] = await Promise.all([
    api.users(), api.audit({ action: "role.assigned", limit: 12 }).catch(() => []),
  ]);
  const byRole = {};
  users.forEach((u) => (byRole[u.role] = (byRole[u.role] || 0) + 1));

  view.innerHTML = `
    <h2>Admin</h2>
    ${adminTabsHtml("roles")}
    <div class="section-title">${icon("lock")} Assign a role</div>
    <div class="card adm-note">
      <b>This is the only way a role is granted.</b>
      <p class="tiny muted" style="margin:6px 0 0">Signing up never grants one, and no endpoint reads a role out of a request — what a member may
      do always comes from the role on their account, set here. Adding somebody to a tournament's staff promotes them only if they hold no role yet.</p>
    </div>
    <div class="card">
      <label>Member</label>
      <div class="cdd" id="rlPick"></div>
      <label style="margin-top:10px">New role</label>
      <select id="rlRole">${ASSIGNABLE_ROLES.map(([k, l]) => `<option value="${h(k)}">${h(l)}</option>`).join("")}</select>
      <p class="tiny muted" id="rlNow" style="margin:8px 0 0">Pick a member to see the role they hold now.</p>
      <div class="spacer"></div>
      <button class="btn" id="rlSave">Assign role</button>
    </div>
    <div class="section-title" style="margin-top:22px">${icon("chart")} Members by role</div>
    <div class="card">${statGrid(ASSIGNABLE_ROLES.slice(0, 4).map(([k, l]) => [l, byRole[k] || 0]))}
      <div class="spacer"></div>
      ${statGrid(ASSIGNABLE_ROLES.slice(4).map(([k, l]) => [l, byRole[k] || 0]).concat([["Members", users.length]]))}</div>
    <div class="section-title" style="margin-top:22px">${icon("gavel")} Recent role changes</div>
    <div class="card" id="rlLog">${auditRowsHtml(recent)}</div>`;
  bindAdminTabs();

  const pick = document.getElementById("rlPick");
  cdd(pick, userPickerOptions(users), users.length ? "Pick a member…" : "No members yet");
  const now = document.getElementById("rlNow");
  pick.addEventListener("change", () => {
    const u = users.find((x) => String(x.id) === String(pick.dataset.value));
    now.innerHTML = u
      ? `<b>${h(u.full_name || u.username)}</b> currently holds <b>${h(roleLabel(u.role))}</b>.`
      : "Pick a member to see the role they hold now.";
  });
  document.getElementById("rlSave").onclick = async (e) => {
    const uid = pick.dataset.value;
    if (!uid) return toast("Pick the member first", "error");
    const role = document.getElementById("rlRole").value;
    const u = users.find((x) => String(x.id) === String(uid));
    if (!confirm(`Set ${(u && (u.full_name || u.username)) || "this member"} to ${roleLabel(role)}?`)) return;
    e.target.disabled = true;
    try { await api.assignRole(uid, role); toast("Role assigned ✓"); renderAdminRoles(); }
    catch (err) { toast(err.message, "error"); e.target.disabled = false; }
  };
}

// --------------------------------------------------------------------------
// Admin → Audit: who changed what, newest first
// --------------------------------------------------------------------------
// The actions the backend records. "" is the unfiltered view.
const AUDIT_ACTIONS = [
  ["", "All actions"], ["role.assigned", "Role assigned"], ["organizer.created", "Organizer created"],
  ["organizer.deactivated", "Organizer stood down"], ["staff.added", "Staff added"], ["staff.removed", "Staff removed"],
  ["tournament.created", "Tournament created"], ["tournament.updated", "Tournament updated"],
  ["tournament.deleted", "Tournament deleted"], ["player.added", "Player added"],
  ["match.deleted", "Match deleted"], ["access.denied", "Access denied"],
];
function auditRowsHtml(rows) {
  if (!rows || !rows.length) return `<div class="empty">Nothing recorded yet.</div>`;
  return rows.map((r) => `<div class="matchitem">
    <div class="mi-main"><b>${h(r.detail || r.action)}</b>
      <div class="tiny muted"><span class="adm-act">${h(r.action)}</span> · ${h(r.actor_name || "system")}${r.resource_type ? ` · ${h(r.resource_type)} ${h(r.resource_id)}` : ""}</div></div>
    <span class="tiny muted" style="flex:0 0 auto">${h(timeago(r.when))}</span></div>`).join("");
}

async function renderAdminAudit() {
  view.innerHTML = `
    <h2>Admin</h2>
    ${adminTabsHtml("audit")}
    <div class="section-title">${icon("gavel")} Audit trail</div>
    <p class="tiny muted" style="margin:-4px 0 10px">Every action that moves authority or destroys data, newest first.</p>
    <div class="card">
      <label>Action</label>
      <select id="auAction">${AUDIT_ACTIONS.map(([k, l]) => `<option value="${h(k)}">${h(l)}</option>`).join("")}</select>
    </div>
    <div class="card" id="auList"><div class="empty">Loading…</div></div>`;
  bindAdminTabs();
  const list = document.getElementById("auList");
  const sel = document.getElementById("auAction");
  let seq = 0;
  async function load() {
    const mine = ++seq;
    list.innerHTML = `<div class="empty">Loading…</div>`;
    try {
      const rows = await api.audit({ action: sel.value || null, limit: 200 });
      if (mine === seq) list.innerHTML = auditRowsHtml(rows);
    } catch (e) { if (mine === seq) list.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  sel.onchange = load;
  load();
}

// --------------------------------------------------------------------------
// Search — players / teams / tournaments / members
// --------------------------------------------------------------------------
function searchGroupsHtml(res) {
  const group = (title, items, row) =>
    items && items.length ? `<div class="section-title">${title}</div><div class="card">${items.map(row).join("")}</div>` : "";
  const body = [
    group("Players", res.players, (p) => `<a class="matchitem" href="#/player/${h(p.id)}">${photoAvatar("player", p.id, p.name, "", p.has_photo)}
      <div class="mi-main"><b>${h(p.name)}</b><div class="tiny muted">${[p.batting_style, p.bowling_style].filter(Boolean).map(h).join(" · ") || "Player"}</div></div>
      <span class="badge badge--grey">view ›</span></a>`),
    group("Teams", res.teams, (t) => `<a class="matchitem" href="#/team/${h(t.id)}">${photoAvatar("team", t.id, t.name, "", t.has_photo)}
      <div class="mi-main"><b>${h(t.name)}</b><div class="tiny muted">${t.members.length} player${t.members.length === 1 ? "" : "s"}${t.location ? " · " + h(t.location) : ""}</div></div>
      <span class="badge badge--grey">open ›</span></a>`),
    group("Tournaments", res.tournaments, (t) => `<a class="matchitem" href="#/tournament/${h(t.id)}">${avatar(t.name)}
      <div class="mi-main"><b>${h(t.name)}</b><div class="tiny muted">${t.format === "knockout" ? "Knockout" : "League"} · ${t.teams.length} teams</div></div>
      <span class="badge badge--grey">open ›</span></a>`),
    group("Members", res.members, (u) => `<div class="matchitem">${photoAvatar("user", u.id, u.full_name || u.username, "", u.has_photo)}
      <div class="mi-main"><b>${h(u.full_name)}</b><div class="tiny muted">@${h(u.username)} · ${h(u.role.replace(/_/g, " "))}</div></div>
      ${String(u.id) !== String((auth.user || {}).id) ? `<a class="badge net-msg" href="#/messages/${h(u.id)}" title="Message ${h(u.full_name)}">${icon("message")}</a>` : ""}
      ${u.mobile_no ? `<a class="badge net-call" href="tel:${h(u.mobile_no)}">${icon("phone")}</a>` : ""}</div>`),
    group("Grounds &amp; academies", res.venues, (v) => `<a class="matchitem" href="#/venues">
      <span class="q-ico" style="margin:0;width:38px;height:38px;border-radius:11px">${v.kind === "academy" ? icon("cap") : icon("pin")}</span>
      <div class="mi-main"><b>${h(v.name)}</b><div class="tiny muted">${[v.city, v.contact].filter(Boolean).map(h).join(" · ") || (v.kind === "academy" ? "Academy" : "Ground")}</div></div>
      <span class="badge badge--grey">${h(v.kind)}</span></a>`),
  ].join("");
  return body || `<div class="empty"><span class="empty-ico">${icon("search")}</span>No matches found.</div>`;
}

let pendingSearch = "";  // a query handed off from the desktop header search

// --------------------------------------------------------------------------
// Grounds & academies directory
// --------------------------------------------------------------------------
function venueRow(v, isAdmin) {
  const ico = v.kind === "academy" ? icon("cap") : icon("pin");
  const sub = [v.city, v.contact].filter(Boolean).map(h).join(" · ") || (v.kind === "academy" ? "Academy" : "Ground");
  return `<div class="matchitem"><span class="q-ico" style="margin:0;width:38px;height:38px;font-size:18px;border-radius:11px">${ico}</span>
    <div class="mi-main"><b>${h(v.name)}</b><div class="tiny muted">${sub}${v.note ? " · " + h(v.note) : ""}</div></div>
    ${isAdmin ? `<button class="btn btn--ghost btn--sm v-del" data-id="${h(v.id)}">Remove</button>`
      : `<span class="badge badge--grey">${v.kind === "academy" ? "academy" : "ground"}</span>`}</div>`;
}

// Add a voice-search mic to any text input (Web Speech API). No-op — and no button —
// when the browser has no speech support, so it's a clean progressive enhancement.
// `onSpeak` runs after the spoken text fills the input (defaults to firing 'input').
function attachVoice(input, onSpeak) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR || !input || input.dataset.voice) return;
  input.dataset.voice = "1";
  const mic = document.createElement("button");
  mic.type = "button";
  mic.className = "mic-btn";
  mic.title = "Search by voice";
  mic.setAttribute("aria-label", "Search by voice");
  mic.innerHTML = icon("mic");
  input.insertAdjacentElement("afterend", mic);
  const fire = onSpeak || (() => input.dispatchEvent(new Event("input")));
  let rec = null, listening = false;
  mic.onclick = () => {
    if (listening) { rec && rec.stop(); return; }
    rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    listening = true;
    mic.classList.add("listening");
    rec.onresult = (e) => { input.value = e.results[0][0].transcript; fire(); };
    rec.onerror = () => toast("Voice input didn't work — try typing.", "error");
    rec.onend = () => { listening = false; mic.classList.remove("listening"); };
    try { rec.start(); } catch (_) { listening = false; mic.classList.remove("listening"); }
  };
}

async function renderVenues() {
  const canAdd = can("team.create");
  const isAdmin = !!(auth.user && auth.user.role === "admin");
  view.innerHTML = `
    <h2>Grounds &amp; academies</h2>
    ${canAdd ? `<div class="card">
      <label>Add a venue</label>
      <input id="v_name" placeholder="Name (e.g. Wankhede Stadium)">
      <div class="row">
        <div><label>Type</label><select id="v_kind"><option value="ground">Ground</option><option value="academy">Academy</option></select></div>
        <div><label>City</label><input id="v_city" placeholder="City"></div>
      </div>
      <label>Contact (optional)</label><input id="v_contact" placeholder="Phone / email">
      <label>Address or note (optional)</label><input id="v_note" placeholder="Address or a short note">
      <div class="spacer"></div>
      <button class="btn" id="v_add">Add venue</button>
    </div>` : ""}
    <div class="netseg" id="v_seg">
      <button data-k="" class="active">All</button>
      <button data-k="ground">Grounds</button>
      <button data-k="academy">Academies</button>
    </div>
    <div class="search-row" style="margin-bottom:12px">
      <input id="v_filter" placeholder="Search grounds &amp; academies…" autocomplete="off">
    </div>
    <div class="card" id="v_list"><div class="empty">Loading…</div></div>`;
  const listEl = document.getElementById("v_list");
  let kind = "";
  async function load() {
    listEl.innerHTML = `<div class="empty">Loading…</div>`;
    const q = (val("v_filter") || "").trim();
    const qs = [kind && "kind=" + encodeURIComponent(kind), q && "q=" + encodeURIComponent(q)].filter(Boolean).join("&");
    try {
      const vs = await api.venues(qs);
      listEl.innerHTML = vs.length ? vs.map((v) => venueRow(v, isAdmin)).join("") : `<div class="empty">No venues yet.</div>`;
      if (isAdmin) listEl.querySelectorAll(".v-del").forEach((b) => (b.onclick = async () => {
        if (!confirm("Remove this venue?")) return;
        try { await api.deleteVenue(b.dataset.id); load(); } catch (e) { toast(e.message, "error"); }
      }));
    } catch (e) { listEl.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  segPick("#v_seg", (k) => { kind = k; load(); });
  let t;
  document.getElementById("v_filter").oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };
  attachVoice(document.getElementById("v_filter"), load);
  if (canAdd) document.getElementById("v_add").onclick = async (ev) => {
    const name = val("v_name");
    if (!name) return toast("Name the venue", "error");
    ev.target.disabled = true;
    try {
      await api.createVenue({
        name, kind: document.getElementById("v_kind").value,
        city: val("v_city") || null, contact: val("v_contact") || null, note: val("v_note") || null,
      });
      ["v_name", "v_city", "v_contact", "v_note"].forEach((id) => (document.getElementById(id).value = ""));
      toast("Venue added ✓");
      load();
    } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
  };
  load();
}

function renderSettings() {
  const active = currentThemeId();
  const card = (t) => `
    <button class="theme-card ${t.id === active ? "active" : ""}" data-theme-id="${t.id}" type="button" aria-label="${h(t.name)} theme">
      <span class="tc-preview" style="background:${t.bg}">
        <span class="tc-bar" style="background:${t.accent}"></span>
        <span class="tc-chip" style="background:${t.surface}">
          <span class="tc-dot" style="background:${t.accent}"></span>
          <span class="tc-lines">
            <span class="tc-line" style="background:${t.ink};opacity:.85"></span>
            <span class="tc-line short" style="background:${t.ink};opacity:.45"></span>
          </span>
        </span>
      </span>
      <span class="tc-meta"><span class="tc-name">${h(t.name)}</span></span>
      <span class="tc-check">✓</span>
    </button>`;
  const group = (mode, label) =>
    `<div class="tc-group-h">${label}</div><div class="theme-grid">${THEMES.filter((t) => t.mode === mode).map(card).join("")}</div>`;
  view.innerHTML = `
    <h2>Settings</h2>
    <div class="card">
      <div class="section-title">${icon("palette")} Theme</div>
      <p class="set-hint">Choose a look for CricNetra — it applies instantly and is saved on this device.</p>
      ${group("dark", "Dark")}
      ${group("light", "Light")}
    </div>
    ${isAuthed() ? `
    <div class="card">
      <div class="section-title">🔔 Notifications</div>
      <p class="set-hint">Choose what you're notified about — changes save instantly.</p>
      <div class="pref-list" id="prefList"><div class="empty">Loading…</div></div>
    </div>
    <div class="card">
      <div class="section-title">🔒 Security</div>
      <p class="set-hint">Sign out of every device and browser, and remove push notifications everywhere.</p>
      <button class="btn btn--ghost" id="logoutAllBtn">Log out everywhere</button>
    </div>` : ""}`;
  view.querySelectorAll(".theme-card").forEach((c) => (c.onclick = () => applyTheme(c.dataset.themeId)));
  if (isAuthed()) loadNotifPrefs();
  const la = document.getElementById("logoutAllBtn");
  if (la) la.onclick = async () => {
    la.disabled = true;
    await unsubscribeFromPush();            // drop this browser's push too
    try { await api.logoutAll(); } catch (_) { api.logout(); }
    auth.user = null; stopNotifStream(); clearNotifCache(); setUnreadBadge(0);
    renderAuthChip(); toast("Signed out on all devices"); nav("#/");
  };
}

async function loadNotifPrefs() {
  const box = document.getElementById("prefList");
  if (!box) return;
  let prefs;
  try { prefs = await api.notifPrefs(); }
  catch (_) { box.innerHTML = `<div class="empty">Couldn't load preferences.</div>`; return; }
  notifPrefsCache = prefs;   // keep the sound/quiet gate in sync with what's shown
  const rows = [
    ["match", "Live matches"], ["tournament", "Tournaments"], ["team", "Teams"], ["player", "Players"],
    ["social", "Social — follows, mentions"], ["achievement", "Achievements"], ["system", "System"],
    ["marketing", "Marketing & tips"], ["push_enabled", "Push notifications"], ["email_enabled", "Email notifications"],
    ["sound", "Notification sound"],
  ];
  const hourOpts = (sel) => `<option value="">Off</option>` + Array.from({ length: 24 }, (_, hh) =>
    `<option value="${hh}"${hh === sel ? " selected" : ""}>${String(hh).padStart(2, "0")}:00</option>`).join("");
  box.innerHTML = rows.map(([k, label]) =>
    `<label class="pref-row"><span>${label}</span><input type="checkbox" data-pref="${k}" ${prefs[k] ? "checked" : ""}></label>`
  ).join("") + `
    <div class="pref-row pref-quiet">
      <span>Quiet hours <span class="tiny muted">— mute pings</span></span>
      <span class="quiet-sel">
        <select data-quiet="start" aria-label="Quiet hours from">${hourOpts(prefs.quiet_start)}</select>
        <span class="tiny muted">to</span>
        <select data-quiet="end" aria-label="Quiet hours to">${hourOpts(prefs.quiet_end)}</select>
      </span>
    </div>`;

  // One save path for every control: collects all toggles + quiet hours, and always
  // stamps the browser's current UTC→local offset so the server can enforce DND.
  const collect = () => {
    const full = { tz_offset: -new Date().getTimezoneOffset() };
    box.querySelectorAll("input[data-pref]").forEach((x) => { full[x.dataset.pref] = x.checked; });
    const gv = (s) => { const el = box.querySelector(`[data-quiet="${s}"]`); return el.value === "" ? null : Number(el.value); };
    full.quiet_start = gv("start"); full.quiet_end = gv("end");
    return full;
  };
  const persist = async (revert) => {
    const full = collect();
    try { await api.saveNotifPrefs(full); notifPrefsCache = full; toast("Saved ✓"); }
    catch (e) { if (revert) revert(); toast(e.message || "Couldn't save", "error"); }
  };
  box.querySelectorAll("input[data-pref]").forEach((inp) => {
    inp.onchange = async () => {
      // The push toggle also drives the browser subscription (permission prompt etc.).
      if (inp.dataset.pref === "push_enabled") {
        if (inp.checked) {
          try { await subscribeToPush(); }
          catch (e) { inp.checked = false; toast(e.message || "Couldn't enable push", "error"); return; }
        } else {
          await unsubscribeFromPush();
        }
      }
      await persist(() => { inp.checked = !inp.checked; });
    };
  });
  box.querySelectorAll("[data-quiet]").forEach((sel) => { sel.onchange = () => persist(); });
}

async function renderSearch() {
  view.innerHTML = `
    <h2>Search</h2>
    <div class="card">
      <div class="search-row">
        <input id="searchInput" placeholder="Find players, teams, grounds, academies…" autocomplete="off" autocapitalize="off">
      </div>
      ${isAuthed() ? "" : `<p class="tiny muted" style="margin-top:8px"><a href="/login">Sign in</a> to also find members (umpires, commentators…).</p>`}
    </div>
    <div id="searchResults"><div class="empty">Type a name to search.</div></div>`;
  const input = document.getElementById("searchInput");
  const out = document.getElementById("searchResults");
  if (pendingSearch) { input.value = pendingSearch; pendingSearch = ""; }
  input.focus();
  let timer, seq = 0;
  async function run() {
    const q = input.value.trim();
    if (!q) { out.innerHTML = `<div class="empty">Type a name to search.</div>`; return; }
    const my = ++seq;
    out.innerHTML = `<div class="empty">Searching…</div>`;
    try {
      const res = await api.search(q);
      if (my !== seq) return; // a newer keystroke superseded this
      out.innerHTML = searchGroupsHtml(res);
    } catch (e) { if (my === seq) out.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
  }
  input.oninput = () => { clearTimeout(timer); timer = setTimeout(run, 220); };
  attachVoice(input, run);  // voice search — mic appears only where speech is supported

  if (input.value.trim()) run();  // a query arrived from the header search
}

// --------------------------------------------------------------------------
// Router
// --------------------------------------------------------------------------
// --------------------------------------------------------------------------
// Direct messages
// --------------------------------------------------------------------------
function setDmBadge(n) {
  document.querySelectorAll(".js-dm-badge").forEach((b) => {
    b.textContent = n > 99 ? "99+" : n;
    b.hidden = !n;
  });
}
function refreshDmBadge() {
  if (!isAuthed()) return setDmBadge(0);
  api.unreadMessages().then((r) => setDmBadge(r.count)).catch(() => {});
}

async function renderMessages() {
  if (!isAuthed()) { view.innerHTML = `<h2>Messages</h2>${signInCard("see your messages")}`; return; }
  view.innerHTML = `<h2>Messages</h2><div id="msgList" class="card"><div class="empty">Loading…</div></div>`;
  let convos;
  try { convos = await api.messages(); }
  catch (e) { document.getElementById("msgList").innerHTML = `<div class="empty">${h(e.message)}</div>`; return; }
  refreshDmBadge();
  const el = document.getElementById("msgList");
  if (!convos.length) {
    el.innerHTML = `<div class="empty">No messages yet.<br>Find someone in <a href="#/network">Network</a> or on the <a href="#/looking-for">Looking For</a> board and say hi.</div>`;
    return;
  }
  el.innerHTML = convos.map((c) => `<a class="matchitem" href="#/messages/${h(c.other_id)}">
    ${avatar(c.other_name, "avatar--sm")}
    <div class="mi-main"><b>${h(c.other_name)}</b>
      <div class="tiny muted msg-prev">${c.last_mine ? "You: " : ""}${h(c.last_text)}</div></div>
    <div class="msg-meta"><span class="tiny muted">${timeago(c.last_when)}</span>${c.unread ? `<span class="dm-dot">${c.unread}</span>` : ""}</div></a>`).join("");
}

async function renderThread(otherId) {
  if (!isAuthed()) { view.innerHTML = `<h2>Messages</h2>${signInCard("send messages")}`; return; }
  view.innerHTML = `<div class="thread-head"><a class="btn btn--ghost btn--sm" href="#/messages">‹ Inbox</a><b id="thOther" style="margin-left:10px">Chat</b></div>
    <div id="thread" class="thread card"><div class="empty">Loading…</div></div>
    <form id="thForm" class="thread-compose">
      <input id="thInput" placeholder="Message…" autocomplete="off" maxlength="2000">
      <button class="btn" type="submit">Send</button>
    </form>`;
  let data;
  try { data = await api.thread(otherId); }
  catch (e) { document.getElementById("thread").innerHTML = `<div class="empty">${h(e.message)}</div>`; return; }
  document.getElementById("thOther").textContent = data.other_name;
  refreshDmBadge();  // opening the thread marked it read on the server
  const box = document.getElementById("thread");
  let msgs = data.messages;
  const paint = () => {
    box.innerHTML = msgs.length
      ? msgs.map((m) => `<div class="bubble ${m.mine ? "bubble--me" : "bubble--them"}"><span>${h(m.text)}</span><time>${timeago(m.when)}</time></div>`).join("")
      : `<div class="empty">Say hello.</div>`;
    box.scrollTop = box.scrollHeight;
  };
  paint();
  document.getElementById("thForm").onsubmit = async (ev) => {
    ev.preventDefault();
    const inp = document.getElementById("thInput");
    const text = inp.value.trim();
    if (!text) return;
    inp.value = "";
    try { msgs = msgs.concat([await api.sendMessage(otherId, text)]); paint(); }
    catch (e) { toast(e.message, "error"); inp.value = text; }
  };
}

// --------------------------------------------------------------------------
// "Looking For" board
// --------------------------------------------------------------------------
const LF_KINDS = [["", "All"], ["player", "Players"], ["team", "Teams"], ["match", "Matches"]];
const LF_BADGE = { player: icon("users") + " Players wanted", team: icon("users") + " Team wanted", match: icon("stumps") + " Match wanted" };

function lfCard(p) {
  const action = p.mine
    ? `<div class="lf-own">${p.status === "open" ? `<button class="btn btn--ghost btn--sm" data-close="${h(p.id)}">Close</button>` : `<span class="badge badge--grey">closed</span>`}<button class="btn btn--ghost btn--sm" data-del="${h(p.id)}">Delete</button></div>`
    : `<a class="btn btn--sm" href="#/messages/${h(p.author_id)}">${icon("message")} Message</a>`;
  return `<div class="lf-card">
    <div class="lf-top"><span class="badge lf-${h(p.kind)}">${LF_BADGE[p.kind] || h(p.kind)}</span>
      ${p.location ? `<span class="tiny muted">${icon("pin", "rec-ico")}${h(p.location)}</span>` : ""}</div>
    <div class="lf-text">${h(p.text)}</div>
    <div class="lf-foot"><div class="tiny muted">${h(p.author_name)}${p.role ? " · " + h(p.role) : ""} · ${timeago(p.when)}</div>${action}</div>
  </div>`;
}

async function renderLookingFor() {
  if (!isAuthed()) { view.innerHTML = `<h2>Looking For</h2>${signInCard("browse & post on the Looking For board")}`; return; }
  view.innerHTML = `<h2>Looking For</h2>
    <p class="tiny muted" style="margin:-8px 0 12px">Find players, a team, or a match near you — message anyone to connect.</p>
    <button class="btn btn--sm" id="lfNew" style="margin-bottom:12px">＋ Post a request</button>
    <div id="lfForm"></div>
    <div class="lb-filters">
      <div class="seg lb-seg" id="lfKind">${LF_KINDS.map(([v, l], i) => `<button data-k="${v}" class="${i === 0 ? "active" : ""}">${l}</button>`).join("")}</div>
      <input id="lfLoc" placeholder="location" style="width:auto;flex:0 0 auto;padding:9px 12px">
    </div>
    <div id="lfList" class="card"><div class="empty">Loading…</div></div>`;
  const state = { kind: "", location: "" };
  const listEl = document.getElementById("lfList");
  const kindSeg = document.getElementById("lfKind");
  const locInp = document.getElementById("lfLoc");

  async function load() {
    listEl.innerHTML = `<div class="empty">Loading…</div>`;
    let posts;
    try { posts = await api.lookingFor(state.kind, state.location.trim()); }
    catch (e) { listEl.innerHTML = `<div class="empty">${h(e.message)}</div>`; return; }
    listEl.innerHTML = posts.length ? posts.map(lfCard).join("")
      : `<div class="empty">Nothing here yet. Be the first to post a request.</div>`;
    listEl.querySelectorAll("[data-close]").forEach((b) => (b.onclick = async () => {
      try { await api.closeLookingFor(b.dataset.close); toast("Closed ✓"); load(); } catch (e) { toast(e.message, "error"); }
    }));
    listEl.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
      try { await api.deleteLookingFor(b.dataset.del); toast("Deleted ✓"); load(); } catch (e) { toast(e.message, "error"); }
    }));
  }

  kindSeg.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-k]"); if (!b) return;
    [...kindSeg.children].forEach((c) => c.classList.toggle("active", c === b));
    state.kind = b.dataset.k; load();
  });
  let locT;
  locInp.addEventListener("input", () => { clearTimeout(locT); locT = setTimeout(() => { state.location = locInp.value; load(); }, 350); });

  document.getElementById("lfNew").onclick = () => {
    const box = document.getElementById("lfForm");
    if (box.innerHTML) { box.innerHTML = ""; return; }
    box.innerHTML = `<div class="card">
      <label>I'm looking for</label>
      <select id="lfk"><option value="team">A team (I'm a player)</option><option value="player">Players (for my team)</option><option value="match">A match / opponent</option></select>
      <label>Details</label>
      <textarea id="lft" rows="3" maxlength="500" placeholder="e.g. Right-arm pacer looking for a Sunday-league team in Pune"></textarea>
      <div class="row">
        <div><label>Location</label><input id="lfl" placeholder="City / area"></div>
        <div><label>Role (optional)</label><input id="lfr" placeholder="e.g. all-rounder"></div>
      </div>
      <div class="spacer"></div>
      <button class="btn" id="lfSubmit">Post</button></div>`;
    document.getElementById("lfSubmit").onclick = async (ev) => {
      const text = val("lft").trim();
      if (!text) return toast("Add some details", "error");
      ev.target.disabled = true;
      try {
        await api.postLookingFor({ kind: document.getElementById("lfk").value, text, location: val("lfl") || null, role: val("lfr") || null });
        toast("Posted ✓");
        box.innerHTML = "";
        state.kind = "";
        [...kindSeg.children].forEach((c, i) => c.classList.toggle("active", i === 0));
        load();
      } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
    };
  };
  load();
}

async function router() {
  flushNotifDeletes();  // commit any notification deletes left mid-undo on the previous view
  stopLiveStream();     // tear down any match SSE subscription from the previous view
  stopHomeLive();       // ...and the home dashboard's live-card poll
  const hash = location.hash || "#/";
  backBtn.hidden = hash === "#/" || hash === "";
  setChrome(hash);
  try {
    if (hash.startsWith("#/login")) { location.replace("/login"); return; }
    if (hash.startsWith("#/register")) { location.replace("/register"); return; }
    if (hash.startsWith("#/account")) return await renderAccount();
    if (hash.startsWith("#/network")) return await renderNetwork();
    if (hash.startsWith("#/feed")) return await renderFeed();
    if (hash.startsWith("#/notifications")) return await renderNotifications();
    const mt = hash.match(/^#\/messages\/(.+)$/);
    if (mt) return await renderThread(mt[1]);
    if (hash.startsWith("#/messages")) return await renderMessages();
    if (hash.startsWith("#/looking-for")) return await renderLookingFor();
    if (hash.startsWith("#/admin")) return await renderAdmin();
    if (hash.startsWith("#/settings")) return renderSettings();
    if (hash.startsWith("#/search")) return await renderSearch();
    if (hash.startsWith("#/highlights")) return await renderHighlights();
    const m = hash.match(/^#\/match\/(.+)$/);
    if (m) return await showMatch(m[1]);
    const tm = hash.match(/^#\/team\/(.+)$/);
    if (tm) return await renderTeam(tm[1]);
    if (hash.startsWith("#/teams")) return await renderTeams();
    const cm = hash.match(/^#\/career\/(.+)$/);
    if (cm) return await renderCareer(cm[1]);
    const pm = hash.match(/^#\/player\/(.+)$/);
    if (pm) return await renderPlayer(pm[1]);
    if (hash.startsWith("#/players")) return await renderPlayers();
    if (hash.startsWith("#/venues")) return await renderVenues();
    if (hash.startsWith("#/leaderboards")) return await renderLeaderboards();
    if (hash.startsWith("#/compare")) return await renderCompare();
    const tn = hash.match(/^#\/tournament\/(.+)$/);
    if (tn) return await renderTournament(tn[1]);
    if (hash.startsWith("#/tournaments")) return await renderTournaments();
    if (hash.startsWith("#/new")) return await renderNew();
    if (hash.startsWith("#/rules")) return await renderRules();
    return await renderHome();
  } catch (e) {
    view.innerHTML = `<div class="card empty">Couldn't load.<br><span class="small">${h(e.message)}</span></div>`;
  } finally {
    bindFollowBtns();  // wire any follow buttons the freshly-rendered page contains
  }
}
// ---- themes (Settings → Theme): named palettes applied via html[data-theme] ----
// Each entry carries a few representative colours so the picker can preview a
// palette without switching to it. The CSS token blocks live in styles.css.
const THEMES = [
  // dark
  { id: "emerald",       name: "Emerald",        mode: "dark",  bg: "#080b0a", surface: "#101714", accent: "#2fe08a", ink: "#e8efeb" },
  { id: "ocean",         name: "Midnight Ocean", mode: "dark",  bg: "#060b12", surface: "#0e1a24", accent: "#34c8ff", ink: "#e6f0f7" },
  { id: "carbon",        name: "Carbon",         mode: "dark",  bg: "#0a0b0c", surface: "#16181b", accent: "#bef264", ink: "#eceef0" },
  // light
  { id: "mint",          name: "Mint",           mode: "light", bg: "#eef7f2", surface: "#ffffff", accent: "#0e9f6e", ink: "#10241c" },
  { id: "blossom",       name: "Blossom",        mode: "light", bg: "#fdf0f6", surface: "#ffffff", accent: "#db2777", ink: "#2a1620" },
  { id: "emerald_light", name: "Emerald",        mode: "light", bg: "#eef4f0", surface: "#ffffff", accent: "#0c9b54", ink: "#0f1d16" },
  { id: "rose",          name: "Rose",           mode: "light", bg: "#fdf1f2", surface: "#ffffff", accent: "#e11d48", ink: "#2a1518" },
  { id: "slate",         name: "Slate",          mode: "light", bg: "#eef1f4", surface: "#ffffff", accent: "#2f6f9f", ink: "#1b232b" },
  { id: "sand",          name: "Sand",           mode: "light", bg: "#f5efe3", surface: "#fffdf7", accent: "#a76a12", ink: "#2a2317" },
  { id: "lavender",      name: "Lavender",       mode: "light", bg: "#f4f1fc", surface: "#ffffff", accent: "#7c3aed", ink: "#211a33" },
  { id: "sky",           name: "Sky",            mode: "light", bg: "#eef6fb", surface: "#ffffff", accent: "#0284c7", ink: "#12212b" },
  { id: "sunset",        name: "Sunset",         mode: "light", bg: "#fdf2ea", surface: "#fffdf9", accent: "#ea580c", ink: "#2b1c11" },
];
const THEME_BY_ID = Object.fromEntries(THEMES.map((t) => [t.id, t]));
const DEFAULT_THEME = "emerald";      // dark default (= no data-theme attribute)
const DEFAULT_LIGHT = "emerald_light"; // where the sun/moon toggle lands from a dark theme
const THEME_ICON = {
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2 12h2M20 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>',
};
function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
function currentThemeId() {
  return document.documentElement.getAttribute("data-theme") || DEFAULT_THEME;
}
function applyTheme(id) {
  if (!THEME_BY_ID[id]) id = DEFAULT_THEME;
  if (id === DEFAULT_THEME) document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", id);
  document.documentElement.classList.remove("theme-light");  // legacy class, superseded by data-theme
  lsSet("cn_theme", id);
  // remember the last dark AND last light choice so the header toggle restores each
  lsSet(THEME_BY_ID[id].mode === "dark" ? "cn_theme_dark" : "cn_theme_light", id);
  paintThemeIcons();
  document.querySelectorAll(".theme-card").forEach((c) => c.classList.toggle("active", c.dataset.themeId === id));
}
// return `id` only if it's a real theme of the wanted mode, else `fallback`
function validTheme(id, mode, fallback) {
  const t = THEME_BY_ID[id];
  return t && t.mode === mode ? id : fallback;
}
function paintThemeIcons() {
  const light = (THEME_BY_ID[currentThemeId()] || {}).mode === "light";
  document.querySelectorAll(".js-theme").forEach((b) => (b.innerHTML = light ? THEME_ICON.moon : THEME_ICON.sun));
}
function setupTheme() {
  // The sun/moon button is a quick light↔dark switch; the full palette lives in Settings.
  document.querySelectorAll(".js-theme").forEach((b) => (b.onclick = () => {
    const light = (THEME_BY_ID[currentThemeId()] || {}).mode === "light";
    applyTheme(light ? validTheme(lsGet("cn_theme_dark"), "dark", DEFAULT_THEME)
                     : validTheme(lsGet("cn_theme_light"), "light", DEFAULT_LIGHT));
  }));
  paintThemeIcons();
}

async function boot() {
  setupTheme();
  await loadAuth();
  renderAuthChip();
  startNotifStream();
  if (isAuthed()) { refreshDmBadge(); syncPushOnBoot(); }
  const hf = document.getElementById("hdrSearchForm");
  if (hf) {
    hf.onsubmit = (e) => {
      e.preventDefault();
      const inp = document.getElementById("hdrSearch");
      pendingSearch = (inp.value || "").trim();
      inp.value = "";
      inp.blur();
      if (location.hash.replace(/\?.*/, "") === "#/search") router();
      else nav("#/search");
    };
    attachVoice(document.getElementById("hdrSearch"), () => hf.requestSubmit());
  }
  router();
}
window.addEventListener("hashchange", router);
window.addEventListener("load", boot);
window.addEventListener("beforeunload", stopLiveStream);

// --------------------------------------------------------------------------
// Home
// --------------------------------------------------------------------------

const QUICK_TILES = `<div class="quick">
  <a href="#/new"><div class="q-ico">${icon("stumps")}</div><div class="q-title">New match</div><div class="q-sub">Score ball-by-ball</div></a>
  <a href="#/tournaments"><div class="q-ico">${icon("trophy")}</div><div class="q-title">Tournaments</div><div class="q-sub">Leagues &amp; knockouts</div></a>
  <a href="#/teams"><div class="q-ico">${icon("users")}</div><div class="q-title">Teams</div><div class="q-sub">Squads &amp; players</div></a>
  <a href="#/leaderboards"><div class="q-ico">${icon("chart")}</div><div class="q-title">Leaderboards</div><div class="q-sub">Top performers</div></a>
  <a href="#/network"><div class="q-ico">${icon("network")}</div><div class="q-title">Network</div><div class="q-sub">Players, umpires &amp; more</div></a>
  <a href="#/venues"><div class="q-ico">${icon("pin")}</div><div class="q-title">Venues</div><div class="q-sub">Grounds &amp; academies</div></a>
</div>`;
const DASH_SPARK = "0,15 10,12 20,14 30,8 40,11 50,5 60,7";  // decorative trend flourish

// Inline list-filter box (magnifier icon + input) reused on Players/Teams/Tournaments.
const SEARCH_ICON = `<svg class="list-search-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7.5"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`;
const searchBox = (id, ph) => `<div class="list-search-wrap">${SEARCH_ICON}<input class="list-search" id="${id}" type="search" placeholder="${ph}" aria-label="${ph}"></div>`;

function matchRow(m) {
  return `<a class="matchitem" href="#/match/${h(m.id)}">${avatar(m.team_a)}
    <div class="mi-main"><b>${h(m.team_a)}</b> <span class="muted">vs</span> <b>${h(m.team_b)}</b>
      <div class="tiny muted">${m.result ? h(m.result) : "in progress"}</div></div>
    <span class="badge ${m.status === "complete" ? "badge--grey" : ""}">${m.status === "complete" ? "done" : "live"}</span></a>`;
}

// Live win-probability for the batting side → integer % (or null when the
// innings is over). 2nd innings uses the real chase maths; the 1st innings
// shows a gentle "who's on top" estimate so the card is always present live.
function winProb(st) {
  const inn = st.innings[st.current_innings - 1];
  if (!inn || inn.is_complete) return null;
  const maxW = (st.rules && st.rules.players_per_side ? st.rules.players_per_side - 1 : 10);
  const wktsLeft = maxW - inn.wickets;
  if (inn.target) {
    const balls = inn.balls_remaining || 1;
    const rrr = inn.required_runs / (balls / 6);
    let p = Math.round(50 + (8 - rrr) * 5 + (wktsLeft - 5) * 4);
    if (inn.required_runs <= 0) p = 100;
    return Math.max(4, Math.min(96, p));
  }
  // 1st innings: no target yet → gentle lean from run rate vs a ~7.5 par + wickets in hand
  const p = Math.round(50 + ((inn.run_rate || 0) - 7.5) * 3 + (wktsLeft - 5) * 3);
  return Math.max(28, Math.min(72, p));
}

function liveHeroHtml(live, st) {
  const inn = st.innings[st.current_innings - 1];
  // data-sig lets the home refresher skip the DOM entirely when nothing changed
  const sig = `${inn.runs}/${inn.wickets}/${inn.overs_str}/${st.result || ""}`;
  const p = winProb(st);
  const win = p === null ? "" : `<div class="winbar-wrap">
      <div class="winbar-h">WIN PROBABILITY</div>
      <div class="winbar"><span style="width:${p}%"></span></div>
      <div class="winbar-lbl"><span>${h(inn.batting_team)} ${p}%</span><span class="muted">${h(inn.bowling_team)} ${100 - p}%</span></div>
    </div>`;
  return `<div class="live-hero" data-mid="${h(live.id)}" data-sig="${h(sig)}">
    <div class="lh-main">
      <div class="lh-tag"><span class="lh-dot"></span>LIVE<span class="muted" style="font-weight:600;letter-spacing:0"> · ${h(st.rules_name || "Match")}</span></div>
      <div class="lh-teams">${h(st.team_a)} <span class="muted">v</span> ${h(st.team_b)}</div>
      <div class="lh-score"><span class="score__runs">${inn.runs}/${inn.wickets}</span><span class="lh-ov">${h(inn.overs_str)} ov · CRR ${inn.run_rate.toFixed(2)}</span></div>
    </div>
    <div class="lh-side">
      <div class="lh-btns"><a class="btn" href="#/match/${h(live.id)}">${can("match.score") ? "Resume →" : "Watch live →"}</a></div>
      ${win}
    </div>
  </div>`;
}

// Build one sliding card holding every live match as a slide.
function liveCarouselHtml(liveStates, total) {
  const slides = liveStates.map(({ m, st }) => `<div class="live-slide">${liveHeroHtml(m, st)}</div>`).join("");
  const dots = liveStates.map((_, i) => `<button class="lc-dot${i === 0 ? " is-active" : ""}" data-i="${i}" aria-label="Live match ${i + 1}"></button>`).join("");
  return `<div class="section-title" style="margin-top:0"><span class="live-dot-i"></span>Live now <span class="muted" style="font-weight:600">· ${total} matches</span></div>
    <div class="live-carousel" id="liveCarousel">${slides}</div>
    <div class="lc-nav">
      <button class="lc-arrow" id="lcPrev" aria-label="Previous match">‹</button>
      <div class="lc-dots">${dots}</div>
      <button class="lc-arrow" id="lcNext" aria-label="Next match">›</button>
    </div>`;
}

// Home's live cards keep themselves fresh by POLLING, not SSE: home shows up to
// LIVE_CAP (8) live matches and a browser caps ~6 connections per origin, so eight
// EventSources would starve the page. One match view = one SSE (see startLiveStream).
// Only the changed hero is re-rendered, so the carousel keeps its slide + scroll.
let homeLiveTimer = null;
function stopHomeLive() {
  if (homeLiveTimer) { clearInterval(homeLiveTimer); homeLiveTimer = null; }
}
async function refreshHomeLive() {
  if (document.hidden || !navigator.onLine) return;
  const heroes = [...document.querySelectorAll(".live-hero[data-mid]")];
  if (!heroes.length) return stopHomeLive();
  await Promise.all(heroes.map(async (el) => {
    const id = el.dataset.mid;
    try {
      const st = await api.match(id);
      const inn = st.innings[st.current_innings - 1];
      const sig = `${inn.runs}/${inn.wickets}/${inn.overs_str}/${st.result || ""}`;
      if (el.dataset.sig === sig) return;  // nothing new — leave the DOM (and its pulse) alone
      el.outerHTML = liveHeroHtml({ id }, st);
    } catch (e) { /* transient — try again next tick */ }
  }));
}

// Wire the live carousel: dots, arrows, swipe→dot sync, gentle auto-advance.
let liveCarouselTimer = null;
function setupLiveCarousel() {
  if (liveCarouselTimer) { clearInterval(liveCarouselTimer); liveCarouselTimer = null; }
  const car = document.getElementById("liveCarousel");
  if (!car) return;
  const slides = [...car.querySelectorAll(".live-slide")];
  const dots = [...document.querySelectorAll(".lc-dot")];
  if (slides.length < 2) return;
  let idx = 0;
  const paint = () => dots.forEach((d, j) => d.classList.toggle("is-active", j === idx));
  const stop = () => { if (liveCarouselTimer) { clearInterval(liveCarouselTimer); liveCarouselTimer = null; } };
  const go = (i, smooth = true) => {
    idx = (i + slides.length) % slides.length;
    // offsetLeft is relative to the carousel (position:relative) = the scroll-content x
    car.scrollTo({ left: slides[idx].offsetLeft, behavior: smooth ? "smooth" : "auto" });
    paint();
  };
  dots.forEach((d, i) => d.addEventListener("click", () => { stop(); go(i); }));
  const prev = document.getElementById("lcPrev"), next = document.getElementById("lcNext");
  if (prev) prev.addEventListener("click", () => { stop(); go(idx - 1); });
  if (next) next.addEventListener("click", () => { stop(); go(idx + 1); });
  // keep the dots in sync when the user swipes/scrolls the card directly
  let t;
  car.addEventListener("scroll", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      const w = slides[0].offsetWidth + 14;
      const i = Math.max(0, Math.min(slides.length - 1, Math.round(car.scrollLeft / w)));
      if (i !== idx) { idx = i; paint(); }
    }, 80);
  });
  car.addEventListener("pointerdown", stop, { once: true });
  liveCarouselTimer = setInterval(() => {
    if (!document.body.contains(car)) { stop(); return; }  // route changed away → cleanup
    go(idx + 1);
  }, 5000);
}

// Pending umpire requests across the matches you own — one Approve/Decline inbox
// (so the organizer doesn't have to open each match). Renders nothing if empty.
function officReqRow(it) {
  return `<div class="matchitem">${avatar(it.umpire_name)}
    <div class="mi-main"><b>${h(it.umpire_name)}</b><div class="tiny muted">wants to officiate · ${h(it.match_label)}</div></div>
    <span class="rr-actions"><button class="btn btn--sm ofr-ok" data-mid="${h(it.match_id)}" data-uid="${h(it.umpire_id)}">Approve</button><button class="btn btn--ghost btn--sm ofr-no" data-mid="${h(it.match_id)}" data-uid="${h(it.umpire_id)}">Decline</button></span></div>`;
}
async function loadOfficiatingRequests(containerId) {
  if (!isAuthed()) return;
  const el = document.getElementById(containerId);
  if (!el) return;
  let items = [];
  try { items = await api.pendingOfficials(); } catch (e) { return; }
  if (!items.length) { el.innerHTML = ""; return; }
  el.innerHTML = `<div class="section-title">${icon("gavel")} Requests to officiate <span class="muted">· ${items.length}</span></div>
    <div class="card" id="ofrList">${items.map(officReqRow).join("")}</div>`;
  el.querySelector("#ofrList").onclick = async (e) => {
    const ok = e.target.closest(".ofr-ok"), no = e.target.closest(".ofr-no");
    if (!ok && !no) return;
    const btn = ok || no;
    btn.disabled = true;
    try {
      if (ok) { await api.approveOfficial(btn.dataset.mid, btn.dataset.uid); toast("Approved ✓"); }
      else { await api.removeOfficial(btn.dataset.mid, btn.dataset.uid); toast("Declined"); }
      loadOfficiatingRequests(containerId);  // refresh the inbox
    } catch (err) { toast(err.message, "error"); btn.disabled = false; }
  };
}

async function renderHome() {
  view.innerHTML = `<div class="empty">Loading…</div>`;
  const [matches, players, teams, tours, lb] = await Promise.all([
    api.matches().catch(() => []), api.players().catch(() => []), api.teams().catch(() => []),
    api.tournaments().catch(() => []), api.leaderboards().catch(() => null),
  ]);
  const liveMatches = matches.filter((m) => m.status !== "complete");
  const LIVE_CAP = 8;  // fetch full state (for scores/win bar) for up to this many; rest list compactly
  const liveStates = (await Promise.all(
    liveMatches.slice(0, LIVE_CAP).map((m) => api.match(m.id).then((st) => ({ m, st })).catch(() => null))
  )).filter(Boolean);

  const hr = new Date().getHours();
  const part = hr < 12 ? "morning" : hr < 17 ? "afternoon" : "evening";
  const name = (auth.user && (auth.user.full_name || "").trim().split(/\s+/)[0]) || "there";
  const dateStr = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  let hero;
  if (liveStates.length === 0) {
    hero = `<div class="hero"><h1>CricNetra</h1><p>Score like a pro, build your stats, run leagues &amp; knockouts — your rules.</p></div>`;
  } else if (liveStates.length === 1) {
    hero = liveHeroHtml(liveStates[0].m, liveStates[0].st);
  } else {
    // multiple live matches → one card that slides through them all
    const overflow = liveMatches.slice(LIVE_CAP).map(matchRow).join("");
    hero = liveCarouselHtml(liveStates, liveMatches.length)
      + (overflow ? `<div class="card" style="margin-bottom:18px">${overflow}</div>` : "");
  }

  const kpi = (label, v) => `<div class="kpi"><div class="kpi-top"><span class="kpi-k">${label}</span>
    <svg class="kpi-spark" viewBox="0 0 60 20" preserveAspectRatio="none"><polyline points="${DASH_SPARK}"/></svg></div>
    <div class="kpi-v">${v}</div></div>`;
  const liveCount = liveMatches.length;
  const kpis = `<div class="kpis">${kpi("Matches", matches.length)}${kpi("Live now", liveCount)}${kpi("Players", players.length)}${kpi("Teams", teams.length)}</div>`;

  const recent = matches.length
    ? matches.slice().reverse().slice(0, 6).map(matchRow).join("")
    : `<div class="empty"><span class="empty-ico">${icon("stumps")}</span>No matches yet.<br>Tap the + to start scoring.</div>`;
  const perf = (lb && lb.most_runs && lb.most_runs.length)
    ? lb.most_runs.slice(0, 5).map((e, i) => `<a class="matchitem" href="#/player/${h(e.player_id)}">
        <span class="kpi-rank">${i + 1}</span>${avatar(e.name, "avatar--sm")}
        <div class="mi-main"><b>${h(e.name)}</b><div class="tiny muted">${h(e.detail || "")}</div></div>
        <b class="mono">${e.value}</b></a>`).join("")
    : `<div class="empty tiny">No stats yet — score a match.</div>`;

  view.innerHTML = `
    <div class="dash-greeting"><div class="dg-date">${h(dateStr)}</div><h1>Good ${part}, ${h(name)}</h1></div>
    ${hero}
    <div id="officReqs"></div>
    ${kpis}
    <div class="dash-cols">
      <div><div class="section-title" style="margin-top:0">Recent matches</div><div class="card">${recent}</div></div>
      <div><div class="section-title" style="margin-top:0">Top run-scorers</div><div class="card">${perf}</div></div>
    </div>
    <div class="section-title">Quick actions</div>
    ${QUICK_TILES}`;
  setupLiveCarousel();
  stopHomeLive();
  if (liveStates.length) homeLiveTimer = setInterval(refreshHomeLive, 10000);
  loadOfficiatingRequests("officReqs");
}

// --------------------------------------------------------------------------
// New match
// --------------------------------------------------------------------------
function fmtSelect(presets, templates) {
  const p = presets
    .map((x) => `<option value="preset:${h(x.id)}">${h(x.name)} — ${x.overs_per_innings}ov · ${x.players_per_side}-a-side${x.last_man_stands ? " · LMS" : ""}</option>`)
    .join("");
  const t = templates
    .map((x) => `<option value="template:${h(x.id)}">${h(x.name)} — ${x.rules.overs_per_innings}ov${x.rules.over_boundary_out ? " · rule-out" : ""}</option>`)
    .join("");
  return `<select id="fmt"><optgroup label="Formats">${p}</optgroup>${templates.length ? `<optgroup label="My templates">${t}</optgroup>` : ""}</select>`;
}

async function applyFmt(payload, sel) {
  if (sel.startsWith("preset:")) payload.format_id = sel.slice(7);
  else payload.rules = (await api.template(sel.slice(9))).rules;
}

const val = (id, def = "") => (document.getElementById(id).value || "").trim() || def;

async function renderNew() {
  if (!gate("match.create", "score a match")) return;
  const [presets, templates, teams] = await Promise.all([api.presets(), api.templates(), api.teams()]);
  let mode = "quick";
  let batFirst = "a";

  const inits = (name) => {
    const p = (name || "").trim().split(/\s+/).filter(Boolean);
    if (!p.length) return "?";
    return (p.length === 1 ? p[0].slice(0, 2) : p[0][0] + p[1][0]).toUpperCase();
  };
  const colorFor = (name) => {
    let n = 0;
    for (const c of (name || "x")) n = (n * 31 + c.charCodeAt(0)) % 360;
    return `hsl(${n}, 45%, 42%)`;
  };

  view.innerHTML = `
    <div class="nm-wrap">
      <div class="nm-head"><h2>New match</h2><p class="nm-sub">Set up a match and start scoring ball-by-ball — by your rules.</p></div>
      <div class="nm-grid">
        <div class="nm-left">
          <div class="seg" id="modeSeg">
            <button type="button" data-v="quick" class="active">Quick</button>
            <button type="button" data-v="teams">From teams</button>
          </div>
          <div class="spacer"></div>
          <div id="formArea"></div>
        </div>
        <aside class="nm-right">
          <div class="nm-card">
            <div class="nm-card-label">Match preview</div>
            <div class="nm-vs">
              <div class="nm-team"><span class="nm-av" id="pvAav">ST</span><span class="nm-tn" id="pvA">Strikers</span></div>
              <span class="nm-vs-b">vs</span>
              <div class="nm-team"><span class="nm-av" id="pvBav">BL</span><span class="nm-tn" id="pvB">Blasters</span></div>
            </div>
            <div class="nm-meta">
              <div class="nm-meta-row"><span>Format</span><b id="pvFmt">T20</b></div>
              <div class="nm-meta-row"><span>Overs</span><b id="pvOvers">20 overs</b></div>
              <div class="nm-meta-row"><span>Squad</span><b id="pvPlayers">11-a-side</b></div>
              <div class="nm-meta-row"><span>Rules</span><b id="pvTags">Standard</b></div>
              <div class="nm-meta-row"><span>Bats first</span><b id="pvBat">Strikers</b></div>
            </div>
            <ul class="nm-tips">
              <li>Ball-by-ball scoring with instant undo</li>
              <li>A shareable public scorecard link</li>
              <li>Career stats &amp; leaderboards, automatically</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>`;

  const modeBtns = view.querySelectorAll("#modeSeg button");
  modeBtns.forEach((b) => (b.onclick = () => {
    mode = b.dataset.v;
    modeBtns.forEach((x) => x.classList.toggle("active", x === b));
    renderForm();
  }));

  function fmtInfo() {
    const sel = document.getElementById("fmt");
    if (!sel || !sel.value) return null;
    const v = sel.value;
    if (v.indexOf("preset:") === 0) return presets.find((p) => p.id === v.slice(7)) || null;
    const t = templates.find((x) => x.id === v.slice(9));
    return t ? t.rules : null;
  }

  function syncPreview() {
    let aName = "Team A", bName = "Team B";
    if (mode === "quick") {
      const ea = document.getElementById("teamA"), eb = document.getElementById("teamB");
      aName = (ea && ea.value.trim()) || "Team A";
      bName = (eb && eb.value.trim()) || "Team B";
    } else {
      const tA = document.getElementById("tA"), tB = document.getElementById("tB");
      const fa = tA && teams.find((t) => t.id === tA.value);
      const fb = tB && teams.find((t) => t.id === tB.value);
      aName = fa ? fa.name : "Team A";
      bName = fb ? fb.name : "Team B";
    }
    const setT = (id, t) => { const e = document.getElementById(id); if (e) e.textContent = t; };
    const setAv = (id, name) => { const e = document.getElementById(id); if (e) { e.textContent = inits(name); e.style.background = colorFor(name); } };
    setT("pvA", aName); setAv("pvAav", aName);
    setT("pvB", bName); setAv("pvBav", bName);
    const f = fmtInfo();
    if (f) {
      setT("pvFmt", f.name || "Custom");
      setT("pvOvers", f.overs_per_innings + (f.overs_per_innings === 1 ? " over" : " overs"));
      setT("pvPlayers", f.players_per_side + "-a-side");
      const tags = [];
      if (f.over_boundary_out) tags.push("Rule-out");
      if (f.last_man_stands) tags.push("Last-man-stands");
      if (f.super_over_on_tie) tags.push("Super over");
      if (f.dls_enabled) tags.push("DLS");
      if (f.allow_declaration) tags.push("Declarations");
      if (f.powerplays && f.powerplays.length) tags.push(f.powerplays.length + " powerplay" + (f.powerplays.length > 1 ? "s" : ""));
      setT("pvTags", tags.length ? tags.join(" · ") : "Standard");
    }
    setT("pvBat", batFirst === "a" ? aName : bName);
  }

  function renderForm() {
    const area = document.getElementById("formArea");
    if (mode === "quick") {
      area.innerHTML = `<div class="card">
        <label>Team A</label><input id="teamA" value="Strikers" autocomplete="off">
        <label>Team B</label><input id="teamB" value="Blasters" autocomplete="off">
        <label>Format / rules</label>${fmtSelect(presets, templates)}
        <label>Bats first</label>
        <div class="seg" id="batFirst"><button type="button" data-v="a" class="active">Team A</button><button type="button" data-v="b">Team B</button></div>
        ${matchMetaFieldsHtml()}
        <div class="spacer"></div>
        <button class="btn" id="createBtn">Create &amp; score →</button>
        <p class="tiny muted">Squads are auto-generated. Pick “From teams” to choose a real XI.</p>
      </div>`;
      segPick("#batFirst", (v) => { batFirst = v; syncPreview(); });
      document.getElementById("teamA").oninput = syncPreview;
      document.getElementById("teamB").oninput = syncPreview;
      document.getElementById("fmt").onchange = syncPreview;
      document.getElementById("createBtn").onclick = async (ev) => {
        ev.target.disabled = true;
        try {
          const payload = { team_a: val("teamA", "Team A"), team_b: val("teamB", "Team B"), bat_first: batFirst };
          readMatchMeta(payload);
          await applyFmt(payload, document.getElementById("fmt").value);
          nav(`#/match/${(await api.createMatch(payload)).id}`);
        } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
      };
    } else {
      if (!teams.length) {
        area.innerHTML = `<div class="card empty">No teams yet.<br><a class="btn btn--ghost btn--sm" href="#/teams" style="margin-top:8px">Create teams →</a></div>`;
        syncPreview();
        return;
      }
      const opts = teams.map((t) => `<option value="${h(t.id)}">${h(t.name)}</option>`).join("");
      area.innerHTML = `<div class="card">
        <label>Team A</label><select id="tA">${opts}</select><div id="xiA" class="xi"></div>
        <label>Team B</label><select id="tB">${opts}</select><div id="xiB" class="xi"></div>
        <label>Format / rules</label>${fmtSelect(presets, templates)}
        <label>Bats first</label>
        <div class="seg" id="batFirst2"><button type="button" data-v="a" class="active">Team A</button><button type="button" data-v="b">Team B</button></div>
        ${matchMetaFieldsHtml()}
        <div class="spacer"></div>
        <button class="btn" id="createBtn2">Create &amp; score →</button>
        <p class="tiny muted">Tick the playing XI for each side (equal sizes).</p>
      </div>`;
      segPick("#batFirst2", (v) => { batFirst = v; syncPreview(); });
      if (teams.length > 1) document.getElementById("tB").value = teams[1].id;
      const loadXI = async (selId, boxId) => {
        const team = await api.team(document.getElementById(selId).value);
        document.getElementById(boxId).innerHTML = team.members.length
          ? team.members.map((m) => `<label class="ximember"><input type="checkbox" checked value="${h(m.player_id)}" data-name="${h(m.name)}">${h(m.name)}${m.is_captain ? " (c)" : ""}</label>`).join("")
          : `<div class="tiny muted">No players — add some in Teams.</div>`;
      };
      document.getElementById("tA").onchange = () => { loadXI("tA", "xiA"); syncPreview(); };
      document.getElementById("tB").onchange = () => { loadXI("tB", "xiB"); syncPreview(); };
      document.getElementById("fmt").onchange = syncPreview;
      loadXI("tA", "xiA");
      loadXI("tB", "xiB");
      document.getElementById("createBtn2").onclick = async (ev) => {
        ev.target.disabled = true;
        try {
          const checked = (boxId) => [...document.querySelectorAll(`#${boxId} input:checked`)];
          const a = checked("xiA"), b = checked("xiB");
          if (a.length < 2 || b.length < 2) throw new Error("Pick at least 2 players per side");
          if (a.length !== b.length) throw new Error("Both sides need the same number of players");
          const teamA = teams.find((t) => t.id === document.getElementById("tA").value);
          const teamB = teams.find((t) => t.id === document.getElementById("tB").value);
          const payload = {
            team_a: teamA.name, team_b: teamB.name, bat_first: batFirst,
            squad_a: a.map((c) => c.dataset.name), squad_b: b.map((c) => c.dataset.name),
            squad_a_ids: a.map((c) => c.value), squad_b_ids: b.map((c) => c.value),
            team_a_id: teamA.id, team_b_id: teamB.id,
          };
          readMatchMeta(payload);
          await applyFmt(payload, document.getElementById("fmt").value);
          nav(`#/match/${(await api.createMatch(payload)).id}`);
        } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
      };
    }
    syncPreview();
  }
  renderForm();
}

// Optional match-setup metadata (venue / toss / tournament) shared by both New-match
// form modes. Collapsed by default so the common path stays a two-team + format form.
function matchMetaFieldsHtml() {
  return `<details class="match-extra">
    <summary>Match details <span class="tiny muted">— venue, toss, tournament (optional)</span></summary>
    <label>Tournament</label><input id="mTournament" placeholder="e.g. Summer Cup 2026" autocomplete="off" maxlength="120">
    <div class="mrow">
      <div><label>Match #</label><input id="mMatchNo" placeholder="e.g. 12 / Final" autocomplete="off" maxlength="40"></div>
      <div><label>Venue</label><input id="mVenue" placeholder="Ground / stadium" autocomplete="off" maxlength="120"></div>
    </div>
    <label>Toss</label>
    <div class="mrow">
      <select id="mTossWinner"><option value="">Won by…</option><option value="a">Team A</option><option value="b">Team B</option></select>
      <select id="mTossDecision"><option value="">Elected to…</option><option value="bat">Bat</option><option value="bowl">Bowl</option></select>
    </div>
  </details>`;
}
function readMatchMeta(payload) {
  const v = (id) => { const el = document.getElementById(id); return el ? el.value.trim() : ""; };
  const t = v("mTournament"); if (t) payload.tournament = t;
  const mn = v("mMatchNo"); if (mn) payload.match_no = mn;
  const vn = v("mVenue"); if (vn) payload.venue = vn;
  const tw = v("mTossWinner");
  if (tw === "a" || tw === "b") {
    payload.toss_winner = tw;
    const td = v("mTossDecision");
    if (td === "bat" || td === "bowl") payload.toss_decision = td;
  }
  return payload;
}

// --------------------------------------------------------------------------
// Teams
// --------------------------------------------------------------------------
async function renderTeams() {
  const canAdd = can("team.create");
  view.innerHTML = `
    <h2>Teams</h2>
    ${canAdd ? `<div class="card">
      <label>Team logo (optional)</label>
      ${photoEditorHtml({ kind: "team", id: null, name: "", hasPhoto: false })}
      <label>New team</label>
      <div class="addrow"><input id="newTeam" placeholder="e.g. Mumbai Mavericks"><button class="btn btn--sm" id="addTeam">Add</button></div>
    </div>` : ""}
    <div class="section-title">Your teams</div>
    ${searchBox("teamSearch", "Search your teams by name…")}
    <div id="teamList" class="card-grid"><div class="empty">Loading…</div></div>`;
  let newTeamLogo = null;  // chosen before the team exists; uploaded after create
  bindPhotoEditor(view.querySelector(".photo-edit"), {
    kind: "team", name: "", getId: () => null, onLocalFile: (f) => (newTeamLogo = f),
  });
  if (canAdd) document.getElementById("addTeam").onclick = async () => {
    const name = val("newTeam");
    if (!name) return;
    try {
      const team = await api.createTeam({ name });
      if (newTeamLogo) {
        try { await api.uploadPhoto("team", team.id, newTeamLogo); photoBust = Date.now(); }
        catch (e) { toast("Team created, but logo failed: " + e.message, "error"); }
        newTeamLogo = null;
      }
      document.getElementById("newTeam").value = "";
      const pe = view.querySelector(".photo-edit");
      if (pe) {
        pe.querySelector(".pe-prev").innerHTML = avatar("?", "avatar--lg");
        pe.querySelector(".pe-rm").hidden = true;
        pe.querySelector(".pe-pick").textContent = "Upload photo";
        pe.querySelector(".pe-file").value = "";
      }
      refresh();
    } catch (e) { toast(e.message, "error"); }
  };
  let allTeams = [];
  function paintTeams() {
    const q = (val("teamSearch") || "").toLowerCase();
    const list = q ? allTeams.filter((t) => (t.name || "").toLowerCase().includes(q) || (t.location || "").toLowerCase().includes(q)) : allTeams;
    document.getElementById("teamList").innerHTML = list.length
      ? list.map((t) => `<a class="card team-card" href="#/team/${h(t.id)}">
          ${photoAvatar("team", t.id, t.name, "", t.has_photo)}
          <div class="mi-main"><b>${h(t.name)}</b><div class="tiny muted">${t.members.length} player${t.members.length === 1 ? "" : "s"}${t.location ? " · " + h(t.location) : ""}</div></div>
          <span class="badge badge--grey">open ›</span></a>`).join("")
      : `<div class="empty">${allTeams.length ? "No teams match your search." : "No teams yet. Add one above."}</div>`;
  }
  async function refresh() {
    allTeams = await api.teams();
    paintTeams();
  }
  document.getElementById("teamSearch").oninput = paintTeams;
  refresh();
}

const titleCase = (s) => (s || "").replace(/\b\w/g, (c) => c.toUpperCase());  // "rohit" -> "Rohit"

// A tiny custom dropdown so each row can lay out left/right ("P00047 - Rohit" on
// the left, "in MI" pushed to the right) — native <option> can't. Options:
//   {value, left, right?}             a normal selectable row
//   {value, left, right?, accent}     a highlighted action (e.g. "＋ Create…")
//   {value, left, right?, disabled}   shown greyed, not selectable
//   {group}                           a non-selectable section header
// The chosen value is read from container.dataset.value; selecting fires 'change'.
function closeAllCdd(except) {
  document.querySelectorAll(".cdd-menu:not([hidden])").forEach((m) => {
    if (except && m === except) return;
    m.hidden = true;
    const t = m.closest(".cdd") && m.closest(".cdd").querySelector(".cdd-trigger");
    if (t) t.setAttribute("aria-expanded", "false");
  });
}
document.addEventListener("mousedown", (e) => { if (!e.target.closest(".cdd")) closeAllCdd(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAllCdd(); });

function cdd(container, options, placeholder) {
  const current = String(container.dataset.value || "");
  const pickable = options.filter((o) => !o.group && !o.disabled && o.value !== undefined);
  const selected = pickable.find((o) => String(o.value) === current);
  const tagOf = (o) => (o.right ? `<span class="cdd-tag">${h(o.right)}</span>` : "");
  const rowHtml = (o) => {
    if (o.group) return `<div class="cdd-group">${h(o.group)}</div>`;
    if (o.disabled) return `<div class="cdd-opt cdd-opt--off"><span class="cdd-main">${h(o.left)}</span>${tagOf(o)}</div>`;
    const cls = "cdd-opt" + (o.accent ? " cdd-opt--accent" : "");
    return `<div class="${cls}" role="option" data-value="${h(String(o.value))}" aria-selected="${String(o.value) === current}"><span class="cdd-main">${h(o.left)}</span>${tagOf(o)}</div>`;
  };
  container.innerHTML = `
    <button type="button" class="cdd-trigger" aria-haspopup="listbox" aria-expanded="false" ${pickable.length ? "" : "disabled"}>
      <span class="cdd-label${selected ? "" : " is-ph"}">${h(selected ? selected.left : placeholder)}</span>
      <span class="cdd-caret" aria-hidden="true">▾</span>
    </button>
    <div class="cdd-menu" role="listbox" hidden>
      ${options.length ? options.map(rowHtml).join("") : `<div class="cdd-opt cdd-opt--off">${h(placeholder)}</div>`}
    </div>`;
  const trigger = container.querySelector(".cdd-trigger");
  const menu = container.querySelector(".cdd-menu");
  const label = container.querySelector(".cdd-label");
  trigger.onclick = () => {
    const willOpen = menu.hidden;
    closeAllCdd();
    if (willOpen) { menu.hidden = false; trigger.setAttribute("aria-expanded", "true"); }
  };
  menu.querySelectorAll(".cdd-opt[data-value]").forEach((opt) => (opt.onclick = () => {
    container.dataset.value = opt.dataset.value;
    const o = pickable.find((x) => String(x.value) === String(opt.dataset.value));
    label.textContent = o ? o.left : placeholder;
    label.classList.toggle("is-ph", !o);
    menu.querySelectorAll(".cdd-opt[data-value]").forEach((x) => x.setAttribute("aria-selected", x === opt));
    closeAllCdd();
    container.dispatchEvent(new Event("change"));
  }));
}

async function renderTeam(id) {
  const [team, stats, players, allTeams] = await Promise.all([
    api.team(id), api.teamStats(id).catch(() => null), api.players(), api.teams().catch(() => []),
  ]);
  // Which *other* teams each player already belongs to — shown as a hint in the
  // picker so an organizer sees existing memberships before adding. A player may
  // be in several teams (that's allowed), so this informs rather than blocks.
  const teamsByPlayer = new Map();
  allTeams.forEach((t) => {
    if (String(t.id) === String(id)) return;  // skip the team being edited
    (t.members || []).forEach((m) => {
      const k = String(m.player_id);
      if (!teamsByPlayer.has(k)) teamsByPlayer.set(k, []);
      teamsByPlayer.get(k).push(t.name);
    });
  });
  const teamTag = (pid) => {  // bare right-side label, e.g. "in MI" or "in MI, RCB"
    const names = teamsByPlayer.get(String(pid)) || [];
    if (!names.length) return "";
    const shown = names.slice(0, 2).map((n) => n.toUpperCase()).join(", ");  // team names in CAPS
    return `in ${shown}${names.length > 2 ? ` +${names.length - 2}` : ""}`;
  };
  const record = stats ? `
    <div class="card">
      <div class="record">
        <div class="stat"><div class="stat__v">${stats.played}</div><div class="stat__k">Played</div></div>
        <div class="stat"><div class="stat__v">${stats.won}</div><div class="stat__k">Won</div></div>
        <div class="stat"><div class="stat__v">${stats.lost}</div><div class="stat__k">Lost</div></div>
        <div class="stat"><div class="stat__v">${stats.tied}</div><div class="stat__k">Tied</div></div>
        <div class="stat"><div class="stat__v">${stats.win_pct}%</div><div class="stat__k">Win%</div></div>
      </div>
      <div class="tiny muted" style="margin-top:8px">Runs for ${stats.runs_for} · against ${stats.runs_against}</div>
    </div>` : "";
  view.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px"><span id="tHero">${photoAvatar("team", team.id, team.name, "avatar--lg", team.has_photo)}</span><h2 style="margin:0">${h(team.name)}</h2><span style="margin-left:auto">${followBtnHtml("team", team.id)}</span></div>
    ${record}
    <div class="card">
      <div class="section-title" style="margin-top:0">Team logo</div>
      ${photoEditorHtml({ kind: "team", id: team.id, name: team.name, hasPhoto: team.has_photo })}
    </div>
    <div class="card">
      <label>Add an existing player</label>
      <div class="addrow"><div class="cdd" id="pickPlayer"></div><button class="btn btn--sm" id="addExisting">Add</button></div>
      <label style="margin-top:12px">…or create a new player</label>
      <div class="addrow"><input id="newPlayer" placeholder="New player name"><button class="btn btn--ghost btn--sm" id="addPlayer">Add new</button></div>
      <div class="spacer"></div>
      <div class="section-title">Squad (<span id="sqCount">${team.members.length}</span>)</div>
      <div id="members"></div>
    </div>
    ${(auth.user && auth.user.role === "admin") ? `<button class="btn btn--red" id="delTeam">Delete team</button>` : ""}`;
  // dropdown of pool players not already in this squad (add via player_id → no dup)
  function buildPicker(members) {
    const inSquad = new Set(members.map((m) => String(m.player_id)));
    const avail = players.filter((p) => !inSquad.has(String(p.id)));
    const container = document.getElementById("pickPlayer");
    container.dataset.value = "";
    cdd(container, avail.map((p) => ({
      value: p.id,
      left: `${p.code || pcode(p.id)} - ${titleCase(p.name)}`,
      right: teamTag(p.id),
    })), avail.length ? "Choose an existing player…" : "No other players in your pool");
    document.getElementById("addExisting").disabled = !avail.length;
  }
  function renderMembers(t) {
    document.getElementById("sqCount").textContent = t.members.length;
    const el = document.getElementById("members");
    el.innerHTML = t.members.length
      ? t.members.map((m) => `<div class="matchitem">${photoAvatar("player", m.player_id, m.name, "", m.has_photo)}
          <a class="mi-main" href="#/player/${h(m.player_id)}" style="text-decoration:none;color:inherit"><b>${h(m.name)}</b>${m.is_captain ? " <span class='badge'>C</span>" : ""}<div class="tiny muted">${h(m.code || pcode(m.player_id))}</div></a>
          <button class="btn btn--ghost btn--sm" data-rm="${h(m.player_id)}">Remove</button></div>`).join("")
      : `<div class="empty">No players yet.</div>`;
    el.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = async () => {
      try { renderMembers(await api.removeMember(id, b.dataset.rm)); } catch (e) { toast(e.message, "error"); }
    }));
    buildPicker(t.members);
  }
  renderMembers(team);
  bindPhotoEditor(view.querySelector(".photo-edit"), {
    kind: "team", name: team.name, getId: () => id,
    onChanged: (has) => {
      team.has_photo = has;
      const hero = document.getElementById("tHero");
      if (hero) hero.innerHTML = photoAvatar("team", id, team.name, "avatar--lg", has);
    },
  });
  // 1) add an existing player from the pool (no duplicate)
  document.getElementById("addExisting").onclick = async () => {
    const pid = document.getElementById("pickPlayer").dataset.value;
    if (!pid) return;
    try { renderMembers(await api.addMember(id, { player_id: pid })); }
    catch (e) { toast(e.message, "error"); }
  };
  // 2) create a brand-new player by name (and keep it in the pool for re-use)
  document.getElementById("addPlayer").onclick = async () => {
    const name = val("newPlayer");
    if (!name) return;
    try {
      const t = await api.addMember(id, { name });
      const added = t.members.find((m) => !players.some((p) => String(p.id) === String(m.player_id)));
      if (added) players.push({ id: added.player_id, name: added.name, code: added.code });
      renderMembers(t);
      document.getElementById("newPlayer").value = "";
    } catch (e) { toast(e.message, "error"); }
  };
  const delTeamBtn = document.getElementById("delTeam");  // admins only (see markup)
  if (delTeamBtn) delTeamBtn.onclick = async () => {
    if (!confirm(`Delete team "${team.name}"? This can't be undone.`)) return;
    try { await api.deleteTeam(id); nav("#/teams"); } catch (e) { toast(e.message, "error"); }
  };
}

// --------------------------------------------------------------------------
// Players + profiles
// --------------------------------------------------------------------------
const BAT_STYLES = ["Right-hand bat", "Left-hand bat"];
const BOWL_STYLES = [
  "Right-arm fast", "Right-arm medium", "Right-arm off-spin", "Right-arm leg-spin",
  "Left-arm fast", "Left-arm medium", "Left-arm orthodox", "Left-arm wrist-spin",
];
function styleOptions(list, selected) {
  return ["", ...list]
    .map((o) => `<option value="${h(o)}" ${o === (selected || "") ? "selected" : ""}>${o || "—"}</option>`)
    .join("");
}

async function renderPlayers() {
  const canAdd = can("team.create");
  view.innerHTML = `
    <h2>Players</h2>
    ${canAdd ? `<div class="card">
      <label>Player photo (optional)</label>
      ${photoEditorHtml({ kind: "player", id: null, name: "", hasPhoto: false })}
      <label>New player</label>
      <input id="np_name" placeholder="Name">
      <label>Phone</label>
      <input id="np_phone" placeholder="optional">
      <div class="row">
        <div><label>Batting style</label><select id="np_bat">${styleOptions(BAT_STYLES)}</select></div>
        <div><label>Bowling style</label><select id="np_bowl">${styleOptions(BOWL_STYLES)}</select></div>
      </div>
      <div class="spacer"></div>
      <button class="btn" id="np_add">Add player</button>
    </div>` : ""}
    <div class="section-title">All players</div>
    ${searchBox("playerSearch", "Search players by name or code…")}
    <div class="card" id="plist"><div class="empty">Loading…</div></div>`;

  let newPlayerFile = null;  // chosen before the player exists; uploaded after create
  bindPhotoEditor(view.querySelector(".photo-edit"), {
    kind: "player", name: "", getId: () => null, onLocalFile: (f) => (newPlayerFile = f),
  });

  if (canAdd) document.getElementById("np_add").onclick = async (ev) => {
    const name = val("np_name");
    if (!name) { toast("Enter a name", "error"); return; }
    ev.target.disabled = true;
    try {
      const created = await api.createPlayer({
        name,
        phone: val("np_phone") || null,
        batting_style: document.getElementById("np_bat").value || null,
        bowling_style: document.getElementById("np_bowl").value || null,
      });
      if (newPlayerFile) {
        try { await api.uploadPhoto("player", created.id, newPlayerFile); photoBust = Date.now(); }
        catch (e) { toast("Player added, but photo failed: " + e.message, "error"); }
        newPlayerFile = null;
      }
      ["np_name", "np_phone"].forEach((id) => (document.getElementById(id).value = ""));
      const pe = view.querySelector(".photo-edit");
      if (pe) {
        pe.querySelector(".pe-prev").innerHTML = avatar("?", "avatar--lg");
        pe.querySelector(".pe-rm").hidden = true;
        pe.querySelector(".pe-pick").textContent = "Upload photo";
        pe.querySelector(".pe-file").value = "";
      }
      toast("Player added ✓");
      refresh();
    } catch (e) { toast(e.message, "error"); }
    finally { ev.target.disabled = false; }
  };

  let allPlayers = [];
  function paintPlayers() {
    const q = (val("playerSearch") || "").toLowerCase();
    const list = q ? allPlayers.filter((p) => (p.name || "").toLowerCase().includes(q) || (p.code || pcode(p.id) || "").toLowerCase().includes(q)) : allPlayers;
    document.getElementById("plist").innerHTML = list.length
      ? list.map((p) => `<a class="matchitem" href="#/player/${h(p.id)}">
          ${photoAvatar("player", p.id, p.name, "", p.has_photo)}
          <div class="mi-main"><b>${h(p.name)}</b><div class="tiny muted"><span class="pcode">${h(p.code || pcode(p.id))}</span>${[p.batting_style, p.bowling_style].filter(Boolean).length ? " · " + [p.batting_style, p.bowling_style].filter(Boolean).map(h).join(" · ") : ""}</div></div>
          <span class="badge badge--grey">stats ›</span></a>`).join("")
      : `<div class="empty">${allPlayers.length ? "No players match your search." : "No players yet. Add one above."}</div>`;
  }
  async function refresh() {
    allPlayers = await api.players();
    paintPlayers();
  }
  document.getElementById("playerSearch").oninput = paintPlayers;
  refresh();
}

function statGrid(pairs) {
  return `<div class="stats">${pairs
    .map(([k, v]) => `<div class="stat"><div class="stat__v">${h(v)}</div><div class="stat__k">${h(k)}</div></div>`)
    .join("")}</div>`;
}

function breakdown(dict, labelFn) {
  const entries = Object.entries(dict || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return "";
  const max = Math.max(...entries.map((e) => e[1]));
  return `<div style="margin-top:8px">${entries.map(([k, v]) => `<div class="bd-row">
    <span class="bd-label">${h(labelFn ? labelFn(k) : k)}</span>
    <span class="bd-bar"><span style="width:${Math.round(100 * v / max)}%"></span></span>
    <span class="bd-val">${v}</span></div>`).join("")}</div>`;
}

function insightsSection(ins) {
  if (!ins || (!ins.batting.balls_faced && !ins.bowling.balls_bowled)) return "";
  const label = (k) => DISMISSALS[k] || k;
  let html = "";
  if (ins.batting.balls_faced) {
    const d = ins.batting;
    html += `<div class="section-title">Batting insights</div>
      <div class="card">${statGrid([
        ["Dot %", d.dot_pct], ["Boundary %", d.boundary_pct], ["Runs in 4/6", d.boundary_runs_pct + "%"], ["Balls", d.balls_faced],
      ])}${Object.keys(d.dismissals || {}).length ? `<div class="tiny muted" style="margin-top:14px">How out</div>${breakdown(d.dismissals, label)}` : ""}${d.shots_tracked ? `<div class="tiny muted" style="margin-top:14px">Shot analysis · ${d.shots_tracked} shots</div>${statGrid([["Off side", d.off_side_pct + "%"], ["Leg side", d.leg_side_pct + "%"], ["Six %", d.six_pct + "%"]])}${d.top_zone ? `<div class="tiny" style="margin-top:8px">Most productive area: <b>${h(d.top_zone)}</b></div>` : ""}${breakdown(d.runs_by_zone)}` : ""}</div>`;
  }
  if (ins.bowling.balls_bowled) {
    const d = ins.bowling;
    html += `<div class="section-title">Bowling insights</div>
      <div class="card">${statGrid([["Dot %", d.dot_pct], ["Balls", d.balls_bowled]])}
      ${Object.keys(d.wickets_by_type || {}).length ? `<div class="tiny muted" style="margin-top:14px">Wickets by type</div>${breakdown(d.wickets_by_type, label)}` : ""}${d.pitches_tracked ? `<div class="tiny muted" style="margin-top:14px">Length distribution · ${d.pitches_tracked} tracked</div>${breakdown(d.length_dist)}<div class="tiny muted" style="margin-top:10px">Economy by length</div>${breakdown(d.econ_by_length)}` : ""}</div>`;
  }
  return html;
}

// ----- per-format / per-ball-type splits + pace/spin matchups (#138) --------
function splitTable(colLabel, rows) {
  if (!rows || rows.length < 2) return "";  // a single bucket just repeats career totals
  const row = (s) => {
    const b = s.batting, w = s.bowling;
    return `<tr><td>${h(s.label)}</td><td>${s.matches}</td><td>${b.runs}</td>
      <td>${b.average ?? "–"}</td><td>${b.strike_rate || "–"}</td>
      <td>${w.wickets}</td><td>${w.economy || "–"}</td></tr>`;
  };
  return `<div class="card" style="overflow-x:auto">
    <table class="split-tbl"><thead><tr>
      <th>${colLabel}</th><th>M</th><th>Runs</th><th>Avg</th><th>SR</th><th>Wkts</th><th>Econ</th>
    </tr></thead><tbody>${rows.map(row).join("")}</tbody></table></div>`;
}
function vsCard(v) {
  return `<div class="vs-card">
    <div class="vs-h">${h(v.label)}</div>
    <div class="vs-big">${v.runs}<span> runs</span></div>
    <div class="vs-sub">${v.balls} balls · SR ${v.strike_rate}</div>
    <div class="vs-row"><span>Dismissals</span><b>${v.dismissals}</b></div>
    <div class="vs-row"><span>Dot %</span><b>${v.dot_pct}</b></div>
    <div class="vs-row"><span>4s / 6s</span><b>${v.fours} / ${v.sixes}</b></div>
    <div class="vs-row"><span>Average</span><b>${v.average ?? "–"}</b></div>
  </div>`;
}
function splitsSection(sp) {
  if (!sp) return "";
  const fmt = splitTable("Format", sp.by_format);
  const ball = splitTable("Ball", sp.by_ball);
  const matchup = sp.has_matchup
    ? `<div class="section-title">Batting matchups</div>
       <div class="vs-grid">${vsCard(sp.vs_pace)}${vsCard(sp.vs_spin)}</div>` : "";
  if (!fmt && !ball && !matchup) return "";
  return `${fmt ? `<div class="section-title">By format</div>${fmt}` : ""}
    ${ball ? `<div class="section-title">By ball type</div>${ball}` : ""}
    ${matchup}`;
}

const AWARD_NAMES = { mom: "Man of the Match", best_bat: "Best batter", best_bowl: "Best bowler" };
const AWARD_EMOJI = { mom: "🏅", best_bat: "🏏", best_bowl: "🎯" };

// ---- career history ---------------------------------------------------
// A player's whole record: every match they have played, and how they went in
// each competition. The profile summarises; this answers "what have they
// actually done".

const CAREER_OUTCOMES = {
  won: ["Won", "co-won"],
  lost: ["Lost", "co-lost"],
  tied: ["Tied", "co-tied"],
  no_result: ["No result", "co-nr"],
  in_progress: ["Live", "co-live"],
};

function careerDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

// One line of a career: the fixture, and what this player did in it.
function careerMatchHtml(m) {
  const [label, cls] = CAREER_OUTCOMES[m.outcome] || CAREER_OUTCOMES.in_progress;
  const context = [m.tournament, m.venue, careerDate(m.played_on)].filter(Boolean).map(h).join(" · ");

  // Only the parts that actually happened, so a blank row never needs decoding.
  const bits = [];
  if (m.batted) {
    const milestone = (m.runs || 0) >= 50 ? " is-hl" : "";
    bits.push(`<span class="cm-bit${milestone}">🏏 ${h(m.bat_line || "")}${
      m.dismissal_text ? ` <span class="muted tiny">${h(m.dismissal_text)}</span>` : ""}</span>`);
  }
  if (m.bowled) {
    const haul = (m.wickets || 0) >= 3 ? " is-hl" : "";
    bits.push(`<span class="cm-bit${haul}">⚾ ${h(m.bowl_line || "")}</span>`);
  }
  const field = [
    m.catches ? `${m.catches} ${m.catches === 1 ? "catch" : "catches"}` : "",
    m.run_outs ? `${m.run_outs} run out${m.run_outs === 1 ? "" : "s"}` : "",
    m.stumpings ? `${m.stumpings} stumping${m.stumpings === 1 ? "" : "s"}` : "",
  ].filter(Boolean).join(" · ");
  if (field) bits.push(`<span class="cm-bit">🧤 ${h(field)}</span>`);

  const did = bits.length
    ? `<div class="cm-bits">${bits.join("")}</div>`
    : `<div class="tiny muted">${m.outcome === "in_progress" ? "Yet to bat or bowl" : "Did not bat or bowl"}</div>`;

  return `<a class="cm-row" href="#/match/${h(m.match_id)}">
    <div class="cm-head">
      <b>v ${h(m.opponent)}</b>
      <span class="cm-out ${cls}">${h(label)}</span>
    </div>
    ${context ? `<div class="tiny muted">${context}</div>` : ""}
    ${did}
  </a>`;
}

// One grouping's record — a tournament, a season, or a side.
function careerBucketHtml(b, detailed) {
  const bat = b.batting || {};
  const bowl = b.bowling || {};
  const hasBat = (bat.innings || 0) > 0;
  const hasBowl = (bowl.balls || 0) > 0;

  const batRow = hasBat
    ? statGrid(detailed
      ? [["Inns", bat.innings], ["Runs", bat.runs], ["HS", bat.highest],
         ["Avg", bat.average ?? "–"], ["SR", bat.strike_rate], ["4s", bat.fours],
         ["6s", bat.sixes], ["50s", bat.fifties]]
      : [["Runs", bat.runs], ["Avg", bat.average ?? "–"], ["SR", bat.strike_rate], ["HS", bat.highest]])
    : "";
  const bowlRow = hasBowl
    ? statGrid(detailed
      ? [["Overs", bowl.overs], ["Wkts", bowl.wickets], ["Best", bowl.best],
         ["Avg", bowl.average ?? "–"], ["Econ", bowl.economy], ["Runs", bowl.runs],
         ["Mdns", bowl.maidens], ["Inns", bowl.innings]]
      : [["Wkts", bowl.wickets], ["Econ", bowl.economy], ["Best", bowl.best], ["Overs", bowl.overs]])
    : "";

  return `<div class="card">
    <div class="cb-head">
      <b>${h(b.label)}</b>
      <span class="badge">${b.matches} ${b.matches === 1 ? "match" : "matches"}</span>
    </div>
    ${b.won + b.lost > 0 ? `<div class="tiny muted">${b.won} won · ${b.lost} lost</div>` : ""}
    ${!hasBat && !hasBowl ? `<div class="tiny muted" style="margin-top:8px">Did not bat or bowl.</div>` : ""}
    ${hasBat ? `<div class="tiny muted" style="margin-top:10px">Batting</div>${batRow}` : ""}
    ${hasBowl ? `<div class="tiny muted" style="margin-top:10px">Bowling</div>${bowlRow}` : ""}
  </div>`;
}

async function renderCareer(id) {
  const c = await api.playerHistory(id);
  const p = c.player;

  if (!c.matches_played) {
    view.innerHTML = `<div class="card empty">
      <span class="empty-ico">🏏</span>
      ${h(p.name)} has not played yet.
      <div class="tiny muted" style="margin-top:6px">Once they take the field, every match shows up here
      with their batting, bowling and fielding.</div>
      <div class="spacer"></div>
      <a class="btn btn--ghost btn--sm" href="#/player/${h(id)}">Back to profile</a>
    </div>`;
    return;
  }

  const b = c.batting, w = c.bowling, f = c.fielding;
  const span = c.debut === c.last_played
    ? `Played ${careerDate(c.debut)}`
    : `${careerDate(c.debut)} — ${careerDate(c.last_played)}`;

  // The standout innings and spell, picked out of the whole career.
  const best = c.matches.filter((m) => m.batted)
    .sort((x, y) => (y.runs || 0) - (x.runs || 0))[0];
  const spell = c.matches.filter((m) => m.bowled && (m.wickets || 0) > 0)
    .sort((x, y) => (y.wickets || 0) - (x.wickets || 0) || (x.runs_conceded || 0) - (y.runs_conceded || 0))[0];

  view.innerHTML = `
    <div class="card" style="display:flex;align-items:center;gap:14px">
      ${photoAvatar("player", p.id, p.name, "avatar--lg", p.has_photo)}
      <div>
        <h2 style="margin:0 0 2px">${h(p.name)}</h2>
        <div class="tiny muted">${h(span)}</div>
      </div>
      <a class="btn btn--ghost btn--sm" style="margin-left:auto" href="#/player/${h(id)}">Profile</a>
    </div>

    <div class="card">${statGrid([
      ["Mat", c.matches_played], ["Won", c.won], ["Lost", c.lost], ["Win %", c.win_pct],
    ])}</div>

    ${best || spell ? `<div class="section-title">Career best</div>
    <div class="card cb-best">
      ${best ? `<a class="cm-row" href="#/match/${h(best.match_id)}">
        <div class="cm-head"><b>🏏 ${h(best.bat_line || "")}</b></div>
        <div class="tiny muted">v ${h(best.opponent)}${best.tournament ? " · " + h(best.tournament) : ""}</div>
      </a>` : ""}
      ${spell ? `<a class="cm-row" href="#/match/${h(spell.match_id)}">
        <div class="cm-head"><b>⚾ ${h(spell.bowl_line || "")}</b></div>
        <div class="tiny muted">v ${h(spell.opponent)}${spell.tournament ? " · " + h(spell.tournament) : ""}</div>
      </a>` : ""}
    </div>` : ""}

    ${b.innings ? `<div class="section-title">Batting</div>
    <div class="card">${statGrid([
      ["Inns", b.innings], ["Runs", b.runs], ["HS", b.highest], ["Avg", b.average ?? "–"],
      ["SR", b.strike_rate], ["50s", b.fifties], ["100s", b.hundreds], ["NO", b.not_outs],
    ])}</div>` : ""}

    ${w.balls ? `<div class="section-title">Bowling</div>
    <div class="card">${statGrid([
      ["Inns", w.innings], ["Overs", w.overs], ["Wkts", w.wickets], ["Best", w.best],
      ["Avg", w.average ?? "–"], ["Econ", w.economy], ["Runs", w.runs], ["Mdns", w.maidens],
    ])}</div>` : ""}

    <div class="section-title">Fielding</div>
    <div class="card">${statGrid([
      ["Catches", f.catches], ["Run-outs", f.run_outs], ["Stumpings", f.stumpings],
      ["Runs saved", f.runs_saved || 0],
    ])}</div>

    ${c.by_tournament.length ? `<div class="section-title">By tournament</div>
    ${c.by_tournament.map((t) => careerBucketHtml(t, true)).join("")}` : ""}

    ${c.by_year.length > 1 ? `<div class="section-title">Season by season</div>
    ${c.by_year.map((y) => careerBucketHtml(y, false)).join("")}` : ""}

    ${c.by_team.length ? `<div class="section-title">Teams played for</div>
    ${c.by_team.map((t) => careerBucketHtml(t, false)).join("")}` : ""}

    <div class="section-title">Every match</div>
    <div class="card cm-list">${c.matches.map(careerMatchHtml).join("")}</div>`;
}

async function renderPlayer(id) {
  const [s, ins, sp, awards] = await Promise.all([
    api.playerStats(id),
    api.playerInsights(id).catch(() => null),
    api.playerSplits(id).catch(() => null),
    api.playerAwards(id).catch(() => []),
  ]);
  const p = s.player, b = s.batting, w = s.bowling, f = s.fielding, recent = s.recent || [];
  const style = [p.batting_style, p.bowling_style].filter(Boolean).map(h).join(" · ") || "Cricketer";
  const insightsHtml = insightsSection(ins);
  const splitsHtml = splitsSection(sp);
  const mineP = auth.user && p.claimed_by && String(p.claimed_by) === String(auth.user.id);
  const canClaimP = auth.user && !p.claimed_by && auth.user.is_verified && p.phone && p.phone === auth.user.mobile_no;
  const claimBadge = mineP
    ? `<span class="badge" style="display:inline-block;margin-top:6px">✓ Your profile</span>`
    : canClaimP ? `<button class="btn btn--sm" id="claimThis" style="margin-top:6px">Claim this profile</button>` : "";
  view.innerHTML = `
    <div class="card" style="display:flex;align-items:center;gap:14px">
      <span id="pHero">${photoAvatar("player", p.id, p.name, "avatar--lg", p.has_photo)}</span>
      <div><h2 style="margin:0 0 2px">${h(p.name)}</h2><div class="tiny muted">${style}</div>${claimBadge}</div>
      <span style="margin-left:auto">${followBtnHtml("player", p.id)}</span>
    </div>
    <a class="card cm-row" href="#/career/${h(p.id)}" style="display:block">
      <div class="cm-head"><b>📖 Career history</b><span class="cm-out">→</span></div>
      <div class="tiny muted">${b.matches
        ? `All ${b.matches} ${b.matches === 1 ? "match" : "matches"}, cup by cup`
        : "Every match, once they have played one"}</div>
    </a>
    ${awards && awards.length ? `<div class="section-title">🏅 Honours</div>
    <div class="card">${awards.map((a) => `<div class="matchitem">
      <div class="ntf-ico" aria-hidden="true">${AWARD_EMOJI[a.award_type] || "🏅"}</div>
      <a class="mi-main" href="#/match/${h(a.match_id)}" style="text-decoration:none;color:inherit">
        <b>${h(AWARD_NAMES[a.award_type] || a.award_type)}</b>${a.detail ? `<div class="tiny muted">${h(a.detail)}</div>` : ""}</a>
    </div>`).join("")}</div>` : ""}
    <div class="section-title">Batting</div>
    <div class="card">${statGrid([
      ["Mat", b.matches], ["Inns", b.innings], ["Runs", b.runs], ["HS", b.highest],
      ["Avg", b.average ?? "–"], ["SR", b.strike_rate], ["NO", b.not_outs], ["Balls", b.balls],
      ["4s", b.fours], ["6s", b.sixes], ["50s", b.fifties], ["100s", b.hundreds],
    ])}</div>
    <div class="section-title">Bowling</div>
    <div class="card">${statGrid([
      ["Mat", w.matches], ["Inns", w.innings], ["Overs", w.overs], ["Wkts", w.wickets],
      ["Runs", w.runs], ["Econ", w.economy], ["Avg", w.average ?? "–"], ["SR", w.strike_rate ?? "–"],
      ["Best", w.best], ["Mdns", w.maidens],
    ])}</div>
    <div class="section-title">Fielding</div>
    <div class="card">${statGrid([
      ["Catches", f.catches], ["Run-outs", f.run_outs], ["Stumpings", f.stumpings],
      ["Drops", f.drops || 0], ["Runs saved", f.runs_saved || 0],
    ])}</div>
    ${recent.length ? `<div class="section-title">Recent form</div>
    <div class="card">${recent.map((m) => `<div class="form-pill">
      <span class="muted tiny" style="min-width:78px">${h(m.teams)}</span>
      <span class="fp-bat">${m.bat ? h(m.bat) : "–"}</span>
      <span class="fp-bowl">${m.bowl ? h(m.bowl) : ""}</span></div>`).join("")}</div>` : ""}
    ${insightsHtml}
    ${splitsHtml}
    <div class="section-title">Details</div>
    <div class="card">
      <label>Player photo</label>
      ${photoEditorHtml({ kind: "player", id: p.id, name: p.name, hasPhoto: p.has_photo })}
      <label>Phone</label><input id="ep_phone" value="${h(p.phone || "")}">
      <div class="row">
        <div><label>Batting style</label><select id="ep_bat">${styleOptions(BAT_STYLES, p.batting_style)}</select></div>
        <div><label>Bowling style</label><select id="ep_bowl">${styleOptions(BOWL_STYLES, p.bowling_style)}</select></div>
      </div>
      <div class="spacer"></div>
      <button class="btn" id="ep_save">Save details</button>
    </div>`;
  bindPhotoEditor(view.querySelector(".photo-edit"), {
    kind: "player", name: p.name, getId: () => id,
    onChanged: (has) => {
      p.has_photo = has;
      const hero = document.getElementById("pHero");
      if (hero) hero.innerHTML = photoAvatar("player", id, p.name, "avatar--lg", has);
    },
  });
  document.getElementById("ep_save").onclick = async (ev) => {
    ev.target.disabled = true;
    try {
      await api.updatePlayer(id, {
        phone: val("ep_phone") || null,
        batting_style: document.getElementById("ep_bat").value || null,
        bowling_style: document.getElementById("ep_bowl").value || null,
      });
      toast("Saved ✓");
      renderPlayer(id);
    } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
  };
  const claimThis = document.getElementById("claimThis");
  if (claimThis) claimThis.onclick = async () => {
    claimThis.disabled = true;
    try { await api.claimPlayer(id); toast("Profile claimed ✓"); renderPlayer(id); }
    catch (e) { toast(e.message, "error"); claimThis.disabled = false; }
  };
}

// --------------------------------------------------------------------------
// Leaderboards
// --------------------------------------------------------------------------
async function renderLeaderboards() {
  const windows = [["all", "All time"], ["year", "This year"], ["month", "This month"], ["week", "This week"]];
  view.innerHTML = `<h2>Leaderboards</h2>
    <a class="btn btn--ghost" href="#/compare" style="margin-bottom:12px">${icon("swap")} Compare players &amp; teams</a>
    <div class="lb-filters">
      <div class="seg lb-seg" id="lbWindow">${windows
        .map(([v, l], i) => `<button data-w="${v}" class="${i === 0 ? "active" : ""}">${l}</button>`).join("")}</div>
      <select id="lbLoc" aria-label="Filter by location"><option value="">All locations</option></select>
    </div>
    <div id="lbs" class="lb-grid"><div class="empty">Loading…</div></div>`;

  const state = { window: "all", location: "" };
  const winSeg = document.getElementById("lbWindow");
  const locSel = document.getElementById("lbLoc");
  const board = (title, entries) =>
    entries.length
      ? `<div class="lb-board"><div class="section-title">${h(title)}</div>
         <div class="card">${entries
           .map((e, i) => `<div class="matchitem">
             ${i < 3 ? `<span class="medal medal--${i + 1}">${i + 1}</span>` : `<span class="lb-rank">${i + 1}</span>`}
             ${avatar(e.name, "avatar--sm")}
             <div class="mi-main"><a href="#/player/${h(e.player_id)}" style="text-decoration:none;color:inherit;font-weight:700">${h(e.name)}</a>${e.detail ? `<div class="tiny muted">${h(e.detail)}</div>` : ""}</div>
             <b>${h(e.value)}</b></div>`).join("")}</div></div>`
      : "";

  async function load() {
    const lbs = document.getElementById("lbs");
    lbs.innerHTML = `<div class="empty">Loading…</div>`;
    let lb;
    try { lb = await api.leaderboards(state); }
    catch (e) { lbs.innerHTML = `<div class="empty">${h(e.message)}</div>`; return; }
    // (re)fill the location dropdown from the places on record, keeping the choice
    const keep = locSel.value;
    locSel.innerHTML = `<option value="">All locations</option>` +
      (lb.locations || []).map((l) => `<option value="${h(l)}">${h(l)}</option>`).join("");
    locSel.value = keep;
    const html = [
      board("MVP — all-rounders", lb.mvp),
      board("Most runs", lb.most_runs),
      board("Most wickets", lb.most_wickets),
      board("Highest score", lb.highest_score),
      board("Best bowling (innings)", lb.best_bowling),
      board("Most catches", lb.most_catches),
      board("Best batting average", lb.best_average),
      board("Best strike rate", lb.best_strike_rate),
      board("Best economy", lb.best_economy),
      board("Best bowling average", lb.best_bowling_average),
      board("Most sixes", lb.most_sixes),
      board("Most fours", lb.most_fours),
    ].join("");
    const scope = state.location ? ` in ${h(state.location)}` : "";
    lbs.innerHTML = html || `<div class="empty">No stats${scope} for this period.<br>Try “All time” / “All locations”.</div>`;
  }

  winSeg.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-w]");
    if (!b) return;
    [...winSeg.children].forEach((c) => c.classList.toggle("active", c === b));
    state.window = b.dataset.w;
    load();
  });
  locSel.addEventListener("change", () => { state.location = locSel.value; load(); });
  load();
}

async function renderCompare() {
  const [players, teams] = await Promise.all([api.players(), api.teams()]);
  view.innerHTML = `
    <h2>Compare</h2>
    <div class="seg cmp-mode" id="cmpMode">
      <button type="button" data-v="players" class="active">Players</button>
      <button type="button" data-v="teams">Teams</button>
    </div>
    <div class="card" id="cmpCard"></div>
    <div id="cmpResult"></div>`;
  let mode = "players";

  function build() {
    const card = document.getElementById("cmpCard");
    const result = document.getElementById("cmpResult");
    result.innerHTML = "";
    const list = mode === "players" ? players : teams;
    const noun = mode === "players" ? "players" : "teams";
    const kind = mode === "players" ? "player" : "team";
    if (list.length < 2) {
      card.innerHTML = `<div class="empty"><span class="empty-ico">${icon("swap")}</span>Add at least 2 ${noun} to compare.</div>`;
      return;
    }
    card.innerHTML = `
      <div class="row cmp-pickrow">
        ${entityPickerHtml("A", "Search a " + kind + "…")}
        ${entityPickerHtml("B", "Search a " + kind + "…")}
      </div>
      <div class="spacer"></div>
      <button class="btn" id="cmpGo">Compare →</button>`;
    const pickA = setupEntityPicker("A", list, list[0], kind);
    const pickB = setupEntityPicker("B", list, list[1], kind);
    const run = async () => {
      const a = pickA.value(), b = pickB.value();
      if (!a || !b) return toast("Pick two " + noun, "error");
      if (a === b) return toast("Pick two different " + noun, "error");
      try {
        if (mode === "players") {
          result.innerHTML = compareHtml(await api.compare(a, b));
        } else {
          const [sa, sb] = await Promise.all([api.teamStats(a), api.teamStats(b)]);
          const ta = teams.find((t) => String(t.id) === String(a));
          const tb = teams.find((t) => String(t.id) === String(b));
          result.innerHTML = teamCompareHtml(ta, sa, tb, sb);
        }
      } catch (e) { toast(e.message, "error"); }
    };
    document.getElementById("cmpGo").onclick = run;
    run();
  }
  segPick("#cmpMode", (v) => { mode = v; build(); });
  build();
}

// Searchable combobox for players or teams — type to filter, keyboard-navigable.
function entityPickerHtml(side, placeholder) {
  return `<div class="pp" data-pp="${h(side)}">
    <svg class="pp-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
    <input class="pp-input" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" autocomplete="off" placeholder="${h(placeholder)}">
    <div class="pp-menu" role="listbox" hidden></div>
  </div>`;
}

function setupEntityPicker(side, items, initial, kind) {
  const root = view.querySelector(`.pp[data-pp="${side}"]`);
  const input = root.querySelector(".pp-input");
  const menu = root.querySelector(".pp-menu");
  let selected = initial || null;
  let filtered = items;
  let active = -1;  // highlighted index within `filtered`
  if (selected) input.value = selected.name;

  const sub = (it) => kind === "team"
    ? `${(it.members || []).length} player${(it.members || []).length === 1 ? "" : "s"}`
    : (it.code || pcode(it.id));
  const hay = (it) => (kind === "team" ? it.name : it.name + " " + (it.code || pcode(it.id))).toLowerCase();
  const optHtml = (it, i) => `<button type="button" class="pp-opt${i === active ? " is-active" : ""}" role="option" data-id="${h(it.id)}">
    ${photoAvatar(kind, it.id, it.name, "", it.has_photo)}<span class="pp-opt-main"><b>${h(it.name)}</b><span class="tiny muted">${h(sub(it))}</span></span></button>`;
  const paint = () => {
    menu.innerHTML = filtered.length ? filtered.map(optHtml).join("") : `<div class="pp-empty">No ${kind === "team" ? "teams" : "players"} match.</div>`;
  };
  const scrollActive = () => { const el = menu.querySelector(".pp-opt.is-active"); if (el) el.scrollIntoView({ block: "nearest" }); };
  const open = (showAll) => {
    // focusing shows the whole list to browse; typing narrows it
    const q = showAll ? "" : input.value.trim().toLowerCase();
    filtered = q ? items.filter((it) => hay(it).includes(q)) : items;
    active = selected ? filtered.findIndex((it) => String(it.id) === String(selected.id)) : -1;
    paint();
    menu.hidden = false;
    input.setAttribute("aria-expanded", "true");
  };
  const close = () => {
    menu.hidden = true;
    input.setAttribute("aria-expanded", "false");
    if (selected) input.value = selected.name;  // input always reflects a committed pick
  };
  const pick = (it) => { selected = it; input.value = it.name; close(); };

  input.addEventListener("focus", () => { input.select(); open(true); });
  input.addEventListener("input", () => open());
  input.addEventListener("blur", () => setTimeout(close, 120));  // allow option mousedown to land first
  input.addEventListener("keydown", (e) => {
    if (menu.hidden && (e.key === "ArrowDown" || e.key === "ArrowUp")) { open(true); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(active + 1, filtered.length - 1); paint(); scrollActive(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(active - 1, 0); paint(); scrollActive(); }
    else if (e.key === "Enter" && !menu.hidden && filtered[active]) { e.preventDefault(); pick(filtered[active]); }
    else if (e.key === "Escape") { close(); input.blur(); }
  });
  // mousedown (not click) so the input doesn't blur before we read the choice
  menu.addEventListener("mousedown", (e) => {
    const opt = e.target.closest(".pp-opt");
    if (!opt) return;
    e.preventDefault();
    const it = items.find((x) => String(x.id) === opt.getAttribute("data-id"));
    if (it) pick(it);
  });

  return { value: () => (selected ? String(selected.id) : "") };
}

// Head-to-head team record comparison (uses /teams/{id}/stats).
function teamCompareHtml(ta, sa, tb, sb) {
  const row = (label, av, bv) => `<tr><td class="cmp-a">${h(av)}</td><td class="cmp-k">${h(label)}</td><td class="cmp-b">${h(bv)}</td></tr>`;
  const net = (s) => { const n = s.runs_for - s.runs_against; return (n > 0 ? "+" : "") + n; };
  return `
    <div class="card cmp-head">
      <div>${photoAvatar("team", ta.id, ta.name, "avatar--lg", ta.has_photo)}<div class="cmp-name">${h(ta.name)}</div></div>
      <div class="cmp-vs">vs</div>
      <div>${photoAvatar("team", tb.id, tb.name, "avatar--lg", tb.has_photo)}<div class="cmp-name">${h(tb.name)}</div></div>
    </div>
    <div class="section-title">Record</div>
    <div class="card"><table class="cmp-table"><tbody>
      ${row("Played", sa.played, sb.played)}
      ${row("Won", sa.won, sb.won)}
      ${row("Lost", sa.lost, sb.lost)}
      ${row("Tied", sa.tied, sb.tied)}
      ${row("Win %", sa.win_pct + "%", sb.win_pct + "%")}
    </tbody></table></div>
    <div class="section-title">Runs</div>
    <div class="card"><table class="cmp-table"><tbody>
      ${row("Runs for", sa.runs_for, sb.runs_for)}
      ${row("Runs against", sa.runs_against, sb.runs_against)}
      ${row("Net runs", net(sa), net(sb))}
    </tbody></table></div>`;
}

function compareHtml(c) {
  const A = c.player_a, B = c.player_b;
  const row = (label, av, bv) => `<tr><td class="cmp-a">${h(av)}</td><td class="cmp-k">${h(label)}</td><td class="cmp-b">${h(bv)}</td></tr>`;
  return `
    <div class="card cmp-head">
      <div>${avatar(A.player.name, "avatar--lg")}<div class="cmp-name">${h(A.player.name)}</div></div>
      <div class="cmp-vs">vs</div>
      <div>${avatar(B.player.name, "avatar--lg")}<div class="cmp-name">${h(B.player.name)}</div></div>
    </div>
    <div class="section-title">Batting</div>
    <div class="card"><table class="cmp-table"><tbody>
      ${row("Runs", A.batting.runs, B.batting.runs)}
      ${row("Average", A.batting.average ?? "–", B.batting.average ?? "–")}
      ${row("Strike rate", A.batting.strike_rate, B.batting.strike_rate)}
      ${row("Highest", A.batting.highest, B.batting.highest)}
      ${row("50s / 100s", A.batting.fifties + " / " + A.batting.hundreds, B.batting.fifties + " / " + B.batting.hundreds)}
      ${row("4s / 6s", A.batting.fours + " / " + A.batting.sixes, B.batting.fours + " / " + B.batting.sixes)}
    </tbody></table></div>
    <div class="section-title">Bowling</div>
    <div class="card"><table class="cmp-table"><tbody>
      ${row("Wickets", A.bowling.wickets, B.bowling.wickets)}
      ${row("Economy", A.bowling.economy, B.bowling.economy)}
      ${row("Average", A.bowling.average ?? "–", B.bowling.average ?? "–")}
      ${row("Best", A.bowling.best, B.bowling.best)}
    </tbody></table></div>`;
}

// --------------------------------------------------------------------------
// Tournaments
// --------------------------------------------------------------------------
async function renderTournaments() {
  const canCreate = can("tournament.create");
  // "mine/staffing" takes the person from the token — it's the umpire's and
  // commentator's own list of postings, and empty for everybody else.
  const [tournaments, teams, presets, templates, staffing] = await Promise.all([
    api.tournaments(), api.teams(), api.presets(), api.templates(),
    isAuthed() ? api.myStaffing().catch(() => []) : [],
  ]);
  const teamChecks = teams.length
    ? teams.map((t) => `<label class="ximember"><input type="checkbox" value="${h(t.id)}">${h(t.name)}</label>`).join("")
    : `<div class="tiny muted">No teams yet — create teams first.</div>`;
  view.innerHTML = `
    <h2>Tournaments</h2>
    ${canCreate ? `<div class="card">
      <label>New tournament</label>
      <input id="tn_name" placeholder="e.g. Society Premier League">
      <label>Type</label>
      <div class="seg" id="tn_type">
        <button type="button" data-v="round_robin" class="active">League</button>
        <button type="button" data-v="groups">Groups + playoffs</button>
        <button type="button" data-v="knockout">Knockout</button>
      </div>
      <div id="tn_groupopts" hidden>
        <div class="row">
          <div><label>Number of groups</label><input id="tn_ng" type="number" min="2" max="16" value="2"></div>
          <div><label>Advance per group</label><input id="tn_adv" type="number" min="1" max="8" value="2"></div>
        </div>
        <p class="tiny muted">Teams are split into pools (round-robin each), then the top finishers go to a seeded knockout.</p>
      </div>
      <div id="tn_pts">
        <label>Points</label>
        <div class="tn-pts">
          <div><span class="tiny muted">Win</span><input id="tn_win" type="number" min="0" value="2"></div>
          <div><span class="tiny muted">Tie</span><input id="tn_tie" type="number" min="0" value="1"></div>
          <div><span class="tiny muted">No result</span><input id="tn_nr" type="number" min="0" value="1"></div>
        </div>
      </div>
      <label>Match format / rules</label>
      ${fmtSelect(presets, templates)}
      <p class="tiny muted">Every match in this tournament uses these rules. Pick a preset or one of your saved <a href="#/rules">custom rule templates</a>.</p>
      <label>Teams (pick 2+)</label>
      <div class="xi">${teamChecks}</div>
      <div class="spacer"></div>
      <button class="btn" id="tn_create">Create tournament</button>
    </div>` : ""}
    ${staffing.length ? `<div class="section-title">${icon("gavel")} You're on the staff</div>
      <p class="tiny muted" style="margin:-4px 0 10px">Competitions an organizer put you on as an umpire or commentator.</p>
      <div class="card">${staffing.map((s) => `<a class="matchitem" href="#/tournament/${h(s.tournament_id)}">
        <span class="q-ico" style="margin:0;width:38px;height:38px;border-radius:11px">${icon(s.staff_role === "commentator" ? "mic" : "gavel")}</span>
        <div class="mi-main"><b>${h(s.tournament_name || "Tournament " + s.tournament_id)}</b>
          <div class="tiny muted">${h(roleLabel(s.staff_role))}</div></div>
        <span class="badge ${s.is_active ? "" : "badge--grey"}">${s.is_active ? "active" : "stood down"}</span></a>`).join("")}</div>` : ""}
    <div class="section-title">Your tournaments</div>
    ${searchBox("tourSearch", "Search your tournaments…")}
    <div class="card" id="tlist"></div>`;
  function paintTours() {
    const q = (val("tourSearch") || "").toLowerCase();
    const list = q ? tournaments.filter((t) => (t.name || "").toLowerCase().includes(q) || (t.format || "").replace("_", " ").includes(q)) : tournaments;
    document.getElementById("tlist").innerHTML = list.length
      ? list.map((t) => `<a class="matchitem" href="#/tournament/${h(t.id)}">
          <span class="q-ico" style="margin:0;width:38px;height:38px;border-radius:11px">${icon("trophy")}</span>
          <div class="mi-main"><b>${h(t.name)}</b><div class="tiny muted">${t.teams.length} teams · ${h(t.format.replace("_", " "))}</div></div>
          <span class="badge badge--grey">open ›</span></a>`).join("")
      : `<div class="empty">${tournaments.length ? "No tournaments match your search." : "No tournaments yet. Create one above."}</div>`;
  }
  document.getElementById("tourSearch").oninput = paintTours;
  paintTours();
  if (!canCreate) return;  // list only — creating needs the tournament.create capability
  let tnType = "round_robin";
  segPick("#tn_type", (v) => {
    tnType = v;
    document.getElementById("tn_groupopts").hidden = v !== "groups";
    document.getElementById("tn_pts").hidden = v === "knockout";  // points only for league/groups
  });
  const numIn = (id, d) => { const n = parseInt(val(id), 10); return isNaN(n) ? d : n; };
  document.getElementById("tn_create").onclick = async (ev) => {
    const name = val("tn_name");
    const team_ids = [...view.querySelectorAll(".xi input:checked")].map((c) => c.value);
    if (!name) return toast("Name the tournament", "error");
    if (team_ids.length < 2) return toast("Pick at least 2 teams", "error");
    ev.target.disabled = true;
    try {
      const payload = { name, format: tnType, team_ids };
      await applyFmt(payload, document.getElementById("fmt").value);
      if (tnType !== "knockout") {
        payload.win_points = numIn("tn_win", 2);
        payload.tie_points = numIn("tn_tie", 1);
        payload.nr_points = numIn("tn_nr", 1);
      }
      if (tnType === "groups") {
        payload.num_groups = numIn("tn_ng", 2);
        payload.advance_per_group = numIn("tn_adv", 2);
      }
      const t = await api.createTournament(payload);
      nav(`#/tournament/${t.id}`);
    } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
  };
}

function fixtureRow(f) {
  const a = f.team_a ? f.team_a.name : "TBD";
  if (!f.team_b) {
    return `<div class="matchitem"><div>${h(a)}</div><span class="badge badge--grey">bye</span></div>`;
  }
  const b = f.team_b.name;
  let right;
  if (f.status === "completed" && f.match_id) right = `<a class="badge" href="#/match/${h(f.match_id)}" style="text-decoration:none">${h(f.result || "done")}</a>`;
  else if (f.status === "live") right = `<a class="badge" href="#/match/${h(f.match_id)}" style="text-decoration:none;background:var(--amber);color:#3a2a00">resume ›</a>`;
  else right = `<button class="btn btn--sm" data-start="${h(f.id)}">Start</button>`;
  return `<div class="matchitem"><div>${h(a)} <span class="muted">v</span> ${h(b)}</div>${right}</div>`;
}

// Render a set of fixtures grouped by round (knockout rounds get Final/SF/QF labels).
function tourFixtureRounds(fixtures, ko) {
  const byRound = {};
  fixtures.forEach((f) => (byRound[f.round] = byRound[f.round] || []).push(f));
  const nums = Object.keys(byRound).map(Number).sort((x, y) => x - y);
  const label = (rnd, count) =>
    ko ? (count === 1 ? "Final" : count === 2 ? "Semi-finals" : count === 4 ? "Quarter-finals" : "Round " + rnd) : "Round " + rnd;
  return nums.map((rnd) =>
    `<div class="section-title">${label(rnd, byRound[rnd].length)}</div><div class="card">${byRound[rnd].map(fixtureRow).join("")}</div>`).join("");
}

function pointsTableHtml(rows, title) {
  return `<div class="section-title">${h(title)}</div>
    <div class="card" style="overflow-x:auto">
      <table class="crease">
        <thead><tr><th>Team</th><th>P</th><th>W</th><th>L</th><th>T</th><th>Pts</th><th>NRR</th></tr></thead>
        <tbody>${rows.map((s) => `<tr>
          <td>${h(s.name)}</td><td>${s.played}</td><td>${s.won}</td><td>${s.lost}</td><td>${s.tied}</td>
          <td><b>${s.points}</b></td><td>${s.nrr > 0 ? "+" : ""}${s.nrr}</td></tr>`).join("")}</tbody>
      </table>
    </div>`;
}

function squadCardHtml(s, canManage) {
  const rows = s.players.length
    ? s.players.map((p) => `<div class="matchitem">${avatar(p.name)}
        <div class="mi-main"><b>${h(titleCase(p.name))}</b><div class="tiny muted"><span class="pcode">${h(p.code || pcode(p.id))}</span></div></div>
        ${canManage ? `<button class="btn btn--ghost btn--sm sq-rm" data-team="${h(s.team_id)}" data-player="${h(p.id)}">Remove</button>` : ""}</div>`).join("")
    : `<div class="empty" style="padding:14px">No players registered yet.</div>`;
  // The picker is a custom dropdown — populated after render by cdd() so each row can
  // lay out "CODE - Name" on the left with the squad tag on the right (see renderTournament).
  const picker = canManage ? `<div class="addrow" style="margin-top:10px;flex-wrap:wrap">
      <div class="cdd sq-pick" data-team="${h(s.team_id)}"></div>
      <input class="sq-new" data-team="${h(s.team_id)}" placeholder="New player's name" hidden>
      <button class="btn btn--sm sq-add" data-team="${h(s.team_id)}">Add</button></div>` : "";
  return `<div class="card">
      <div class="between"><b>${h(s.team_name)}</b><span class="tiny muted">${s.players.length} player${s.players.length === 1 ? "" : "s"}</span></div>
      ${rows}${picker}
    </div>`;
}

// --------------------------------------------------------------------------
// A competition's staff — the organizer's umpires and commentators
// --------------------------------------------------------------------------
const STAFF_KINDS = [["umpire", "Umpire", "Umpires", "gavel"], ["commentator", "Commentator", "Commentators", "mic"]];

function staffRowHtml(s) {
  return `<div class="adm-org" data-row="${h(s.user_id)}">
    <div class="matchitem">${avatar(s.full_name || s.username)}
      <div class="mi-main"><b>${h(s.full_name || s.username)}</b>
        <div class="tiny muted">@${h(s.username)}${s.mobile_no ? " · " + h(s.mobile_no) : ""}</div></div>
      <span class="badge ${s.is_active ? "" : "badge--grey"}">${s.is_active ? "active" : "stood down"}</span></div>
    <div class="rr-actions adm-acts">
      <button class="btn btn--ghost btn--sm st-act" data-uid="${h(s.user_id)}" data-role="${h(s.staff_role)}" data-to="${s.is_active ? "0" : "1"}">${s.is_active ? "Stand down" : "Reinstate"}</button>
      <button class="btn btn--ghost btn--sm st-rm" data-uid="${h(s.user_id)}" data-role="${h(s.staff_role)}" data-label="${h(s.full_name || s.username)}">Remove</button>
    </div>
  </div>`;
}

function tournamentStaffHtml(t, staff, tourPlayers) {
  const of = (role) => staff.filter((s) => s.staff_role === role);
  const lists = STAFF_KINDS.map(([role, , plural, ico]) => {
    const rows = of(role);
    return `<div class="section-title" style="margin-top:16px">${icon(ico)} ${plural}</div>
      <div class="card">${rows.length ? rows.map(staffRowHtml).join("")
        : `<div class="empty" style="padding:14px">No ${plural.toLowerCase()} on this competition yet.</div>`}</div>`;
  }).join("");
  return `<div class="section-title" style="margin-top:22px">${icon("shield")} Staff
      <span class="tiny muted" style="font-weight:600">· your competition</span></div>
    <p class="tiny muted" style="margin:-4px 0 10px">The umpires and commentators who work this competition. Standing somebody down keeps the
      entry so you can bring them back later; removing them is "not on my competition", never "no longer an umpire".</p>
    <div class="card">${statGrid([
      ["Umpires", of("umpire").filter((s) => s.is_active).length],
      ["Commentators", of("commentator").filter((s) => s.is_active).length],
      ["Teams", (t.teams || []).length],
      ["Players", tourPlayers.length],
    ])}</div>
    ${lists}
    <div class="card">
      <div class="section-title" style="margin-top:0">Add to the staff</div>
      <div class="seg" id="stKind">${STAFF_KINDS.map(([role, one], i) =>
        `<button type="button" data-v="${h(role)}"${i === 0 ? ' class="active"' : ""}>${h(one)}</button>`).join("")}</div>
      <label style="margin-top:10px">Member</label>
      <div class="cdd" id="stPick"></div>
      <p class="tiny muted" style="margin:8px 0 0">A member with no role yet is promoted on the way in. Somebody who already holds a different
        role keeps it — an admin has to change their role first.</p>
      <div class="spacer"></div>
      <button class="btn" id="stAdd">Add to staff</button>
    </div>`;
}

async function bindTournamentStaff(id, staff) {
  const pick = document.getElementById("stPick");
  const addBtn = document.getElementById("stAdd");
  if (!pick || !addBtn) return;
  const users = await api.users().catch(() => []);
  let kind = "umpire";
  function paintPicker() {
    // The server promotes a roleless account and refuses anybody already holding
    // a different role, so the picker greys those out with the reason rather
    // than offering a button that 409s.
    const already = new Set(staff.filter((s) => s.staff_role === kind && s.is_active).map((s) => String(s.user_id)));
    pick.dataset.value = "";
    cdd(pick, userPickerOptions(users, {
      skip: (u) => already.has(String(u.id)) || (u.role !== "general_user" && u.role !== kind),
      reason: (u) => (already.has(String(u.id)) ? "already on staff" : `is ${roleLabel(u.role)}`),
    }), users.length ? "Pick a member…" : "No members yet");
  }
  segPick("#stKind", (v) => { kind = v; paintPicker(); });
  paintPicker();
  addBtn.onclick = async (e) => {
    const uid = pick.dataset.value;
    if (!uid) return toast("Pick the member to add", "error");
    e.target.disabled = true;
    try {
      await (kind === "umpire" ? api.addUmpire(id, uid) : api.addCommentator(id, uid));
      toast("Added to the staff ✓");
      renderTournament(id);
    } catch (err) { toast(err.message, "error"); e.target.disabled = false; }
  };
  view.querySelectorAll(".st-act, .st-rm").forEach((btn) => (btn.onclick = async () => {
    const remove = btn.classList.contains("st-rm");
    if (remove && !confirm(`Take ${btn.dataset.label} off this competition's staff?\n\nTheir account and their work on other competitions are untouched.`)) return;
    btn.disabled = true;
    try {
      if (remove) { await api.removeStaff(id, btn.dataset.role, btn.dataset.uid); toast("Removed from the staff"); }
      else {
        const on = btn.dataset.to === "1";
        await api.setStaffActive(id, btn.dataset.role, btn.dataset.uid, on);
        toast(on ? "Reinstated ✓" : "Stood down");
      }
      renderTournament(id);
    } catch (err) { toast(err.message, "error"); btn.disabled = false; }
  }));
}

async function renderTournament(id) {
  // The staff panel is an organizer's working view of their OWN competition, so
  // only somebody who can run competitions at all asks for it. The list is
  // owner/staff/admin-scoped server-side and an organizer can never be somebody
  // else's staff, so a 200 here means the caller owns this one (or is admin) —
  // a 403 means it belongs to another organizer and the panel is left off the
  // page rather than offering buttons that would 403.
  const mayStaff = can("tournament.create");
  const [t, players, squads, staff] = await Promise.all([
    api.tournament(id), api.players().catch(() => []), api.tournamentSquads(id).catch(() => []),
    mayStaff ? api.tournamentStaff(id).catch(() => null) : null,
  ]);
  // Only asked for once the staff list came back 200 — the same scope guards it,
  // so firing both at once would just mean two refusals instead of one.
  const tourPlayers = staff ? await api.tournamentPlayers(id).catch(() => []) : [];
  const isKO = t.format === "knockout";
  const isGroups = t.format === "groups";
  const canManage = can("tournament.create");
  // a player already in ANY team's squad here can't be added to another (one team /
  // tournament). Map each registered player to the team holding them, so every
  // picker can show cross-squad players greyed out with the reason.
  const takenBy = new Map();
  squads.forEach((s) => s.players.forEach((p) => takenBy.set(String(p.id), s.team_name)));
  const poss = (n) => (/s$/i.test(n) ? n + "'" : n + "'s");  // MI -> MI's, BLASTERS -> BLASTERS'
  // Options for one team's picker: free players are selectable ("CODE - Name"); a
  // "Create new" action; then players locked to another squad, disabled with the
  // team on the right ("in MI's squad"). Players already in THIS squad are skipped.
  const squadPickerOptions = (s) => {
    const free = [], elsewhere = [];
    players.forEach((p) => {
      const team = takenBy.get(String(p.id));
      if (team === s.team_name) return;
      (team ? elsewhere : free).push({ p, team });
    });
    const left = (p) => `${p.code || pcode(p.id)} - ${titleCase(p.name)}`;
    const opts = free.map(({ p }) => ({ value: p.id, left: left(p) }));
    opts.push({ value: "__new__", left: "＋ Create a new player…", accent: true });
    if (elsewhere.length) {
      opts.push({ group: "Unavailable — one team per player" });
      elsewhere.forEach(({ p, team }) => opts.push({
        value: p.id, disabled: true, left: left(p), right: `in ${poss(team.toUpperCase())} squad`,
      }));
    }
    return opts;
  };
  const squadsHtml = squads.length
    ? `<div class="section-title">Squads <span class="tiny muted" style="font-weight:600">· one team per player</span></div>` +
      squads.map((s) => squadCardHtml(s, canManage)).join("")
    : "";
  const champBanner = t.champion
    ? `<div class="card" style="text-align:center"><div class="tiny muted">CHAMPION</div>
       <div style="font-size:22px;font-weight:800;color:var(--accent);margin-top:4px">${icon("trophy")} ${h(t.champion.name)}</div></div>`
    : "";

  let top, fixturesHtml;
  if (isGroups) {
    top = champBanner + (t.groups || []).map((g) => pointsTableHtml(g.standings, "Group " + g.group)).join("");
    const byGroup = {};
    t.fixtures.filter((f) => f.group).forEach((f) => (byGroup[f.group] = byGroup[f.group] || []).push(f));
    const groupFix = Object.keys(byGroup).sort().map((g) =>
      `<div class="section-title">Group ${h(g)} · fixtures</div><div class="card">${byGroup[g].map(fixtureRow).join("")}</div>`).join("");
    const bracketFx = t.fixtures.filter((f) => !f.group);
    const bracket = bracketFx.length
      ? `<div class="section-title">Playoffs</div>${tourFixtureRounds(bracketFx, true)}`
      : `<div class="empty" style="margin-top:10px">Playoffs are seeded once every group game is played.</div>`;
    fixturesHtml = groupFix + bracket;
  } else if (isKO) {
    top = champBanner;
    fixturesHtml = tourFixtureRounds(t.fixtures, true);
  } else {
    top = pointsTableHtml(t.standings, "Points table");
    fixturesHtml = tourFixtureRounds(t.fixtures, false);
  }
  const typeLabel = isKO ? "knockout" : isGroups ? "groups + playoffs" : "league";
  const staffHtml = staff ? tournamentStaffHtml(t, staff, tourPlayers) : "";
  view.innerHTML = `<h2 class="page-h">${h(t.name)} <span class="tiny muted">${typeLabel}</span> ${followBtnHtml("tournament", id)}</h2>${top}${squadsHtml}${staffHtml}${fixturesHtml}
    <button class="btn btn--ghost" id="tn_share">Share</button>
    <div class="spacer"></div>
    ${(auth.user && auth.user.role === "admin") ? `<button class="btn btn--red" id="tn_del">Delete tournament</button>` : ""}`;
  document.getElementById("tn_share").onclick = () => share("/t/" + id, t.name);
  if (staff) bindTournamentStaff(id, staff);
  view.querySelectorAll("[data-start]").forEach((btn) => (btn.onclick = () => startFixtureModal(t, btn.dataset.start)));
  // build each team's custom-dropdown picker; toggle the "new player name" field
  // when "Create a new player…" is chosen.
  squads.forEach((s) => {
    const container = view.querySelector(`.sq-pick[data-team="${s.team_id}"]`);
    if (!container) return;
    cdd(container, squadPickerOptions(s), "Add a player…");
    container.addEventListener("change", () => {
      const input = view.querySelector(`.sq-new[data-team="${s.team_id}"]`);
      if (!input) return;
      input.hidden = container.dataset.value !== "__new__";
      if (!input.hidden) input.focus();
    });
  });
  view.querySelectorAll(".sq-add").forEach((btn) => (btn.onclick = async () => {
    const team = btn.dataset.team;
    const sel = view.querySelector(`.sq-pick[data-team="${team}"]`);
    const choice = sel && sel.dataset.value;
    if (!choice) return;
    btn.disabled = true;
    try {
      let pid = choice;
      if (choice === "__new__") {
        const input = view.querySelector(`.sq-new[data-team="${team}"]`);
        const name = (input.value || "").trim();
        if (!name) { toast("Type the new player's name", "error"); btn.disabled = false; return; }
        pid = (await api.createPlayer({ name })).id;  // create in the pool, then register
      }
      await api.registerSquad(id, team, pid);
      renderTournament(id);
    } catch (e) { toast(e.message, "error"); btn.disabled = false; }
  }));
  view.querySelectorAll(".sq-rm").forEach((btn) => (btn.onclick = async () => {
    try { await api.unregisterSquad(id, btn.dataset.team, btn.dataset.player); renderTournament(id); }
    catch (e) { toast(e.message, "error"); }
  }));
  const tnDelBtn = document.getElementById("tn_del");  // admins only (see markup)
  if (tnDelBtn) tnDelBtn.onclick = async () => {
    if (!confirm("Delete this tournament? This can't be undone.")) return;
    try { await api.deleteTournament(id); nav("#/tournaments"); } catch (e) { toast(e.message, "error"); }
  };
}

async function startFixtureModal(t, fixtureId) {
  const fx = t.fixtures.find((f) => f.id === fixtureId);
  if (!fx || !fx.team_a || !fx.team_b) return toast("Fixture not ready", "error");
  // XI comes from each team's tournament squad; fall back to the global roster only
  // if no squad has been registered for the team.
  const squads = await api.tournamentSquads(t.id).catch(() => []);
  const squadOf = (teamId) => (squads.find((s) => String(s.team_id) === String(teamId)) || {}).players || [];
  const rosterFor = async (ref) => {
    const sq = squadOf(ref.id);
    if (sq.length) return { name: ref.name, members: sq.map((p) => ({ player_id: p.id, name: p.name })) };
    const team = await api.team(ref.id);
    return { name: team.name, members: team.members };
  };
  const [teamA, teamB] = await Promise.all([rosterFor(fx.team_a), rosterFor(fx.team_b)]);
  const xi = (team) => team.members.length
    ? team.members.map((m) => `<label class="ximember"><input type="checkbox" checked value="${h(m.player_id)}">${h(m.name)}</label>`).join("")
    : `<div class="tiny muted">No squad for ${h(team.name)} — register players in the Squads section.</div>`;
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `
    <div class="modal__sheet">
      <h3>${h(teamA.name)} v ${h(teamB.name)}</h3>
      <label>${h(teamA.name)} XI</label><div class="xi" id="sfA">${xi(teamA)}</div>
      <label>${h(teamB.name)} XI</label><div class="xi" id="sfB">${xi(teamB)}</div>
      <label>Bats first</label>
      <div class="seg" id="sfBat"><button type="button" data-v="a" class="active">${h(teamA.name)}</button><button type="button" data-v="b">${h(teamB.name)}</button></div>
      <div class="row modal__actions">
        <button class="btn btn--ghost" id="sf_cancel">Cancel</button>
        <button class="btn" id="sf_ok">Start &amp; score →</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  let batFirst = "a";
  overlay.querySelectorAll("#sfBat button").forEach((b) => (b.onclick = () => {
    overlay.querySelectorAll("#sfBat button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active"); batFirst = b.dataset.v;
  }));
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("#sf_cancel").onclick = close;
  overlay.querySelector("#sf_ok").onclick = async (ev) => {
    const aIds = [...overlay.querySelectorAll("#sfA input:checked")].map((c) => c.value);
    const bIds = [...overlay.querySelectorAll("#sfB input:checked")].map((c) => c.value);
    if (aIds.length < 2 || bIds.length < 2) return toast("Pick at least 2 players per side", "error");
    if (aIds.length !== bIds.length) return toast("Both XIs need the same size", "error");
    ev.target.disabled = true;
    try {
      const started = await api.startFixture(fixtureId, { squad_a_ids: aIds, squad_b_ids: bIds, bat_first: batFirst });
      close();
      nav(`#/match/${started.match_id}`);
    } catch (e) { toast(e.message, "error"); ev.target.disabled = false; }
  };
}

// --------------------------------------------------------------------------
// Rule builder
// --------------------------------------------------------------------------
async function renderRules() {
  if (!gate("rules.manage", "build rule templates")) return;
  view.innerHTML = `
    <div class="nm-wrap">
      <div class="nm-head"><h2>Rule builder</h2><p class="nm-sub">Compose your own rulebook — box, gully, indoor or league — and reuse it for matches &amp; tournaments.</p></div>
      <div class="nm-grid">
        <div class="nm-left">
          <div class="card">
            <label>Template name</label><input id="r_name" value="My Society Box Cricket">
            <div class="row">
              <div><label>Players / side</label><input id="r_players" type="number" min="2" max="20" value="8"></div>
              <div><label>Overs</label><input id="r_overs" type="number" min="1" max="200" value="6"></div>
            </div>
            <div class="row">
              <div><label>Balls / over</label><input id="r_bpo" type="number" min="1" max="12" value="6"></div>
              <div><label>Max overs / bowler</label><input id="r_maxob" type="number" min="1" placeholder="none"></div>
            </div>
            <label>Ball type</label>
            <select id="r_ball"><option value="tennis">Tennis</option><option value="leather">Leather</option><option value="other">Other</option></select>
            <label>Boundary rule</label>
            <div class="seg" id="r_boundary">
              <button type="button" data-v="full">Full ground (sixes)</button>
              <button type="button" data-v="ruleout" class="active">Rule-out (over = OUT)</button>
            </div>
            <p class="tiny muted">Rule-out: hitting the ball over the boundary on the full is OUT, not six.</p>
          </div>
          <div class="card">
            <div class="section-title">Options</div>
            ${toggle("r_lms", "Last man stands", true)}
            ${toggle("r_fh", "No-ball gives free hit", false)}
            ${toggle("r_wide", "Wides count as runs", true)}
            ${toggle("r_byes", "Allow byes", false)}
            ${toggle("r_lbyes", "Allow leg-byes", false)}
            ${toggle("r_lbw", "Allow LBW", false)}
            ${toggle("r_super", "Super over breaks a tie", false)}
            ${toggle("r_dls", "DLS / revised target (rain)", false)}
            ${toggle("r_declare", "Allow declarations", false)}
            <p class="tiny muted">A super over is played when scores are level. DLS flags the match for rain-revised targets you set during the chase. Declarations let the batting captain close an innings early (timed games).</p>
          </div>
          <div class="card">
            <div class="section-title">Fielding restrictions</div>
            <div class="row">
              <div><label>Max fielders outside the circle <span class="tiny muted">· normal overs</span></label><input id="r_fout" type="number" min="0" max="11" value="5"></div>
              <div></div>
            </div>
            <label style="margin-top:4px">Powerplay overs <span class="tiny muted" style="font-weight:600">· tighter limit for set overs</span></label>
            <div id="ppList"></div>
            <button type="button" class="btn btn--ghost btn--sm" id="ppAdd">+ Add powerplay</button>
            <p class="tiny muted">Powerplays override the limit above for their overs (e.g. only 2 fielders out in overs 1–6). The middle box is the max fielders allowed outside the circle. A live “Powerplay” badge shows the limit while you score those overs.</p>
          </div>
          <button class="btn" id="saveBtn">Save rule template</button>
          <div class="spacer"></div>
          <div class="section-title">Saved templates</div>
          <div class="card" id="tplList"><div class="empty">Loading…</div></div>
        </div>
        <aside class="nm-right">
          <div class="nm-card">
            <div class="nm-card-label">Rules preview</div>
            <div class="rb-pv-name" id="rbName">My Society Box Cricket</div>
            <div class="nm-meta">
              <div class="nm-meta-row"><span>Players / side</span><b id="rbPlayers">8</b></div>
              <div class="nm-meta-row"><span>Overs</span><b id="rbOvers">6</b></div>
              <div class="nm-meta-row"><span>Balls / over</span><b id="rbBpo">6</b></div>
              <div class="nm-meta-row"><span>Max overs / bowler</span><b id="rbMaxob">Any</b></div>
              <div class="nm-meta-row"><span>Ball type</span><b id="rbBall">Tennis</b></div>
              <div class="nm-meta-row"><span>Boundary</span><b id="rbBoundary">Rule-out</b></div>
              <div class="nm-meta-row"><span>Fielders out</span><b id="rbFout">5</b></div>
              <div class="nm-meta-row"><span>Powerplays</span><b id="rbPP">1–2 (2 out)</b></div>
            </div>
            <div class="rb-pv-chips" id="rbChips"></div>
          </div>
        </aside>
      </div>
    </div>`;

  let boundary = "ruleout";
  segPick("#r_boundary", (v) => { boundary = v; syncPreview(); });

  function syncPreview() {
    const gv = (id) => document.getElementById(id);
    const setT = (id, t) => { const e = gv(id); if (e) e.textContent = t; };
    setT("rbName", gv("r_name").value.trim() || "Custom rules");
    setT("rbPlayers", gv("r_players").value || "—");
    setT("rbOvers", gv("r_overs").value || "—");
    setT("rbBpo", gv("r_bpo").value || "—");
    setT("rbMaxob", gv("r_maxob").value ? gv("r_maxob").value : "Any");
    const ball = gv("r_ball");
    setT("rbBall", ball.options[ball.selectedIndex].text);
    setT("rbBoundary", boundary === "ruleout" ? "Rule-out (6 = OUT)" : "Full ground");
    setT("rbFout", gv("r_fout").value || "—");
    const pps = [...ppList.querySelectorAll("[data-pp]")].map((row) => {
      const s = row.querySelector(".pp-start").value, e = row.querySelector(".pp-end").value, o = row.querySelector(".pp-out").value;
      return (s && e) ? `${s}–${e} (${o || 2} out)` : null;
    }).filter(Boolean);
    setT("rbPP", pps.length ? pps.join(", ") : "None");
    const flags = [["r_lms", "Last-man-stands"], ["r_fh", "Free hit"], ["r_wide", "Wides count"], ["r_byes", "Byes"], ["r_lbyes", "Leg-byes"], ["r_lbw", "LBW"], ["r_super", "Super over"], ["r_dls", "DLS"], ["r_declare", "Declarations"]];
    const chips = flags.filter(([id]) => gv(id) && gv(id).checked).map(([, label]) => label);
    const chipEl = gv("rbChips");
    if (chipEl) chipEl.innerHTML = chips.length ? chips.map((c) => `<span class="cap-chip">${h(c)}</span>`).join("") : `<span class="tiny muted">No extra rules</span>`;
  }

  // ----- powerplay editor -----
  const ppList = document.getElementById("ppList");
  function addPP(start, end, label, out) {
    const row = document.createElement("div");
    row.className = "pprow";
    row.dataset.pp = "";
    row.innerHTML = `
      <input type="number" min="1" class="pp-start" value="${start ?? ""}" placeholder="from" aria-label="Powerplay start over">
      <span class="tiny muted">to</span>
      <input type="number" min="1" class="pp-end" value="${end ?? ""}" placeholder="to" aria-label="Powerplay end over">
      <span class="tiny muted">·</span>
      <input type="number" min="0" max="11" class="pp-out" value="${out ?? 2}" title="Max fielders outside the circle" aria-label="Max fielders outside circle">
      <span class="tiny muted">out</span>
      <input type="text" class="pp-label" value="${label ? h(label) : "Powerplay"}" placeholder="Label" aria-label="Powerplay label">
      <button type="button" class="pp-del" aria-label="Remove powerplay">✕</button>`;
    row.querySelector(".pp-del").onclick = () => { row.remove(); syncPreview(); };
    ppList.appendChild(row);
  }
  document.getElementById("ppAdd").onclick = () => { addPP(1, 2, "Powerplay", 2); syncPreview(); };
  addPP(1, 2, "Powerplay", 2); // one sensible default — removable
  // keep the live preview in sync with every field (delegated input/change)
  const rbLeft = view.querySelector(".nm-left");
  rbLeft.addEventListener("input", syncPreview);
  rbLeft.addEventListener("change", syncPreview);
  syncPreview();

  function collectPowerplays(overs) {
    const pps = [...ppList.querySelectorAll("[data-pp]")]
      .map((row) => {
        const s = parseInt(row.querySelector(".pp-start").value, 10);
        const e = parseInt(row.querySelector(".pp-end").value, 10);
        const out = parseInt(row.querySelector(".pp-out").value, 10);
        const label = row.querySelector(".pp-label").value.trim() || "Powerplay";
        return Number.isInteger(s) && Number.isInteger(e) && s >= 1 && e >= s
          ? { start_over: s, end_over: e, label, max_fielders_outside: Number.isInteger(out) && out >= 0 ? out : 2 }
          : null;
      })
      .filter(Boolean);
    if (pps.some((pp) => pp.end_over > overs))
      throw new Error("Powerplay overs can’t exceed the innings length");
    return pps;
  }

  async function refresh() {
    const tpls = await api.templates();
    const el = document.getElementById("tplList");
    el.innerHTML = tpls.length
      ? tpls
          .map(
            (t) => `<div class="matchitem">
              <div><b>${h(t.name)}</b><div class="tiny muted">${t.rules.players_per_side}-a-side · ${t.rules.overs_per_innings}ov · ${t.rules.over_boundary_out ? "rule-out" : "full ground"}${t.rules.powerplays && t.rules.powerplays.length ? ` · ${t.rules.powerplays.length} PP` : ""}${t.rules.super_over_on_tie ? " · super over" : ""}${t.rules.dls_enabled ? " · DLS" : ""}</div></div>
              <button class="btn btn--ghost btn--sm" data-del="${h(t.id)}">Delete</button>
            </div>`
          )
          .join("")
      : `<div class="empty">No templates yet.</div>`;
    el.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
      try { await api.deleteTemplate(b.dataset.del); refresh(); } catch (e) { toast(e.message, "error"); }
    }));
  }
  refresh();

  document.getElementById("saveBtn").onclick = async (ev) => {
    ev.target.disabled = true;
    try {
      const maxob = document.getElementById("r_maxob").value;
      const overs = +document.getElementById("r_overs").value;
      const powerplays = collectPowerplays(overs);
      const allowed = ["bowled", "caught", "caught_behind", "caught_and_bowled", "run_out", "stumped", "hit_wicket", "retired_out", "obstructing_field", "hit_ball_twice", "timed_out"];
      if (document.getElementById("r_lbw").checked) allowed.push("lbw");
      const rules = {
        name: document.getElementById("r_name").value.trim() || "Custom rules",
        format_id: "custom",
        players_per_side: +document.getElementById("r_players").value,
        overs_per_innings: overs,
        balls_per_over: +document.getElementById("r_bpo").value,
        ball_type: document.getElementById("r_ball").value,
        max_overs_per_bowler: maxob ? +maxob : null,
        last_man_stands: document.getElementById("r_lms").checked,
        over_boundary_out: boundary === "ruleout",
        super_over_on_tie: document.getElementById("r_super").checked,
        dls_enabled: document.getElementById("r_dls").checked,
        allow_declaration: document.getElementById("r_declare").checked,
        byes_allowed: document.getElementById("r_byes").checked,
        leg_byes_allowed: document.getElementById("r_lbyes").checked,
        no_ball: { free_hit: document.getElementById("r_fh").checked },
        wide: { enabled: document.getElementById("r_wide").checked },
        default_fielders_outside: +document.getElementById("r_fout").value,
        powerplays,
        allowed_dismissals: allowed,
      };
      await api.saveTemplate(rules);
      toast("Template saved ✓");
      refresh();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      ev.target.disabled = false;
    }
  };
}

// --------------------------------------------------------------------------
// Scoring screen
// --------------------------------------------------------------------------
// --------------------------------------------------------------------------
// Offline-first scoring — queue scoring actions in IndexedDB when there's no
// signal, show an optimistic scoreboard, and flush to the server on reconnect.
// Nothing is lost; the full card re-derives from the server on sync.
// --------------------------------------------------------------------------
const offlineDB = (() => {
  const NAME = "cricnetra-offline", STORE = "matches";
  let dbp = null;
  function open() {
    if (dbp) return dbp;
    dbp = new Promise((resolve, reject) => {
      let r;
      try { r = indexedDB.open(NAME, 1); } catch (e) { return reject(e); }
      r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "id" });
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    return dbp;
  }
  const run = (mode, fn, fallback) => open().then((db) => new Promise((res) => {
    const rq = fn(db.transaction(STORE, mode).objectStore(STORE));
    rq.onsuccess = () => res(rq.result);
    rq.onerror = () => res(fallback);
  })).catch(() => fallback);
  return {
    get: (id) => run("readonly", (s) => s.get(id), null).then((r) => r || null),
    put: (rec) => run("readwrite", (s) => s.put(rec), false),
    keys: () => run("readonly", (s) => s.getAllKeys(), []).then((r) => r || []),
  };
})();

// fetch() rejects with a TypeError when unreachable; our req() stamps err.status
// for HTTP errors, so a missing status ≈ a network failure.
function isNetworkError(e) { return !navigator.onLine || !e || e.status === undefined; }

function rawSend(id, op) {
  if (op.kind === "ball") return api.ball(id, op.payload);
  if (op.kind === "bowler") return api.setBowler(id, op.payload.bowler);
  if (op.kind === "undo") return api.undo(id);
  return Promise.resolve(null);
}

// optimistic top-line scoreboard: clone the last server snapshot and tally the
// queued deliveries (runs/wickets/over.ball/this-over/strike — best effort; the
// server is authoritative once it syncs).
function projectOffline(snapshot, queue) {
  if (!snapshot) return null;
  const st = JSON.parse(JSON.stringify(snapshot));
  const inn = st.innings[st.current_innings - 1];
  if (inn) {
    const bpo = (st.rules && st.rules.balls_per_over) || 6;
    const wpen = (st.rules && st.rules.wide && st.rules.wide.run_penalty) || 1;
    const npen = (st.rules && st.rules.no_ball && st.rules.no_ball.run_penalty) || 1;
    const swap = () => { const t = inn.striker; inn.striker = inn.non_striker; inn.non_striker = t; };
    const pool = (snapshot.available_bowlers || []).slice();  // best-effort eligible pool
    let bowler = inn.bowler || st.staged_bowler || null;
    for (const op of queue) {
      if (op.kind === "bowler") {
        bowler = op.payload.bowler; inn.bowler = bowler;
        st.staged_bowler = bowler; st.awaiting_bowler = false;  // over_pending stays until the first ball
        continue;
      }
      if (op.kind !== "ball") continue;
      const a = op.payload;
      if (inn.legal_balls > 0 && inn.legal_balls % bpo === 0) inn.this_over = [];
      const chips = inn.this_over || (inn.this_over = []);
      let legal = false;
      if (a.action === "runs") { inn.runs += a.value; chips.push(String(a.value)); legal = true; if (a.value % 2 === 1) swap(); }
      else if (a.action === "wide") { inn.runs += wpen + (a.value || 0); chips.push("Wd"); }
      else if (a.action === "no_ball") { inn.runs += npen + (a.value || 0); chips.push("Nb"); }
      else if (a.action === "bye") { inn.runs += a.value; chips.push(a.value + "B"); legal = true; if (a.value % 2 === 1) swap(); }
      else if (a.action === "leg_bye") { inn.runs += a.value; chips.push(a.value + "L"); legal = true; if (a.value % 2 === 1) swap(); }
      else if (a.action === "wicket") { inn.wickets += 1; inn.runs += (a.value || 0); chips.push("W"); legal = true; inn.striker = null; }
      if (legal) {
        st.over_pending = false;  // a ball is bowled -> the over is underway
        inn.legal_balls += 1;
        if (inn.legal_balls % bpo === 0) {  // over complete -> need a (different) bowler next
          swap();
          st.over_pending = true; st.awaiting_bowler = true; st.staged_bowler = null;
          st.available_bowlers = pool.filter((b) => b !== bowler);
          if (!st.available_bowlers.length) st.available_bowlers = pool.slice();
          inn.bowler = null; bowler = null;
        }
      }
    }
    inn.overs_str = `${Math.floor(inn.legal_balls / bpo)}.${inn.legal_balls % bpo}`;
    const ov = inn.legal_balls / bpo;
    inn.run_rate = ov ? Math.round((inn.runs / ov) * 100) / 100 : 0;
  }
  st._pending = queue.length;
  return st;
}

async function scoreOffline(id, op) {
  const rec = (await offlineDB.get(id)) || { id, snapshot: null, queue: [], canScore: true };
  if (op.kind === "undo") {
    if (!rec.queue.length) throw new Error("Connect to the internet to undo earlier balls.");
    rec.queue.pop();
  } else {
    rec.queue.push(op);
  }
  await offlineDB.put(rec);
  return projectOffline(rec.snapshot, rec.queue);
}

async function flushMatch(id) {
  const rec = await offlineDB.get(id);
  if (!rec || !rec.queue.length) return false;
  while (rec.queue.length) {
    const st = await rawSend(id, rec.queue[0]);  // throws on failure → keep the rest, retry later
    rec.queue.shift();
    rec.snapshot = st;
    await offlineDB.put(rec);
  }
  return true;
}

async function cacheState(id, state, canScore) {
  const rec = (await offlineDB.get(id)) || { id, snapshot: null, queue: [], canScore: false };
  if (!rec.queue.length) { rec.snapshot = state; rec.canScore = canScore; await offlineDB.put(rec); }
}

async function pendingCount(id) { const rec = await offlineDB.get(id); return rec ? rec.queue.length : 0; }

async function syncAllOffline() {
  for (const id of await offlineDB.keys()) { try { await flushMatch(id); } catch (e) { /* still offline */ } }
}

// re-sync + re-render the match screen when connectivity flips
window.addEventListener("online", async () => {
  await syncAllOffline();
  const m = location.hash.match(/^#\/match\/(.+)$/);
  if (m) showMatch(m[1]);
});
window.addEventListener("offline", () => {
  const m = location.hash.match(/^#\/match\/(.+)$/);
  if (m) showMatch(m[1]);
});

// test/debug hook for the offline mechanics
window.__cnOffline = { db: offlineDB, project: projectOffline, score: scoreOffline, flush: flushMatch, pending: pendingCount };

// The stream <iframe> must SURVIVE score re-renders: a re-created iframe reloads,
// which pauses the live video. So the match screen is a persistent stream host
// (rebuilt only when the stream itself changes) + a body that re-renders freely.
let _matchStream = { id: null, url: null, manage: null };
let _matchClips = { id: null, sig: null, manage: null };
const clipSig = (clips) => (clips || []).map((c) => c.id + "|" + c.url + "|" + c.source).join(",");

function bindStream(id) {
  const save = document.getElementById("streamSave");
  if (save) save.onclick = async () => {
    const url = (val("streamUrl") || "").trim();
    if (!url) return toast("Paste a YouTube or Facebook live link", "error");
    if (!navigator.onLine) return toast("Connect to the internet for this.", "error");
    try { await api.setStream(id, url); toast("Live stream added ✓"); await showMatch(id); }
    catch (e) { toast(e.message, "error"); }
  };
  const clear = document.getElementById("streamClear");
  if (clear) clear.onclick = async () => {
    if (!confirm("Remove the live-stream link?")) return;
    try { await api.setStream(id, ""); toast("Stream removed"); await showMatch(id); }
    catch (e) { toast(e.message, "error"); }
  };
  const ovlCopy = document.getElementById("ovlCopy");
  if (ovlCopy) ovlCopy.onclick = async () => {
    const inp = document.getElementById("ovlUrl");
    const url = inp ? inp.value : "";
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      if (inp) { inp.focus(); inp.select(); document.execCommand("copy"); }
    }
    toast("Overlay URL copied ✓");
  };
  const ovlAnCopy = document.getElementById("ovlAnCopy");
  if (ovlAnCopy) ovlAnCopy.onclick = async () => {
    const inp = document.getElementById("ovlAnUrl");
    const url = inp ? inp.value : "";
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      if (inp) { inp.focus(); inp.select(); document.execCommand("copy"); }
    }
    toast("Analysis scene URL copied ✓");
  };
}

// Highlight clips also live in a persistent host so their <video>/<iframe> survive
// score re-renders. Rebuilt only when the clip set (or manage-rights) changes.
function renderClipHost(id, clips, canManage) {
  const el = document.getElementById("clipArea");
  let recInfo = null;
  const parseAnchor = (s) => {
    s = (s || "").trim();
    if (/^\d+(\.\d+)?$/.test(s)) return parseFloat(s);
    const m = s.match(/^(\d+):([0-5]?\d)$/);  // mm:ss
    return m ? (+m[1]) * 60 + (+m[2]) : NaN;
  };
  const setClips = (c) => { clips = c; _matchClips = { id, sig: clipSig(c), manage: canManage }; paint(); };
  const paint = () => {
    const inner = clipsHtml(clips, canManage, recInfo);
    el.innerHTML = inner ? `<div class="card"><div class="section-title" style="margin-top:0">${icon("radio")} Highlight clips</div>${inner}</div>` : "";
    wire();
  };
  const wire = () => {
    const add = document.getElementById("clipAdd");
    if (add) add.onclick = async () => {
      const u = (val("clipUrl") || "").trim();
      if (!u) return toast("Paste a YouTube or Facebook clip link", "error");
      if (!navigator.onLine) return toast("Connect to the internet for this.", "error");
      try { setClips(await api.addClip(id, u, val("clipLabel") || null)); toast("Clip added ✓"); }
      catch (e) { toast(e.message, "error"); }
    };
    el.querySelectorAll(".clip-del").forEach((b) => (b.onclick = () => {
      if (confirm("Remove this clip?")) api.removeClip(id, b.dataset.cid).then(setClips).catch((e) => toast(e.message, "error"));
    }));
    const up = document.getElementById("recUpload");
    if (up) up.onclick = async () => {
      const f = document.getElementById("recFile").files[0];
      if (!f) return toast("Choose a video file first", "error");
      up.disabled = true; up.textContent = "Uploading…";
      try {
        const r = await api.uploadRecording(id, f);
        recInfo = Object.assign({}, recInfo, { has_recording: true });
        toast(`Recording uploaded (${Math.round(r.duration)}s) ✓`); paint();
      } catch (e) { toast(e.message, "error"); up.disabled = false; up.textContent = "Upload"; }
    };
    const gen = document.getElementById("autoGen");
    if (gen) gen.onclick = async () => {
      const anchor = parseAnchor(val("clipAnchor"));
      if (!(anchor >= 0)) return toast("Enter when the first ball is bowled (e.g. 0:45)", "error");
      gen.disabled = true; gen.textContent = "Generating…";
      try { setClips(await api.autoClips(id, anchor)); toast("Highlight clips generated ✓"); }
      catch (e) { toast(e.message, "error"); gen.disabled = false; gen.textContent = "Generate highlight clips"; }
    };
  };
  if (canManage) api.recordingStatus(id).then((r) => { recInfo = r; }).catch(() => {}).then(paint);
  else paint();
}

// The in-app Highlights hub (#/highlights): a gallery of EVERY match's clips for
// everyone, plus a "pick a match → add clip / auto-cut video" panel for owners &
// admins (the clip-management that used to sit on each match's scoring screen).
async function renderHighlights() {
  view.innerHTML = `
    <h2>Highlights</h2>
    <p class="muted" style="margin:-6px 0 14px">Every highlight clip from across CricNetra — watch them all here, and add clips or auto-cut videos to your own matches.</p>
    <div id="hlManage"></div>
    <div class="section-title">${icon("radio")} All highlights</div>
    <div id="hlGallery"><div class="card empty">Loading…</div></div>`;

  const galleryEl = document.getElementById("hlGallery");
  async function loadGallery() {
    try {
      const groups = await api.allHighlights();
      if (!groups.length) {
        galleryEl.innerHTML = `<div class="card empty"><span class="empty-ico">${icon("radio")}</span>No highlights yet. Clips added to any match show up here for everyone to watch.</div>`;
        return;
      }
      galleryEl.innerHTML = groups.map((g) => `
        <div class="card hl-group">
          <a class="hl-ghead" href="#/match/${h(g.match_id)}">
            <span class="hl-gmain">
              <span class="hl-gbadge${g.live ? " is-live" : ""}">${g.live ? "● Live" : "Result"}</span>
              <b>${h(g.team_a)} <span class="muted">vs</span> ${h(g.team_b)}</b>
              <span class="tiny muted">${g.clips.length} clip${g.clips.length === 1 ? "" : "s"}</span>
            </span>
            <span class="hl-glink">Open match →</span>
          </a>
          ${clipsHtml(g.clips, false)}
        </div>`).join("");
    } catch (e) {
      galleryEl.innerHTML = `<div class="card empty">${h(e.message)}</div>`;
    }
  }
  loadGallery();

  // ---- management (owners/admins): pick a match, add a link or auto-cut a video ----
  if (!isAuthed()) return;
  let mine = [];
  try { mine = await api.myMatches(); } catch (e) { mine = []; }
  const mel = document.getElementById("hlManage");
  if (!mel || !mine.length) return;  // nothing you can manage → gallery only

  mel.innerHTML = `
    <div class="card">
      <div class="section-title" style="margin-top:0">${icon("zap")} Add highlights &amp; clips</div>
      <p class="tiny muted" style="margin:-4px 0 12px">Pick one of your matches, then paste a YouTube / Facebook clip link — or upload a recording and we auto-cut a clip around every wicket &amp; boundary.</p>
      <label>Your match</label>
      <select id="hlMatchSel">${mine.map((m) => `<option value="${h(m.id)}">${h(m.team_a)} vs ${h(m.team_b)}</option>`).join("")}</select>
      <div id="hlMatchClips" style="margin-top:12px"></div>
    </div>`;
  const sel = document.getElementById("hlMatchSel");
  const box = document.getElementById("hlMatchClips");

  let manageSeq = 0;  // ignore a slow load once a newer match is picked (avoids a stale paint)
  async function loadManage(id) {
    const seq = ++manageSeq;
    box.innerHTML = `<div class="empty">Loading…</div>`;
    let clips = [], rec = null;
    try {
      clips = await api.matchClips(id);
      rec = await api.recordingStatus(id).catch(() => null);
    } catch (e) { if (seq === manageSeq) box.innerHTML = `<div class="empty">${h(e.message)}</div>`; return; }
    if (seq !== manageSeq) return;  // a newer selection superseded this one

    const parseAnchor = (s) => {
      s = (s || "").trim();
      if (/^\d+(\.\d+)?$/.test(s)) return parseFloat(s);
      const mm = s.match(/^(\d+):([0-5]?\d)$/);
      return mm ? (+mm[1]) * 60 + (+mm[2]) : NaN;
    };
    const paint = () => { if (seq !== manageSeq) return; box.innerHTML = clipsHtml(clips, true, rec) || ""; wire(); };
    const after = (c) => { clips = c; paint(); loadGallery(); };  // refresh the gallery too
    const wire = () => {
      const add = box.querySelector("#clipAdd");
      if (add) add.onclick = async () => {
        const u = (val("clipUrl") || "").trim();
        if (!u) return toast("Paste a YouTube or Facebook clip link", "error");
        if (!navigator.onLine) return toast("Connect to the internet for this.", "error");
        try { after(await api.addClip(id, u, val("clipLabel") || null)); toast("Clip added ✓"); }
        catch (e) { toast(e.message, "error"); }
      };
      box.querySelectorAll(".clip-del").forEach((b) => (b.onclick = () => {
        if (confirm("Remove this clip?")) api.removeClip(id, b.dataset.cid).then(after).catch((e) => toast(e.message, "error"));
      }));
      const up = box.querySelector("#recUpload");
      if (up) up.onclick = async () => {
        const f = box.querySelector("#recFile").files[0];
        if (!f) return toast("Choose a video file first", "error");
        up.disabled = true; up.textContent = "Uploading…";
        try {
          const r = await api.uploadRecording(id, f);
          rec = Object.assign({}, rec, { has_recording: true });
          toast(`Recording uploaded (${Math.round(r.duration)}s) ✓`); paint();
        } catch (e) { toast(e.message, "error"); up.disabled = false; up.textContent = "Upload"; }
      };
      const gen = box.querySelector("#autoGen");
      if (gen) gen.onclick = async () => {
        const a = parseAnchor(val("clipAnchor"));
        if (!(a >= 0)) return toast("Enter when the first ball is bowled (e.g. 0:45)", "error");
        gen.disabled = true; gen.textContent = "Generating…";
        try { after(await api.autoClips(id, a)); toast("Highlight clips generated ✓"); }
        catch (e) { toast(e.message, "error"); gen.disabled = false; gen.textContent = "Generate highlight clips"; }
      };
    };
    paint();
  }
  sel.onchange = () => loadManage(sel.value);
  loadManage(sel.value);
}

function renderMatch(state, officials) {
  const canScore = !!(officials && officials.can_score);
  if (!document.getElementById("matchBody")) {  // build the shell once
    // Two columns on desktop: LEFT = the scoring console (scoreboard + pad), sticky
    // so the buttons stay put; RIGHT = live stream + highlight clips + scorecard /
    // commentary, which scrolls. The stream & clip hosts are PERSISTENT (never
    // re-rendered on a score) so their <iframe>/<video> keep playing through updates.
    view.innerHTML = `
      <div style="display:flex;justify-content:flex-end;margin-bottom:10px">${followBtnHtml("match", state.id)}</div>
      <div class="match-grid">
      <div class="match-left" id="matchLeft"></div>
      <div class="match-right">
        <div id="streamHost"></div><div id="clipArea"></div><div id="matchBody"></div>
      </div>
    </div>`;
    _matchStream = { id: null, url: null, manage: null };
    _matchClips = { id: null, sig: null, manage: null };
  }
  // stream — rebuild ONLY when it changed (a score leaves it identical → iframe untouched)
  const url = state.stream ? state.stream.url : null;
  if (state.id !== _matchStream.id || url !== _matchStream.url || canScore !== _matchStream.manage) {
    document.getElementById("streamHost").innerHTML = streamHtml(state, canScore);
    _matchStream = { id: state.id, url, manage: canScore };
    bindStream(state.id);
  }
  // highlight clips — READ-ONLY gallery here (videos keep playing across score
  // re-renders); adding/managing clips lives in the #/highlights hub now.
  const clips = state.clips || [];
  const sig = clipSig(clips);
  if (state.id !== _matchClips.id || sig !== _matchClips.sig) {
    _matchClips = { id: state.id, sig, manage: false };
    renderClipHost(state.id, clips, false);
  }
  const parts = matchHtml(state, officials);
  document.getElementById("matchLeft").innerHTML = parts.left;    // scoreboard + pad (sticky)
  document.getElementById("matchBody").innerHTML = parts.right;   // scorecard / commentary / charts
  bindMatch(state, officials);
}

async function showMatch(id) {
  let state = null, officials = null;
  if (navigator.onLine) { try { await flushMatch(id); } catch (e) { /* couldn't flush; keep going */ } }
  try {
    state = await api.match(id);
    if (isAuthed()) { try { officials = await api.matchOfficials(id); } catch (e) { /* ignore */ } }
    await cacheState(id, state, !!(officials && officials.can_score));
  } catch (e) {
    if (!isNetworkError(e)) throw e;
    const rec = await offlineDB.get(id);  // offline → render from the cached optimistic snapshot
    state = rec ? projectOffline(rec.snapshot, rec.queue) : null;
    if (!state) { view.innerHTML = `<div class="card empty">You're offline and this match isn't saved on this device yet.</div>`; return; }
    officials = { can_score: !!(rec && rec.canScore), _offline: true };
  }
  renderMatch(state, officials);
  if (navigator.onLine) startLiveStream(id, state);
}

// --------------------------------------------------------------------------
// Live updates — subscribe to the server's SSE score stream while a match is
// live so a watcher's scoreboard/scorecard/charts/feed update on their own.
// Mirrors the public page's live.js (SSE → re-render, polling fallback).
// --------------------------------------------------------------------------
let liveES = null, livePoll = null, liveBusy = false;

function stopLiveStream() {
  if (liveES) { try { liveES.close(); } catch (e) { /* noop */ } liveES = null; }
  if (livePoll) { clearInterval(livePoll); livePoll = null; }
}

async function refreshMatch(id) {
  // bail if the viewer navigated away, or a refresh is already in flight
  if (liveBusy || !location.hash.startsWith("#/match/")) return;
  liveBusy = true;
  try {
    const state = await api.match(id);
    const activeTab = view.querySelector(".chtab.active");
    const openTab = activeTab ? activeTab.dataset.ch : null;
    let officials = null;
    if (isAuthed()) { try { officials = await api.matchOfficials(id); } catch (e) { /* ignore */ } }
    renderMatch(state, officials);
    if (openTab && openTab !== "manhattan") {  // keep the watcher on their chart tab
      const t = view.querySelector(`.chtab[data-ch="${openTab}"]`);
      if (t) t.click();
    }
    flashScore();
    if (state.result) stopLiveStream();  // decided — stop watching
  } catch (e) { /* transient — keep the current view */ }
  finally { liveBusy = false; }
}

function flashScore() {
  const el = view.querySelector(".score__runs");
  if (!el) return;
  el.classList.remove("just-scored"); void el.offsetWidth; el.classList.add("just-scored");
}

function startLiveStream(id, state) {
  stopLiveStream();
  if (!state || state.result) return;  // already decided — nothing to stream
  const poll = () => { if (!livePoll) livePoll = setInterval(() => refreshMatch(id), 5000); };
  if (!window.EventSource) return poll();
  try {
    let first = true;
    liveES = new EventSource(`/api/v1/matches/${id}/stream`);
    // the stream sends the current snapshot on connect — skip it (already rendered)
    liveES.onmessage = () => { if (first) { first = false; return; } refreshMatch(id); };
    liveES.addEventListener("gone", stopLiveStream);
    liveES.onerror = () => { if (liveES && liveES.readyState === EventSource.CLOSED) { liveES = null; poll(); } };
  } catch (e) { poll(); }
}

function chipClass(s) {
  if (s.includes("Wd") || s.includes("Nb")) return "chip--extra";
  if (s.includes("W")) return "chip--wkt";
  if (s === "4" || s === "6") return "chip--boundary";
  return "chip--run";
}

// --------------------------------------------------------------------------
// Match charts (SVG) — manhattan / worm / wagon wheel. All data is already in
// the match state (inn.manhattan, inn.worm, inn.wagon); these just draw it.
// --------------------------------------------------------------------------
let trackShots = localStorage.getItem("cn_trackshots") === "1";
let trackPitch = localStorage.getItem("cn_trackpitch") === "1";

function chartEmpty(msg) {
  return `<div class="chart-empty">${h(msg)}</div>`;
}

function manhattanChartSvg(inn, r) {
  const data = inn.manhattan || [];
  if (!data.length) return chartEmpty("No overs bowled yet — the runs-per-over chart appears here.");
  const W = 520, H = 200, padL = 24, padB = 22, padT = 34, padR = 8;
  const n = data.length, max = Math.max(4, ...data);
  const plotH = H - padB - padT, bw = (W - padL - padR) / n;
  const wkts = {};
  (inn.fall_of_wickets || []).forEach((f) => { const o = parseInt(String(f.over).split(".")[0], 10); wkts[o] = (wkts[o] || 0) + 1; });
  const pp = (r && r.powerplays) || [];
  const inPP = (over1) => pp.some((p) => over1 >= p.start_over && over1 <= p.end_over);
  const barW = Math.min(bw * 0.46, 26);  // thin bars centred in each slot
  const bars = data.map((v, i) => {
    const bh = (v / max) * plotH, cx = padL + i * bw + bw / 2, x = cx - barW / 2, y = padT + plotH - bh;
    const cls = inPP(i + 1) ? "mh-bar mh-pp" : "mh-bar";
    const val = v > 0 ? `<text x="${cx}" y="${y - 4}" class="mh-val" text-anchor="middle">${v}</text>` : "";
    // one red dot per wicket that fell this over, stacked above the runs label
    const wk = Array.from({ length: wkts[i] || 0 }, (_, j) =>
      `<circle cx="${cx}" cy="${(y - 15 - j * 7).toFixed(1)}" r="3" class="mh-wkt"/>`).join("");
    const lbl = (i === 0 || i === n - 1 || (i + 1) % 2 === 0) ? `<text x="${cx}" y="${H - 6}" class="mh-axis" text-anchor="middle">${i + 1}</text>` : "";
    return `<rect x="${x}" y="${y}" width="${barW}" height="${Math.max(0, bh)}" rx="3" class="${cls}"/>${val}${wk}${lbl}`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Runs per over">
    <line x1="${padL}" y1="${padT + plotH}" x2="${W - padR}" y2="${padT + plotH}" class="mh-base"/>${bars}</svg>
    <div class="chart-legend"><span class="lg lg-bar"></span>Runs/over <span class="lg lg-pp"></span>Powerplay <span class="lg lg-wkt"></span>Wicket</div>`;
}

// Catmull-Rom → cubic bezier, so the worm reads as a smooth curve.
function smoothPath(pts) {
  if (pts.length < 3) return pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

function wormChartSvg(state) {
  const series = (state.innings || []).filter((x) => !x.is_super_over).slice(0, 2)
    .map((inn) => ({ name: inn.batting_team, worm: inn.worm || [], fall: inn.fall_of_wickets || [] }))
    .filter((s) => s.worm.length);
  if (!series.length) return chartEmpty("No overs bowled yet — the cumulative worm appears here.");
  const W = 520, H = 210, padL = 30, padB = 24, padT = 12, padR = 10;
  const bpo = (state.rules && state.rules.balls_per_over) || 6;
  const maxRuns = Math.max(10, ...series.flatMap((s) => s.worm));
  const maxOv = Math.max(...series.map((s) => s.worm.length));
  const plotW = W - padL - padR, plotH = H - padB - padT, baseY = padT + plotH;
  const xAt = (i) => padL + (maxOv ? (i / maxOv) * plotW : 0);
  const yAt = (v) => baseY - (v / maxRuns) * plotH;
  const cls = ["worm-a", "worm-b"], grad = ["worm-grad-a", "worm-grad-b"];
  const areas = series.map((s, si) => {
    const pts = [[xAt(0), yAt(0)]].concat(s.worm.map((v, k) => [xAt(k + 1), yAt(v)]));
    const line = smoothPath(pts), end = pts[pts.length - 1];
    const area = `${line} L${end[0].toFixed(1)} ${baseY.toFixed(1)} L${pts[0][0].toFixed(1)} ${baseY.toFixed(1)} Z`;
    // a red dot at each wicket, placed at its exact (over, score) on the run curve
    const wkts = s.fall.map((f) => {
      const p = String(f.over).split(".");
      const frac = (parseInt(p[0], 10) || 0) + (parseInt(p[1], 10) || 0) / bpo;
      return `<circle cx="${xAt(frac).toFixed(1)}" cy="${yAt(f.score).toFixed(1)}" r="3.4" class="worm-wkt"/>`;
    }).join("");
    return `<path d="${area}" fill="url(#${grad[si]})" stroke="none"/>
      <path d="${line}" class="worm-line ${cls[si]}" fill="none"/>
      <circle cx="${end[0].toFixed(1)}" cy="${end[1].toFixed(1)}" r="3" class="worm-dot ${cls[si]}"/>${wkts}`;
  }).join("");
  const yTicks = [0, Math.round(maxRuns / 2), maxRuns].map((v) =>
    `<text x="${padL - 4}" y="${yAt(v) + 3}" class="mh-axis" text-anchor="end">${v}</text>
     <line x1="${padL}" y1="${yAt(v)}" x2="${W - padR}" y2="${yAt(v)}" class="worm-grid"/>`).join("");
  let legend = series.map((s, si) => `<span class="lg ${si === 0 ? "lg-worm-a" : "lg-worm-b"}"></span>${h(s.name)}`).join("  ");
  if (series.some((s) => s.fall.length)) legend += `  <span class="lg lg-wkt"></span>Wicket`;
  const defs = `<defs>
    <linearGradient id="worm-grad-a" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#16b364" stop-opacity=".13"/><stop offset="100%" stop-color="#16b364" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="worm-grad-b" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2f6fed" stop-opacity=".12"/><stop offset="100%" stop-color="#2f6fed" stop-opacity="0"/>
    </linearGradient>
  </defs>`;
  return `<svg viewBox="0 0 ${W} ${H}" class="chart-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cumulative runs">${defs}${yTicks}${areas}</svg>
    <div class="chart-legend">${legend}</div>`;
}

function wagonRunClass(n) { return n >= 6 ? "shot-6" : n >= 4 ? "shot-4" : "shot-lo"; }

function wagonField(S, c, R) {
  return `<circle cx="${c}" cy="${c}" r="${R}" class="wag-field"/>
    <circle cx="${c}" cy="${c}" r="${(R * 0.6).toFixed(1)}" class="wag-30"/>
    <rect x="${c - 6}" y="${c - 20}" width="12" height="40" rx="3" class="wag-pitch"/>`;
}

function wagonWheelSvg(inn) {
  const shots = inn.wagon || [];
  const S = 240, c = S / 2, R = S / 2 - 14;
  if (!shots.length) {
    return `<svg viewBox="0 0 ${S} ${S}" class="chart-svg wag-svg">${wagonField(S, c, R)}</svg>
      ${chartEmpty("No shot directions recorded yet. Turn on Track shots while scoring to build the wagon wheel.")}`;
  }
  const lines = shots.map((s) => {
    const x = c + (s.x || 0) * R, y = c - (s.y || 0) * R, k = wagonRunClass(s.runs);
    return `<line x1="${c}" y1="${c}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" class="wag-shot ${k}"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" class="wag-dot ${k}"/>`;
  }).join("");
  return `<svg viewBox="0 0 ${S} ${S}" class="chart-svg wag-svg" role="img" aria-label="Wagon wheel">${wagonField(S, c, R)}${lines}</svg>
    <div class="chart-legend"><span class="lg lg-lo"></span>1-3 <span class="lg lg-4"></span>4 <span class="lg lg-6"></span>6 · ${shots.length} shot${shots.length === 1 ? "" : "s"}</div>`;
}

// Optional shot-direction picker shown when "Track shots" is on. Always resolves
// (cb(null) on skip/dismiss) so the run is recorded either way.
function openWagon(runs, cb) {
  const S = 260, c = S / 2, R = S / 2 - 16;
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `<div class="modal__sheet wag-sheet">
    <h3>Where did it go? <span class="tiny muted">· ${runs} run${runs === 1 ? "" : "s"}</span></h3>
    <p class="tiny muted" style="margin-top:0">Tap the field — batter is at the centre, facing up (straight).</p>
    <svg viewBox="0 0 ${S} ${S}" class="chart-svg wag-svg wag-pick" id="wagPick">
      ${wagonField(S, c, R)}
      <text x="${c}" y="13" text-anchor="middle" class="mh-axis">straight</text></svg>
    <div class="row"><button class="btn btn--ghost" id="wagSkip">Skip direction</button></div>
  </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) { close(); cb(null); } });
  overlay.querySelector("#wagSkip").onclick = () => { close(); cb(null); };
  const svg = overlay.querySelector("#wagPick");
  svg.addEventListener("click", (e) => {
    const rect = svg.getBoundingClientRect();
    let x = ((e.clientX - rect.left) / rect.width * S - c) / R;
    let y = -(((e.clientY - rect.top) / rect.height * S) - c) / R;
    const mag = Math.hypot(x, y);
    if (mag > 1) { x /= mag; y /= mag; }
    close();
    cb({ wagon_x: +x.toFixed(3), wagon_y: +y.toFixed(3) });
  });
}

// Optional pitch-map picker (bowling). One tap = where it pitched; Skip = no mark.
// Always resolves (cb(null) on skip/dismiss) so the delivery records either way.
function openPitch(cb) {
  const W = 220, H = 300, sX = W * 0.34, sW = W * 0.32, top = H * 0.06, bot = H * 0.94;
  const bandTxt = [["Yorker", 0.86], ["Full", 0.75], ["Good", 0.58], ["Back", 0.42], ["Short", 0.26], ["Bouncer", 0.12]]
    .map(([lbl, f]) => `<text x="${sX + sW + 6}" y="${(H * 0.86 - f * H * 0.58 + 3).toFixed(1)}" class="mh-axis" text-anchor="start">${lbl}</text>`).join("");
  const stumps = (y) => `<g class="pitch-stumps"><line x1="${W / 2 - 5}" y1="${y}" x2="${W / 2 - 5}" y2="${y + 9}"/><line x1="${W / 2}" y1="${y}" x2="${W / 2}" y2="${y + 9}"/><line x1="${W / 2 + 5}" y1="${y}" x2="${W / 2 + 5}" y2="${y + 9}"/></g>`;
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `<div class="modal__sheet wag-sheet">
    <h3>Where did it pitch? <span class="tiny muted">· bowling</span></h3>
    <p class="tiny muted" style="margin-top:0">Tap the pitch — the batter's end is at the bottom.</p>
    <svg viewBox="0 0 ${W} ${H}" class="chart-svg wag-pick pitch-pick" id="pitchPick">
      <rect x="0" y="0" width="${W}" height="${H}" rx="10" class="pitch-bg"/>
      <rect x="${sX}" y="${top}" width="${sW}" height="${bot - top}" rx="3" class="pitch-strip"/>
      <line x1="${sX}" y1="${(H * 0.86).toFixed(1)}" x2="${sX + sW}" y2="${(H * 0.86).toFixed(1)}" class="pitch-crease"/>
      ${bandTxt}${stumps(H * 0.885)}${stumps(top + 3)}
    </svg>
    <div class="row"><button class="btn btn--ghost" id="pitchSkip">Skip pitch</button></div>
  </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) { close(); cb(null); } });
  overlay.querySelector("#pitchSkip").onclick = () => { close(); cb(null); };
  const svg = overlay.querySelector("#pitchPick");
  svg.addEventListener("click", (e) => {
    const rect = svg.getBoundingClientRect();
    const fx = (e.clientX - rect.left) / rect.width, fy = (e.clientY - rect.top) / rect.height;
    let px = (fx - 0.5) / 0.15;          // line: strip edges → ±1 (beyond = wide, clamped)
    let py = (0.86 - fy) / 0.58;         // length: reverse of the display mapping
    px = Math.max(-1, Math.min(1, px));
    py = Math.max(0, Math.min(1, py));
    close();
    cb({ pitch_x: +px.toFixed(3), pitch_y: +py.toFixed(3) });
  });
}

// Chain the optional captures onto a ball payload, then submit. Wagon is offered only
// when `wagonOffBat` (a real bat shot) and Track-shots is on; pitch on every delivery
// when Track-pitch is on. Each picker has Skip, so nothing is ever forced.
function captureBall(payload, wagonOffBat, submit) {
  const pitchThen = (base) => trackPitch
    ? openPitch((p) => submit(p ? { ...base, ...p } : base))
    : submit(base);
  if (trackShots && wagonOffBat)
    return openWagon(payload.value || 0, (w) => pitchThen(w ? { ...payload, ...w } : payload));
  return pitchThen(payload);
}

// Bring-your-own live stream (Option A): embed a YouTube/Facebook player next to
// the score (no video touches our servers). The owner/scorer sets the link.
function streamHost(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch (_) { return "link"; }
}
function streamHtml(state, canScore) {
  const s = state.stream;
  let media = "";
  if (s && s.embed_url) {
    media = `<div class="stream-embed"><iframe src="${h(s.embed_url)}" title="Live stream"
      frameborder="0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
      allowfullscreen loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`;
  } else if (s && s.url) {  // a provider we can't safely embed → a plain watch-out link
    media = `<a class="stream-watch" href="${h(s.url)}" target="_blank" rel="noopener noreferrer">
      ${icon("radio")} Watch live on <b>${h(streamHost(s.url))}</b> ↗</a>`;
  }
  let control = "";
  if (canScore) {
    control = `<div class="stream-set">
      <input id="streamUrl" type="url" inputmode="url" autocomplete="off"
        placeholder="Paste a YouTube / Facebook live link…" value="${s ? h(s.url) : ""}">
      <button class="btn btn--sm" id="streamSave">${s ? "Update" : "Go live"}</button>
      ${s ? `<button class="btn btn--ghost btn--sm" id="streamClear">Remove</button>` : ""}
    </div>`;
  }
  let ovl = "";
  if (canScore) {
    const overlayUrl = `${location.origin}/overlay/${state.id}`;
    const analysisUrl = `${overlayUrl}/analysis`;
    ovl = `<div class="ovl-block">
      <div class="section-title" style="margin:14px 0 6px">${icon("radio")} Broadcast overlay <span class="tiny muted">— for OBS / vMix</span></div>
      <div class="ovl-row">
        <input id="ovlUrl" class="ovl-url" type="text" readonly value="${h(overlayUrl)}" aria-label="Overlay URL">
        <button class="btn btn--sm" id="ovlCopy">Copy</button>
        <a class="btn btn--ghost btn--sm" href="${h(overlayUrl)}" target="_blank" rel="noopener">Open ↗</a>
      </div>
      <div class="ovl-row" style="margin-top:6px">
        <input id="ovlAnUrl" class="ovl-url" type="text" readonly value="${h(analysisUrl)}" aria-label="Analysis scene URL">
        <button class="btn btn--sm" id="ovlAnCopy">Copy</button>
        <a class="btn btn--ghost btn--sm" href="${h(analysisUrl)}" target="_blank" rel="noopener">Open ↗</a>
      </div>
      <p class="tiny muted" style="margin:6px 0 0">Add the first URL as a <b>Browser source</b> (1920×1080, transparent) in OBS / Streamlabs / vMix — scoreboard, batters, bowler, partnership, boundary &amp; wicket graphics update live. The second is an optional <b>Analysis scene</b> (worm graph, projected score, powerplay) — add it as a separate OBS scene. Options: <code>?theme=light</code>, <code>?compact=1</code>, <code>?ticker=0</code>.</p>
    </div>`;
  }
  if (!media && !canScore) return "";  // a viewer with no stream sees nothing
  return `<div class="card stream-card">
    <div class="section-title" style="margin-top:0">${icon("radio")} Live stream</div>
    ${media}
    ${control}
    ${canScore && !s ? `<p class="tiny muted" style="margin:8px 0 0">Go live free on YouTube or Facebook from your phone, then paste the link — it plays right here beside the score. Nothing is uploaded to CricNetra.</p>` : ""}
    ${ovl}
  </div>`;
}

// Auto highlights reel (Option B): the match's key moments, derived server-side
// from the ball log (no video). Grouped by innings, filterable by moment type.
const HL_BADGE = { wicket: "W", six: "6", four: "4", fifty: "50", hundred: "100",
  bowling: icon("target"), innings: icon("flag"), result: icon("trophy") };
function highlightsHtml(items, filter) {
  const pass = (x) => filter === "wickets" ? (x.kind === "wicket" || x.kind === "bowling")
    : filter === "boundaries" ? (x.kind === "six" || x.kind === "four") : true;
  const shown = items.filter(pass);
  if (!shown.length) return `<div class="empty tiny">No highlights yet — they build as the match is scored.</div>`;
  const groups = [];
  for (const x of shown) {
    let g = groups[groups.length - 1];
    if (!g || g.label !== x.innings) { g = { label: x.innings, rows: [] }; groups.push(g); }
    g.rows.push(x);
  }
  return groups.map((g) => `<div class="hl-group">
      <div class="hl-inn">${h(g.label)}</div>
      ${g.rows.map((r) => `<div class="hl-item hl-${r.kind}">
        <span class="hl-badge">${HL_BADGE[r.kind] || "•"}</span>
        <div class="hl-body"><b>${h(r.title)}</b> <span class="hl-txt">${h(r.text)}</span>${r.over_ball ? `<span class="hl-ov">${h(r.over_ball)}</span>` : ""}</div>
      </div>`).join("")}
    </div>`).join("");
}

// Bring-your-own highlight CLIPS (Option B video) — the organizer/admin attaches
// YouTube/Facebook clip links; they embed as a gallery. No video on our servers.
function clipsHtml(clips, canManage, recInfo) {
  let gallery = "";
  if (clips.length) {
    gallery = `<div class="clip-grid">${clips.map((c) => `<div class="clip">
      ${(c.source === "auto" || c.kind === "video")
        ? `<div class="stream-embed"><video controls preload="metadata" src="${h(c.url)}"></video></div>`
        : c.embed_url
          ? `<div class="stream-embed"><iframe src="${h(c.embed_url)}" title="${h(c.label || "Highlight clip")}" frameborder="0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`
          : `<a class="stream-watch clip-ext" href="${h(c.url)}" target="_blank" rel="noopener noreferrer">${icon("radio")} Watch clip on <b>${h(streamHost(c.url))}</b> ↗</a>`}
      <div class="clip-foot"><span class="clip-label">${h(c.label || "Highlight")}</span>${canManage ? `<button class="clip-del" data-cid="${h(c.id)}" title="Remove clip">${icon("trash")}</button>` : ""}</div>
    </div>`).join("")}</div>`;
  }
  let controls = "";
  if (canManage) {
    controls += `<div class="clip-add">
      <input id="clipUrl" type="url" inputmode="url" autocomplete="off" placeholder="Paste a YouTube / Facebook clip link…">
      <input id="clipLabel" maxlength="80" placeholder="Label (optional)">
      <button class="btn btn--sm" id="clipAdd">Add clip</button>
    </div>`;
    if (recInfo && recInfo.ffmpeg_available) {
      controls += `<div class="autoclip">
        <div class="autoclip-h">${icon("zap")} Auto-clip from a recording${recInfo.has_recording ? ` <span class="tiny" style="color:var(--green-700);font-weight:800">✓ recording uploaded</span>` : ""}</div>
        <div class="clip-add">
          <input id="recFile" type="file" accept="video/*">
          <button class="btn btn--sm btn--ghost" id="recUpload">Upload</button>
        </div>
        <div class="clip-add">
          <input id="clipAnchor" type="text" inputmode="numeric" placeholder="First ball at… e.g. 0:45 or 45">
          <button class="btn btn--sm" id="autoGen"${recInfo.has_recording ? "" : " disabled"}>Generate highlight clips</button>
        </div>
        <p class="tiny muted" style="margin:2px 0 0">Upload your match video, tell us when the first ball is bowled, and we cut a clip around every wicket &amp; boundary — synced to the scoring.</p>
      </div>`;
    }
  }
  if (!gallery && !controls) return "";
  return `<div class="clip-wrap">${gallery}${controls}</div>`;
}

// Prominent innings-transition actions, shown right under the scoreboard when an
// innings ends — so "Start 2nd innings" isn't buried at the bottom of the column.
function inningsBreakHtml(state) {
  if (state.can_start_second_innings)
    return `<div class="card ibreak"><div class="ib-t">First innings complete</div>
      <button class="btn ib-btn" id="secondBtn">Start 2nd innings →</button></div>`;
  if (state.needs_super_over)
    return `<div class="card ibreak"><div class="ib-t">${icon("zap")} Scores level — Super Over</div>
      <p class="tiny muted" style="margin:2px 0 9px">A one-over eliminator (all out at 2 wickets). Who bats first?</p>
      <div class="ib-row"><button class="btn ib-btn" data-bf="a">${h(state.team_a)} first</button><button class="btn ib-btn" data-bf="b">${h(state.team_b)} first</button></div></div>`;
  if (state.awaiting_super_second)
    return `<div class="card ibreak"><div class="ib-t">${icon("zap")} Super Over — the reply</div>
      <button class="btn ib-btn" id="soSecond">Start the reply →</button></div>`;
  return "";
}

const PNR_ORD = ["", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th"];
// Every stand of an innings, with the biggest one badged "Best".
function partnershipsHtml(inn) {
  const ps = inn.partnerships || [];
  if (!ps.length) return "";
  const best = ps.reduce((a, b) => (b.runs > a.runs ? b : a), ps[0]);
  const rows = ps.map((p) => {
    const isBest = ps.length > 1 && p === best && p.runs > 0;
    return `<div class="pnr-row${isBest ? " pnr-best" : ""}">
      <span class="pnr-wkt">${PNR_ORD[p.wicket] || p.wicket + "th"}</span>
      <span class="pnr-names">${h(p.batter_a)} <span class="muted">&amp;</span> ${h(p.batter_b)}${p.unbroken ? ` <span class="pnr-unb">not out</span>` : ""}</span>
      <span class="pnr-runs">${p.runs}<span class="tiny muted"> (${p.balls})</span></span>
      ${isBest ? `<span class="pnr-badge">Best</span>` : ""}
    </div>`;
  }).join("");
  return `<div class="section-title">${icon("users")} Partnerships</div><div class="card pnr-card">${rows}</div>`;
}

function matchHtml(state, officials) {
  const r = state.rules;
  const canScore = !!(officials && officials.can_score);  // owner, admin, or approved umpire
  const inn = state.innings[state.current_innings - 1];
  const target = inn.target;
  const chips = inn.this_over.length
    ? inn.this_over.map((s) => `<span class="chip ${chipClass(s)}">${h(s)}</span>`).join("")
    : `<span class="muted small">—</span>`;

  const plName = (name, id) => (id ? `<a href="#/player/${encodeURIComponent(id)}" class="pl-link">${h(name)}</a>` : h(name));
  const batRows = inn.batters
    .filter((b) => b.has_batted)
    .map(
      (b) => `<tr><td class="${b.on_strike ? "onstrike" : ""}">${plName(b.name, b.player_id)}</td>
        <td>${b.runs}</td><td>${b.balls}</td><td>${b.fours}</td><td>${b.sixes}</td>
        <td>${b.strike_rate.toFixed(1)}</td><td class="tiny muted" style="text-align:left">${b.out ? h(b.dismissal_text || "out") : b.on_strike || b.name === inn.non_striker ? "not out" : ""}</td></tr>`
    )
    .join("");
  const bowlRows = inn.bowlers
    .map(
      (w) => `<tr><td>${plName(w.name, w.player_id)}</td><td>${h(w.overs)}</td><td>${w.maidens}</td>
        <td>${w.runs}</td><td>${w.wickets}</td><td>${w.economy.toFixed(1)}</td></tr>`
    )
    .join("");

  let resultBanner = "";
  if (state.result) resultBanner = `<div style="background:var(--accent);color:var(--accent-ink);border-radius:12px;padding:9px 12px;text-align:center;font-weight:800">${h(state.result)}</div>`;
  else if (inn.is_complete && inn.result_note) resultBanner = `<div style="background:var(--accent-soft);color:var(--accent);border-radius:12px;padding:9px 12px;text-align:center;font-weight:700">${h(inn.result_note)}</div>`;

  // auto awards — only present once the match is decided
  let awardsHtml = "";
  const aw = state.awards;
  if (aw && aw.man_of_the_match) {
    const row = (emo, label, e) => e
      ? `<div class="award-row"><span class="award-emo">${emo}</span>
         <div><div class="tiny muted">${label}</div><b>${h(e.name)}</b> <span class="muted">${h(e.line)}</span></div></div>`
      : "";
    awardsHtml = `<div class="card award-card">
      <div class="section-title" style="margin-top:0">${icon("trophy")} Match awards</div>
      ${row(icon("star"), "Player of the Match", aw.man_of_the_match)}
      ${row(icon("stumps"), "Best batter", aw.best_batter)}
      ${row(icon("target"), "Best bowler", aw.best_bowler)}
    </div>`;
  }

  // names seen so far (for the fielding-log autocomplete)
  const fieldNames = [...new Set(state.innings.flatMap((i) =>
    [...i.batters.map((b) => b.name), ...i.bowlers.map((w) => w.name)]))];

  return {
    left: `
    <div class="scoreboard">
      <div class="between">
        <h2 class="sb-team">${h(inn.batting_team)} <span class="sb-vs">v ${h(inn.bowling_team)}</span></h2>
        <div class="sb-badges">
          ${inn.is_super_over ? `<span class="rulechip so-chip">${icon("zap")} SUPER OVER</span>` : ""}
          ${inn.in_powerplay ? `<span class="powerplay">⬤ ${h(inn.powerplay_label || "Powerplay")}${inn.fielders_outside_limit != null ? ` · ${inn.fielders_outside_limit} out` : ""}</span>` : ""}
          ${r && r.super_over_on_tie ? `<span class="rulechip">${icon("zap")} Super over</span>` : ""}
          ${r && r.dls_enabled ? `<span class="rulechip">${icon("umbrella")} DLS</span>` : ""}
          ${inn.free_hit ? `<span class="freehit">FREE HIT</span>` : ""}
        </div>
      </div>
      <div class="score">
        <div class="score__runs">${inn.runs}/${inn.wickets}</div>
        <div class="score__ov">${h(inn.overs_str)} / ${inn.max_overs} ov</div>
      </div>
      <div class="sb-stats">
        <div class="sb-stat"><div class="sb-stat-k">CRR</div><div class="sb-stat-v">${inn.run_rate.toFixed(2)}</div></div>
        ${target && !inn.is_complete ? `
          <div class="sb-stat"><div class="sb-stat-k">REQ</div><div class="sb-stat-v sb-stat-v--amber">${inn.required_run_rate ?? "–"}</div></div>
          <div class="sb-stat"><div class="sb-stat-k">TARGET</div><div class="sb-stat-v">${target}</div></div>`
        : `<div class="sb-stat"><div class="sb-stat-k">EXTRAS</div><div class="sb-stat-v">${(inn.extras && inn.extras.total) || 0}</div></div>
          <div class="sb-stat"><div class="sb-stat-k">PROJ</div><div class="sb-stat-v">${inn.run_rate ? Math.round(inn.run_rate * inn.max_overs) : 0}</div></div>`}
      </div>
      ${target && !inn.is_complete ? `<div class="sb-chase">Need ${inn.required_runs} off ${inn.balls_remaining} ball${inn.balls_remaining === 1 ? "" : "s"}</div>` : ""}
      <div class="chips">${chips}</div>
      ${(!navigator.onLine || state._pending) ? `<div class="offline-badge">${navigator.onLine ? `↻ syncing ${state._pending || 0}…` : `offline · ${state._pending || 0} ball${(state._pending || 0) === 1 ? "" : "s"} saved`}</div>` : ""}
      ${resultBanner ? `<div class="spacer"></div>${resultBanner}` : ""}
    </div>
    ${canScore && !inn.is_complete ? padHtml(state, r, inn) : ""}
    ${canScore ? inningsBreakHtml(state) : ""}
    ${awardsHtml}`,
    right: `
    <div class="card sc-tables">
      <div class="sc-tbl">
        <table class="crease">
          <thead><tr><th>Batter</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th><th></th></tr></thead>
          <tbody>${batRows || `<tr><td colspan="7" class="muted small">yet to bat</td></tr>`}</tbody>
        </table>
      </div>
      <div class="sc-tbl">
        <table class="crease">
          <thead><tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th></tr></thead>
          <tbody>${bowlRows || `<tr><td colspan="6" class="muted small">—</td></tr>`}</tbody>
        </table>
      </div>
    </div>

    ${inn.fall_of_wickets.length ? `<div class="small muted" style="margin:-6px 4px 12px"><b>Fall:</b> ${inn.fall_of_wickets.map((f) => `${f.score}-${f.wicket} (${h(f.batter_out)}, ${f.over})`).join(" · ")}</div>` : ""}

    ${partnershipsHtml(inn)}

    <div class="sc-actions">
      <button class="btn btn--ghost" id="shareBtn">${icon("share")} Share scorecard</button>
      <button class="btn btn--ghost" id="pdfBtn">${icon("chart")} Download PDF</button>
    </div>

    <div class="section-title">${icon("zap")} Key moments</div>
    <div class="card" id="hlCard">
      <div class="hl-filters">
        <button class="hlf active" data-f="all">All</button>
        <button class="hlf" data-f="wickets">Wickets</button>
        <button class="hlf" data-f="boundaries">Boundaries</button>
      </div>
      <div id="hlList"><div class="empty tiny">Loading highlights…</div></div>
    </div>

    <div class="section-title">${icon("radio")} Commentary</div>
    <div class="card" id="commCard">
      ${can("match.commentate") ? `<div class="comm-compose"><input id="commText" maxlength="280" placeholder="Add a commentary note…"><button class="btn btn--sm" id="commPost">Post</button></div>` : ""}
      <div id="commNotes"></div>
      <div id="ballFeed"><div class="empty tiny">Loading ball-by-ball…</div></div>
    </div>

    <div class="section-title">${icon("shield")} Fielding log</div>
    <div class="card" id="fieldCard">
      ${canScore ? `<div class="fld-compose">
        <input id="fldName" list="fldNames" placeholder="Fielder">
        <select id="fldKind"><option value="drop">Dropped catch</option><option value="save">Runs saved</option><option value="misfield">Misfield</option></select>
        <input id="fldRuns" type="number" min="0" value="0" title="runs (for saved / misfield)">
        <button class="btn btn--sm" id="fldAdd">Log</button>
        <datalist id="fldNames">${fieldNames.map((n) => `<option value="${h(n)}">`).join("")}</datalist>
      </div>` : ""}
      <div id="fldList"><div class="empty tiny">Loading fielding…</div></div>
    </div>

    <div class="section-title">${icon("chart")} Match charts</div>
    <div class="card charts-card">
      <div class="chart-tabs">
        <button class="chtab active" data-ch="manhattan">Manhattan</button>
        <button class="chtab" data-ch="worm">Worm</button>
        <button class="chtab" data-ch="wagon">Wagon wheel</button>
        <button class="chtab" data-ch="pitch">Pitch map</button>
      </div>
      <div class="chart-pane" data-pane="manhattan">${manhattanChartSvg(inn, r)}</div>
      <div class="chart-pane" data-pane="worm" hidden>${wormChartSvg(state)}</div>
      <div class="chart-pane" data-pane="wagon" hidden><div class="an-mount" id="wagonMount"></div></div>
      <div class="chart-pane" data-pane="pitch" hidden><div class="an-mount" id="pitchMount"></div></div>
    </div>
    <div class="spacer"></div>
    ${canScore ? scoringCardsHtml(state, r, inn) : ""}
    ${officialsPanel(state, officials)}
    `,
  };
}

// The scoring-action cards (rain/DLS, super over, 2nd innings) — only shown to a
// user who may score the match (owner, admin, or an approved umpire).
const DLS_REASONS = [["rain", "🌧 Rain"], ["bad_light", "🔦 Bad light"], ["wet_outfield", "💧 Wet outfield"],
  ["ground_delay", "🚧 Ground delay"], ["power_failure", "🔌 Power failure"], ["other", "• Other"]];
const DLS_REASON_LABEL = Object.fromEntries(DLS_REASONS.map(([k, l]) => [k, l]));

// The automatic DLS card: the scorer only clicks Interrupt and confirms overs —
// the revised target, par and required rate are all computed by the engine.
function dlsCardHtml(state, inn) {
  const d = state.dls;
  if (!d || state.result || (inn && inn.is_super_over)) return "";
  const chase = state.current_innings >= 2 && state.innings[1] ? state.innings[1] : null;
  let summary = "";
  if (d.applied || d.revised_target != null) {
    const need = chase && d.revised_target != null ? Math.max(0, d.revised_target - chase.runs) : null;
    const ahead = chase && d.par != null
      ? (chase.runs > d.par ? `<span class="dls-ahead">${chase.runs - d.par} ahead</span>`
        : chase.runs < d.par ? `<span class="dls-behind">${d.par - chase.runs} behind</span>` : `<span class="tiny muted">level</span>`)
      : "";
    summary = `<div class="dls-grid">
      <div><div class="dls-k">Original</div><div class="dls-v">${d.original_overs} ov</div></div>
      <div><div class="dls-k">Revised</div><div class="dls-v">${d.revised_overs || d.original_overs} ov</div></div>
      <div><div class="dls-k">Target</div><div class="dls-v dls-hl">${d.revised_target ?? "—"}</div></div>
      ${d.par != null ? `<div><div class="dls-k">Par now</div><div class="dls-v">${d.par} ${ahead}</div></div>` : ""}
      ${chase ? `<div><div class="dls-k">Current</div><div class="dls-v">${chase.runs}/${chase.wickets}</div></div>` : ""}
      ${need != null ? `<div><div class="dls-k">Need</div><div class="dls-v">${need} from ${chase.balls_remaining}</div></div>` : ""}
    </div>
    <div class="tiny muted" style="margin-top:2px">Duckworth–Lewis–Stern (Standard Edition) · overs lost ${d.overs_lost} · resources ${d.r1}% v ${d.r2}%</div>`;
  }
  const log = (d.interruptions || []).length
    ? `<div class="dls-log">${d.interruptions.map((it) => `<div class="tiny muted">${DLS_REASON_LABEL[it.reason] || it.reason} · innings ${it.innings}${it.pending ? ` · <b style="color:var(--amber,#b7791f)">in progress</b>` : ` · −${it.overs_lost} ov`}</div>`).join("")}</div>`
    : "";
  let controls;
  if (d.pending) {
    controls = `<div class="dls-resume">
      <div class="tiny" style="font-weight:800;color:var(--amber,#b7791f);margin-bottom:6px">⛈ Play interrupted — confirm the new total overs to resume</div>
      <div class="row">
        <div><label>New total overs <span class="tiny muted">this innings</span></label><input id="dls_overs" type="number" min="1" placeholder="e.g. 16"></div>
        <div><label>Resume time <span class="tiny muted">optional</span></label><input id="dls_resume_at" type="time"></div>
      </div>
      <div class="spacer"></div>
      <div class="dls-actions">
        <button class="btn btn--sm btn--ghost" id="dlsCancelBtn">Cancel (false alarm)</button>
        <button class="btn btn--sm" id="dlsResumeBtn">Resume play</button>
      </div>
    </div>`;
  } else {
    controls = `<div class="dls-actions">
      <select id="dls_reason" class="dls-reason" aria-label="Interruption reason">${DLS_REASONS.map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select>
      <button class="btn btn--sm" id="dlsInterruptBtn">⛈ Interrupt match</button>
      <button class="btn btn--sm btn--ghost btn--red" id="dlsAbandonBtn">Abandon</button>
    </div>`;
  }
  return `<div class="card dls-card">
    <div class="section-title" style="margin-top:0">${icon("umbrella")} DLS — rain &amp; interruptions</div>
    ${summary}${log}${controls}</div>
    <p class="tiny muted" style="margin:6px 2px 0">You only confirm overs — the revised target, par and required rate compute themselves (Standard Edition).</p>`;
}

function scoringCardsHtml(state, r, inn) {
  return `
    ${dlsCardHtml(state, inn)}
    ${r.allow_declaration && !inn.is_complete && !inn.is_super_over && !state.result
      ? `<button class="btn btn--ghost" id="declareBtn" style="margin-top:10px">${icon("flag")} Declare innings</button>` : ""}`;
}

// Match officials: the owner approves/declines umpire requests; an umpire (or other
// score-capable user) requests to officiate and sees their status.
function officialsPanel(state, officials) {
  if (!officials) return "";
  if (officials.is_manager) {
    const rows = officials.officials.length
      ? officials.officials.map((o) => `<div class="matchitem">${avatar(o.umpire_name)}
          <div class="mi-main"><b>${h(o.umpire_name)}</b><div class="tiny muted">${o.status === "approved" ? "✓ officiating" : "wants to officiate"}</div></div>
          <span class="rr-actions">${o.status === "pending" ? `<button class="btn btn--sm of-ok" data-uid="${h(o.umpire_id)}">Approve</button>` : ""}<button class="btn btn--ghost btn--sm of-no" data-uid="${h(o.umpire_id)}">${o.status === "approved" ? "Remove" : "Decline"}</button></span></div>`).join("")
      : `<div class="empty">No umpire requests yet.</div>`;
    return `<div class="section-title">${icon("gavel")} Match officials</div><div class="card" id="ofCard">${rows}</div>`;
  }
  if (!officials.can_score) {  // an umpire (or anyone signed in who can't already score)
    let body;
    if (officials.my_status === "approved") body = `<div class="tiny" style="color:var(--green-700);font-weight:800">✓ You're approved to officiate this match.</div>`;
    else if (officials.my_status === "pending") body = `<div class="tiny muted">⏳ Requested — awaiting the organizer's approval.</div>`;
    else body = `<button class="btn btn--sm" id="ofReq">${icon("gavel")} Request to officiate</button>`;
    return `<div class="section-title">${icon("gavel")} Officiate</div><div class="card" id="ofCard">${body}</div>`;
  }
  return "";
}

// Ball-by-ball feed: group the (oldest-first) feed into overs, newest over on top.
const BBL_MARK = { wicket: "W", four: "4", six: "6", wide: "wd", noball: "nb", bye: "b", legbye: "lb", dot: "•" };
function ballRow(b, canEdit) {
  const marker = BBL_MARK[b.kind] || String(b.runs);
  const tools = (canEdit && b.editable) ? `<span class="bbl-tools">
    <button class="bbl-edit" data-idx="${b.idx}" title="Correct this ball" aria-label="Edit">✎</button>
    <button class="bbl-del" data-idx="${b.idx}" title="Remove this ball" aria-label="Delete">${icon("trash")}</button></span>` : "";
  return `<div class="bbl-row"><span class="bbl-ov">${h(b.over_ball)}</span>
    <span class="bbl-badge bbl-${h(b.kind)}">${h(marker)}</span>
    <span class="bbl-text">${h(b.text)}</span>${tools}</div>`;
}
function ballFeedHtml(feed, canEdit) {
  const groups = [];
  feed.forEach((b) => {
    const over = b.over_ball.split(".")[0];
    const last = groups[groups.length - 1];
    if (!last || last.innings !== b.innings || last.over !== over) groups.push({ innings: b.innings, over, balls: [] });
    groups[groups.length - 1].balls.push(b);
  });
  return groups.reverse().map((g) => `<div class="bbl-over">
    <div class="bbl-over-h">${h(g.innings)} · Over ${+g.over + 1}</div>
    ${g.balls.slice().reverse().map((b) => ballRow(b, canEdit)).join("")}</div>`).join("");
}

function padHtml(state, r, inn) {
  // Between overs: choose or *change* the bowler. The previous over's bowler isn't
  // offered (no consecutive overs), and the picker stays up until the first ball is
  // bowled, so a wrong pick never traps the scorer.
  if (state.over_pending) {
    const staged = state.staged_bowler || "";
    const opts = state.available_bowlers.map((b) => `<option ${b === staged ? "selected" : ""}>${h(b)}</option>`).join("");
    const picker = `<div class="pad__inner bowler-pick">
      <div class="section-title" style="margin-top:0">New over — ${staged ? "bowler (change before you bowl)" : "pick the bowler"}</div>
      <div class="row">
        <select id="bowlerSel">${opts}</select>
        <button class="btn btn--sm" id="bowlerBtn" style="flex:0 0 auto">${staged ? "Change" : "Start over"}</button>
      </div></div>`;
    // once a bowler is staged, show the run pad too so the over can begin
    return `<div class="pad">${picker}${staged ? runPadInner(r, inn, staged) : ""}</div>`;
  }
  return `<div class="pad">${runPadInner(r, inn, inn.bowler || "")}</div>`;
}

function runPadInner(r, inn, bowler) {
  const sixBtn = r.over_boundary_out
    ? `<button class="padbtn padbtn--out" data-act="boundaryout">6=OUT</button>`
    : `<button class="padbtn padbtn--boundary" data-act="six">6</button>`;
  const extras = [
    r.wide.enabled ? `<button class="padbtn padbtn--extra" data-act="wide">Wd</button>` : "",
    r.no_ball.enabled ? `<button class="padbtn padbtn--extra" data-act="noball">Nb</button>` : "",
    r.byes_allowed ? `<button class="padbtn padbtn--extra" data-act="bye">B</button>` : "",
    r.leg_byes_allowed ? `<button class="padbtn padbtn--extra" data-act="legbye">Lb</button>` : "",
  ].filter(Boolean).join("");
  return `<div class="pad__inner">
    <div class="between" style="margin-bottom:6px">
      <div class="tiny muted">Bowling: <b>${h(bowler)}</b></div>
      <div class="shot-toggles">
        <label class="shot-track tiny"><input type="checkbox" id="trackShots" ${trackShots ? "checked" : ""}> ${icon("target", "rec-ico")} Shots</label>
        <label class="shot-track tiny"><input type="checkbox" id="trackPitch" ${trackPitch ? "checked" : ""}> Pitch</label>
      </div>
    </div>
    <div class="pad__grid">
      <button class="padbtn padbtn--run" data-act="run" data-v="0">0</button>
      <button class="padbtn padbtn--run" data-act="run" data-v="1">1</button>
      <button class="padbtn padbtn--run" data-act="run" data-v="2">2</button>
      <button class="padbtn padbtn--run" data-act="run" data-v="3">3</button>
      <button class="padbtn padbtn--boundary" data-act="run" data-v="4">4</button>
      ${sixBtn}
      ${extras}
      <button class="padbtn padbtn--wkt" data-act="wicket">OUT</button>
      <button class="padbtn padbtn--undo" data-act="undo">↶ Undo</button>
    </div></div>`;
}

function bindMatch(state, officials) {
  const id = state.id;
  const canScore = !!(officials && officials.can_score);
  const refresh = () => showMatch(id);
  const act = async (fn) => {
    try { await fn(); await refresh(); } catch (e) { toast(e.message, "error"); }
  };
  // actions that need the server (innings transitions, DLS, super-over, edit/delete)
  const onlineAct = (fn) => navigator.onLine ? act(fn) : toast("Connect to the internet for this.", "error");
  // scoring actions — routed through the offline queue so they work with no signal
  const doScore = async (op) => {
    if (navigator.onLine) {
      try { await flushMatch(id); await rawSend(id, op); await refresh(); return; }
      catch (e) { if (!isNetworkError(e)) return toast(e.message, "error"); }  // network died → offline path
    }
    try {
      const st = await scoreOffline(id, op);
      const offOf = { can_score: true, _offline: true };
      if (st) { stopLiveStream(); renderMatch(st, offOf); flashScore(); }
      else await refresh();
      toast(op.kind === "undo" ? "Undone offline" : "Saved offline — will sync", "ok");
    } catch (e) { toast(e.message, "error"); }
  };

  const secondBtn = document.getElementById("secondBtn");
  if (secondBtn) secondBtn.onclick = () => onlineAct(() => api.secondInnings(id));
  const declareBtn = document.getElementById("declareBtn");
  if (declareBtn) declareBtn.onclick = () => {
    if (confirm("Declare this innings closed? It can't be reopened.")) onlineAct(() => api.declareInnings(id));
  };

  // --- DLS interruption workflow: interrupt → confirm overs → auto target ---
  const nowHM = () => { const t = new Date(); return `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`; };
  const dlsInterruptBtn = document.getElementById("dlsInterruptBtn");
  if (dlsInterruptBtn) dlsInterruptBtn.onclick = () => {
    const reason = (document.getElementById("dls_reason") || {}).value || "rain";
    onlineAct(() => api.interruptMatch(id, reason, nowHM()));
  };
  const dlsResumeBtn = document.getElementById("dlsResumeBtn");
  if (dlsResumeBtn) dlsResumeBtn.onclick = () => {
    const overs = parseInt(document.getElementById("dls_overs").value, 10);
    if (!Number.isInteger(overs) || overs < 1) return toast("Enter the innings' new total overs", "error");
    const at = (document.getElementById("dls_resume_at") || {}).value || nowHM();
    onlineAct(() => api.resumeMatch(id, overs, at));
  };
  const dlsCancelBtn = document.getElementById("dlsCancelBtn");
  if (dlsCancelBtn) dlsCancelBtn.onclick = () => onlineAct(() => api.cancelInterruption(id));
  const dlsAbandonBtn = document.getElementById("dlsAbandonBtn");
  if (dlsAbandonBtn) dlsAbandonBtn.onclick = () => {
    const reason = (document.getElementById("dls_reason") || {}).value || "rain";
    if (!confirm("Abandon the match? If the chase has passed the minimum overs it will be decided on DLS par; otherwise it's a no-result.")) return;
    onlineAct(() => api.abandonMatch(id, reason));
  };

  // "Download PDF" opens the dedicated premium scorecard report (/scorecard/{id})
  // with ?print=1, which fires the print dialog itself.
  const pdfBtn = document.getElementById("pdfBtn");
  if (pdfBtn) pdfBtn.onclick = () => {
    window.open(`/scorecard/${encodeURIComponent(id)}?print=1`, "_blank", "noopener");
  };

  view.querySelectorAll("[data-bf]").forEach((b) => (b.onclick = () => onlineAct(() => api.superOver(id, b.dataset.bf))));
  const soSecond = document.getElementById("soSecond");
  if (soSecond) soSecond.onclick = () => onlineAct(() => api.superOver(id));

  const shareBtn = document.getElementById("shareBtn");
  if (shareBtn) shareBtn.onclick = () => share("/m/" + id, `${state.team_a} vs ${state.team_b}`);
  // stream controls live in the persistent #streamHost and are wired by bindStream(),
  // so they survive score re-renders (see renderMatch).

  // highlights reel — auto key moments (wickets / boundaries / milestones), filterable
  const hlList = document.getElementById("hlList");
  if (hlList) {
    let hlData = [], hlFilter = "all";
    const paintHl = () => { hlList.innerHTML = hlData.length ? highlightsHtml(hlData, hlFilter) : `<div class="empty tiny">Highlights will appear as the match is scored.</div>`; };
    view.querySelectorAll(".hlf").forEach((b) => (b.onclick = () => {
      view.querySelectorAll(".hlf").forEach((x) => x.classList.toggle("active", x === b));
      hlFilter = b.dataset.f; paintHl();
    }));
    api.highlights(id).then((d) => { hlData = d; paintHl(); }).catch((e) => { hlList.innerHTML = `<div class="empty tiny">${h(e.message)}</div>`; });
  }

  // highlight clips — YouTube/Facebook links the organizer/admin attaches
  // highlight clips live in the persistent #clipArea host (see renderMatch /
  // renderClipHost) so their videos survive score re-renders — nothing to wire here.
  const ballFeedEl = document.getElementById("ballFeed");
  if (ballFeedEl) {
    const commNotes = document.getElementById("commNotes");
    const loadNotes = async () => {
      try {
        const items = await api.matchCommentary(id);
        commNotes.innerHTML = items.length
          ? `<div class="comm-notes">${items.map((c) => `<div class="comm-note"><b>${icon("radio", "rec-ico")}${h(c.author_name)}</b> ${h(c.text)} <span class="tiny muted">${h(timeago(c.when))}</span></div>`).join("")}</div>`
          : "";
      } catch (e) { /* notes are optional */ }
    };
    const loadFeed = async () => {
      try {
        const feed = await api.ballFeed(id);
        ballFeedEl.innerHTML = feed.length ? ballFeedHtml(feed, canScore) : `<div class="empty tiny">Ball-by-ball will appear here as the match is scored.</div>`;
        if (canScore) {
          ballFeedEl.querySelectorAll(".bbl-edit").forEach((b) => (b.onclick = () => openEditBall(state, +b.dataset.idx, onlineAct)));
          ballFeedEl.querySelectorAll(".bbl-del").forEach((b) => (b.onclick = () => {
            if (confirm("Remove this delivery? The scorecard will be recomputed.")) onlineAct(async () => { await api.deleteBall(id, +b.dataset.idx); toast("Delivery removed ✓"); });
          }));
        }
      } catch (e) { ballFeedEl.innerHTML = `<div class="empty">${h(e.message)}</div>`; }
    };
    const postBtn = document.getElementById("commPost"), txt = document.getElementById("commText");
    if (postBtn) postBtn.onclick = async () => {
      const t = (txt.value || "").trim();
      if (!t) return;
      postBtn.disabled = true;
      try { await api.postCommentary(id, t); txt.value = ""; toast("Note posted ✓"); await loadNotes(); }
      catch (e) { toast(e.message, "error"); }
      finally { postBtn.disabled = false; }
    };
    if (txt) txt.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); postBtn && postBtn.click(); } });

    // ----- fielding log (dropped catches / runs saved / misfields) -----
    const fldList = document.getElementById("fldList");
    const FLD_ICO = { drop: icon("alert"), save: icon("shield"), misfield: icon("ban") };
    const FLD_LBL = { drop: "dropped a catch", save: "saved", misfield: "misfield" };
    const loadFielding = async () => {
      if (!fldList) return;
      try {
        const evs = await api.matchFielding(id);
        fldList.innerHTML = evs.length
          ? evs.map((e) => `<div class="fld-row"><span class="fld-ico">${FLD_ICO[e.kind] || icon("shield")}</span>
              <span class="fld-main"><b>${h(e.fielder)}</b> ${h(FLD_LBL[e.kind] || e.kind)}${e.kind !== "drop" && e.runs ? " " + e.runs : ""}${e.batter ? " — " + h(e.batter) : ""}${e.bowler ? ` <span class="muted">b ${h(e.bowler)}</span>` : ""}${e.note ? ` <span class="muted">· ${h(e.note)}</span>` : ""}</span>
              ${canScore ? `<button class="fld-del" data-id="${h(e.id)}" title="Remove">✕</button>` : ""}</div>`).join("")
          : `<div class="empty tiny">No fielding events logged.</div>`;
        if (canScore) fldList.querySelectorAll(".fld-del").forEach((b) => (b.onclick = async () => {
          try { await api.deleteFielding(id, b.dataset.id); await loadFielding(); }
          catch (e) { toast(e.message, "error"); }
        }));
      } catch (e) { fldList.innerHTML = `<div class="empty tiny">${h(e.message)}</div>`; }
    };
    const fldAdd = document.getElementById("fldAdd");
    if (fldAdd) fldAdd.onclick = async () => {
      const fielder = (val("fldName") || "").trim();
      if (!fielder) return toast("Enter a fielder", "error");
      const kind = document.getElementById("fldKind").value;
      const runs = parseInt(val("fldRuns"), 10) || 0;
      fldAdd.disabled = true;
      try {
        await api.addFielding(id, { fielder, kind, runs });
        document.getElementById("fldName").value = "";
        document.getElementById("fldRuns").value = "0";
        toast("Logged ✓");
        await loadFielding();
      } catch (e) { toast(e.message, "error"); }
      finally { fldAdd.disabled = false; }
    };

    loadNotes();
    loadFeed();
    loadFielding();
  }

  // match officials: owner approves/declines; umpire requests to officiate
  const ofCard = document.getElementById("ofCard");
  if (ofCard) ofCard.addEventListener("click", async (e) => {
    const ok = e.target.closest(".of-ok"), no = e.target.closest(".of-no"), req = e.target.closest("#ofReq");
    const btn = ok || no || req;
    if (!btn) return;
    btn.disabled = true;
    try {
      if (ok) { await api.approveOfficial(id, ok.dataset.uid); toast("Approved ✓"); }
      else if (no) { await api.removeOfficial(id, no.dataset.uid); toast("Removed"); }
      else { await api.requestOfficiate(id); toast("Request sent ✓"); }
      showMatch(id);
    } catch (err) { toast(err.message, "error"); btn.disabled = false; }
  });

  const bowlerBtn = document.getElementById("bowlerBtn");
  if (bowlerBtn) bowlerBtn.onclick = () =>
    doScore({ kind: "bowler", payload: { bowler: document.getElementById("bowlerSel").value } });

  // chart tabs (manhattan / worm / wagon / pitch). Wagon + pitch mount the shared
  // interactive components lazily on first view (hover tooltips + filters).
  const inn0 = state.innings[(state.current_innings || 1) - 1] || {};
  const ppEnd = (state.rules.powerplays && state.rules.powerplays[0]) ? state.rules.powerplays[0].end_over : 0;
  const mountChart = (ch) => {
    if (ch === "wagon" && window.CricWagon) {
      const host = document.getElementById("wagonMount");
      if (host && !host.dataset.mounted) {
        host.dataset.mounted = "1";
        CricWagon.mount(host, inn0.wagon || [], { batter: inn0.striker, ppOvers: ppEnd, maxOvers: inn0.max_overs });
      }
    }
    if (ch === "pitch" && window.CricPitch) {
      const host = document.getElementById("pitchMount");
      if (host && !host.dataset.mounted) {
        host.dataset.mounted = "1";
        CricPitch.mount(host, inn0.pitch || [], { bowler: inn0.bowler, ppOvers: ppEnd, maxOvers: inn0.max_overs });
      }
    }
  };
  view.querySelectorAll(".chtab").forEach((b) => (b.onclick = () => {
    view.querySelectorAll(".chtab").forEach((x) => x.classList.toggle("active", x === b));
    view.querySelectorAll(".chart-pane").forEach((p) => (p.hidden = p.dataset.pane !== b.dataset.ch));
    mountChart(b.dataset.ch);
  }));

  // optional wagon (batting) + pitch (bowling) shot tracking
  const tsBox = document.getElementById("trackShots");
  if (tsBox) tsBox.onchange = () => { trackShots = tsBox.checked; localStorage.setItem("cn_trackshots", trackShots ? "1" : "0"); };
  const tpBox = document.getElementById("trackPitch");
  if (tpBox) tpBox.onchange = () => { trackPitch = tpBox.checked; localStorage.setItem("cn_trackpitch", trackPitch ? "1" : "0"); };
  const submitBall = (payload) => doScore({ kind: "ball", payload });
  const CAUGHT = { caught: 1, caught_behind: 1, caught_and_bowled: 1 };
  const recordRun = (v) => captureBall({ action: "runs", value: v }, v > 0, submitBall);

  view.querySelectorAll(".padbtn").forEach((btn) => {
    btn.onclick = () => {
      const a = btn.dataset.act;
      if (a === "run") return recordRun(+btn.dataset.v);
      if (a === "six") return recordRun(6);
      if (a === "boundaryout") return captureBall({ action: "wicket", dismissal: "boundary_out" }, true, submitBall);
      const r = state.rules;
      if (a === "wide") return r.wide.allow_byes
        ? openExtraRuns("wide", (v) => captureBall({ action: "wide", value: v }, false, submitBall))
        : captureBall({ action: "wide", value: 0 }, false, submitBall);
      if (a === "noball") return r.no_ball.off_bat_counts
        ? openExtraRuns("no_ball", (v) => captureBall({ action: "no_ball", value: v }, v > 0, submitBall))
        : captureBall({ action: "no_ball", value: 0 }, false, submitBall);
      if (a === "bye") return openExtraRuns("bye", (v) => captureBall({ action: "bye", value: v }, false, submitBall));
      if (a === "legbye") return openExtraRuns("leg_bye", (v) => captureBall({ action: "leg_bye", value: v }, false, submitBall));
      if (a === "undo") return doScore({ kind: "undo" });
      if (a === "wicket") return openWicket(state, (body) => captureBall(body, !!CAUGHT[body.dismissal], submitBall));
    };
  });
}

function openWicket(state, onSubmit) {
  const allowed = state.rules.allowed_dismissals.filter((d) => d !== "boundary_out");
  const opts = allowed.map((d) => `<option value="${d}">${h(DISMISSALS[d] || d)}</option>`).join("");
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `
    <div class="modal__sheet">
      <h3>Wicket</h3>
      <label>How out</label><select id="w_type">${opts}</select>
      <label>Who's out</label>
      <select id="w_who"><option value="striker">Striker</option><option value="non_striker">Non-striker</option></select>
      <label>Fielder (optional)</label>
      <select id="w_fielder"><option value="">—</option>${(state.available_bowlers || []).map((b) => `<option value="${h(b)}">${h(b)}</option>`).join("")}</select>
      <div class="spacer"></div>
      <div class="row">
        <button class="btn btn--ghost" id="w_cancel">Cancel</button>
        <button class="btn btn--red" id="w_ok">Out!</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("#w_cancel").onclick = close;
  overlay.querySelector("#w_ok").onclick = () => {
    const body = {
      action: "wicket",
      dismissal: overlay.querySelector("#w_type").value,
      batter_out: overlay.querySelector("#w_who").value,
      fielder: overlay.querySelector("#w_fielder").value || null,
    };
    close();
    onSubmit(body);
  };
}

// Extras can carry runs: a no-ball hit off the bat, a wide the batters also ran,
// or 1-4 byes/leg-byes. Tapping the extra opens this quick chooser. The no-ball /
// wide one-run penalty is added by the engine automatically — this captures only
// the runs the batters actually made.
function openExtraRuns(kind, onPick) {
  const cfg = {
    no_ball: { title: "No-ball + runs off the bat", hint: "How many did the batter hit? The no-ball penalty is added automatically.", runs: [0, 1, 2, 3, 4, 6] },
    wide: { title: "Wide + runs", hint: "How many did the batters run? The wide penalty is added automatically.", runs: [0, 1, 2, 3, 4] },
    bye: { title: "Byes", hint: "How many byes did they run?", runs: [1, 2, 3, 4] },
    leg_bye: { title: "Leg byes", hint: "How many leg byes did they run?", runs: [1, 2, 3, 4] },
  }[kind];
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `<div class="modal__sheet">
    <h3>${h(cfg.title)}</h3>
    <p class="tiny muted" style="margin-top:0">${h(cfg.hint)}</p>
    <div class="pad__grid edit-grid">
      ${cfg.runs.map((n) => `<button class="padbtn padbtn--run" data-v="${n}">${n}</button>`).join("")}
    </div>
    <div class="spacer"></div>
    <button class="btn btn--ghost" id="x_cancel">Cancel</button>
  </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("#x_cancel").onclick = close;
  overlay.querySelectorAll(".padbtn").forEach((btn) => (btn.onclick = () => { close(); onPick(+btn.dataset.v); }));
}

// Correct an earlier delivery: pick the right outcome → PUT edit at its index.
function openEditBall(state, idx, act) {
  const id = state.id, r = state.rules;
  const opts = [
    ["0", { action: "runs", value: 0 }], ["1", { action: "runs", value: 1 }],
    ["2", { action: "runs", value: 2 }], ["3", { action: "runs", value: 3 }],
    ["4", { action: "runs", value: 4 }], ["6", { action: "runs", value: 6 }],
    r.wide.enabled ? ["Wd", { action: "wide", value: 0 }] : null,
    r.no_ball.enabled ? ["Nb", { action: "no_ball", value: 0 }] : null,
    r.byes_allowed ? ["B", { action: "bye", value: 1 }] : null,
    r.leg_byes_allowed ? ["Lb", { action: "leg_bye", value: 1 }] : null,
  ].filter(Boolean);
  const overlay = document.createElement("div");
  overlay.className = "modal";
  overlay.innerHTML = `<div class="modal__sheet">
    <h3>Correct this delivery</h3>
    <p class="tiny muted" style="margin-top:0">Pick the right outcome — the scorecard recomputes.</p>
    <div class="pad__grid edit-grid">
      ${opts.map(([lbl], i) => `<button class="padbtn padbtn--run" data-i="${i}">${lbl}</button>`).join("")}
      <button class="padbtn padbtn--wkt" data-i="wkt">OUT</button>
    </div>
    <div class="spacer"></div>
    <button class="btn btn--ghost" id="e_cancel">Cancel</button>
  </div>`;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("#e_cancel").onclick = close;
  const apply = (body) => act(async () => { await api.editBall(id, idx, body); toast("Delivery updated ✓"); });
  overlay.querySelectorAll(".padbtn").forEach((btn) => (btn.onclick = () => {
    const i = btn.dataset.i;
    close();
    if (i === "wkt") return openWicket(state, apply);
    apply(opts[+i][1]);
  }));
}

// --------------------------------------------------------------------------
// small helpers
// --------------------------------------------------------------------------
function segPick(sel, onPick) {
  const buttons = view.querySelectorAll(`${sel} button`);
  buttons.forEach((b) =>
    (b.onclick = () => {
      buttons.forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      onPick(b.dataset.v);
    })
  );
}

function toggle(id, label, checked) {
  return `<div class="switch"><label for="${id}">${h(label)}</label>
    <input type="checkbox" id="${id}" ${checked ? "checked" : ""} style="width:auto"></div>`;
}

// Register the service worker (PWA install + offline app shell).
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
