// CricNetra SPA service worker.
// Network-first for app code (so updates show immediately online), with a cached
// shell as the offline fallback. The API is never cached.
const CACHE = "cricnetra-spa-v127";
const SHELL = ["/app", "/css/styles.css?v=116", "/js/app.js?v=117", "/js/api.js?v=97", "/js/analytics.js?v=2", "/icon.svg?v=89", "/icon-192.png?v=1", "/icon-512.png?v=1", "/icon-180.png?v=1", "/manifest.webmanifest?v=2"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ---- Web Push ------------------------------------------------------------
// A push arrives as JSON: {title, body, url, tag, category}. Show it, and on
// click focus an existing app tab (or open one) at the target URL.
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  const title = d.title || "CricNetra";
  const opts = {
    body: d.body || "",
    tag: d.tag || d.category || "cricnetra",
    icon: "/icon-192.png?v=1",
    badge: "/icon-192.png?v=1",
    data: { url: d.url || "/app/" },
    renotify: true,
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || "/app/";
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const w of wins) {
      if (w.url.includes("/app") && "focus" in w) {
        w.navigate(target).catch(() => {});
        return w.focus();
      }
    }
    if (self.clients.openWindow) return self.clients.openWindow(target);
  })());
});

// When the browser rotates a subscription, re-subscribe and tell the server.
// The SW can't read the app's JWT, so it identifies by the old (secret,
// unguessable) endpoint via the unauthenticated /push/rotate endpoint.
self.addEventListener("pushsubscriptionchange", (e) => {
  e.waitUntil((async () => {
    try {
      const oldSub = e.oldSubscription;
      const appKey = oldSub && oldSub.options && oldSub.options.applicationServerKey;
      const newSub = e.newSubscription ||
        (await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: appKey }));
      const j = newSub.toJSON();
      await fetch("/api/v1/social/push/rotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_endpoint: oldSub ? oldSub.endpoint : null,
          endpoint: newSub.endpoint,
          keys: { p256dh: j.keys.p256dh, auth: j.keys.auth },
        }),
      });
    } catch (_) { /* best-effort; the app re-subscribes on next load anyway */ }
  })());
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Offline-friendly bell: the notifications list is cached (network-first) so the
  // notification center still renders when offline. Everything else under /api is live.
  if (e.request.method === "GET" && url.pathname === "/api/v1/social/notifications") {
    e.respondWith(
      fetch(e.request)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return res; })
        .catch(() => caches.match(e.request).then((m) => m || new Response("[]", { headers: { "Content-Type": "application/json" } })))
    );
    return;
  }
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return; // live data, never cached
  // `cache: "reload"` bypasses the browser HTTP cache so a returning visitor
  // always gets the latest app code online; the SW cache is only the offline
  // fallback below.
  e.respondWith(
    fetch(e.request, { cache: "reload" })
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
