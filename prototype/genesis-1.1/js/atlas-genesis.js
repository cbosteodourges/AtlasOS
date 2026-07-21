"use strict";

(() => {

    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION ET ÉTAT
    // ████████████████████████████████████████████████████████████

    const VERSION = "1.1.0";

    const state = {
        selectedAvatar: null,
        profile: null,
        audioContext: null
    };

    const scenes =
        Array.from(
            document.querySelectorAll(".atlas-scene")
        );

    const elements = {
        enterButton:
            document.getElementById("enterAtlasButton"),

        openingSequence:
            document.getElementById("openingSequence"),

        heartbeat:
            document.getElementById("heartbeatVisual"),

        logoStage:
            document.getElementById("logoStage"),

        openingTitle:
            document.getElementById("openingTitle"),

        openingStatus:
            document.getElementById("openingStatus"),

        skipOpeningButton:
            document.getElementById("skipOpeningButton"),

        avatarContinue:
            document.getElementById("avatarContinueButton"),

        avatarHint:
            document.getElementById("avatarHint"),

        profileForm:
            document.getElementById("profileForm"),

        createdAvatar:
            document.getElementById("createdAvatar"),

        creationMessage:
            document.getElementById("creationMessage"),

        creationProgress:
            document.getElementById("creationProgress"),

        creationPercent:
            document.getElementById("creationPercent"),

        readyAvatar:
            document.getElementById("readyAvatar"),

        readySummary:
            document.getElementById("readySummary"),

        openHubButton:
            document.getElementById("openHubButton"),

        hubAvatar:
            document.getElementById("hubAvatar"),

        hubUserName:
            document.getElementById("hubUserName"),

        briefFirstName:
            document.getElementById("briefFirstName"),

        dialog:
            document.getElementById("atlasDialog"),

        dialogTitle:
            document.getElementById("dialogTitle"),

        dialogText:
            document.getElementById("dialogText"),

        dialogAction:
            document.getElementById("dialogAction")
    };

    // ████████████████████████████████████████████████████████████
    // 🟩 PARTIE B — B01 — NAVIGATION ENTRE LES SCÈNES
    // ████████████████████████████████████████████████████████████

    function showScene(sceneName) {
        scenes.forEach((scene) => {
            scene.classList.toggle(
                "is-active",
                scene.dataset.scene === sceneName
            );
        });
    }

    function wait(milliseconds) {
        return new Promise((resolve) => {
            window.setTimeout(resolve, milliseconds);
        });
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — PARTICULES
    // ████████████████████████████████████████████████████████████

    function initializeParticleCanvas(canvasId, density = 65) {
        const canvas =
            document.getElementById(canvasId);

        if (!canvas) {
            return;
        }

        const context =
            canvas.getContext("2d");

        let particles = [];

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            particles = Array.from(
                {
                    length:
                        Math.max(
                            45,
                            Math.round(
                                window.innerWidth /
                                (density / 3)
                            )
                        )
                },
                () => ({
                    x:
                        Math.random() *
                        canvas.width,

                    y:
                        Math.random() *
                        canvas.height,

                    radius:
                        Math.random() *
                        1.5 +
                        0.25,

                    speed:
                        Math.random() *
                        0.22 +
                        0.04,

                    alpha:
                        Math.random() *
                        0.5 +
                        0.1
                })
            );
        }

        function animate() {
            context.clearRect(
                0,
                0,
                canvas.width,
                canvas.height
            );

            particles.forEach((particle) => {
                particle.y -= particle.speed;

                if (particle.y < -4) {
                    particle.y =
                        canvas.height + 4;

                    particle.x =
                        Math.random() *
                        canvas.width;
                }

                context.beginPath();

                context.arc(
                    particle.x,
                    particle.y,
                    particle.radius,
                    0,
                    Math.PI * 2
                );

                context.fillStyle =
                    `rgba(96, 224, 255, ${particle.alpha})`;

                context.fill();
            });

            window.requestAnimationFrame(
                animate
            );
        }

        resize();
        animate();

        window.addEventListener(
            "resize",
            resize
        );
    }

    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — AUDIO ET OPENING
    // ████████████████████████████████████████████████████████████

    function getAudioContext() {
        if (!state.audioContext) {
            const AudioContextClass =
                window.AudioContext ||
                window.webkitAudioContext;

            if (AudioContextClass) {
                state.audioContext =
                    new AudioContextClass();
            }
        }

        return state.audioContext;
    }

    function playBoom(
        offset,
        gainValue
    ) {
        const audioContext =
            getAudioContext();

        if (!audioContext) {
            return;
        }

        const start =
            audioContext.currentTime +
            offset;

        const oscillator =
            audioContext.createOscillator();

        const gain =
            audioContext.createGain();

        const lowPass =
            audioContext.createBiquadFilter();

        oscillator.type = "sine";

        oscillator.frequency.setValueAtTime(
            50,
            start
        );

        oscillator.frequency.exponentialRampToValueAtTime(
            28,
            start + 0.24
        );

        lowPass.type = "lowpass";
        lowPass.frequency.value = 125;

        gain.gain.setValueAtTime(
            0.0001,
            start
        );

        gain.gain.exponentialRampToValueAtTime(
            gainValue,
            start + 0.02
        );

        gain.gain.exponentialRampToValueAtTime(
            0.0001,
            start + 0.38
        );

        oscillator.connect(lowPass);
        lowPass.connect(gain);
        gain.connect(
            audioContext.destination
        );

        oscillator.start(start);
        oscillator.stop(start + 0.4);
    }

    function playThreeDoubleBeats() {
        [
            0,
            1.4,
            2.8
        ].forEach((pairStart) => {
            playBoom(
                pairStart,
                0.66
            );

            playBoom(
                pairStart + 0.23,
                0.52
            );
        });
    }

    async function startOpening() {
        elements.enterButton.classList.add(
            "is-hidden"
        );

        elements.openingSequence.classList.remove(
            "is-hidden"
        );

        elements.skipOpeningButton.classList.remove(
            "is-hidden"
        );

        await wait(650);

        elements.heartbeat.classList.add(
            "is-visible"
        );

        playThreeDoubleBeats();

        await wait(4300);

        elements.heartbeat.classList.remove(
            "is-visible"
        );

        elements.logoStage.classList.add(
            "is-visible"
        );

        await wait(1200);

        elements.openingTitle.classList.add(
            "is-visible"
        );

        elements.openingStatus.classList.add(
            "is-visible"
        );

        const messages = [
            "Synchronisation de l’environnement Atlas…",
            "Connexion aux moteurs du Digital Twin…",
            "Initialisation du parcours utilisateur…",
            "Atlas OS prêt."
        ];

        for (const message of messages) {
            elements.openingStatus.textContent =
                message;

            await wait(750);
        }

        showScene("avatar");
    }

    // ████████████████████████████████████████████████████████████
    // 🟪 PARTIE E — E01 — AVATAR ET PROFIL
    // ████████████████████████████████████████████████████████████

    function getAvatarAsset() {
        return (
            state.selectedAvatar === "female"
                ? "./assets/avatar-female.jpg"
                : "./assets/avatar-male.jpg"
        );
    }

    function createAvatarImage(
        altText
    ) {
        return `
            <img
                src="${getAvatarAsset()}"
                alt="${altText}"
            >
        `;
    }

    function selectAvatar(card) {
        state.selectedAvatar =
            card.dataset.avatar;

        document
            .querySelectorAll(
                "[data-avatar]"
            )
            .forEach((item) => {
                const selected =
                    item === card;

                item.classList.toggle(
                    "is-selected",
                    selected
                );

                item.setAttribute(
                    "aria-pressed",
                    String(selected)
                );
            });

        elements.avatarContinue.disabled =
            false;

        elements.avatarHint.textContent =
            state.selectedAvatar === "female"
                ? "Avatar féminin sélectionné."
                : "Avatar masculin sélectionné.";

        elements.avatarHint.classList.add(
            "is-ready"
        );
    }

    // ████████████████████████████████████████████████████████████
    // 🟥 PARTIE F — F01 — CRÉATION ET VALIDATION
    // ████████████████████████████████████████████████████████████

    async function runCreationSequence() {
        elements.createdAvatar.innerHTML =
            createAvatarImage(
                "Digital Twin en cours de création"
            );

        const steps = [
            {
                message:
                    "Initialisation de votre Digital Twin…",
                progress: 15
            },
            {
                message:
                    "Construction du modèle morphologique…",
                progress: 34
            },
            {
                message:
                    "Cartographie biomécanique initiale…",
                progress: 53
            },
            {
                message:
                    "Synchronisation du contexte humain…",
                progress: 72
            },
            {
                message:
                    "Connexion au moteur Atlas IA…",
                progress: 89
            },
            {
                message:
                    "Digital Twin prêt.",
                progress: 100
            }
        ];

        for (const step of steps) {
            elements.creationMessage.textContent =
                step.message;

            elements.creationProgress.style.width =
                `${step.progress}%`;

            elements.creationPercent.textContent =
                `${step.progress}%`;

            await wait(1050);
        }

        elements.readyAvatar.innerHTML =
            createAvatarImage(
                "Digital Twin créé"
            );

        elements.readySummary.textContent =
            `${state.profile.firstName}, votre profil initial Atlas a été créé avec succès.`;

        showScene("ready");
    }

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — HUB ET DIALOGUES
    // ████████████████████████████████████████████████████████████

    const moduleContent = Object.freeze({
        "Santé":
            "Accédez à vos données cliniques, symptômes, examens et antécédents.",

        "Corps":
            "Explorez la cartographie corporelle, les douleurs et les systèmes anatomiques.",

        "Entraînement":
            "Consultez la charge, les séances et la progression proposée.",

        "Sommeil":
            "Analysez la durée, la qualité et la régularité du sommeil.",

        "Nutrition":
            "Visualisez hydratation, énergie et recommandations nutritionnelles.",

        "Atlas IA":
            "Posez une question et obtenez une réponse contextualisée.",

        "Demander à Atlas":
            "Décrivez un symptôme, une préoccupation ou un objectif."
    });

    function openHub() {
        elements.hubAvatar.innerHTML =
            createAvatarImage(
                "Digital Twin Atlas"
            );

        elements.hubUserName.textContent =
            `Bonjour ${state.profile.firstName}`;

        elements.briefFirstName.textContent =
            state.profile.firstName;

        showScene("hub");
    }

    function openDialog(
        title,
        text
    ) {
        elements.dialogTitle.textContent =
            title;

        elements.dialogText.textContent =
            text;

        elements.dialog.showModal();
    }

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G02 — ÉVÉNEMENTS ET DÉMARRAGE
    // ████████████████████████████████████████████████████████████

    function bindEvents() {
        elements.enterButton.addEventListener(
            "click",
            startOpening
        );

        elements.skipOpeningButton.addEventListener(
            "click",
            () => {
                showScene("avatar");
            }
        );

        document
            .querySelectorAll(
                "[data-avatar]"
            )
            .forEach((card) => {
                card.addEventListener(
                    "click",
                    () => {
                        selectAvatar(card);
                    }
                );
            });

        elements.avatarContinue.addEventListener(
            "click",
            () => {
                if (!state.selectedAvatar) {
                    return;
                }

                showScene("profile");
            }
        );

        document
            .querySelectorAll(
                "[data-back]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        showScene(
                            button.dataset.back
                        );
                    }
                );
            });

        elements.profileForm.addEventListener(
            "submit",
            (event) => {
                event.preventDefault();

                state.profile =
                    Object.fromEntries(
                        new FormData(
                            elements.profileForm
                        ).entries()
                    );

                window.localStorage.setItem(
                    "atlasGenesisProfile",
                    JSON.stringify({
                        avatar:
                            state.selectedAvatar,
                        profile:
                            state.profile
                    })
                );

                showScene("creation");
                runCreationSequence();
            }
        );

        elements.openHubButton.addEventListener(
            "click",
            openHub
        );

        document
            .querySelectorAll(
                "[data-module]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        const moduleName =
                            button.dataset.module;

                        openDialog(
                            moduleName,
                            moduleContent[
                                moduleName
                            ] ||
                            "Ce module sera développé progressivement."
                        );
                    }
                );
            });

        elements.dialogAction.addEventListener(
            "click",
            () => {
                elements.dialog.close();
            }
        );
    }

    function initialize() {
        initializeParticleCanvas(
            "openingParticles"
        );

        initializeParticleCanvas(
            "creationParticles"
        );

        initializeParticleCanvas(
            "readyParticles"
        );

        initializeParticleCanvas(
            "hubParticles"
        );

        bindEvents();

        console.info(
            `Atlas OS Genesis ${VERSION} chargé.`
        );
    }

    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }

})();
