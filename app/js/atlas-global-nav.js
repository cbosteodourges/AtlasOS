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
    <div class="atlas-context-subnav" data-context-title="ESPACE ENTRAÎNEMENT" aria-label="Sous-menu Entraînement">
      <button type="button" data-coach-nav="overview"><span class="atlas-context-icon">⌂</span><span>Vue d’ensemble</span></button>
      <button type="button" data-coach-nav="sensors"><span class="atlas-context-icon">⌁</span><span>Montres et capteurs</span></button>
      <button type="button" data-coach-nav="profile"><span class="atlas-context-icon">◇</span><span>Profil et objectif</span></button>
      <button type="button" data-coach-nav="deadline"><span class="atlas-context-icon">◎</span><span>Prochaine échéance</span></button>
      <button type="button" data-coach-nav="plan"><span class="atlas-context-icon">▦</span><span>Plan personnalisé</span></button>
      <button type="button" data-coach-nav="history"><span class="atlas-context-icon">↝</span><span>Historique des séances</span></button>
    </div>` : "";

  const healthModules = isHub ? `
    <div class="atlas-health-modules">
      <button class="atlas-health-modules-toggle" type="button"
        data-health-modules-toggle aria-expanded="false">
        <span class="atlas-nav-icon">＋</span>
        <span>Modules spécialisés</span>
        <i aria-hidden="true">⌄</i>
      </button>
      <div class="atlas-health-modules-list" data-health-modules-list hidden>
        <a href="./physiologie.html"><span>∿</span><span>Physiologie</span></a>
        <a href="./biomecanique.html"><span>◇</span><span>Atlas Physio</span></a>
        <a href="./prevention.html"><span>△</span><span>Prévention</span></a>
        <a href="./memoire.html"><span>▣</span><span>Mémoire Atlas</span></a>
      </div>
    </div>` : "";

  const healthSubnav = isHub ? `
    <div class="atlas-context-subnav atlas-health-subnav"
      data-context-title="ESPACE SANTÉ" aria-label="Sous-menu Santé">
      <button type="button" data-tab="health" data-health-nav="health">
        <span class="atlas-context-icon">♡</span><span>Santé globale</span>
      </button>
      <button type="button" data-tab="injuries" data-health-nav="injuries">
        <span class="atlas-context-icon">⌁</span><span>Douleurs et blessures</span>
      </button>
      <a href="./atlas-cockpit.html#athlete-analysis" data-health-nav="analysis">
        <span class="atlas-context-icon">✦</span><span>Analyse Atlas</span>
      </a>
      <button type="button" data-tab="timeline" data-health-nav="timeline">
        <span class="atlas-context-icon">↝</span><span>Chronologie</span>
      </button>
      ${healthModules}
    </div>` : "";

  const nav = document.createElement("aside");
  nav.className = "atlas-global-nav";
  nav.setAttribute("aria-label", "Navigation Atlas");
  nav.innerHTML = `
    <a class="atlas-brand atlas-nav-brand" href="./atlas-cockpit.html" aria-label="Retour à Aujourd’hui">
      <img src="./assets/atlas-logo-full.jpg" alt="">
      <span><strong>ATLAS OS</strong><small>Jumeau numérique humain</small></span>
    </a>

    <nav class="atlas-primary-nav">
      ${primaryItem({ href: "./atlas-cockpit.html", icon: "⌂", label: "Aujourd’hui", active: page === "atlas-cockpit.html" })}
      ${primaryItem({ href: "./performance-running.html", icon: "◎", label: "Entraînement", active: isCoach })}
      ${coachSubnav}
      ${primaryItem({ href: "./atlas-hub.html#health", tab: "health", icon: "♡", label: "Santé", active: isHub, extra: 'data-health-root="true"' })}
      ${healthSubnav}
    </nav>

    <button class="atlas-talk-button" type="button" data-atlas-talk>
      <span class="atlas-talk-orb">✦</span>
      <span class="atlas-talk-copy"><strong>Adapter ma séance</strong><small>Ressenti et choix guidé</small></span>
    </button>

    <div class="atlas-profile atlas-nav-user">
      <span class="atlas-profile-avatar atlas-nav-avatar">CB</span>
      <span class="atlas-profile-copy"><strong>Christophe</strong><small>Jumeau synchronisé</small></span>
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
    const healthRoot = nav.querySelector("[data-health-root]");

    const syncHealthNavigation = selected => {
      contextButtons.forEach(button => {
        const active = button.dataset.healthNav === selected;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      healthRoot?.classList.add("active");
      healthRoot?.setAttribute("aria-expanded", "true");
    };

    nav.querySelectorAll("[data-tab]").forEach(button => {
      button.addEventListener("click", () => syncHealthNavigation(button.dataset.tab));
    });

    const moduleToggle = nav.querySelector("[data-health-modules-toggle]");
    const moduleList = nav.querySelector("[data-health-modules-list]");
    moduleToggle?.addEventListener("click", () => {
      const expanded = moduleToggle.getAttribute("aria-expanded") === "true";
      moduleToggle.setAttribute("aria-expanded", String(!expanded));
      moduleList.hidden = expanded;
    });

    window.addEventListener("load", () => {
      const requested = location.hash.replace("#", "");
      const selected = ["health", "injuries", "analysis", "timeline"].includes(requested)
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
