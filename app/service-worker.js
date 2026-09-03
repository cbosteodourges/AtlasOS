"use strict";

const CACHE_NAME = "atlas-shell-v21";
const APP_SHELL = [
  "./atlas-cockpit.html",
  "./performance-running.html",
  "./atlas-hub.html",
  "./nutrition-hydration.html",
  "./atlas-metric-history.html",
  "./offline.html",
  "./manifest.webmanifest",
  "./assets/atlas-logo-full.jpg",
  "./assets/atlas-os-icon-avatar-master.png",
  "./assets/anatomy/servier/foot-ankle-anterior.png",
  "./assets/anatomy/servier/foot-ankle-lateral-deep.png",
  "./css/atlas-responsive.css",
  "./css/nutrition-hydration.css",
  "./js/atlas-pwa.js",
  "./js/nutrition-hydration.js"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request).then(
          cached => cached || caches.match("./offline.html")
        ))
    );
    return;
  }
  if (["style", "script"].includes(event.request.destination)) {
    event.respondWith(
      fetch(event.request, { cache: "no-store" })
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(cached => {
      const refreshed = fetch(event.request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        }
        return response;
      });
      if (cached) {
        event.waitUntil(refreshed.catch(() => undefined));
        return cached;
      }
      return refreshed;
    })
  );
});
