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
      ${primaryItem({ href: "./atlas-hub.html#health", tab: "health", icon: "♡", label: "Santé globale", active: isHub, extra: 'data-primary-health="health"' })}
      ${primaryItem({ href: "./atlas-hub.html#injuries", tab: "injuries", icon: "⌁", label: "Douleurs et blessures", extra: 'data-primary-health="injuries"' })}
      ${primaryItem({ href: "./atlas-hub.html#analysis", tab: "analysis", icon: "✦", label: "Analyse Atlas", extra: 'data-primary-health="analysis"' })}
      ${primaryItem({ href: "./atlas-hub.html#timeline", tab: "timeline", icon: "↝", label: "Chronologie", extra: 'data-primary-health="timeline"' })}
      ${healthModules}
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
    const primaryButtons = [...nav.querySelectorAll("[data-primary-health]")];

    const syncHealthNavigation = selected => {
      primaryButtons.forEach(button => {
        const active = button.dataset.primaryHealth === selected;
        button.classList.toggle("active", active);
      });
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
      nav.querySelector(`[data-primary-health="${selected}"]`)?.click();
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
