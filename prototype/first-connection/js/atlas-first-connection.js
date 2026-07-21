"use strict";

(() => {
  const DESIGN_WIDTH = 1536;
  const DESIGN_HEIGHT = 1024;

  const state = {
    selectedAvatar: null,
    profile: null,
    audioContext: null
  };

  const scenes = Array.from(document.querySelectorAll(".scene"));
  const enterButton = document.getElementById("enterButton");
  const openingSequence = document.getElementById("openingSequence");
  const heartbeat = document.getElementById("heartbeat");
  const atlasLogo = document.getElementById("atlasLogo");
  const atlasTitle = document.getElementById("atlasTitle");
  const avatarContinue = document.getElementById("avatarContinue");
  const profileForm = document.getElementById("profileForm");
  const creationAvatar = document.getElementById("creationAvatar");
  const creationMessage = document.getElementById("creationMessage");
  const creationProgress = document.getElementById("creationProgress");
  const hubCanvas = document.getElementById("hubCanvas");
  const hubWelcome = document.getElementById("hubWelcome");
  const hubWelcomeName = document.getElementById("hubWelcomeName");
  const dialog = document.getElementById("atlasDialog");
  const dialogTitle = document.getElementById("dialogTitle");
  const dialogText = document.getElementById("dialogText");
  const dialogAction = document.getElementById("dialogAction");

  function showScene(name) {
    scenes.forEach(scene => {
      scene.classList.toggle("active", scene.dataset.scene === name);
    });
  }

  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function getAudioContext() {
    if (!state.audioContext) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) state.audioContext = new Ctx();
    }
    return state.audioContext;
  }

  function playBoom(offset, gainValue = 0.55) {
    const ctx = getAudioContext();
    if (!ctx) return;

    const start = ctx.currentTime + offset;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const filter = ctx.createBiquadFilter();

    osc.type = "sine";
    osc.frequency.setValueAtTime(52, start);
    osc.frequency.exponentialRampToValueAtTime(30, start + 0.22);

    filter.type = "lowpass";
    filter.frequency.value = 130;

    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.018);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.34);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    osc.start(start);
    osc.stop(start + 0.36);
  }

  function playThreeDoubleBeats() {
    const pairs = [0, 1.35, 2.65];
    pairs.forEach(pair => {
      playBoom(pair, 0.62);
      playBoom(pair + 0.22, 0.48);
    });
  }

  function initializeParticles() {
    const canvas = document.getElementById("particleCanvas");
    const ctx = canvas.getContext("2d");
    let particles = [];

    function resize() {
      canvas.width = innerWidth;
      canvas.height = innerHeight;
      particles = Array.from({length: Math.max(55, Math.round(innerWidth / 20))}, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.4 + 0.3,
        s: Math.random() * 0.18 + 0.04,
        a: Math.random() * 0.55 + 0.12
      }));
    }

    function animate() {
      ctx.clearRect(0,0,canvas.width,canvas.height);
      for (const p of particles) {
        p.y -= p.s;
        if (p.y < -3) {
          p.y = canvas.height + 3;
          p.x = Math.random() * canvas.width;
        }
        ctx.beginPath();
        ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
        ctx.fillStyle = `rgba(96,222,255,${p.a})`;
        ctx.fill();
      }
      requestAnimationFrame(animate);
    }

    resize();
    animate();
    addEventListener("resize", resize);
  }

  async function startOpening() {
    enterButton.classList.add("hidden");
    openingSequence.classList.remove("hidden");

    await wait(650);
    heartbeat.classList.add("active");
    playThreeDoubleBeats();

    await wait(4200);
    heartbeat.classList.remove("active");
    atlasLogo.classList.add("visible");

    await wait(1200);
    atlasTitle.classList.add("visible");

    await wait(2200);
    showScene("avatar");
  }

  function avatarSvg(type) {
    const female = type === "female";
    const gradientA = female ? "#d7f9ff" : "#b4fbff";
    const gradientB = female ? "#9f7cff" : "#55c9ff";
    const gradientC = female ? "#5e4dff" : "#2876ff";
    const bodyPath = female
      ? "M98 94 C108 80 152 80 162 94 L178 178 L163 262 L177 318 L158 522 L133 522 L130 330 L127 522 L102 522 L83 318 L97 262 L82 178 Z"
      : "M90 94 C104 76 156 76 170 94 L190 196 L167 300 L161 522 L133 522 L130 324 L127 522 L99 522 L93 300 L70 196 Z";

    return `
      <svg viewBox="0 0 260 560">
        <defs><linearGradient id="chosenGradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${gradientA}"/>
          <stop offset="48%" stop-color="${gradientB}"/>
          <stop offset="100%" stop-color="${gradientC}"/>
        </linearGradient></defs>
        <g fill="url(#chosenGradient)" stroke="#f1ffff">
          <circle cx="130" cy="48" r="31"/>
          <path d="${bodyPath}"/>
          <path d="M86 112 L40 264 L55 274 L108 145 Z"/>
          <path d="M174 112 L220 264 L205 274 L152 145 Z"/>
        </g>
      </svg>`;
  }

  document.querySelectorAll("[data-avatar]").forEach(card => {
    card.addEventListener("click", () => {
      state.selectedAvatar = card.dataset.avatar;
      document.querySelectorAll("[data-avatar]").forEach(item => {
        item.classList.toggle("selected", item === card);
      });
      avatarContinue.disabled = false;
    });
  });

  avatarContinue.addEventListener("click", () => showScene("profile"));

  profileForm.addEventListener("submit", event => {
    event.preventDefault();
    state.profile = Object.fromEntries(new FormData(profileForm).entries());
    creationAvatar.innerHTML = avatarSvg(state.selectedAvatar);
    showScene("creation");
    runCreation();
  });

  async function runCreation() {
    const steps = [
      ["Initialisation de votre Digital Twin…", 18],
      ["Construction de la structure corporelle…", 38],
      ["Application du profil morphologique…", 58],
      ["Synchronisation des moteurs Atlas…", 78],
      ["Digital Twin prêt.", 100]
    ];

    for (const [message, progress] of steps) {
      creationMessage.textContent = message;
      creationProgress.style.width = `${progress}%`;
      await wait(1100);
    }

    hubWelcomeName.textContent = `Bonjour ${state.profile.firstName}.`;
    showScene("hub");
    updateHubScale();

    setTimeout(() => hubWelcome.classList.add("visible"), 400);
    setTimeout(() => hubWelcome.classList.remove("visible"), 3900);
  }

  function updateHubScale() {
    const scale = Math.min(innerWidth / DESIGN_WIDTH, innerHeight / DESIGN_HEIGHT);
    hubCanvas.style.setProperty("--hub-scale", String(scale));
  }

  function openDialog(title, text) {
    dialogTitle.textContent = title;
    dialogText.textContent = text;
    dialog.showModal();
  }

  document.querySelectorAll(".hotspot").forEach(hotspot => {
    hotspot.addEventListener("click", () => {
      openDialog(hotspot.dataset.title, hotspot.dataset.text);
    });
  });

  dialogAction.addEventListener("click", () => dialog.close());
  addEventListener("resize", updateHubScale);

  initializeParticles();
  enterButton.addEventListener("click", startOpening);

  console.info("Atlas First Connection Genesis 1.0.0 chargé.");
})();
