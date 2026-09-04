"use strict";

(() => {
  const page = location.pathname.split("/").pop() || "";
  const isHub = page === "atlas-hub.html";
  const isCoach = page === "performance-running.html";
  const isNutrition = page === "nutrition-hydration.html";

  const primaryItem = ({ href, tab, icon, label, active = false, extra = "" }) => {
    const className = `atlas-nav-item ${active ? "active" : ""}`;
    const content = `<span class="atlas-nav-icon">${icon}</span><span class="atlas-nav-label">${label}</span>`;
    return tab && isHub
      ? `<button class="${className}" type="button" data-tab="${tab}" ${extra}>${content}</button>`
      : `<a class="${className}" href="${href}" ${extra}>${content}</a>`;
  };

  const coachSubnav = isCoach ? `
    <div class="atlas-context-subnav" data-context-title="ESPACE ENTRAÎNEMENT" aria-label="Sous-menu Entraînement">
      <button type="button" data-coach-nav="sensors"><span class="atlas-context-icon">⌁</span><span>Montres et capteurs</span></button>
      <button type="button" data-coach-nav="profile"><span class="atlas-context-icon">◇</span><span>Profil et disponibilités</span></button>
      <button type="button" data-coach-nav="calibration"><span class="atlas-context-icon">◫</span><span>Calibration du profil</span></button>
      <button type="button" data-coach-nav="deadline"><span class="atlas-context-icon">◎</span><span>Objectifs et échéances</span></button>
      <button type="button" data-coach-nav="plan"><span class="atlas-context-icon">▦</span><span>Plan personnalisé</span></button>
      <button type="button" data-coach-nav="history"><span class="atlas-context-icon">↝</span><span>Historique des séances</span></button>
    </div>` : "";

  const healthSubnav = isHub ? `
    <div class="atlas-context-subnav atlas-health-subnav"
      data-context-title="ESPACE SANTÉ" aria-label="Sous-menu Santé">
      <button type="button" data-tab="injuries" data-health-nav="injuries">
        <span class="atlas-context-icon">⌁</span><span>Signaler une douleur</span>
      </button>
      <button type="button" data-tab="prevention" data-health-nav="prevention">
        <span class="atlas-context-icon">△</span><span>Prévention et charge</span>
      </button>
      <button type="button" data-tab="timeline" data-health-nav="timeline">
        <span class="atlas-context-icon">↝</span><span>L’histoire de votre corps</span>
      </button>
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
      ${primaryItem({ href: "./atlas-hub.html#injuries", tab: "injuries", icon: "♡", label: "Santé", active: isHub, extra: 'data-health-root="true"' })}
      ${healthSubnav}
      ${primaryItem({ href: "./nutrition-hydration.html", icon: "◒", label: "Nutrition", active: isNutrition, extra: 'data-nutrition-root' })}
    </nav>

    ${isCoach ? "" : `<button class="atlas-talk-button" type="button" data-atlas-talk>
      <span class="atlas-talk-orb">✦</span>
      <span class="atlas-talk-copy"><strong>Adapter ma séance</strong><small>Ressenti et choix guidé</small></span>
    </button>`}

    <div class="atlas-profile atlas-nav-user">
      <span class="atlas-profile-avatar atlas-nav-avatar">CB</span>
      <span class="atlas-profile-copy"><strong>Christophe</strong><small>Jumeau synchronisé</small></span>
    </div>
  `;

  fetch("/api/atlas/nutrition-hydration", { cache: "no-store" })
    .then(response => response.ok ? response.json() : null)
    .then(payload => {
      if (payload?.access?.enabled) {
        nav.querySelector("[data-nutrition-root]")?.removeAttribute("hidden");
      }
    })
    .catch(() => {});

  const app = document.querySelector(".app");
  if (isHub && app) {
    // atlas-hub.html conserve encore sa navigation historique dans le HTML.
    // La laisser à côté de la navigation globale crée une troisième colonne et
    // repousse le contenu Santé hors de l'écran. La navigation globale devient
    // l'unique navigation visible du Hub.
    app.querySelector(":scope > .sidebar")?.remove();
    app.prepend(nav);
    app.classList.add("has-atlas-global-nav");
  } else {
    document.body.prepend(nav);
    document.body.classList.add("has-atlas-global-nav");
  }

  const setExpandedLayout = () => {
    nav.classList.add("is-expanded");
    // Dans le Hub, la navigation appartient déjà à la grille `.app` : ajouter
    // aussi un retrait au body réserverait deux fois sa largeur et décalerait
    // toute la page Santé vers la droite. Le Coach conserve au contraire une
    // navigation fixe directement rattachée au body et a besoin de ce retrait.
    document.body.classList.toggle("has-atlas-context-nav", !isHub);
    app?.classList.add("has-atlas-context-nav");
  };

  if (isCoach) {
    setExpandedLayout();
    const panels = [...document.querySelectorAll("[data-coach-section]")];
    const buttons = [...nav.querySelectorAll("[data-coach-nav]")];
    let sectionChosenByUser = false;

    const showCoachSection = requested => {
      const selected = panels.some(panel => panel.dataset.coachSection === requested)
        ? requested
        : "plan";

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
      button.addEventListener("click", () => {
        sectionChosenByUser = true;
        showCoachSection(button.dataset.coachNav);
      });
    });

    window.addEventListener("atlas:coach-section-request", event => {
      showCoachSection(event.detail?.section);
    });

    const sensorSetupComplete =
      localStorage.getItem("atlasCoachSensorSetupComplete") === "true";
    const rememberedSection =
      localStorage.getItem("atlasCoachActiveSection");
    showCoachSection(
      sensorSetupComplete
        ? (rememberedSection || "plan")
        : "sensors"
    );

    const showPlanForConfiguredUser = () => {
      if (
        !sectionChosenByUser &&
        document.body.dataset.coachSection === "sensors"
      ) {
        showCoachSection("plan");
      }
    };

    window.addEventListener(
      "atlas:athlete-profile-loaded",
      showPlanForConfiguredUser
    );
    window.addEventListener(
      "atlas:training-program-loaded",
      showPlanForConfiguredUser
    );
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

    window.addEventListener("load", () => {
      const requested = location.hash.replace("#", "");
      const selected = ["injuries", "prevention", "timeline"].includes(requested)
        ? requested
        : "injuries";
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
