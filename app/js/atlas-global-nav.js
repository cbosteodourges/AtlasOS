"use strict";

(() => {
  const page = location.pathname.split("/").pop() || "";
  const isHub = page === "atlas-hub.html";
  const isCoach = page === "performance-running.html";

  const hubItem = (tab, icon, label) => isHub
    ? `
      <button class="atlas-nav-item nav"
        type="button" data-tab="${tab}">
        <span class="atlas-nav-icon">${icon}</span>
        <span class="atlas-nav-label">${label}</span>
      </button>
    `
    : `
      <a class="atlas-nav-item"
        href="./atlas-hub.html#${tab}">
        <span class="atlas-nav-icon">${icon}</span>
        <span class="atlas-nav-label">${label}</span>
      </a>
    `;

  const linkItem = (href, icon, label, active = false) => `
    <a class="atlas-nav-item ${active ? "active" : ""}"
      href="${href}">
      <span class="atlas-nav-icon">${icon}</span>
      <span class="atlas-nav-label">${label}</span>
    </a>
  `;

  const markup = `
    <a class="atlas-nav-brand" href="./atlas-hub.html">
      <img src="./assets/atlas-logo-full.jpg" alt="Atlas OS">
      <span>
        <strong>ATLAS OS</strong>
        <small>Human Digital Twin</small>
      </span>
    </a>

    <button class="atlas-talk-button" type="button"
      data-atlas-talk aria-label="Parler à Atlas">
      <span class="atlas-talk-orb">✦</span>
      <span class="atlas-talk-copy">
        <strong>Parler à Atlas</strong>
        <small>Enrichissez votre Jumeau Numérique</small>
      </span>
    </button>
    <div class="atlas-nav-items">
      ${hubItem("balance", "⌂", "Aujourd’hui")}
      ${linkItem(
        "./performance-running.html",
        "◉",
        "Atlas Coach",
        isCoach
      )}
      ${hubItem("health", "♡", "Santé globale")}
      ${hubItem("injuries", "⌁", "Douleurs et blessures")}
      ${hubItem("analysis", "✦", "Analyse Atlas")}
      ${hubItem("timeline", "↝", "Chronologie")}

      <div class="atlas-nav-divider"></div>

      ${linkItem("./physiologie.html", "∿", "Physiologie")}
      ${linkItem("./biomecanique.html", "◇", "Atlas Physio")}
      ${linkItem("./prevention.html", "△", "Prévention")}
      ${linkItem("./memoire.html", "◫", "Mémoire Atlas")}
    </div>

    <div class="atlas-nav-user">
      <span class="atlas-nav-avatar">CB</span>
      <span>
        <strong>Christophe</strong>
        <small>Digital Twin actif</small>
      </span>
    </div>
  `;

  let nav;

  if (isHub) {
    const app = document.querySelector(".app");
    nav = document.querySelector(".sidebar");

    if (!app || !nav) return;

    app.classList.add("has-atlas-global-nav");
    nav.className = "sidebar atlas-global-nav";
    nav.innerHTML = markup;
  } else {
    nav = document.createElement("aside");
    nav.className = "atlas-global-nav";
    nav.setAttribute("aria-label", "Navigation Atlas OS");
    nav.innerHTML = markup;
    document.body.prepend(nav);
    document.body.classList.add("has-atlas-global-nav");
  }

  nav.querySelector("[data-atlas-talk]")?.addEventListener(
    "click",
    () => window.dispatchEvent(
      new CustomEvent("atlas:conversation-open")
    )
  );
  nav.addEventListener("dblclick", () => {
    nav.classList.toggle("is-expanded");
  });

  if (isHub && location.hash) {
    window.addEventListener("load", () => {
      const tab = location.hash.slice(1);
      document.querySelector(
        `[data-tab="${CSS.escape(tab)}"]`
      )?.click();
    });
  }
})();