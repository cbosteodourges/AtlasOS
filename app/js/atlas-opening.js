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
  const hubAvatarLabel = document.getElementById("hubTwinLabel");
  const hubTwinImage = document.getElementById("hubTwinImage");
  const hubProfileName = document.getElementById("hubProfileName");
  const hubProfileInitials = document.getElementById("hubProfileInitials");
  const brainGreeting = document.getElementById("brainGreeting");
  const brainMainText = document.getElementById("brainMainText");
  const moduleToast = document.getElementById("moduleToast");
  let selectedAvatar = null;

  function showPage(name) {
    pages.forEach(page => page.classList.toggle("is-active", page.dataset.page === name));
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  enterButton.addEventListener("click", () => showPage("avatar"));

  if (window.location.hash === "#hub") {
    selectedAvatar = localStorage.getItem("atlasPreselectedAvatar") || "male";
    const isFemale = selectedAvatar === "female";

    hubAvatarLabel.textContent = isFemale
      ? "Avatar Femme actif"
      : "Avatar Homme actif";

    if (hubTwinImage) {
      hubTwinImage.src = isFemale
        ? "./assets/avatar-female-hub.jpg"
        : "./assets/avatar-male-hub.jpg";
    }

    showPage("hub");
  }

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

    const isFemale = selectedAvatar === "female";

    hubAvatarLabel.textContent = isFemale
      ? "Avatar Femme actif"
      : "Avatar Homme actif";

    if (hubTwinImage) {
      hubTwinImage.src = isFemale
        ? "./assets/avatar-female-hub.jpg"
        : "./assets/avatar-male-hub.jpg";
    }

    showPage("hub");
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
  // 🟪 PARTIE E — E06 — INTERACTIONS HUB 4.0
  // ████████████████████████████████████████████████████████████

  const enginePanel = document.getElementById("enginePanel");
  const enginePanelClose = document.getElementById("enginePanelClose");
  const enginePanelTitle = document.getElementById("enginePanelTitle");
  const enginePanelText = document.getElementById("enginePanelText");
  const enginePanelAction = document.getElementById("enginePanelAction");

  const engineContent = {
    "Atlas IA": {
      text: "Atlas IA relie les données physiologiques, cliniques, biomécaniques et sportives afin d’expliquer chaque recommandation."
    },
    "Clinique": {
      text: "Le moteur Clinique organise les symptômes, antécédents, traitements, examens et hypothèses dans une chronologie cohérente."
    },
    "Performance": {
      text: "Le moteur Performance génère des plans datés et adaptatifs selon l’objectif, la VMA, la fréquence cardiaque, SV1, SV2 et la récupération.",
      href: "./performance-running.html"
    },
    "Biomécanique": {
      text: "Le moteur Biomécanique regroupe le Corps 3D, la mobilité, les articulations, les muscles, les tendons et les chaînes de mouvement."
    },
    "Prévention": {
      text: "Le moteur Prévention surveille les hausses de volume, la fatigue, la charge tendineuse et les facteurs de risque de blessure."
    },
    "Physiologie": {
      text: "Le moteur Physiologie analyse la fréquence cardiaque, la VFC, la VO₂max, la VMA, SV1, SV2, le sommeil et la récupération."
    },
    "Mémoire": {
      text: "La Mémoire du Jumeau conserve la chronologie, les documents, l’imagerie, les blessures, les traitements et les performances."
    }
  };

  function openEngine(engine, trigger) {
    document.querySelectorAll("[data-engine]").forEach(item => {
      item.classList.toggle("active", item === trigger);
    });

    const content = engineContent[engine] || {
      text: "Ce module sera progressivement relié au Digital Twin."
    };

    if (enginePanelTitle) enginePanelTitle.textContent = engine;
    if (enginePanelText) enginePanelText.textContent = content.text;
    if (enginePanelAction) {
      enginePanelAction.textContent = content.href
        ? "Ouvrir le module →"
        : "Bientôt disponible";
      enginePanelAction.disabled = !content.href;
      enginePanelAction.dataset.href = content.href || "";
    }

    if (enginePanel) enginePanel.hidden = false;
    if (brainMainText) brainMainText.textContent = content.text;
  }

  document.querySelectorAll("[data-engine]").forEach(button => {
    button.addEventListener("click", () => {
      openEngine(button.dataset.engine, button);
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

  function initHubParticles4() {
    const canvas = document.getElementById("hubParticles");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];

    function resize() {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      particles = Array.from({length:90}, () => ({
        x:Math.random()*canvas.width,
        y:Math.random()*canvas.height,
        r:Math.random()*1.3+.2,
        s:Math.random()*.14+.03,
        a:Math.random()*.28+.05
      }));
    }

    function animate() {
      ctx.clearRect(0,0,canvas.width,canvas.height);

      particles.forEach(p => {
        p.y -= p.s;
        if (p.y < -2) {
          p.y = canvas.height + 2;
          p.x = Math.random()*canvas.width;
        }

        ctx.beginPath();
        ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
        ctx.fillStyle = `rgba(53,204,255,${p.a})`;
        ctx.fill();
      });

      requestAnimationFrame(animate);
    }

    resize();
    animate();
    window.addEventListener("resize", resize);
  }

  initHubParticles4();

})();
