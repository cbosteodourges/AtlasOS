"use strict";

(() => {
  const page = location.pathname.split("/").pop() || "";
  const isHub = page === "atlas-hub.html";
  const isCoach = page === "performance-running.html";

  const hubDestination = (tab, icon, label, active = false) => isHub
    ? `<button class="atlas-nav-item ${active ? "active" : ""}" type="button" data-tab="${tab}">
        <span class="atlas-nav-icon">${icon}</span><span class="atlas-nav-label">${label}</span>
      </button>`
    : `<a class="atlas-nav-item ${active ? "active" : ""}" href="./atlas-hub.html#${tab}">
        <span class="atlas-nav-icon">${icon}</span><span class="atlas-nav-label">${label}</span>
      </a>`;

  const link = (href, icon, label, active = false) => `
    <a class="atlas-nav-item ${active ? "active" : ""}" href="${href}">
      <span class="atlas-nav-icon">${icon}</span><span class="atlas-nav-label">${label}</span>
    </a>`;

  const markup = `
    <a class="atlas-nav-brand" href="./atlas-opening.html">
      <img src="./assets/atlas-logo-full.jpg" alt="Atlas OS">
      <span><strong>ATLAS OS</strong><small>Jumeau numérique humain</small></span>
    </a>
    <div class="atlas-nav-items">
      ${link("./atlas-cockpit.html", "⌂", "Aujourd’hui", page === "atlas-cockpit.html")}
      ${link("./performance-running.html", "◉", "Entraînement", isCoach)}
      ${hubDestination("health", "♡", "Santé", isHub && location.hash !== "#timeline")}
      ${hubDestination("timeline", "↝", "Historique", isHub && location.hash === "#timeline")}
    </div>
    <button class="atlas-talk-button" type="button" data-atlas-talk aria-label="Parler à Atlas">
      <span class="atlas-talk-orb">✦</span>
      <span class="atlas-talk-copy"><strong>Parler à Atlas</strong><small>Ajouter un ressenti ou poser une question</small></span>
    </button>
    <div class="atlas-nav-user">
      <span class="atlas-nav-avatar">CB</span>
      <span><strong>Christophe</strong><small>Jumeau synchronisé</small></span>
    </div>`;

  let nav;
  if (isHub) {
    const app = document.querySelector(".app");
    nav = document.querySelector(".sidebar");
    if (!app || !nav) return;
    app.classList.add("has-atlas-global-nav");
    nav.className = "sidebar atlas-global-nav";
  } else {
    nav = document.createElement("aside");
    nav.className = "atlas-global-nav";
    nav.setAttribute("aria-label", "Navigation Atlas OS");
    document.body.prepend(nav);
    document.body.classList.add("has-atlas-global-nav");
  }
  nav.innerHTML = markup;

  nav.querySelector("[data-atlas-talk]")?.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("atlas:conversation-open"));
  });

  if (isHub) {
    const requested = location.hash.slice(1);
    const initial = ["health", "timeline"].includes(requested) ? requested : "health";
    window.addEventListener("load", () => {
      nav.querySelector(`[data-tab="${initial}"]`)?.click();
    });
  }
})();
