// Thin wrapper around the CricNetra JSON API (same-origin /api/v1).
const BASE = "/api/v1";
const TOKEN_KEY = "cn_token";
const REFRESH_KEY = "cn_refresh";
let TOKEN = localStorage.getItem(TOKEN_KEY) || null;
let REFRESH = localStorage.getItem(REFRESH_KEY) || null;

function setTokens(access, refresh) {
  TOKEN = access || null;
  if (access) localStorage.setItem(TOKEN_KEY, access);
  else localStorage.removeItem(TOKEN_KEY);
  // a refresh of undefined means "leave it"; null/"" means "clear it"
  if (refresh !== undefined) {
    REFRESH = refresh || null;
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    else localStorage.removeItem(REFRESH_KEY);
  }
}

function _raw(method, path, body) {
  const opt = { method, headers: {} };
  if (TOKEN) opt.headers["Authorization"] = "Bearer " + TOKEN;
  if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  return fetch(BASE + path, opt);
}

// Access tokens are short-lived; on a 401 we transparently rotate the refresh
// token once and retry. Concurrent 401s share one in-flight refresh.
let _refreshing = null;
function _tryRefresh() {
  if (!REFRESH) return Promise.resolve(false);
  if (!_refreshing) {
    _refreshing = fetch(BASE + "/auth/refresh", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: REFRESH }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("refresh failed");
        const d = await r.json();
        setTokens(d.access_token, d.refresh_token);
        return true;
      })
      .catch(() => { setTokens(null, null); return false; })
      .finally(() => { _refreshing = null; });
  }
  return _refreshing;
}

const FIELD_LABELS = {
  full_name: "Full name", username: "Username", mobile_no: "Mobile number",
  email: "Email", password: "Password", role: "Role", identifier: "Mobile or username",
};
// Turn a FastAPI error body into one readable sentence. `detail` is either a string
// (our HTTPExceptions) or the 422 validation array [{loc,msg,…}] — never show it raw.
function humanError(data, fallback) {
  const d = data ? (data.detail !== undefined ? data.detail : data.message) : null;
  if (typeof d === "string" && d) return d;
  if (Array.isArray(d) && d.length) {
    const parts = d.map((e) => {
      const field = e && e.loc && e.loc[e.loc.length - 1];
      const label = FIELD_LABELS[field];
      const m = (e && e.msg) || "";
      if (/^Value error,/i.test(m)) return m.replace(/^Value error,\s*/i, "");
      return label ? m.replace(/^String /, label + " ") : m;
    }).filter(Boolean);
    if (parts.length) return parts.join(". ");
  }
  if (d && d.msg) return String(d.msg).replace(/^Value error,\s*/i, "");
  return fallback || "Something went wrong — please try again.";
}

async function req(method, path, body) {
  let res = await _raw(method, path, body);
  if (res.status === 401 && REFRESH && !path.startsWith("/auth/refresh") && !path.startsWith("/auth/login")) {
    if (await _tryRefresh()) res = await _raw(method, path, body);  // retry once with the new token
  }
  if (res.status === 401) setTokens(null, null); // still unauthorized → fully logged out
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const err = new Error(humanError(data, res.statusText));
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  // ----- auth -----
  isAuthed: () => !!TOKEN,
  register: (body) => req("POST", "/auth/register", body),
  async login(identifier, password) {
    const r = await req("POST", "/auth/login", { identifier, password });
    setTokens(r.access_token, r.refresh_token);
    return r;
  },
  me: () => req("GET", "/auth/me"),
  setEmail: (email) => req("PATCH", "/auth/email", { email }),
  logout() {
    const rt = REFRESH;
    setTokens(null, null);  // clear locally right away
    if (rt) fetch(BASE + "/auth/logout", {  // best-effort server-side revoke
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    }).catch(() => {});
  },
  myProfile: () => req("GET", "/auth/profile"),
  completeProfile: (b) => req("POST", "/auth/profile", b),
  updateProfile: (b) => req("PATCH", "/auth/profile", b),
  users: (role) => req("GET", role ? "/users?role=" + encodeURIComponent(role) : "/users"),
  search: (q) => req("GET", "/search?q=" + encodeURIComponent(q)),

  // venues — grounds + coaching academies directory
  venues: (qs) => req("GET", "/venues" + (qs ? "?" + qs : "")),
  createVenue: (b) => req("POST", "/venues", b),
  venue: (id) => req("GET", `/venues/${id}`),
  deleteVenue: (id) => req("DELETE", `/venues/${id}`),

  // account verification + password reset
  requestVerify: () => req("POST", "/auth/verify/request"),
  confirmVerify: (code) => req("POST", "/auth/verify/confirm", { code }),
  forgotPassword: (identifier) => req("POST", "/auth/password/forgot", { identifier }),
  resetPassword: (token, new_password) => req("POST", "/auth/password/reset", { token, new_password }),

  // community / social
  follow: (id) => req("POST", `/social/follow/${id}`),
  unfollow: (id) => req("DELETE", `/social/follow/${id}`),
  myFollowing: () => req("GET", "/social/following"),
  feed: () => req("GET", "/social/feed"),
  notifications: () => req("GET", "/social/notifications"),
  unreadCount: () => req("GET", "/social/notifications/unread"),
  markNotifsRead() {
    return req("POST", "/social/notifications/read").catch((e) => {
      // offline? replay once we're back so the read state syncs to the server
      if (!navigator.onLine) {
        const replay = () => { window.removeEventListener("online", replay); req("POST", "/social/notifications/read").catch(() => {}); };
        window.addEventListener("online", replay);
      }
      throw e;
    });
  },
  markNotifClicked: (id) => req("POST", `/social/notifications/${id}/click`),
  deleteNotification: (id) => req("DELETE", `/social/notifications/${id}`),
  // follow non-user entities (team | player | tournament | match | club | academy)
  followEntity: (type, id) => req("POST", `/social/follow/entity/${type}/${id}`),
  unfollowEntity: (type, id) => req("DELETE", `/social/follow/entity/${type}/${id}`),
  entityFollowState: (type, id) => req("GET", `/social/follow/entity/${type}/${id}`),
  followedEntities: () => req("GET", "/social/following/entities"),
  // notification preferences
  notifPrefs: () => req("GET", "/social/notifications/preferences"),
  saveNotifPrefs: (prefs) => req("PUT", "/social/notifications/preferences", prefs),
  // realtime SSE (EventSource can't send headers → token in the query string)
  notifStreamUrl: () => BASE + "/social/notifications/stream?token=" + encodeURIComponent(TOKEN || ""),
  // web push (browser notifications)
  vapidKey: () => req("GET", "/social/push/vapid-key"),
  pushSubscribe: (sub) => req("POST", "/social/push/subscribe", sub),
  pushUnsubscribe: (endpoint) => req("POST", "/social/push/unsubscribe", { endpoint }),
  // sign out on every device (revokes all refresh tokens + forgets push devices)
  async logoutAll() {
    try { await req("POST", "/auth/logout-all"); } finally { setTokens(null, null); }
  },

  // direct messages
  messages: () => req("GET", "/messages"),
  thread: (uid) => req("GET", `/messages/${uid}`),
  sendMessage: (recipient_id, text) => req("POST", "/messages", { recipient_id, text }),
  unreadMessages: () => req("GET", "/messages/unread"),

  // "Looking For" board
  lookingFor: (kind, location) => {
    const p = new URLSearchParams();
    if (kind) p.set("kind", kind);
    if (location) p.set("location", location);
    const qs = p.toString();
    return req("GET", "/looking-for" + (qs ? "?" + qs : ""));
  },
  myLookingFor: () => req("GET", "/looking-for/mine"),
  postLookingFor: (body) => req("POST", "/looking-for", body),
  closeLookingFor: (id) => req("POST", `/looking-for/${id}/close`),
  deleteLookingFor: (id) => req("DELETE", `/looking-for/${id}`),

  // admin — elevated-role approval queue
  roleRequests: () => req("GET", "/admin/role-requests"),
  approveRole: (userId) => req("POST", `/admin/role-requests/${userId}/approve`),
  rejectRole: (userId) => req("POST", `/admin/role-requests/${userId}/reject`),
  // admin — broadcast announcements + engagement analytics
  sendAnnouncement: (body) => req("POST", "/admin/announcements", body),
  announcementAnalytics: () => req("GET", "/admin/announcements/analytics"),
  // admin — areas, organizations & organizers (an organizer is a promoted account,
  // never a new one: createOrganizer takes the user_id of somebody who signed up)
  areas: () => req("GET", "/admin/areas"),
  createArea: (b) => req("POST", "/admin/areas", b),
  deleteArea: (id) => req("DELETE", `/admin/areas/${id}`),
  organizations: (areaId) => req("GET", "/admin/organizations" + (areaId ? "?area_id=" + encodeURIComponent(areaId) : "")),
  createOrganization: (b) => req("POST", "/admin/organizations", b),
  deleteOrganization: (id) => req("DELETE", `/admin/organizations/${id}`),
  organizers: (areaId) => req("GET", "/admin/organizers" + (areaId ? "?area_id=" + encodeURIComponent(areaId) : "")),
  createOrganizer: (b) => req("POST", "/admin/organizers", b),
  updateOrganizer: (userId, b) => req("PATCH", `/admin/organizers/${userId}`, b),
  standDownOrganizer: (userId) => req("DELETE", `/admin/organizers/${userId}`),
  // admin — the only way an account's role changes (sign-up can't grant one)
  assignRole: (userId, role) => req("PUT", `/admin/users/${userId}/role`, { role }),
  // admin — who changed what, newest first
  audit: (opts) => {
    const p = new URLSearchParams();
    if (opts && opts.action) p.set("action", opts.action);
    if (opts && opts.actorId) p.set("actor_id", opts.actorId);
    if (opts && opts.limit) p.set("limit", opts.limit);
    const qs = p.toString();
    return req("GET", "/admin/audit" + (qs ? "?" + qs : ""));
  },
  // keepalive variant so a deferred delete still commits during page unload
  deleteNotificationBeacon: (id) =>
    fetch(BASE + `/social/notifications/${id}`, {
      method: "DELETE",
      keepalive: true,
      headers: TOKEN ? { Authorization: "Bearer " + TOKEN } : {},
    }).catch(() => {}),

  // pictures — multipart upload (req() is JSON-only, so use fetch directly).
  // kind is "user" (own profile), "player", or "team". Serve URLs are public so <img> works.
  photoSrc(kind, id, bust) {
    const seg = kind === "user" ? "users" : kind === "team" ? "teams" : "players";
    return `${BASE}/${seg}/${id}/photo${bust ? "?v=" + bust : ""}`;
  },
  _photoPath(kind, id) {
    if (kind === "user") return "/auth/profile/photo";
    return kind === "team" ? `/teams/${id}/photo` : `/players/${id}/photo`;
  },
  async uploadPhoto(kind, id, file) {
    const fd = new FormData();
    fd.append("file", file);
    const headers = TOKEN ? { Authorization: "Bearer " + TOKEN } : {};
    const res = await fetch(BASE + this._photoPath(kind, id), { method: "POST", headers, body: fd });
    if (res.status === 401) setTokens(null, null);
    if (!res.ok) {
      const d = await res.json().catch(() => null);
      throw new Error((d && d.detail) || "Upload failed");
    }
  },
  deletePhoto(kind, id) {
    return req("DELETE", this._photoPath(kind, id));
  },

  // presets & rule templates
  presets: () => req("GET", "/presets"),
  preset: (id) => req("GET", `/presets/${id}`),
  templates: () => req("GET", "/rule-templates"),
  template: (id) => req("GET", `/rule-templates/${id}`),
  saveTemplate: (rules) => req("POST", "/rule-templates", rules),
  deleteTemplate: (id) => req("DELETE", `/rule-templates/${id}`),

  // roster: players & teams
  players: () => req("GET", "/players"),
  createPlayer: (p) => req("POST", "/players", p),
  deletePlayer: (id) => req("DELETE", `/players/${id}`),
  updatePlayer: (id, body) => req("PATCH", `/players/${id}`, body),
  playerStats: (id) => req("GET", `/players/${id}/stats`),
  playerInsights: (id) => req("GET", `/players/${id}/insights`),
  playerAwards: (id) => req("GET", `/players/${id}/awards`),
  playerSplits: (id) => req("GET", `/players/${id}/splits`),
  // The whole career: every match with this player's own line in it, plus the
  // record broken down by tournament, year and side.
  playerHistory: (id) => req("GET", `/players/${id}/history`),
  player: (id) => req("GET", `/players/${id}`),
  claimablePlayers: () => req("GET", "/players/claimable"),
  myPlayers: () => req("GET", "/players/mine"),
  claimPlayer: (id) => req("POST", `/players/${id}/claim`),
  compare: (a, b) => req("GET", `/insights/compare?player_a=${encodeURIComponent(a)}&player_b=${encodeURIComponent(b)}`),
  teamStats: (id) => req("GET", `/teams/${id}/stats`),
  leaderboards: (opts) => {
    const p = new URLSearchParams();
    if (opts && opts.window && opts.window !== "all") p.set("window", opts.window);
    if (opts && opts.location) p.set("location", opts.location);
    const qs = p.toString();
    return req("GET", "/leaderboards" + (qs ? "?" + qs : ""));
  },

  // tournaments
  tournaments: () => req("GET", "/tournaments"),
  tournament: (id) => req("GET", `/tournaments/${id}`),
  createTournament: (b) => req("POST", "/tournaments", b),
  deleteTournament: (id) => req("DELETE", `/tournaments/${id}`),
  startFixture: (fid, b) => req("POST", `/tournaments/fixtures/${fid}/start`, b),
  tournamentSquads: (tid) => req("GET", `/tournaments/${tid}/squads`),
  // tournament staff — an organizer's umpires & commentators, scoped to ONE
  // competition. Reading needs the owner, its staff or the admin (else 403);
  // writing needs the owner. The server decides, not the caller.
  tournamentStaff: (tid, role) => req("GET", `/tournaments/${tid}/staff` + (role ? "?staff_role=" + encodeURIComponent(role) : "")),
  addUmpire: (tid, userId) => req("POST", `/tournaments/${tid}/staff/umpires`, { user_id: userId }),
  addCommentator: (tid, userId) => req("POST", `/tournaments/${tid}/staff/commentators`, { user_id: userId }),
  removeStaff: (tid, role, userId) => req("DELETE", `/tournaments/${tid}/staff/${role}/${userId}`),
  setStaffActive: (tid, role, userId, isActive) => req("PATCH", `/tournaments/${tid}/staff/${role}/${userId}`, { is_active: isActive }),
  myStaffing: (role) => req("GET", "/tournaments/mine/staffing" + (role ? "?staff_role=" + encodeURIComponent(role) : "")),
  tournamentPlayers: (tid) => req("GET", `/tournaments/${tid}/players`),
  registerSquad: (tid, teamId, playerId) => req("POST", `/tournaments/${tid}/teams/${teamId}/squad`, { player_id: playerId }),
  unregisterSquad: (tid, teamId, playerId) => req("DELETE", `/tournaments/${tid}/teams/${teamId}/squad/${playerId}`),
  teams: () => req("GET", "/teams"),
  team: (id) => req("GET", `/teams/${id}`),
  createTeam: (t) => req("POST", "/teams", t),
  deleteTeam: (id) => req("DELETE", `/teams/${id}`),
  addMember: (teamId, body) => req("POST", `/teams/${teamId}/members`, body),
  removeMember: (teamId, playerId) => req("DELETE", `/teams/${teamId}/members/${playerId}`),

  // matches
  matches: () => req("GET", "/matches"),
  match: (id) => req("GET", `/matches/${id}`),
  createMatch: (payload) => req("POST", "/matches", payload),
  setBowler: (id, bowler) => req("POST", `/matches/${id}/bowler`, { bowler }),
  ball: (id, ball) => req("POST", `/matches/${id}/balls`, ball),
  editBall: (id, index, ball) => req("PUT", `/matches/${id}/balls/${index}`, ball),
  deleteBall: (id, index) => req("DELETE", `/matches/${id}/balls/${index}`),
  undo: (id) => req("POST", `/matches/${id}/undo`),
  secondInnings: (id) => req("POST", `/matches/${id}/second-innings`),
  revisedTarget: (id, target, overs) => req("POST", `/matches/${id}/revised-target`, { target, overs: overs || null }),
  dlsSuggest: (id, team2Overs, g50) => req("POST", `/matches/${id}/dls-suggest`, { team2_overs: team2Overs, g50: g50 || null }),
  // DLS rain interruptions — the automatic workflow (scorer only confirms overs)
  interruptMatch: (id, reason, at) => req("POST", `/matches/${id}/interrupt`, { reason, at: at || null }),
  resumeMatch: (id, overs, at) => req("POST", `/matches/${id}/resume`, { overs, at: at || null }),
  cancelInterruption: (id) => req("POST", `/matches/${id}/interrupt/cancel`),
  abandonMatch: (id, reason) => req("POST", `/matches/${id}/abandon`, { reason }),
  declareInnings: (id) => req("POST", `/matches/${id}/declare`),
  superOver: (id, batFirst) => req("POST", `/matches/${id}/super-over`, { bat_first: batFirst || null }),
  setStream: (id, url) => req("PUT", `/matches/${id}/stream`, { stream_url: url || null }),
  commentate: (id) => req("POST", `/matches/${id}/commentate`),
  matchCommentary: (id) => req("GET", `/matches/${id}/commentary`),
  postCommentary: (id, text) => req("POST", `/matches/${id}/commentary`, { text }),
  ballFeed: (id) => req("GET", `/matches/${id}/ball-feed`),
  highlights: (id) => req("GET", `/matches/${id}/highlights`),
  allHighlights: () => req("GET", "/highlights"),                 // every match's clips, grouped
  myMatches: () => req("GET", "/highlights/my-matches"),          // matches I can add clips to
  matchClips: (id) => req("GET", `/matches/${id}/clips`),
  addClip: (id, url, label) => req("POST", `/matches/${id}/clips`, { url, label: label || null }),
  removeClip: (id, clipId) => req("DELETE", `/matches/${id}/clips/${clipId}`),
  recordingStatus: (id) => req("GET", `/matches/${id}/recording`),
  autoClips: (id, anchor) => req("POST", `/matches/${id}/clips/auto`, { anchor }),
  async uploadRecording(id, file) {
    const fd = new FormData();
    fd.append("file", file);
    const headers = TOKEN ? { Authorization: "Bearer " + TOKEN } : {};
    const res = await fetch(BASE + `/matches/${id}/recording`, { method: "POST", headers, body: fd });
    if (res.status === 401) setTokens(null, null);
    if (!res.ok) { const d = await res.json().catch(() => null); throw new Error((d && d.detail) || "Upload failed"); }
    return res.json();
  },
  // fielding events: dropped catches / runs saved / misfields
  matchFielding: (id) => req("GET", `/matches/${id}/fielding`),
  addFielding: (id, body) => req("POST", `/matches/${id}/fielding`, body),
  deleteFielding: (id, eventId) => req("DELETE", `/matches/${id}/fielding/${eventId}`),
  // per-match umpire approval
  matchOfficials: (id) => req("GET", `/matches/${id}/officials`),
  pendingOfficials: () => req("GET", "/matches/officials/pending"),
  requestOfficiate: (id) => req("POST", `/matches/${id}/officials/request`),
  approveOfficial: (id, uid) => req("POST", `/matches/${id}/officials/${uid}/approve`),
  removeOfficial: (id, uid) => req("DELETE", `/matches/${id}/officials/${uid}`),
  deleteMatch: (id) => req("DELETE", `/matches/${id}`),
};
