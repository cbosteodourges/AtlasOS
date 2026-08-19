"use strict";

(() => {
  const page = location.pathname.split("/").pop() || "";
  const isHub = page === "atlas-hub.html";
  const isCoach = page === "performance-running.html";

  const primaryItem = ({ href, tab, icon, label, active = false, extra = "" }) => {
    const className = `atlas-nav-item ${active ? "active" : ""}`;
    const content = `<span class="atlas-nav-icon">${icon}</span><span class="atlas-nav-label">${label}</span>`;
    return tab && isHub
      ? `<button class="${className}" type="button" data-tab="${tab}" ${extra}>${content}</button>`
      : `<a class="${className}" href="${href}" ${extra}>${content}</a>`;
  };

  const coachSubnav = isCoach ? `
    <div class="atlas-context-subnav" aria-label="Sous-menu Entraînement">
      <button type="button" data-coach-nav="overview"><span>Vue d’ensemble</span></button>
      <button type="button" data-coach-nav="sensors"><span>Montres et capteurs</span></button>
      <button type="button" data-coach-nav="profile"><span>Profil et objectif</span></button>
      <button type="button" data-coach-nav="deadline"><span>Prochaine échéance</span></button>
      <button type="button" data-coach-nav="plan"><span>Plan personnalisé</span></button>
      <button type="button" data-coach-nav="history"><span>Historique des séances</span></button>
    </div>` : "";

  const healthSubnav = isHub ? `
    <div class="atlas-context-subnav" aria-label="Sous-menu Santé">
      <button type="button" data-tab="balance" data-health-nav="balance"><span>Équilibre</span></button>
      <button type="button" data-tab="health" data-health-nav="health"><span>Santé</span></button>
      <button type="button" data-tab="injuries" data-health-nav="injuries"><span>Blessures</span></button>
      <button type="button" data-tab="timeline" data-health-nav="timeline"><span>Chronologie</span></button>
    </div>` : "";

  const nav = document.createElement("aside");
  nav.className = "atlas-global-nav";
  nav.setAttribute("aria-label", "Navigation Atlas");
  nav.innerHTML = `
    <a class="atlas-brand" href="./atlas-cockpit.html" aria-label="Retour à Aujourd’hui">
      <img src="./assets/logo-atlas.png" alt="">
      <span><strong>ATLAS OS</strong><small>Jumeau numérique humain</small></span>
    </a>

    <nav class="atlas-primary-nav">
      ${primaryItem({ href: "./atlas-cockpit.html", icon: "⌂", label: "Aujourd’hui", active: page === "atlas-cockpit.html" })}
      ${primaryItem({ href: "./performance-running.html", icon: "◎", label: "Entraînement", active: isCoach })}
      ${coachSubnav}
      ${primaryItem({ href: "./atlas-hub.html#health", tab: "health", icon: "♡", label: "Santé", active: isHub, extra: 'data-primary-health="health"' })}
      ${healthSubnav}
      ${primaryItem({ href: "./atlas-hub.html#timeline", tab: "timeline", icon: "⌁", label: "Historique", extra: 'data-primary-health="timeline"' })}
    </nav>

    <button class="atlas-talk" type="button" data-atlas-talk>
      <span class="atlas-talk-orb">✦</span>
      <span><strong>Parler à Atlas</strong><small>Ajouter un ressenti ou poser une question</small></span>
    </button>

    <div class="atlas-profile">
      <span class="atlas-profile-avatar">CB</span>
      <span><strong>Christophe</strong><small>Jumeau synchronisé</small></span>
    </div>
  `;

  const app = document.querySelector(".app");
  if (isHub && app) {
    app.prepend(nav);
    app.classList.add("has-atlas-global-nav");
  } else {
    document.body.prepend(nav);
    document.body.classList.add("has-atlas-global-nav");
  }

  const setExpandedLayout = () => {
    nav.classList.add("is-expanded");
    document.body.classList.add("has-atlas-context-nav");
    app?.classList.add("has-atlas-context-nav");
  };

  if (isCoach) {
    setExpandedLayout();
    const panels = [...document.querySelectorAll("[data-coach-section]")];
    const buttons = [...nav.querySelectorAll("[data-coach-nav]")];

    const showCoachSection = requested => {
      const selected = panels.some(panel => panel.dataset.coachSection === requested)
        ? requested
        : "overview";

      panels.forEach(panel => {
        const active = panel.dataset.coachSection === selected;
        panel.hidden = !active;
        panel.classList.toggle("is-coach-active", active);
      });

      buttons.forEach(button => {
        const active = button.dataset.coachNav === selected;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });

      document.body.dataset.coachSection = selected;
      localStorage.setItem("atlasCoachActiveSection", selected);
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    buttons.forEach(button => {
      button.addEventListener("click", () => showCoachSection(button.dataset.coachNav));
    });

    window.addEventListener("atlas:coach-section-request", event => {
      showCoachSection(event.detail?.section);
    });

    showCoachSection(localStorage.getItem("atlasCoachActiveSection") || "overview");
  }

  if (isHub) {
    setExpandedLayout();
    const contextButtons = [...nav.querySelectorAll("[data-health-nav]")];
    const primaryButtons = [...nav.querySelectorAll("[data-primary-health]")];

    const syncHealthNavigation = selected => {
      contextButtons.forEach(button => {
        const active = button.dataset.healthNav === selected;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      primaryButtons.forEach(button => {
        const active = button.dataset.primaryHealth === selected
          || (button.dataset.primaryHealth === "health" && selected !== "timeline");
        button.classList.toggle("active", active);
      });
    };

    nav.querySelectorAll("[data-tab]").forEach(button => {
      button.addEventListener("click", () => syncHealthNavigation(button.dataset.tab));
    });

    window.addEventListener("load", () => {
      const requested = location.hash.replace("#", "");
      const selected = ["balance", "health", "injuries", "timeline"].includes(requested)
        ? requested
        : "health";
      nav.querySelector(`[data-health-nav="${selected}"]`)?.click();
      syncHealthNavigation(selected);
    });
  }

  nav.querySelector("[data-atlas-talk]")?.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("atlas:conversation-open"));
  });

  if (!isCoach && !isHub) {
    nav.addEventListener("dblclick", () => nav.classList.toggle("is-expanded"));
  }
})();
