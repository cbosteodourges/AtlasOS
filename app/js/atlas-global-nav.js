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

  const coachSubnav = isCoach ? `
    <div class="atlas-coach-subnav" aria-label="Rubriques Atlas Coach">
      <a class="atlas-coach-back" href="./atlas-cockpit.html">
        <span>←</span>
        Retour au Hub
      </a>
      <button type="button" data-coach-nav="overview">
        <span>⌂</span>
        Vue d’ensemble
      </button>
      <button type="button" data-coach-nav="sensors">
        <span>⌁</span>
        Montres et capteurs
      </button>
      <button type="button" data-coach-nav="profile">
        <span>◇</span>
        Profil et objectif
      </button>
      <button type="button" data-coach-nav="deadline">
        <span>◎</span>
        Prochaine échéance
      </button>
      <button type="button" data-coach-nav="plan">
        <span>▦</span>
        Plan personnalisé
      </button>
      <button type="button" data-coach-nav="history">
        <span>↝</span>
        Historique des séances
      </button>
    </div>
  ` : "";

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
        ${coachSubnav}
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

  if (isCoach) {
    const panels = [
      ...document.querySelectorAll("[data-coach-section]")
    ];
    const buttons = [
      ...nav.querySelectorAll("[data-coach-nav]")
    ];

    const showCoachSection = name => {
      const available = panels.some(
        panel => panel.dataset.coachSection === name
      );
      const selected = available ? name : "overview";

      panels.forEach(panel => {
        panel.classList.toggle(
          "is-coach-active",
          panel.dataset.coachSection === selected
        );
      });
      buttons.forEach(button => {
        const active = button.dataset.coachNav === selected;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });

      document.body.dataset.coachSection = selected;
      localStorage.setItem(
        "atlasCoachActiveSection",
        selected
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    buttons.forEach(button => {
      button.addEventListener(
        "click",
        () => showCoachSection(button.dataset.coachNav)
      );
    });

    showCoachSection(
      localStorage.getItem("atlasCoachActiveSection")
      || "overview"
    );
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
