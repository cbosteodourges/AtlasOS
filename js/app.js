/* ==========================================================
   ATLAS OS V6
   CONTRÔLEUR PRINCIPAL DE L’APPLICATION
   Fichier : js/app.js
========================================================== */

"use strict";

(() => {

    /* ======================================================
       1. CONFIGURATION
    ====================================================== */

    const CONFIG = {

        splashDuration: 2800,

        splashTransitionDuration: 900,

        creationDuration: 6200,

        minimumStoryLength: 10,

        maximumStoryLength: 3000,

        storageKeys: {

            gender: "atlasOS.gender",

            connectedDevices:
                "atlasOS.connectedDevices",

            story: "atlasOS.story",

            onboardingComplete:
                "atlasOS.onboardingComplete"

        }

    };


    /* ======================================================
       2. ÉTAT DE L’APPLICATION
    ====================================================== */

    const state = {

        selectedGender: null,

        connectedDevices: [],

        currentScreen: null,

        creationInterval: null,

        toastTimeout: null,

        atlasIsReplying: false,

        applicationInitialized: false

    };


    /* ======================================================
       3. ÉLÉMENTS DE L’INTERFACE
    ====================================================== */

    const elements = {

        body: document.body,

        splashScreen:
            document.getElementById(
                "splashScreen"
            ),

        genderSelection:
            document.getElementById(
                "genderSelection"
            ),

        intro:
            document.getElementById(
                "intro"
            ),

        sync:
            document.getElementById(
                "sync"
            ),

        assistant:
            document.getElementById(
                "assistant"
            ),

        twinCreation:
            document.getElementById(
                "twinCreation"
            ),

        dashboard:
            document.getElementById(
                "dashboard"
            ),

        aiScreen:
            document.getElementById(
                "aiScreen"
            ),

        historyScreen:
            document.getElementById(
                "historyScreen"
            ),

        profileScreen:
            document.getElementById(
                "profileScreen"
            ),

        genderCards: Array.from(
            document.querySelectorAll(
                ".gender-card"
            )
        ),

        confirmGenderButton:
            document.getElementById(
                "confirmGenderButton"
            ),

        skipGenderButton:
            document.getElementById(
                "skipGenderButton"
            ),

        enterButton:
            document.getElementById(
                "enterButton"
            ),

        selectedAtlasLogo:
            document.getElementById(
                "selectedAtlasLogo"
            ),

        selectedAtlasLogoContainer:
            document.getElementById(
                "selectedAtlasLogoContainer"
            ),

        deviceButtons: Array.from(
            document.querySelectorAll(
                ".device-connect-button"
            )
        ),

        deviceSelectionStatus:
            document.getElementById(
                "deviceSelectionStatus"
            ),

        continueButton:
            document.getElementById(
                "continueButton"
            ),

        atlasStoryForm:
            document.getElementById(
                "atlasStoryForm"
            ),

        story:
            document.getElementById(
                "story"
            ),

        storyCounter:
            document.getElementById(
                "storyCounter"
            ),

        assistantMessage:
            document.getElementById(
                "assistantMessage"
            ),

        creationStatus:
            document.getElementById(
                "creationStatus"
            ),

        creationProgress:
            document.querySelector(
                ".creation-progress"
            ),

        creationProgressBar:
            document.getElementById(
                "creationProgressBar"
            ),

        creationProgressText:
            document.getElementById(
                "creationProgressText"
            ),

        bottomNav:
            document.getElementById(
                "bottomNav"
            ),

        navButtons: Array.from(
            document.querySelectorAll(
                ".nav-button"
            )
        ),

        profileButton:
            document.getElementById(
                "profileButton"
            ),

        resetBodyViewButton:
            document.getElementById(
                "resetBodyViewButton"
            ),

        bodyControls: Array.from(
            document.querySelectorAll(
                ".body-control"
            )
        ),

        chatForm:
            document.getElementById(
                "chatForm"
            ),

        chatInput:
            document.getElementById(
                "chatInput"
            ),

        chatMessages:
            document.getElementById(
                "chatMessages"
            ),

        selectedTwinLabel:
            document.getElementById(
                "selectedTwinLabel"
            ),

        connectedDevicesLabel:
            document.getElementById(
                "connectedDevicesLabel"
            ),

        changeGenderButton:
            document.getElementById(
                "changeGenderButton"
            ),

        manageDevicesButton:
            document.getElementById(
                "manageDevicesButton"
            ),

        resetApplicationButton:
            document.getElementById(
                "resetApplicationButton"
            ),

        atlasToast:
            document.getElementById(
                "atlasToast"
            ),

        atlasToastIcon:
            document.getElementById(
                "atlasToastIcon"
            ),

        atlasToastMessage:
            document.getElementById(
                "atlasToastMessage"
            ),

        atlasModal:
            document.getElementById(
                "atlasModal"
            ),

        atlasModalTitle:
            document.getElementById(
                "atlasModalTitle"
            ),

        atlasModalBody:
            document.getElementById(
                "atlasModalBody"
            ),

        closeModalButton:
            document.getElementById(
                "closeModalButton"
            ),

        modalBackdrop:
            document.querySelector(
                "[data-close-modal]"
            )

    };


    /* ======================================================
       4. LISTE DES ÉCRANS
    ====================================================== */

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


    /* ======================================================
       5. STOCKAGE LOCAL SÉCURISÉ
    ====================================================== */

    const storage = {

        get(key, fallback = null) {

            try {

                const value =
                    window.localStorage
                        .getItem(key);

                if (value === null) {

                    return fallback;

                }

                return JSON.parse(value);

            } catch (error) {

                console.warn(
                    "Atlas OS : lecture du stockage impossible.",
                    error
                );

                return fallback;

            }

        },

        set(key, value) {

            try {

                window.localStorage
                    .setItem(
                        key,
                        JSON.stringify(value)
                    );

            } catch (error) {

                console.warn(
                    "Atlas OS : sauvegarde impossible.",
                    error
                );

            }

        },

        remove(key) {

            try {

                window.localStorage
                    .removeItem(key);

            } catch (error) {

                console.warn(
                    "Atlas OS : suppression impossible.",
                    error
                );

            }

        },

        clearAtlasData() {

            Object.values(
                CONFIG.storageKeys
            ).forEach((key) => {

                this.remove(key);

            });

        }

    };


    /* ======================================================
       6. INITIALISATION
    ====================================================== */

    function initializeApplication() {

        if (
            state.applicationInitialized
        ) {

            return;

        }

        state.applicationInitialized = true;

        restoreSavedState();

        bindEvents();

        updateStoryCounter();

        updateDeviceButtons();

        updateProfileInformation();

        updateSelectedIntroLogo();

        startSplashSequence();

    }


    /* ======================================================
       7. RESTAURATION DES DONNÉES
    ====================================================== */

    function restoreSavedState() {

        const savedGender =
            storage.get(
                CONFIG.storageKeys.gender,
                null
            );

        const savedDevices =
            storage.get(
                CONFIG.storageKeys
                    .connectedDevices,
                []
            );

        const savedStory =
            storage.get(
                CONFIG.storageKeys.story,
                ""
            );

        if (
            savedGender === "male" ||
            savedGender === "female"
        ) {

            state.selectedGender =
                savedGender;

            applyGenderTheme(
                savedGender,
                {
                    save: false
                }
            );

            updateGenderSelection(
                savedGender
            );

        } else {

            state.selectedGender = null;

            elements.body.dataset
                .atlasTheme = "male";

        }

        if (
            Array.isArray(savedDevices)
        ) {

            state.connectedDevices =
                savedDevices.filter(
                    (device) => {

                        return (
                            typeof device ===
                            "string"
                        );

                    }
                );

        }

        if (
            elements.story &&
            typeof savedStory === "string"
        ) {

            elements.story.value =
                savedStory.slice(
                    0,
                    CONFIG.maximumStoryLength
                );

        }

    }


    /* ======================================================
       8. SÉQUENCE D’OUVERTURE
    ====================================================== */

    function startSplashSequence() {

        window.setTimeout(() => {

            if (!elements.splashScreen) {

                openInitialScreen();

                return;

            }

            elements.splashScreen
                .classList
                .add("is-leaving");

            window.setTimeout(() => {

                elements.splashScreen
                    .classList
                    .add("hidden");

                elements.splashScreen
                    .setAttribute(
                        "aria-hidden",
                        "true"
                    );

                openInitialScreen();

            }, CONFIG.splashTransitionDuration);

        }, CONFIG.splashDuration);

    }


    function openInitialScreen() {

        /*
         * Le choix Homme/Femme est volontairement
         * affiché à chaque lancement.
         *
         * Le choix enregistré reste simplement
         * présélectionné.
         */

        showScreen(
            "genderSelection",
            {
                animation: "fade-up",
                instant: true
            }
        );

    }


    /* ======================================================
       9. GESTION DES ÉCRANS
    ====================================================== */

    function showScreen(
        screenId,
        options = {}
    ) {

        const targetScreen =
            document.getElementById(
                screenId
            );

        if (!targetScreen) {

            console.warn(
                `Atlas OS : écran introuvable : ${screenId}`
            );

            return;

        }

        screens.forEach((screen) => {

            screen.classList.add(
                "hidden"
            );

            screen.classList.remove(
                "fade-in",
                "fade-up",
                "fade-scale"
            );

            screen.setAttribute(
                "aria-hidden",
                "true"
            );

        });

        targetScreen.classList.remove(
            "hidden"
        );

        targetScreen.setAttribute(
            "aria-hidden",
            "false"
        );

        void targetScreen.offsetWidth;

        targetScreen.classList.add(
            options.animation ||
            "fade-in"
        );

        state.currentScreen =
            screenId;

        const applicationScreens = [

            "dashboard",

            "aiScreen",

            "historyScreen",

            "profileScreen"

        ];

        if (
            applicationScreens.includes(
                screenId
            )
        ) {

            showBottomNavigation();

        } else {

            hideBottomNavigation();

        }

        updateNavigationState(
            screenId
        );

        if (
            screenId === "intro"
        ) {

            updateSelectedIntroLogo();

        }

        if (
            screenId === "dashboard"
        ) {

            window.setTimeout(() => {

                initializeDashboardBody3D();

                resizeBody3D();

            }, 120);

        }

        window.scrollTo({

            top: 0,

            behavior:
                options.instant
                    ? "auto"
                    : "smooth"

        });

    }


    /* ======================================================
       10. CHOIX HOMME / FEMME
    ====================================================== */

    function selectGender(gender) {

        if (
            gender !== "male" &&
            gender !== "female"
        ) {

            return;

        }

        state.selectedGender = gender;

        applyGenderTheme(gender);

        updateGenderSelection(gender);

        updateSelectedIntroLogo();

        updateProfileInformation();

        if (
            elements.confirmGenderButton
        ) {

            elements.confirmGenderButton
                .disabled = false;

        }

    }


    function applyGenderTheme(
        gender,
        options = {}
    ) {

        const validGender =
            gender === "female"
                ? "female"
                : "male";

        elements.body.dataset
            .atlasTheme = validGender;

        if (options.save !== false) {

            storage.set(
                CONFIG.storageKeys.gender,
                validGender
            );

        }

        if (
            window.AtlasParticles &&
            typeof window.AtlasParticles
                .setTheme === "function"
        ) {

            window.AtlasParticles
                .setTheme(validGender);

        }

        /*
         * body3d.js reste utilisé uniquement
         * dans le tableau de bord.
         */

        if (
            state.currentScreen ===
                "dashboard" &&
            window.AtlasBody3D &&
            typeof window.AtlasBody3D
                .setTheme === "function"
        ) {

            window.AtlasBody3D
                .setTheme(validGender);

        }

        updateSelectedIntroLogo();

    }


    function updateGenderSelection(
        gender
    ) {

        elements.genderCards
            .forEach((card) => {

                const isSelected =
                    card.dataset.gender ===
                    gender;

                card.classList.toggle(
                    "selected",
                    isSelected
                );

                card.setAttribute(
                    "aria-checked",
                    String(isSelected)
                );

                card.setAttribute(
                    "aria-pressed",
                    String(isSelected)
                );

            });

        if (
            elements.confirmGenderButton
        ) {

            elements.confirmGenderButton
                .disabled = !gender;

        }

    }


    function updateSelectedIntroLogo() {

        const logo =
            elements.selectedAtlasLogo ||
            document.getElementById(
                "selectedAtlasLogo"
            );

        if (!logo) {

            return;

        }

        const selectedGender =
            state.selectedGender ===
            "female"
                ? "female"
                : "male";

        logo.classList.remove(
            "selected-atlas-logo-image--male",
            "selected-atlas-logo-image--female"
        );

        logo.classList.add(
            selectedGender === "female"
                ? "selected-atlas-logo-image--female"
                : "selected-atlas-logo-image--male"
        );

        logo.src =
            "./assets/images/atlas-logo.jpg";

        logo.alt =
            selectedGender === "female"
                ? "Logo Atlas, représentation féminine"
                : "Logo Atlas, représentation masculine";

        if (
            elements
                .selectedAtlasLogoContainer
        ) {

            elements
                .selectedAtlasLogoContainer
                .dataset.gender =
                selectedGender;

        }

    }


    function confirmGenderSelection() {

        if (!state.selectedGender) {

            showToast(
                "Sélectionnez une représentation avant de continuer.",
                "warning"
            );

            return;

        }

        storage.set(
            CONFIG.storageKeys.gender,
            state.selectedGender
        );

        updateSelectedIntroLogo();

        updateProfileInformation();

        showScreen(
            "intro",
            {
                animation: "fade-scale"
            }
        );

    }


    function skipGenderSelection() {

        if (!state.selectedGender) {

            state.selectedGender =
                "male";

        }

        applyGenderTheme(
            state.selectedGender
        );

        updateGenderSelection(
            state.selectedGender
        );

        updateSelectedIntroLogo();

        updateProfileInformation();

        showScreen(
            "intro",
            {
                animation: "fade-scale"
            }
        );

    }


    /* ======================================================
       11. PAGE D’INTRODUCTION
    ====================================================== */

    function enterAtlasExperience() {

        showScreen(
            "sync",
            {
                animation: "fade-up"
            }
        );

    }


    /* ======================================================
       12. APPAREILS ET SOURCES DE DONNÉES
    ====================================================== */

    function handleDeviceButton(
        button
    ) {

        const deviceName =
            button.dataset.device;

        if (!deviceName) {

            return;

        }

        if (
            deviceName ===
            "Saisie manuelle"
        ) {

            toggleDevice(
                deviceName
            );

            return;

        }

        openDeviceModal(
            deviceName
        );

    }


    function openDeviceModal(
        deviceName
    ) {

        const alreadyConnected =
            state.connectedDevices
                .includes(deviceName);

        const modalContent =
            document.createElement(
                "div"
            );

        modalContent.className =
            "device-modal-information";

        const description =
            document.createElement(
                "p"
            );

        description.textContent =
            `${deviceName} n’est pas encore relié à une API réelle. ` +
            "Vous pouvez simuler sa connexion dans cette démonstration.";

        description.style
            .marginBottom = "22px";

        const actionButton =
            document.createElement(
                "button"
            );

        actionButton.type =
            "button";

        actionButton.className =
            alreadyConnected
                ? "atlas-secondary-button"
                : "atlas-primary-button";

        actionButton.textContent =
            alreadyConnected
                ? "Déconnecter l’appareil"
                : "Activer la démonstration";

        actionButton.addEventListener(
            "click",
            () => {

                toggleDevice(
                    deviceName
                );

                closeModal();

            }
        );

        modalContent.append(
            description,
            actionButton
        );

        openModal(
            deviceName,
            modalContent
        );

    }


    function toggleDevice(
        deviceName
    ) {

        const deviceIndex =
            state.connectedDevices
                .indexOf(deviceName);

        if (deviceIndex >= 0) {

            state.connectedDevices
                .splice(
                    deviceIndex,
                    1
                );

            showToast(
                `${deviceName} a été déconnecté.`,
                "info"
            );

        } else {

            state.connectedDevices
                .push(deviceName);

            showToast(
                `${deviceName} est maintenant actif.`,
                "success"
            );

        }

        storage.set(
            CONFIG.storageKeys
                .connectedDevices,
            state.connectedDevices
        );

        updateDeviceButtons();

        updateProfileInformation();

    }


    function updateDeviceButtons() {

        elements.deviceButtons
            .forEach((button) => {

                const deviceName =
                    button.dataset.device;

                const isConnected =
                    state.connectedDevices
                        .includes(deviceName);

                button.classList.toggle(
                    "connected",
                    isConnected
                );

                button.setAttribute(
                    "aria-pressed",
                    String(isConnected)
                );

                if (
                    deviceName ===
                    "Saisie manuelle"
                ) {

                    button.textContent =
                        isConnected
                            ? "Activée"
                            : "Utiliser";

                } else {

                    button.textContent =
                        isConnected
                            ? "Connecté"
                            : "Connecter";

                }

            });

        updateDeviceSelectionStatus();

    }


    function updateDeviceSelectionStatus() {

        if (
            !elements
                .deviceSelectionStatus
        ) {

            return;

        }

        const count =
            state.connectedDevices.length;

        if (count === 0) {

            elements
                .deviceSelectionStatus
                .textContent =
                "La connexion des appareils est facultative pour cette démonstration.";

            return;

        }

        if (count === 1) {

            elements
                .deviceSelectionStatus
                .textContent =
                `1 source de données est active : ${state.connectedDevices[0]}.`;

            return;

        }

        elements
            .deviceSelectionStatus
            .textContent =
            `${count} sources de données sont actuellement actives.`;

    }


    function continueAfterSynchronization() {

        showScreen(
            "assistant",
            {
                animation: "fade-up"
            }
        );

        window.setTimeout(() => {

            elements.story?.focus();

        }, 450);

    }


    /* ======================================================
       13. HISTOIRE BIOMÉCANIQUE
    ====================================================== */

    function updateStoryCounter() {

        if (
            !elements.story ||
            !elements.storyCounter
        ) {

            return;

        }

        const currentLength =
            elements.story.value.length;

        elements.storyCounter
            .textContent =
            `${currentLength} / ${CONFIG.maximumStoryLength}`;

        if (
            currentLength >=
            CONFIG.maximumStoryLength - 200
        ) {

            elements.storyCounter
                .style.color =
                "var(--warning)";

        } else {

            elements.storyCounter
                .style.color = "";

        }

    }


    function handleStorySubmission(
        event
    ) {

        event.preventDefault();

        if (!elements.story) {

            return;

        }

        const story =
            elements.story.value.trim();

        if (
            story.length <
            CONFIG.minimumStoryLength
        ) {

            setAssistantMessage(
                `Décrivez votre situation en au moins ${CONFIG.minimumStoryLength} caractères.`
            );

            elements.story.focus();

            return;

        }

        setAssistantMessage("");

        storage.set(
            CONFIG.storageKeys.story,
            story
        );

        startTwinCreation();

    }


    function setAssistantMessage(
        message
    ) {

        if (
            elements.assistantMessage
        ) {

            elements.assistantMessage
                .textContent = message;

        }

    }


    /* ======================================================
       14. CRÉATION DU JUMEAU
    ====================================================== */

    function startTwinCreation() {

        if (
            state.creationInterval
        ) {

            window.clearInterval(
                state.creationInterval
            );

        }

        showScreen(
            "twinCreation",
            {
                animation: "fade-scale"
            }
        );

        resetCreationProgress();

        const startTime =
            performance.now();

        const statuses = [

            {
                progress: 0,
                text:
                    "Analyse de votre profil biomécanique…"
            },

            {
                progress: 18,
                text:
                    "Lecture de votre histoire corporelle…"
            },

            {
                progress: 36,
                text:
                    "Création de votre structure numérique…"
            },

            {
                progress: 55,
                text:
                    "Analyse des chaînes musculaires…"
            },

            {
                progress: 73,
                text:
                    "Évaluation des zones de vigilance…"
            },

            {
                progress: 88,
                text:
                    "Synchronisation du modèle Atlas…"
            },

            {
                progress: 97,
                text:
                    "Finalisation de votre jumeau…"
            }

        ];

        state.creationInterval =
            window.setInterval(() => {

                const elapsed =
                    performance.now() -
                    startTime;

                const progress =
                    Math.min(
                        100,
                        Math.round(
                            (
                                elapsed /
                                CONFIG
                                    .creationDuration
                            ) * 100
                        )
                    );

                updateCreationProgress(
                    progress,
                    statuses
                );

                if (progress >= 100) {

                    window.clearInterval(
                        state.creationInterval
                    );

                    state.creationInterval =
                        null;

                    completeTwinCreation();

                }

            }, 80);

    }


    function resetCreationProgress() {

        if (
            elements
                .creationProgressBar
        ) {

            elements
                .creationProgressBar
                .style.width = "0%";

        }

        if (
            elements
                .creationProgressText
        ) {

            elements
                .creationProgressText
                .textContent = "0 %";

        }

        if (
            elements.creationProgress
        ) {

            elements.creationProgress
                .setAttribute(
                    "aria-valuenow",
                    "0"
                );

        }

        if (
            elements.creationStatus
        ) {

            elements.creationStatus
                .textContent =
                "Analyse de votre profil biomécanique…";

        }

    }


    function updateCreationProgress(
        progress,
        statuses
    ) {

        if (
            elements
                .creationProgressBar
        ) {

            elements
                .creationProgressBar
                .style.width =
                `${progress}%`;

        }

        if (
            elements
                .creationProgressText
        ) {

            elements
                .creationProgressText
                .textContent =
                `${progress} %`;

        }

        if (
            elements.creationProgress
        ) {

            elements.creationProgress
                .setAttribute(
                    "aria-valuenow",
                    String(progress)
                );

        }

        const activeStatus =
            [...statuses]
                .reverse()
                .find((status) => {

                    return (
                        progress >=
                        status.progress
                    );

                });

        if (
            activeStatus &&
            elements.creationStatus
        ) {

            elements.creationStatus
                .textContent =
                activeStatus.text;

        }

    }


    function completeTwinCreation() {

        storage.set(
            CONFIG.storageKeys
                .onboardingComplete,
            true
        );

        updateProfileInformation();

        showScreen(
            "dashboard",
            {
                animation: "fade-up"
            }
        );

        showToast(
            "Votre jumeau biomécanique est prêt.",
            "success"
        );

    }


    /* ======================================================
       15. NAVIGATION PRINCIPALE
    ====================================================== */

    function handleNavigation(
        button
    ) {

        const targetScreen =
            button.dataset.screen;

        const focusTarget =
            button.dataset.focus;

        if (!targetScreen) {

            return;

        }

        showScreen(
            targetScreen,
            {
                animation: "fade-in"
            }
        );

        setActiveNavigationButton(
            button
        );

        if (focusTarget) {

            window.setTimeout(() => {

                const target =
                    document.getElementById(
                        focusTarget
                    );

                target?.scrollIntoView({

                    behavior: "smooth",

                    block: "center"

                });

            }, 180);

        }

    }


    function showBottomNavigation() {

        elements.bottomNav
            ?.classList
            .remove("hidden");

    }


    function hideBottomNavigation() {

        elements.bottomNav
            ?.classList
            .add("hidden");

    }


    function updateNavigationState(
        screenId
    ) {

        elements.navButtons
            .forEach((button) => {

                const isActive =
                    button.dataset.screen ===
                    screenId &&
                    !button.dataset.focus;

                button.classList.toggle(
                    "active",
                    isActive
                );

            });

    }


    function setActiveNavigationButton(
        activeButton
    ) {

        elements.navButtons
            .forEach((button) => {

                button.classList.toggle(
                    "active",
                    button ===
                    activeButton
                );

            });

    }


    /* ======================================================
       16. JUMEAU 3D DU TABLEAU DE BORD
    ====================================================== */

    function initializeDashboardBody3D() {

        if (
            window.AtlasBody3D &&
            typeof window.AtlasBody3D
                .initializeDashboard ===
            "function"
        ) {

            window.AtlasBody3D
                .initializeDashboard(
                    "body3dContainer"
                );

        }

    }


    function resizeBody3D() {

        if (
            window.AtlasBody3D &&
            typeof window.AtlasBody3D
                .resize === "function"
        ) {

            window.AtlasBody3D
                .resize();

        }

    }


    function resetBodyView() {

        if (
            window.AtlasBody3D &&
            typeof window.AtlasBody3D
                .resetView === "function"
        ) {

            window.AtlasBody3D
                .resetView();

            showToast(
                "Vue du jumeau recentrée.",
                "info"
            );

            return;

        }

        showToast(
            "Le moteur 3D est indisponible.",
            "warning"
        );

    }


    function changeBodyLayer(
        button
    ) {

        const layer =
            button.dataset.bodyLayer;

        if (!layer) {

            return;

        }

        elements.bodyControls
            .forEach((control) => {

                control.classList.toggle(
                    "active",
                    control === button
                );

            });

        if (
            window.AtlasBody3D &&
            typeof window.AtlasBody3D
                .setLayer === "function"
        ) {

            window.AtlasBody3D
                .setLayer(layer);

        }

        const layerNames = {

            skin: "Peau",

            muscles: "Muscles",

            skeleton: "Squelette",

            risks: "Zones sensibles"

        };

        showToast(
            `Couche affichée : ${layerNames[layer] || layer}.`,
            "info"
        );

    }


    /* ======================================================
       17. ATLAS AI
    ====================================================== */

    function handleChatSubmission(
        event
    ) {

        event.preventDefault();

        if (
            !elements.chatInput ||
            !elements.chatMessages
        ) {

            return;

        }

        const message =
            elements.chatInput
                .value
                .trim();

        if (
            message.length === 0 ||
            state.atlasIsReplying
        ) {

            return;

        }

        appendChatMessage(
            message,
            "user"
        );

        elements.chatInput.value =
            "";

        state.atlasIsReplying =
            true;

        showAtlasTypingIndicator();

        const delay =
            800 +
            Math.random() * 700;

        window.setTimeout(() => {

            removeAtlasTypingIndicator();

            const response =
                generateAtlasResponse(
                    message
                );

            appendChatMessage(
                response,
                "atlas"
            );

            state.atlasIsReplying =
                false;

        }, delay);

    }


    function appendChatMessage(
        message,
        sender
    ) {

        const article =
            document.createElement(
                "article"
            );

        article.className =
            `chat-message chat-message--${sender}`;

        const avatar =
            document.createElement(
                "div"
            );

        avatar.className =
            "chat-avatar";

        avatar.setAttribute(
            "aria-hidden",
            "true"
        );

        avatar.textContent =
            sender === "atlas"
                ? "A"
                : "V";

        const paragraph =
            document.createElement(
                "p"
            );

        paragraph.textContent =
            message;

        article.append(
            avatar,
            paragraph
        );

        elements.chatMessages
            .appendChild(article);

        scrollChatToBottom();

    }


    function showAtlasTypingIndicator() {

        if (!elements.chatMessages) {

            return;

        }

        removeAtlasTypingIndicator();

        const indicator =
            document.createElement(
                "article"
            );

        indicator.id =
            "atlasTypingIndicator";

        indicator.className =
            "chat-message chat-message--atlas";

        const avatar =
            document.createElement(
                "div"
            );

        avatar.className =
            "chat-avatar";

        avatar.setAttribute(
            "aria-hidden",
            "true"
        );

        avatar.textContent = "A";

        const paragraph =
            document.createElement(
                "p"
            );

        paragraph.textContent =
            "Atlas analyse votre message…";

        indicator.append(
            avatar,
            paragraph
        );

        elements.chatMessages
            .appendChild(indicator);

        scrollChatToBottom();

    }


    function removeAtlasTypingIndicator() {

        document
            .getElementById(
                "atlasTypingIndicator"
            )
            ?.remove();

    }


    function scrollChatToBottom() {

        if (!elements.chatMessages) {

            return;

        }

        elements.chatMessages.scrollTo({

            top:
                elements.chatMessages
                    .scrollHeight,

            behavior: "smooth"

        });

    }


    function generateAtlasResponse(
        message
    ) {

        const normalizedMessage =
            message
                .toLocaleLowerCase(
                    "fr-FR"
                )
                .normalize("NFD")
                .replace(
                    /[\u0300-\u036f]/g,
                    ""
                );

        if (
            normalizedMessage
                .includes("douleur") ||
            normalizedMessage
                .includes("mal")
        ) {

            return (
                "Je prends en compte cette douleur. " +
                "Précisez sa localisation, son intensité sur 10, " +
                "sa durée et les mouvements qui l’aggravent. " +
                "En cas de douleur intense, soudaine ou persistante, " +
                "consultez un professionnel de santé."
            );

        }

        if (
            normalizedMessage
                .includes("sommeil") ||
            normalizedMessage
                .includes("dormi") ||
            normalizedMessage
                .includes("fatigue")
        ) {

            return (
                "Votre récupération dépend notamment de la durée du sommeil, " +
                "de sa régularité et de votre niveau de fatigue au réveil. " +
                "Atlas pourra comparer ces données à votre charge physique."
            );

        }

        if (
            normalizedMessage
                .includes("courir") ||
            normalizedMessage
                .includes("course") ||
            normalizedMessage
                .includes("running")
        ) {

            return (
                "Pour analyser votre course, Atlas utilisera progressivement " +
                "la cadence, le temps de contact au sol, l’équilibre gauche-droite, " +
                "la charge d’entraînement et vos sensations."
            );

        }

        if (
            normalizedMessage
                .includes("recuperation") ||
            normalizedMessage
                .includes("repos")
        ) {

            return (
                "Votre récupération simulée est actuellement favorable. " +
                "Conservez une charge modérée et surveillez l’apparition " +
                "de fatigue inhabituelle ou de douleurs persistantes."
            );

        }

        if (
            normalizedMessage
                .includes("genou")
        ) {

            return (
                "Pour le genou, indiquez si la gêne se situe devant, derrière, " +
                "à l’intérieur ou à l’extérieur de l’articulation. " +
                "Précisez également les mouvements concernés."
            );

        }

        if (
            normalizedMessage
                .includes("dos") ||
            normalizedMessage
                .includes("lombaire")
        ) {

            return (
                "Pour mieux comprendre votre dos, Atlas doit connaître " +
                "la zone exacte, les positions aggravantes, la présence éventuelle " +
                "d’irradiations et l’évolution de la gêne."
            );

        }

        if (
            normalizedMessage
                .includes("bonjour") ||
            normalizedMessage
                .includes("salut")
        ) {

            return (
                "Bonjour. Je suis prêt à explorer votre activité, " +
                "votre récupération ou une région de votre corps."
            );

        }

        if (
            normalizedMessage
                .includes("merci")
        ) {

            return (
                "Avec plaisir. Votre jumeau évoluera progressivement " +
                "avec les informations que vous lui transmettrez."
            );

        }

        return (
            "J’ai enregistré votre message. Dans cette version de démonstration, " +
            "mes réponses sont simulées. La future version d’Atlas analysera " +
            "vos données biomécaniques, votre historique et vos objectifs."
        );

    }


    /* ======================================================
       18. PROFIL
    ====================================================== */

    function updateProfileInformation() {

        if (
            elements.selectedTwinLabel
        ) {

            elements.selectedTwinLabel
                .textContent =
                state.selectedGender ===
                "female"
                    ? "Jumeau féminin"
                    : "Jumeau masculin";

        }

        if (
            elements
                .connectedDevicesLabel
        ) {

            const count =
                state.connectedDevices
                    .length;

            if (count === 0) {

                elements
                    .connectedDevicesLabel
                    .textContent =
                    "Aucun appareil connecté";

            } else if (count === 1) {

                elements
                    .connectedDevicesLabel
                    .textContent =
                    state.connectedDevices[0];

            } else {

                elements
                    .connectedDevicesLabel
                    .textContent =
                    `${count} sources de données actives`;

            }

        }

    }


    function openProfileScreen() {

        showScreen(
            "profileScreen",
            {
                animation: "fade-up"
            }
        );

    }


    function openGenderSettings() {

        updateGenderSelection(
            state.selectedGender
        );

        showScreen(
            "genderSelection",
            {
                animation: "fade-up"
            }
        );

        showToast(
            "Choisissez une nouvelle apparence pour votre jumeau.",
            "info"
        );

    }


    function openDeviceManager() {

        const container =
            document.createElement(
                "div"
            );

        const introduction =
            document.createElement(
                "p"
            );

        introduction.textContent =
            "Gérez les sources de données utilisées dans cette démonstration.";

        introduction.style
            .marginBottom = "22px";

        const list =
            document.createElement(
                "div"
            );

        list.style.display =
            "grid";

        list.style.gap =
            "12px";

        elements.deviceButtons
            .forEach(
                (deviceButton) => {

                    const deviceName =
                        deviceButton
                            .dataset
                            .device;

                    if (!deviceName) {

                        return;

                    }

                    const row =
                        document
                            .createElement(
                                "button"
                            );

                    row.type =
                        "button";

                    row.style.width =
                        "100%";

                    row.style.padding =
                        "14px 16px";

                    row.style.color =
                        "white";

                    row.style
                        .textAlign =
                        "left";

                    row.style.border =
                        "1px solid rgba(255, 255, 255, 0.1)";

                    row.style
                        .borderRadius =
                        "14px";

                    row.style
                        .background =
                        "rgba(255, 255, 255, 0.05)";

                    row.style.cursor =
                        "pointer";

                    const connected =
                        state
                            .connectedDevices
                            .includes(
                                deviceName
                            );

                    row.textContent =
                        `${connected ? "✓" : "○"} ${deviceName}`;

                    row.addEventListener(
                        "click",
                        () => {

                            toggleDevice(
                                deviceName
                            );

                            openDeviceManager();

                        }
                    );

                    list.appendChild(
                        row
                    );

                }
            );

        container.append(
            introduction,
            list
        );

        openModal(
            "Appareils et données",
            container
        );

    }


    function confirmApplicationReset() {

        const container =
            document.createElement(
                "div"
            );

        const warning =
            document.createElement(
                "p"
            );

        warning.textContent =
            "Cette action supprimera les choix enregistrés dans cette démonstration et relancera Atlas OS.";

        warning.style
            .marginBottom = "22px";

        const actions =
            document.createElement(
                "div"
            );

        actions.style.display =
            "flex";

        actions.style.flexWrap =
            "wrap";

        actions.style.gap =
            "12px";

        const cancelButton =
            document.createElement(
                "button"
            );

        cancelButton.type =
            "button";

        cancelButton.className =
            "atlas-secondary-button";

        cancelButton.textContent =
            "Annuler";

        cancelButton.addEventListener(
            "click",
            closeModal
        );

        const confirmButton =
            document.createElement(
                "button"
            );

        confirmButton.type =
            "button";

        confirmButton.className =
            "atlas-primary-button";

        confirmButton.textContent =
            "Réinitialiser Atlas";

        confirmButton.addEventListener(
            "click",
            resetApplication
        );

        actions.append(
            cancelButton,
            confirmButton
        );

        container.append(
            warning,
            actions
        );

        openModal(
            "Réinitialiser la démonstration",
            container
        );

    }


    function resetApplication() {

        storage.clearAtlasData();

        state.selectedGender =
            null;

        state.connectedDevices =
            [];

        closeModal();

        window.location.reload();

    }


    /* ======================================================
       19. NOTIFICATIONS
    ====================================================== */

    function showToast(
        message,
        type = "info"
    ) {

        if (
            !elements.atlasToast ||
            !elements.atlasToastMessage
        ) {

            return;

        }

        const icons = {

            info: "info",

            success: "check_circle",

            warning: "warning",

            error: "error"

        };

        if (state.toastTimeout) {

            window.clearTimeout(
                state.toastTimeout
            );

        }

        elements.atlasToastMessage
            .textContent = message;

        if (
            elements.atlasToastIcon
        ) {

            elements.atlasToastIcon
                .textContent =
                icons[type] ||
                icons.info;

        }

        elements.atlasToast
            .classList
            .add("visible");

        state.toastTimeout =
            window.setTimeout(() => {

                elements.atlasToast
                    .classList
                    .remove("visible");

            }, 3400);

    }


    /* ======================================================
       20. MODALE
    ====================================================== */

    function openModal(
        title,
        content
    ) {

        if (!elements.atlasModal) {

            return;

        }

        if (
            elements.atlasModalTitle
        ) {

            elements.atlasModalTitle
                .textContent =
                title;

        }

        if (
            elements.atlasModalBody
        ) {

            elements.atlasModalBody
                .replaceChildren();

            if (
                content instanceof Node
            ) {

                elements.atlasModalBody
                    .appendChild(
                        content
                    );

            } else {

                const paragraph =
                    document
                        .createElement(
                            "p"
                        );

                paragraph.textContent =
                    String(content);

                elements.atlasModalBody
                    .appendChild(
                        paragraph
                    );

            }

        }

        elements.atlasModal
            .classList
            .remove("hidden");

        elements.atlasModal
            .setAttribute(
                "aria-hidden",
                "false"
            );

        elements.closeModalButton
            ?.focus();

    }


    function closeModal() {

        if (!elements.atlasModal) {

            return;

        }

        elements.atlasModal
            .classList
            .add("hidden");

        elements.atlasModal
            .setAttribute(
                "aria-hidden",
                "true"
            );

    }


    /* ======================================================
       21. CLAVIER
    ====================================================== */

    function handleKeyboard(
        event
    ) {

        if (
            event.key === "Escape" &&
            !elements.atlasModal
                ?.classList
                .contains("hidden")
        ) {

            closeModal();

        }

        if (
            (
                event.key === "Enter" ||
                event.key === " "
            ) &&
            document.activeElement
                ?.classList
                .contains("gender-card")
        ) {

            event.preventDefault();

            selectGender(
                document.activeElement
                    .dataset.gender
            );

        }

    }


    /* ======================================================
       22. ÉVÉNEMENTS
    ====================================================== */

    function bindEvents() {

        elements.genderCards
            .forEach((card) => {

                card.addEventListener(
                    "click",
                    () => {

                        selectGender(
                            card.dataset.gender
                        );

                    }
                );

            });

        elements
            .confirmGenderButton
            ?.addEventListener(
                "click",
                confirmGenderSelection
            );

        elements
            .skipGenderButton
            ?.addEventListener(
                "click",
                skipGenderSelection
            );

        elements.enterButton
            ?.addEventListener(
                "click",
                enterAtlasExperience
            );

        elements.deviceButtons
            .forEach((button) => {

                button.addEventListener(
                    "click",
                    () => {

                        handleDeviceButton(
                            button
                        );

                    }
                );

            });

        elements.continueButton
            ?.addEventListener(
                "click",
                continueAfterSynchronization
            );

        elements.story
            ?.addEventListener(
                "input",
                updateStoryCounter
            );

        elements.atlasStoryForm
            ?.addEventListener(
                "submit",
                handleStorySubmission
            );

        elements.navButtons
            .forEach((button) => {

                button.addEventListener(
                    "click",
                    () => {

                        handleNavigation(
                            button
                        );

                    }
                );

            });

        elements.profileButton
            ?.addEventListener(
                "click",
                openProfileScreen
            );

        elements
            .resetBodyViewButton
            ?.addEventListener(
                "click",
                resetBodyView
            );

        elements.bodyControls
            .forEach((button) => {

                button.addEventListener(
                    "click",
                    () => {

                        changeBodyLayer(
                            button
                        );

                    }
                );

            });

        elements.chatForm
            ?.addEventListener(
                "submit",
                handleChatSubmission
            );

        elements
            .changeGenderButton
            ?.addEventListener(
                "click",
                openGenderSettings
            );

        elements
            .manageDevicesButton
            ?.addEventListener(
                "click",
                openDeviceManager
            );

        elements
            .resetApplicationButton
            ?.addEventListener(
                "click",
                confirmApplicationReset
            );

        elements.closeModalButton
            ?.addEventListener(
                "click",
                closeModal
            );

        elements.modalBackdrop
            ?.addEventListener(
                "click",
                closeModal
            );

        document.addEventListener(
            "keydown",
            handleKeyboard
        );

        window.addEventListener(
            "resize",
            debounce(
                resizeBody3D,
                150
            )
        );

        window.addEventListener(
            "orientationchange",
            () => {

                window.setTimeout(
                    resizeBody3D,
                    300
                );

            }
        );

    }


    /* ======================================================
       23. UTILITAIRES
    ====================================================== */

    function debounce(
        callback,
        delay
    ) {

        let timeoutId = null;

        return (...argumentsList) => {

            if (timeoutId) {

                window.clearTimeout(
                    timeoutId
                );

            }

            timeoutId =
                window.setTimeout(() => {

                    callback(
                        ...argumentsList
                    );

                }, delay);

        };

    }


    /* ======================================================
       24. API PUBLIQUE
    ====================================================== */

    window.AtlasOS = {

        showScreen,

        showToast,

        openModal,

        closeModal,

        selectGender,

        updateSelectedIntroLogo,

        getState() {

            return {

                selectedGender:
                    state.selectedGender,

                connectedDevices:
                    [
                        ...state
                            .connectedDevices
                    ],

                currentScreen:
                    state.currentScreen

            };

        }

    };


    /* ======================================================
       25. DÉMARRAGE
    ====================================================== */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initializeApplication,
            {
                once: true
            }
        );

    } else {

        initializeApplication();

    }

})();
