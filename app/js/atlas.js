"use strict";

(() => {
  const state = {
    avatar: null,
    profile: null
  };

  const scenes = [...document.querySelectorAll(".scene")];

  const avatarNext = document.getElementById("avatarNext");
  const avatarMessage = document.getElementById("avatarMessage");
  const profileAvatar = document.getElementById("profileAvatar");
  const profileForm = document.getElementById("profileForm");
  const creationAvatar = document.getElementById("creationAvatar");
  const readyAvatar = document.getElementById("readyAvatar");
  const dashboardAvatar = document.getElementById("dashboardAvatar");
  const progressBar = document.getElementById("progressBar");
  const progressValue = document.getElementById("progressValue");
  const currentStep = document.getElementById("currentStep");
  const readyNext = document.getElementById("readyNext");
  const accessPercent = document.getElementById("accessPercent");
  const dashboardWelcome = document.getElementById("dashboardWelcome");

  function showScene(name) {
    scenes.forEach(scene => {
      scene.classList.toggle("active", scene.dataset.scene === name);
    });
  }

  function avatarSource() {
    return state.avatar === "female"
      ? "./assets/avatar-female.jpg"
      : "./assets/avatar-male.jpg";
  }

  function avatarImage(alt) {
    return `<img src="${avatarSource()}" alt="${alt}">`;
  }

  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function initParticles(id, color = "55,207,255") {
    const canvas = document.getElementById(id);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];

    function resize() {
      canvas.width = innerWidth;
      canvas.height = innerHeight;
      particles = Array.from({length: Math.max(55, Math.floor(innerWidth / 20))}, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.5 + .25,
        s: Math.random() * .22 + .04,
        a: Math.random() * .5 + .08
      }));
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.y -= p.s;
        if (p.y < -4) {
          p.y = canvas.height + 4;
          p.x = Math.random() * canvas.width;
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${color},${p.a})`;
        ctx.fill();
      });
      requestAnimationFrame(draw);
    }

    resize();
    draw();
    addEventListener("resize", resize);
  }

  document.querySelectorAll("[data-avatar]").forEach(card => {
    card.addEventListener("click", () => {
      state.avatar = card.dataset.avatar;

      document.querySelectorAll("[data-avatar]").forEach(item => {
        item.classList.toggle("selected", item === card);
        item.setAttribute("aria-pressed", String(item === card));
      });

      avatarNext.disabled = false;
      avatarMessage.textContent =
        state.avatar === "female"
          ? "Avatar Femme sélectionné."
          : "Avatar Homme sélectionné.";
    });
  });

  avatarNext.addEventListener("click", () => {
    if (!state.avatar) return;
    profileAvatar.innerHTML = avatarImage("Avatar sélectionné");
    showScene("profile");
  });

  document.querySelectorAll("[data-back]").forEach(button => {
    button.addEventListener("click", () => showScene(button.dataset.back));
  });

  profileForm.addEventListener("submit", async event => {
    event.preventDefault();

    state.profile = Object.fromEntries(new FormData(profileForm).entries());
    localStorage.setItem("atlasProfile", JSON.stringify({
      avatar: state.avatar,
      profile: state.profile
    }));

    creationAvatar.innerHTML = avatarImage("Digital Twin en création");
    showScene("creation");

    const steps = [
      ["Analyse morphologique terminée", 18],
      ["Cartographie corporelle terminée", 38],
      ["Paramètres biomécaniques calculés", 58],
      ["Synchronisation biométrique terminée", 78],
      ["Initialisation d’Atlas OS...", 92],
      ["Digital Twin prêt", 100]
    ];

    for (const [label, progress] of steps) {
      currentStep.textContent = label;
      progressBar.style.width = `${progress}%`;
      progressValue.textContent = `${progress}%`;
      await wait(950);
    }

    readyAvatar.innerHTML = avatarImage("Digital Twin prêt");
    showScene("ready");
  });

  readyNext.addEventListener("click", async () => {
    showScene("access");

    for (let value = 0; value <= 100; value += 4) {
      accessPercent.textContent = `${value}%`;
      await wait(45);
    }

    await wait(500);

    dashboardAvatar.innerHTML = avatarImage("Digital Twin Atlas");
    dashboardWelcome.textContent =
      `Bonjour, ${state.profile?.firstName || "Christophe"}`;

    showScene("dashboard");
  });

  initParticles("creationParticles");
  initParticles("readyParticles");
  initParticles("accessParticles");
  initParticles("dashboardParticles");

  console.info("Atlas OS Genesis 1.2.0 chargé.");
})();