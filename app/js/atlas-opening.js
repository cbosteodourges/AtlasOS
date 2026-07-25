"use strict";

(() => {
  // ████████████████████████████████████████████████████████████
  // 🟦 PARTIE A — A01 — ÉTAT ET NAVIGATION
  // ████████████████████████████████████████████████████████████
  const pages = [...document.querySelectorAll("[data-page]")];
  const enterButton = document.getElementById("atlasEnterButton");
  const avatarStage = document.getElementById("avatarStage");
  const avatarStatus = document.getElementById("avatarStatus");
  const continueButton = document.getElementById("avatarContinue");
  const hubBackButton = document.getElementById("hubBackButton");
  const hubAvatarLabel = document.getElementById("hubAvatarLabel");
  const moduleToast = document.getElementById("moduleToast");
  let selectedAvatar = null;

  function showPage(name) {
    pages.forEach(page => page.classList.toggle("is-active", page.dataset.page === name));
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  enterButton.addEventListener("click", () => showPage("avatar"));

  // ████████████████████████████████████████████████████████████
  // 🟩 PARTIE B — B01 — SÉLECTION HOMME / FEMME
  // ████████████████████████████████████████████████████████████
  document.querySelectorAll("[data-avatar]").forEach(button => {
    button.addEventListener("click", () => {
      selectedAvatar = button.dataset.avatar;
      avatarStage.dataset.selected = selectedAvatar;
      continueButton.disabled = false;
      avatarStatus.classList.add("is-ready");
      avatarStatus.textContent = selectedAvatar === "female"
        ? "Avatar Femme sélectionné."
        : "Avatar Homme sélectionné.";
    });
  });

  continueButton.addEventListener("click", () => {
    if (!selectedAvatar) return;

    localStorage.setItem("atlasPreselectedAvatar", selectedAvatar);

    hubAvatarLabel.textContent = selectedAvatar === "female"
      ? "Digital Twin féminin actif"
      : "Digital Twin masculin actif";

    showPage("hub");
  });

  // ████████████████████████████████████████████████████████████
  // 🟪 PARTIE E — E01 — INTERACTIONS DU HUB
  // ████████████████████████████████████████████████████████████
  hubBackButton.addEventListener("click", () => showPage("avatar"));

  document.querySelectorAll("[data-hub-module]").forEach(button => {
    button.addEventListener("click", () => {
      const moduleName = button.dataset.hubModule;

      moduleToast.textContent =
        `${moduleName} — module préparé pour la prochaine étape du développement.`;

      moduleToast.classList.add("is-visible");

      window.clearTimeout(window.atlasToastTimer);

      window.atlasToastTimer = window.setTimeout(() => {
        moduleToast.classList.remove("is-visible");
      }, 2600);
    });
  });
})();
