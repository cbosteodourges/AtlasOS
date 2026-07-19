"use strict";

(() => {
  const CONFIG = {
    splashDuration: 2400,
    creationDuration: 5200,
    storageKeys: {
      gender: "atlasOS.gender",
      connectedDevices: "atlasOS.connectedDevices",
      story: "atlasOS.story",
      onboardingComplete: "atlasOS.onboardingComplete"
    }
  };

  const state = {
    selectedGender: null,
    connectedDevices: [],
    currentScreen: null,
    creationInterval: null,
    toastTimeout: null,
    atlasIsReplying: false
  };

  const $ = (id) => document.getElementById(id);
  const elements = {
    body: document.body,
    splashScreen: $("splashScreen"),
    genderSelection: $("genderSelection"),
    intro: $("intro"),
    sync: $("sync"),
    assistant: $("assistant"),
    twinCreation: $("twinCreation"),
    dashboard: $("dashboard"),
    aiScreen: $("aiScreen"),
    historyScreen: $("historyScreen"),
    profileScreen: $("profileScreen"),
    genderCards: [...document.querySelectorAll(".gender-card")],
    confirmGenderButton: $("confirmGenderButton"),
    skipGenderButton: $("skipGenderButton"),
    enterButton: $("enterButton"),
    deviceButtons: [...document.querySelectorAll(".device-connect-button")],
    deviceSelectionStatus: $("deviceSelectionStatus"),
    continueButton: $("continueButton"),
    atlasStoryForm: $("atlasStoryForm"),
    story: $("story"),
    storyCounter: $("storyCounter"),
    assistantMessage: $("assistantMessage"),
    creationStatus: $("creationStatus"),
    creationProgress: document.querySelector(".creation-progress"),
    creationProgressBar: $("creationProgressBar"),
    creationProgressText: $("creationProgressText"),
    bottomNav: $("bottomNav"),
    navButtons: [...document.querySelectorAll(".nav-button")],
    profileButton: $("profileButton"),
    resetBodyViewButton: $("resetBodyViewButton"),
    bodyControls: [...document.querySelectorAll(".body-control")],
    chatForm: $("chatForm"),
    chatInput: $("chatInput"),
    chatMessages: $("chatMessages"),
    selectedTwinLabel: $("selectedTwinLabel"),
    connectedDevicesLabel: $("connectedDevicesLabel"),
    changeGenderButton: $("changeGenderButton"),
    manageDevicesButton: $("manageDevicesButton"),
    resetApplicationButton: $("resetApplicationButton"),
    atlasToast: $("atlasToast"),
    atlasToastIcon: $("atlasToastIcon"),
    atlasToastMessage: $("atlasToastMessage"),
    atlasModal: $("atlasModal"),
    atlasModalTitle: $("atlasModalTitle"),
    atlasModalBody: $("atlasModalBody"),
    closeModalButton: $("closeModalButton"),
    modalBackdrop: document.querySelector("[data-close-modal]")
  };

  const screens = [
    elements.genderSelection,
    elements.intro,
    elements.sync,
    elements.assistant,
    elements.twinCreation,
    elements.dashboard,
    elements.aiScreen,
    elements.historyScreen,
    elements.profileScreen
  ].filter(Boolean);

  const storage = {
    get(key, fallback = null) {
      try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : JSON.parse(value);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
    },
    clearAtlasData() {
      Object.values(CONFIG.storageKeys).forEach((key) => localStorage.removeItem(key));
    }
  };

  function initializeApplication() {
    restoreSavedState();
    bindEvents();
    updateStoryCounter();
    updateProfileInformation();
    startSplashSequence();
  }

  function restoreSavedState() {
    const gender = storage.get(CONFIG.storageKeys.gender, null);
    const devices = storage.get(CONFIG.storageKeys.connectedDevices, []);
    const story = storage.get(CONFIG.storageKeys.story, "");

    if (gender === "male" || gender === "female") {
      state.selectedGender = gender;
      applyGenderTheme(gender);
      updateGenderSelection(gender);
    }
    if (Array.isArray(devices)) state.connectedDevices = devices;
    if (elements.story && typeof story === "string") elements.story.value = story;
    updateDeviceButtons();
  }

  function startSplashSequence() {
    window.setTimeout(() => {
      if (!elements.splashScreen) {
        openInitialScreen();
        return;
      }
      elements.splashScreen.classList.add("is-leaving");
      window.setTimeout(() => {
        elements.splashScreen.classList.add("hidden");
        elements.splashScreen.setAttribute("aria-hidden", "true");
        openInitialScreen();
      }, 850);
    }, CONFIG.splashDuration);
  }

  /* Toujours revenir au choix Homme/Femme au lancement. */
  function openInitialScreen() {
    showScreen("genderSelection", { animation: "fade-scale", instant: true });
    if (state.selectedGender) {
      updateGenderSelection(state.selectedGender);
      showToast("Votre choix précédent est présélectionné. Vous pouvez le modifier.", "info");
    }
  }

  function showScreen(screenId, options = {}) {
    const target = $(screenId);
    if (!target) return;

    screens.forEach((screen) => {
      screen.classList.add("hidden");
      screen.classList.remove("fade-in", "fade-up", "fade-scale");
      screen.setAttribute("aria-hidden", "true");
    });

    target.classList.remove("hidden");
    target.setAttribute("aria-hidden", "false");
    void target.offsetWidth;
    target.classList.add(options.animation || "fade-in");
    state.currentScreen = screenId;

    const appScreens = ["dashboard", "aiScreen", "historyScreen", "profileScreen"];
    elements.bottomNav?.classList.toggle("hidden", !appScreens.includes(screenId));
    updateNavigationState(screenId);
    window.scrollTo({ top: 0, behavior: options.instant ? "auto" : "smooth" });

    if (screenId === "intro") window.setTimeout(initializeIntroBody3D, 80);
    if (screenId === "dashboard") window.setTimeout(initializeBody3D, 80);
  }

  function selectGender(gender) {
    if (!['male', 'female'].includes(gender)) return;
    state.selectedGender = gender;
    applyGenderTheme(gender);
    updateGenderSelection(gender);
    if (elements.confirmGenderButton) elements.confirmGenderButton.disabled = false;
  }

  function applyGenderTheme(gender) {
    elements.body.dataset.atlasTheme = gender;
    storage.set(CONFIG.storageKeys.gender, gender);
    window.AtlasBody3D?.setTheme?.(gender);
    window.AtlasParticles?.setTheme?.(gender);
  }

  function updateGenderSelection(gender) {
    elements.genderCards.forEach((card) => {
      const selected = card.dataset.gender === gender;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-checked", String(selected));
    });
    if (elements.confirmGenderButton) elements.confirmGenderButton.disabled = !gender;
  }

  function confirmGenderSelection() {
    if (!state.selectedGender) {
      showToast("Sélectionnez Homme ou Femme avant de continuer.", "warning");
      return;
    }
    storage.set(CONFIG.storageKeys.gender, state.selectedGender);
    updateProfileInformation();
    showScreen("intro", { animation: "fade-scale" });
  }

  function skipGenderSelection() {
    selectGender(state.selectedGender || "male");
    confirmGenderSelection();
  }

  function handleDeviceButton(button) {
    const device = button.dataset.device;
    if (!device) return;
    const index = state.connectedDevices.indexOf(device);
    if (index >= 0) state.connectedDevices.splice(index, 1);
    else state.connectedDevices.push(device);
    storage.set(CONFIG.storageKeys.connectedDevices, state.connectedDevices);
    updateDeviceButtons();
    updateProfileInformation();
    showToast(index >= 0 ? `${device} déconnecté.` : `${device} connecté.`, index >= 0 ? "info" : "success");
  }

  function updateDeviceButtons() {
    elements.deviceButtons.forEach((button) => {
      const device = button.dataset.device;
      const connected = state.connectedDevices.includes(device);
      button.classList.toggle("connected", connected);
      button.textContent = connected ? "Connecté" : (device === "Saisie manuelle" ? "Utiliser" : "Connecter");
      button.setAttribute("aria-pressed", String(connected));
    });
    if (elements.deviceSelectionStatus) {
      const count = state.connectedDevices.length;
      elements.deviceSelectionStatus.textContent = count === 0
        ? "La connexion des appareils est facultative pour cette démonstration."
        : `${count} source${count > 1 ? "s" : ""} de données active${count > 1 ? "s" : ""}.`;
    }
  }

  function updateStoryCounter() {
    if (!elements.story || !elements.storyCounter) return;
    elements.storyCounter.textContent = `${elements.story.value.length} / 3000`;
  }

  function handleStorySubmission(event) {
    event.preventDefault();
    const story = elements.story?.value.trim() || "";
    if (story.length < 10) {
      if (elements.assistantMessage) elements.assistantMessage.textContent = "Décrivez votre situation en au moins 10 caractères.";
      return;
    }
    storage.set(CONFIG.storageKeys.story, story);
    if (elements.assistantMessage) elements.assistantMessage.textContent = "";
    startTwinCreation();
  }

  function startTwinCreation() {
    showScreen("twinCreation", { animation: "fade-scale" });
    let progress = 0;
    const statuses = [
      [0, "Analyse de votre profil biomécanique…"],
      [25, "Lecture de votre histoire corporelle…"],
      [50, "Création de votre modèle Atlas…"],
      [75, "Synchronisation des données…"],
      [94, "Finalisation de votre jumeau…"]
    ];
    clearInterval(state.creationInterval);
    state.creationInterval = setInterval(() => {
      progress = Math.min(100, progress + 2);
      if (elements.creationProgressBar) elements.creationProgressBar.style.width = `${progress}%`;
      if (elements.creationProgressText) elements.creationProgressText.textContent = `${progress} %`;
      elements.creationProgress?.setAttribute("aria-valuenow", String(progress));
      const status = [...statuses].reverse().find(([threshold]) => progress >= threshold);
      if (status && elements.creationStatus) elements.creationStatus.textContent = status[1];
      if (progress >= 100) {
        clearInterval(state.creationInterval);
        storage.set(CONFIG.storageKeys.onboardingComplete, true);
        showScreen("dashboard", { animation: "fade-up" });
        showToast("Votre jumeau biomécanique est prêt.", "success");
      }
    }, CONFIG.creationDuration / 50);
  }

  function initializeIntroBody3D() {
    window.AtlasBody3D?.initializeIntro?.("viewer3D");
  }

  function initializeBody3D() {
    window.AtlasBody3D?.initializeDashboard?.("body3dContainer");
  }

  function updateNavigationState(screenId) {
    elements.navButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.screen === screenId && !button.dataset.focus);
    });
  }

  function handleNavigation(button) {
    const screen = button.dataset.screen;
    if (!screen) return;
    showScreen(screen, { animation: "fade-in" });
  }

  function appendChatMessage(message, sender) {
    if (!elements.chatMessages) return;
    const article = document.createElement("article");
    article.className = `chat-message chat-message--${sender}`;
    const avatar = document.createElement("div");
    avatar.className = "chat-avatar";
    avatar.textContent = sender === "atlas" ? "A" : "V";
    const paragraph = document.createElement("p");
    paragraph.textContent = message;
    article.append(avatar, paragraph);
    elements.chatMessages.appendChild(article);
    elements.chatMessages.scrollTo({ top: elements.chatMessages.scrollHeight, behavior: "smooth" });
  }

  function handleChatSubmission(event) {
    event.preventDefault();
    const message = elements.chatInput?.value.trim();
    if (!message || state.atlasIsReplying) return;
    appendChatMessage(message, "user");
    elements.chatInput.value = "";
    state.atlasIsReplying = true;
    setTimeout(() => {
      appendChatMessage("J’ai enregistré votre message. Cette démonstration prépare l’analyse biomécanique personnalisée d’Atlas.", "atlas");
      state.atlasIsReplying = false;
    }, 900);
  }

  function updateProfileInformation() {
    if (elements.selectedTwinLabel) {
      elements.selectedTwinLabel.textContent = state.selectedGender === "female" ? "Jumeau féminin" : "Jumeau masculin";
    }
    if (elements.connectedDevicesLabel) {
      const count = state.connectedDevices.length;
      elements.connectedDevicesLabel.textContent = count === 0 ? "Aucun appareil connecté" : `${count} source${count > 1 ? "s" : ""} active${count > 1 ? "s" : ""}`;
    }
  }

  function showToast(message, type = "info") {
    if (!elements.atlasToast || !elements.atlasToastMessage) return;
    const icons = { info: "info", success: "check_circle", warning: "warning", error: "error" };
    clearTimeout(state.toastTimeout);
    elements.atlasToastMessage.textContent = message;
    if (elements.atlasToastIcon) elements.atlasToastIcon.textContent = icons[type] || icons.info;
    elements.atlasToast.classList.add("visible");
    state.toastTimeout = setTimeout(() => elements.atlasToast.classList.remove("visible"), 3300);
  }

  function openModal(title, content) {
    if (!elements.atlasModal) return;
    if (elements.atlasModalTitle) elements.atlasModalTitle.textContent = title;
    if (elements.atlasModalBody) {
      elements.atlasModalBody.replaceChildren();
      if (content instanceof Node) elements.atlasModalBody.appendChild(content);
      else elements.atlasModalBody.textContent = String(content);
    }
    elements.atlasModal.classList.remove("hidden");
    elements.atlasModal.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    elements.atlasModal?.classList.add("hidden");
    elements.atlasModal?.setAttribute("aria-hidden", "true");
  }

  function resetApplication() {
    storage.clearAtlasData();
    window.location.reload();
  }

  function confirmReset() {
    const wrapper = document.createElement("div");
    const p = document.createElement("p");
    p.textContent = "Cette action effacera les choix enregistrés et relancera Atlas OS.";
    p.style.marginBottom = "20px";
    const button = document.createElement("button");
    button.className = "atlas-primary-button";
    button.textContent = "Réinitialiser Atlas";
    button.addEventListener("click", resetApplication);
    wrapper.append(p, button);
    openModal("Réinitialiser la démonstration", wrapper);
  }

  function bindEvents() {
    elements.genderCards.forEach((card) => card.addEventListener("click", () => selectGender(card.dataset.gender)));
    elements.confirmGenderButton?.addEventListener("click", confirmGenderSelection);
    elements.skipGenderButton?.addEventListener("click", skipGenderSelection);
    elements.enterButton?.addEventListener("click", () => showScreen("sync", { animation: "fade-up" }));
    elements.deviceButtons.forEach((button) => button.addEventListener("click", () => handleDeviceButton(button)));
    elements.continueButton?.addEventListener("click", () => showScreen("assistant", { animation: "fade-up" }));
    elements.story?.addEventListener("input", updateStoryCounter);
    elements.atlasStoryForm?.addEventListener("submit", handleStorySubmission);
    elements.navButtons.forEach((button) => button.addEventListener("click", () => handleNavigation(button)));
    elements.profileButton?.addEventListener("click", () => showScreen("profileScreen", { animation: "fade-up" }));
    elements.resetBodyViewButton?.addEventListener("click", () => window.AtlasBody3D?.resetView?.());
    elements.bodyControls.forEach((button) => button.addEventListener("click", () => {
      elements.bodyControls.forEach((control) => control.classList.toggle("active", control === button));
      window.AtlasBody3D?.setLayer?.(button.dataset.bodyLayer);
    }));
    elements.chatForm?.addEventListener("submit", handleChatSubmission);
    elements.changeGenderButton?.addEventListener("click", () => showScreen("genderSelection", { animation: "fade-up" }));
    elements.manageDevicesButton?.addEventListener("click", () => showScreen("sync", { animation: "fade-up" }));
    elements.resetApplicationButton?.addEventListener("click", confirmReset);
    elements.closeModalButton?.addEventListener("click", closeModal);
    elements.modalBackdrop?.addEventListener("click", closeModal);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });
    window.addEventListener("resize", () => window.AtlasBody3D?.resize?.());
  }

  window.AtlasOS = {
    showScreen,
    showToast,
    openModal,
    closeModal,
    getState: () => ({ ...state, connectedDevices: [...state.connectedDevices] })
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeApplication, { once: true });
  } else {
    initializeApplication();
  }
})();
