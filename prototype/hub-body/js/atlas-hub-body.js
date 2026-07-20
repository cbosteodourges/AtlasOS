// ╔════════════════════════════════════════════════════════════════╗
// ║                           ATLAS OS                             ║
// ╠════════════════════════════════════════════════════════════════╣
// ║ Fichier : prototype/hub-body/js/atlas-hub-body.js             ║
// ║ Module  : Hub Dashboard                                      ║
// ║ Version : 0.6.0                                               ║
// ╚════════════════════════════════════════════════════════════════╝

"use strict";

(() => {

    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION
    // ████████████████████████████████████████████████████████████

    const VERSION = "0.6.0";

    const BODY_POINTS = Object.freeze([
        { id: "head", label: "Crâne", x: 170, y: 40 },
        { id: "neck", label: "Jonction crânio-cervicale", x: 170, y: 93 },
        { id: "cervical", label: "Cervicales", x: 170, y: 118 },
        { id: "shoulder-left", label: "Épaule gauche", x: 125, y: 138 },
        { id: "shoulder-right", label: "Épaule droite", x: 215, y: 138 },
        { id: "thoracic-1", label: "Dorsales hautes", x: 170, y: 170 },
        { id: "thoracic-2", label: "Dorsales moyennes", x: 170, y: 208 },
        { id: "thoracolumbar", label: "Jonction dorso-lombaire", x: 170, y: 247 },
        { id: "lumbar", label: "Lombaires", x: 170, y: 286 },
        { id: "lumbosacral", label: "Jonction lombo-sacrée", x: 170, y: 329 },
        { id: "elbow-left", label: "Coude gauche", x: 75, y: 277 },
        { id: "elbow-right", label: "Coude droit", x: 265, y: 277 },
        { id: "wrist-left", label: "Poignet gauche", x: 64, y: 340 },
        { id: "wrist-right", label: "Poignet droit", x: 276, y: 340 },
        { id: "hand-left", label: "Main gauche", x: 57, y: 375 },
        { id: "hand-right", label: "Main droite", x: 283, y: 375 },
        { id: "si-left", label: "Sacro-iliaque gauche", x: 151, y: 346 },
        { id: "si-right", label: "Sacro-iliaque droite", x: 189, y: 346 },
        { id: "pubis", label: "Symphyse pubienne", x: 170, y: 372 },
        { id: "hip-left", label: "Hanche gauche", x: 142, y: 390 },
        { id: "hip-right", label: "Hanche droite", x: 198, y: 390 },
        { id: "knee-left", label: "Genou gauche", x: 145, y: 505 },
        { id: "knee-right", label: "Genou droit", x: 195, y: 505 },
        { id: "ankle-left", label: "Cheville gauche", x: 143, y: 600 },
        { id: "ankle-right", label: "Cheville droite", x: 197, y: 600 },
        { id: "foot-left", label: "Pied gauche", x: 137, y: 626 },
        { id: "foot-right", label: "Pied droit", x: 203, y: 626 }
    ]);

    const MODULE_TEXT = Object.freeze({
        "Santé": "Accédez à vos données cliniques, symptômes, examens et antécédents.",
        "Renforcement": "Consultez les propositions de force, stabilité et tolérance à la charge.",
        "Mobilité": "Explorez vos amplitudes, restrictions et exercices de mobilité.",
        "Sommeil": "Analysez durée, qualité, régularité et récupération nocturne.",
        "Nutrition": "Visualisez hydratation, énergie et recommandations nutritionnelles.",
        "Analyse IA": "Posez une question et obtenez une réponse contextualisée.",
        "Progression": "Suivez votre évolution et comparez les périodes.",
        "Laboratoire": "Simulez des scénarios et observez leurs effets probables.",
        "Objectifs": "Définissez et suivez vos objectifs de santé ou de performance.",
        "Entraînement": "Consultez votre charge, vos séances et la progression proposée."
    });

    // ████████████████████████████████████████████████████████████
    // 🟩 PARTIE B — B01 — RENDU DU CORPS
    // ████████████████████████████████████████████████████████████

    const bodyPointsContainer =
        document.getElementById("bodyPoints");

    function renderBodyPoints() {
        bodyPointsContainer.replaceChildren();

        BODY_POINTS.forEach((point, index) => {
            const circle = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "circle"
            );

            circle.setAttribute("cx", point.x);
            circle.setAttribute("cy", point.y);
            circle.setAttribute("r", index === 4 ? "7" : "5.5");
            circle.setAttribute(
                "fill",
                index === 4 ? "#b26cff" : "#54dfff"
            );
            circle.setAttribute("stroke", "#e7ffff");
            circle.setAttribute("stroke-width", "1.3");
            circle.dataset.pointId = point.id;

            circle.addEventListener(
                "click",
                () => {
                    openDialog(
                        "RÉGION CORPORELLE",
                        point.label,
                        "Cette zone sera reliée à son historique, ses douleurs, sa mobilité, sa force et ses examens."
                    );
                }
            );

            bodyPointsContainer.appendChild(circle);
        });
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — DIALOGUES
    // ████████████████████████████████████████████████████████████

    const dialog =
        document.getElementById("atlasDialog");

    const dialogKicker =
        document.getElementById("dialogKicker");

    const dialogTitle =
        document.getElementById("dialogTitle");

    const dialogText =
        document.getElementById("dialogText");

    function openDialog(kicker, title, text) {
        dialogKicker.textContent = kicker;
        dialogTitle.textContent = title;
        dialogText.textContent = text;
        dialog.showModal();
    }

    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — ÉVÉNEMENTS
    // ████████████████████████████████████████████████████████████

    function bindEvents() {
        document
            .querySelectorAll("[data-module]")
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        const moduleName =
                            button.dataset.module;

                        openDialog(
                            "MODULE ATLAS",
                            moduleName,
                            MODULE_TEXT[moduleName]
                        );
                    }
                );
            });

        document
            .querySelectorAll("[data-system]")
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        openDialog(
                            "SYSTÈME CORPOREL",
                            button.textContent.trim(),
                            "Ce système sera affiché comme une couche anatomique dédiée dans la prochaine phase."
                        );
                    }
                );
            });

        document
            .getElementById("askAtlasButton")
            .addEventListener(
                "click",
                () => {
                    openDialog(
                        "ATLAS AI",
                        "Que souhaitez-vous comprendre ?",
                        "Décrivez votre symptôme, votre objectif ou votre question."
                    );
                }
            );
    }

    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — DÉMARRAGE
    // ████████████████████████████████████████████████████████████

    function initialize() {
        renderBodyPoints();
        bindEvents();

        console.info(
            `Atlas Hub Body ${VERSION} chargé.`
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }

})();
