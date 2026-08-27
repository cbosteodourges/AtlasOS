"use strict";

const atlasPwaSecure = location.protocol === "https:" ||
  location.hostname === "localhost" || location.hostname === "127.0.0.1";

window.atlasPwaStatus = {
  supported: "serviceWorker" in navigator,
  secure: atlasPwaSecure,
  scope: "shell-only",
  offlineApi: false
};

if ("serviceWorker" in navigator && atlasPwaSecure) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js?v=4").catch(() => {
      // Le fonctionnement local classique reste disponible sans service worker.
    });
  });
}
