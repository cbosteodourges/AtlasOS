"use strict";

(() => {
  // ████████████████████████████████████████████████████████████
  // 🟦 PARTIE A — A01 — ÉTAT ET NAVIGATION
  // ████████████████████████████████████████████████████████████
  const pages = [...document.querySelectorAll("[data-page]")];
  const enterButton = document.getElementById("atlasEnterButton");
  const avatarStage = document.getElementById("avatarStage");
  const avatarStatus = document.getElementById("avatarStatus");
  const hubBackButton = document.getElementById("hubBackButton");
  const hubProfileName = document.getElementById("hubProfileName");
  const hubProfileInitials = document.getElementById("hubProfileInitials");
  const brainGreeting = document.getElementById("brainGreeting");
  const brainMainText = document.getElementById("brainMainText");
  const moduleToast = document.getElementById("moduleToast");
  const hubFinalImage = document.getElementById("hubFinalImage");
  const hubPersistentAvatar = document.getElementById("hubPersistentAvatar");
  let selectedAvatar = null;

  function syncHubAvatar() {
    if (!hubPersistentAvatar) return;

    const isFemale = selectedAvatar === "female";
    hubPersistentAvatar.src = isFemale
      ? "./assets/atlas-avatar-femme-clean-final.png?v=2"
      : "./assets/atlas-avatar-homme-clean-final.png?v=2";

    hubPersistentAvatar.dataset.avatar = isFemale
      ? "female"
      : "male";
  }

  function showPage(name) {
    pages.forEach(page => page.classList.toggle("is-active", page.dataset.page === name));
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  enterButton.addEventListener("click", () => showPage("avatar"));

  if (window.location.hash === "#hub") {
    selectedAvatar = localStorage.getItem("atlasPreselectedAvatar") || "male";
  syncHubAvatar();

    window.location.href = "./atlas-cockpit.html";
  }

  // ████████████████████████████████████████████████████████████
  // 🟩 PARTIE B — B01 — SÉLECTION HOMME / FEMME
  // ████████████████████████████████████████████████████████████
  document.querySelectorAll("[data-avatar]").forEach(button => {
    button.addEventListener("click", () => {
      selectedAvatar = button.dataset.avatar;
      avatarStage.dataset.selected = selectedAvatar;
      avatarStatus.classList.add("is-ready");
      avatarStatus.textContent = selectedAvatar === "female"
        ? "Ouverture du profil Femme…"
        : "Ouverture du profil Homme…";

      localStorage.setItem(
        "atlasPreselectedAvatar",
        selectedAvatar
      );
      syncHubAvatar();
      window.location.href = "./atlas-cockpit.html";
    });
  });

  // ████████████████████████████████████████████████████████████
  // 🟪 PARTIE E — E01 — INTERACTIONS DU HUB
  // ████████████████████████████████████████████████████████████
  hubBackButton.addEventListener("click", () => showPage("avatar"));

  const savedProfile = JSON.parse(localStorage.getItem("atlasProfile") || "null");
  const savedName = savedProfile?.profile?.firstName || "Christophe";

  if (hubProfileName) hubProfileName.textContent = savedName;
  if (brainGreeting) brainGreeting.textContent = `Bonjour ${savedName}.`;
  if (hubProfileInitials) {
    hubProfileInitials.textContent = savedName
      .split(/\s+/)
      .filter(Boolean)
      .map(part => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "AT";
  }

  // ████████████████████████████████████████████████████████████
  // 🟪 PARTIE E — E08 — INTERACTIONS HUB FINAL
  // ████████████████████████████████████████████████████████████

  const enginePanel = document.getElementById("enginePanel");
  const enginePanelClose = document.getElementById("enginePanelClose");
  const enginePanelTitle = document.getElementById("enginePanelTitle");
  const enginePanelText = document.getElementById("enginePanelText");
  const enginePanelAction = document.getElementById("enginePanelAction");

  const hubEngineContent = {
    "Atlas IA": {
      text: "Atlas IA relie vos données et explique ses décisions.",
      href: "./atlas-ai.html"
    },
    "Clinique": {
      text: "Le moteur Clinique organise les symptômes, antécédents, traitements et examens.",
      href: "./clinique.html"
    },
    "Atlas Coach": {
      text: "Atlas Coach analyse votre profil, construit vos entraînements, prépare vos compétitions et suit votre performance.",
      href: "./performance-running.html"
    },
    "Biomécanique": {
      text: "Le moteur Biomécanique explore le Corps 3D, la mobilité, les muscles et les articulations.",
      href: "./biomecanique.html"
    },
    "Prévention": {
      text: "Le moteur Prévention surveille le volume, la récupération et le risque de blessure.",
      href: "./prevention.html"
    },
    "Physiologie": {
      text: "Le moteur Physiologie analyse FC, VFC, VO₂max, VMA, SV1 et SV2.",
      href: "./physiologie.html"
    },
    "Mémoire": {
      text: "La Mémoire du Jumeau conserve la chronologie, les documents et l’évolution.",
      href: "./memoire.html"
    }
  };

  document.querySelectorAll(".hub-final-hotspot[data-engine]").forEach(button => {
    button.addEventListener("click", () => {
      const engine = button.dataset.engine;
      const content = hubEngineContent[engine];

      document.querySelectorAll(".hub-final-hotspot").forEach(item => {
        item.classList.remove("is-active");
      });
      button.classList.add("is-active");

      if (enginePanelTitle) enginePanelTitle.textContent = engine;
      if (enginePanelText) enginePanelText.textContent = content.text;

      if (enginePanelAction) {
        enginePanelAction.dataset.href = content.href || "";
        enginePanelAction.disabled = !content.href;
        enginePanelAction.textContent = content.href
          ? "Ouvrir le module →"
          : "Bientôt disponible";
      }

      if (enginePanel) enginePanel.hidden = false;
    });
  });

  if (enginePanelClose) {
    enginePanelClose.addEventListener("click", () => {
      enginePanel.hidden = true;
    });
  }

  if (enginePanel) {
    enginePanel.addEventListener("click", event => {
      if (event.target === enginePanel) enginePanel.hidden = true;
    });
  }

  if (enginePanelAction) {
    enginePanelAction.addEventListener("click", () => {
      const href = enginePanelAction.dataset.href;
      if (href) window.location.href = href;
    });
  }

})();
