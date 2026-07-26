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
        ? "./assets/avatar-female.jpg"
        : "./assets/avatar-male.jpg";
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
        ? "./assets/avatar-female.jpg"
        : "./assets/avatar-male.jpg";
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
  // 🟪 PARTIE E — E05 — INTERACTIONS HUB 3.0
  // ████████████████████████████████████████████████████████████

  const engineMessages = {
    "Atlas IA": "Je relie vos données et j’explique chaque décision.",
    "Clinique": "J’analyse votre histoire, vos symptômes et vos antécédents.",
    "Performance": "Je construis et adapte vos plans d’entraînement.",
    "Biomécanique": "J’explore muscles, articulations, tendons et chaînes de mouvement.",
    "Prévention": "Je surveille les hausses de volume, la récupération et le risque de blessure.",
    "Physiologie": "J’analyse fréquence cardiaque, VFC, VO₂max, SV1 et SV2.",
    "Mémoire": "Je conserve votre chronologie, vos examens et votre évolution."
  };

  document.querySelectorAll("[data-engine]").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-engine]").forEach(item => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      const engine = button.dataset.engine;

      if (brainMainText) {
        brainMainText.textContent = engineMessages[engine];
      }

      if (engine === "Performance") {
        window.setTimeout(() => {
          window.location.href = "./performance-running.html";
        }, 260);
      }
    });
  });

  function initHubParticles() {
    const canvas = document.getElementById("hubParticles");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let points = [];

    function resize() {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      points = Array.from({ length: 80 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.4 + .2,
        s: Math.random() * .16 + .03,
        a: Math.random() * .35 + .06
      }));
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      points.forEach(point => {
        point.y -= point.s;
        if (point.y < -3) {
          point.y = canvas.height + 3;
          point.x = Math.random() * canvas.width;
        }

        ctx.beginPath();
        ctx.arc(point.x, point.y, point.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(53,204,255,${point.a})`;
        ctx.fill();
      });

      requestAnimationFrame(draw);
    }

    resize();
    draw();
    window.addEventListener("resize", resize);
  }

  initHubParticles();


})();
