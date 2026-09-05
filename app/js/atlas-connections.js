"use strict";

(() => {
  const workspace = document.querySelector("[data-connection-workspace]");
  const inventory = document.querySelector("[data-connection-inventory]");
  const buttons = [...document.querySelectorAll("[data-connection-method]")];
  const stateKey = "atlasCoachSensorConnection";
  const setupKey = "atlasCoachSensorSetupComplete";
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);

  function readConnection() {
    try {
      return JSON.parse(localStorage.getItem(stateKey) || "null");
    } catch (_error) {
      return null;
    }
  }

  function configurePageContext() {
    const connection = readConnection();
    if (!connection?.provider || localStorage.getItem(setupKey) !== "true") return;
    document.body.classList.add("is-configured");
    document.querySelector(".connections-hero h1").textContent = "Vos connexions et vos données";
    document.querySelector(".connections-hero p").textContent = "Contrôlez la source principale, ajoutez une autre méthode et vérifiez précisément les données reçues par Atlas.";
    document.getElementById("connectionChoiceTitle").textContent = "Source principale et autres possibilités";
    const currentProvider = connection.provider === "health-connect" ? "atlas-connect" : connection.provider;
    const current = buttons.find(button => button.dataset.connectionMethod === currentProvider);
    if (!current) return;
    current.classList.add("is-current");
    let badge = current.querySelector("b");
    if (!badge) {
      badge = document.createElement("b");
      current.prepend(badge);
    }
    badge.textContent = "Source actuelle";
  }

  function formatDay(day) {
    if (!day) return "—";
    const date = new Date(`${day}T12:00:00`);
    return Number.isNaN(date.getTime()) ? day : date.toLocaleDateString("fr-FR");
  }

  async function loadInventory() {
    try {
      const response = await fetch(`/api/atlas/wellness-history?v=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Données indisponibles");
      const payload = await response.json();
      const latest = payload.latest_observation || payload.latest;
      const metrics = payload.latest_metrics || {};
      const types = payload.health_connect_inventory?.record_types || [];
      const record = name => types.find(item => item.record_type === name);
      const healthHrvCount = Number(record("HeartRateVariabilityRmssdRecord")?.count || 0);
      const hrv = metrics.hrv;
      const hrvSource = hrv?.hrv_last_night_ms_source === "health_connect" ? "Atlas Connect" : "Garmin Wellness";
      const hrvDetail = hrv?.hrv_last_night_ms != null
        ? `${formatDay(hrv.day)} · ${hrvSource}${healthHrvCount ? "" : " · absente de Santé Connect"}`
        : healthHrvCount ? "Santé Connect" : "Non transmise par Santé Connect";
      const hrvTone = hrv?.hrv_last_night_ms == null ? "missing" : hrv.day === latest?.day ? "available" : "stale";
      const cards = [
        ["Dernière journée", latest?.day || "—", latest ? "available" : "missing", "Atlas Connect"],
        ["Sommeil", latest?.sleep_duration_minutes != null ? "Disponible" : "Absent", latest?.sleep_duration_minutes != null ? "available" : "missing", latest?.sleep_duration_source || "—"],
        ["FC de repos", metrics.resting_heart_rate?.resting_heart_rate_bpm != null ? `${Math.round(metrics.resting_heart_rate.resting_heart_rate_bpm)} bpm` : "Absente", metrics.resting_heart_rate ? "available" : "missing", formatDay(metrics.resting_heart_rate?.day)],
        ["VFC RMSSD", hrv?.hrv_last_night_ms != null ? `${Math.round(hrv.hrv_last_night_ms)} ms` : "Absente", hrvTone, hrvDetail]
      ];
      inventory.innerHTML = cards.map(([label, value, tone, detail]) => `<article class="${tone}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></article>`).join("");
    } catch (error) {
      inventory.innerHTML = `<p class="connection-status">${escapeHtml(error.message)}. Vérifiez que le serveur Atlas OS est démarré.</p>`;
    }
  }

  function choose(method) {
    buttons.forEach(button => button.classList.toggle("selected", button.dataset.connectionMethod === method));
    workspace.hidden = false;
    if (method === "atlas-connect") {
      workspace.innerHTML = `<div class="section-copy"><span>ÉTAPE 2 · ATLAS CONNECT</span><h2>Synchroniser depuis Android</h2></div><ol><li><strong>Ouvrez Atlas Connect sur le téléphone</strong>Le téléphone et le PC doivent utiliser le même réseau Wi-Fi.</li><li><strong>Autorisez Santé Connect</strong>Atlas lit uniquement les catégories acceptées.</li><li><strong>Appuyez sur « Synchroniser Atlas »</strong>Attendez 100 %, puis vérifiez les données ci-dessous.</li></ol><button type="button" data-refresh-inventory>Vérifier les données reçues</button>`;
      localStorage.setItem(stateKey, JSON.stringify({ provider: method, updated_at: new Date().toISOString() }));
      localStorage.setItem(setupKey, "true");
    } else if (method === "garmin") {
      workspace.innerHTML = `<div class="section-copy"><span>ÉTAPE 2 · GARMIN</span><h2>Importer les fichiers Garmin disponibles</h2></div><p class="connection-status">Les fichiers FIT détaillent les activités. Les archives Wellness complètent notamment la VFC que Garmin peut ne pas publier dans Santé Connect.</p><a href="./physiologie.html">Ouvrir l’import Garmin →</a>`;
    } else if (method === "manual") {
      workspace.innerHTML = `<div class="section-copy"><span>ÉTAPE 2 · SANS MONTRE</span><h2>Commencer avec un profil prudent</h2></div><p class="connection-status">Atlas utilisera votre expérience, vos chronos, vos disponibilités et vos repères connus. Une montre pourra être ajoutée plus tard.</p><a href="./performance-running.html#profile">Compléter mon profil →</a>`;
      localStorage.setItem(stateKey, JSON.stringify({ provider: method, updated_at: new Date().toISOString() }));
      localStorage.setItem(setupKey, "true");
    } else {
      const names = { polar: "Polar", suunto: "Suunto", coros: "COROS", strava: "Strava" };
      workspace.innerHTML = `<div class="section-copy"><span>CONNECTEUR PARTENAIRE</span><h2>${escapeHtml(names[method] || method)}</h2></div><p class="connection-status">Ce connecteur est préparé mais ne sera jamais présenté comme actif avant une authentification réelle. Atlas Connect ou l’import de fichiers restent disponibles immédiatement.</p>`;
    }
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  configurePageContext();
  buttons.forEach(button => button.addEventListener("click", () => choose(button.dataset.connectionMethod)));
  workspace.addEventListener("click", event => {
    if (event.target.closest("[data-refresh-inventory]")) loadInventory();
  });
  loadInventory();
})();
