// ╔════════════════════════════════════════════════════════════════╗
// ║                           ATLAS OS                             ║
// ╠════════════════════════════════════════════════════════════════╣
// ║ Fichier : prototype/js/atlas-cockpit.js                       ║
// ║ Module  : Atlas Cockpit Prototype                             ║
// ║ Cycle   : Genesis                                             ║
// ║ Version : 0.4.0                                               ║
// ║ Statut  : Prototype interactif                                ║
// ╚════════════════════════════════════════════════════════════════╝

"use strict";

(() => {

    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION DES MODULES
    // ████████████████████████████████████████████████████████████

    const VERSION = "0.4.0";

    const MODULE_CONTENT = Object.freeze({
        "Santé": {
            text:
                "Accédez à l'historique clinique, aux symptômes, aux examens et aux zones corporelles suivies."
        },

        "Entraînement": {
            text:
                "Atlas organise la charge, l'intensité et la récupération en fonction de votre capacité d'adaptation."
        },

        "Renforcement": {
            text:
                "Retrouvez les exercices destinés à améliorer la force, la stabilité et la tolérance mécanique."
        },

        "Mobilité": {
            text:
                "Explorez les amplitudes articulaires utiles, les restrictions suivies et les routines proposées."
        },

        "Sommeil": {
            text:
                "Visualisez la durée, la qualité, la régularité et l'influence du sommeil sur votre récupération."
        },

        "Nutrition": {
            text:
                "Suivez les fondamentaux liés à l'énergie, l'hydratation et la récupération nutritionnelle."
        },

        "Chronologie": {
            text:
                "Parcourez les événements de vie, les blessures, les changements professionnels et les périodes d'entraînement."
        },

        "Progression": {
            text:
                "Comparez les indicateurs actuels à leur évolution récente et à vos objectifs."
        },

        "Confiance": {
            text:
                "Cet indice indique la solidité des informations utilisées par Atlas pour formuler ses interprétations."
        },

        "Prévention": {
            text:
                "Atlas hiérarchise les actions susceptibles d'améliorer votre tolérance à la charge."
        }
    });

    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟩 PARTIE B — B01 — ÉLÉMENTS DE L'INTERFACE
    // ████████████████████████████████████████████████████████████

    const elements = {
        dialog:
            document.getElementById("atlasDialog"),

        dialogKicker:
            document.getElementById("dialogKicker"),

        dialogTitle:
            document.getElementById("dialogTitle"),

        dialogText:
            document.getElementById("dialogText"),

        dialogPrimaryButton:
            document.getElementById(
                "dialogPrimaryButton"
            ),

        askAtlasButton:
            document.getElementById(
                "askAtlasButton"
            ),

        interactiveRegions:
            Array.from(
                document.querySelectorAll(
                    "[data-region]"
                )
            ),

        moduleButtons:
            Array.from(
                document.querySelectorAll(
                    "[data-module]"
                )
            )
    };

    // ████████████████████████████████████████████████████████████
    // 🟩 FIN PARTIE B — B01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — AFFICHAGE DES MODULES
    // ████████████████████████████████████████████████████████████

    function openModule(moduleName) {
        const content =
            MODULE_CONTENT[moduleName] || {
                text:
                    "Ce module sera relié progressivement au Digital Twin."
            };

        showDialog({
            kicker: "MODULE ATLAS",
            title: moduleName,
            text: content.text,
            actionLabel: "Explorer ce module"
        });
    }

    function openBodyRegion(regionName) {
        showDialog({
            kicker: "RÉGION CORPORELLE",
            title: regionName,
            text:
                "Cette région pourra afficher son historique, les douleurs déclarées, la mobilité, la force, les examens et les recommandations associées.",
            actionLabel: "Voir l'historique"
        });
    }

    function openAtlasConversation() {
        showDialog({
            kicker: "ATLAS AI",
            title: "Que souhaitez-vous comprendre ?",
            text:
                "Dans la prochaine étape, cette zone deviendra un dialogue relié aux données du Digital Twin, au contexte humain et au raisonnement clinique.",
            actionLabel: "Commencer une question"
        });
    }

    function showDialog({
        kicker,
        title,
        text,
        actionLabel
    }) {
        if (!elements.dialog) {
            return;
        }

        elements.dialogKicker.textContent =
            kicker;

        elements.dialogTitle.textContent =
            title;

        elements.dialogText.textContent =
            text;

        elements.dialogPrimaryButton.textContent =
            actionLabel;

        elements.dialog.showModal();
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 FIN PARTIE C — C01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — ÉVÉNEMENTS
    // ████████████████████████████████████████████████████████████

    function bindEvents() {
        elements.moduleButtons.forEach(
            (button) => {
                button.addEventListener(
                    "click",
                    () => {
                        openModule(
                            button.dataset.module
                        );
                    }
                );
            }
        );

        elements.interactiveRegions.forEach(
            (region) => {
                region.addEventListener(
                    "click",
                    () => {
                        openBodyRegion(
                            region.dataset.region
                        );
                    }
                );
            }
        );

        elements.askAtlasButton
            ?.addEventListener(
                "click",
                openAtlasConversation
            );

        elements.dialogPrimaryButton
            ?.addEventListener(
                "click",
                () => {
                    elements.dialog?.close();
                }
            );
    }

    // ████████████████████████████████████████████████████████████
    // 🟧 FIN PARTIE D — D01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — DÉMARRAGE ET API PUBLIQUE
    // ████████████████████████████████████████████████████████████

    function initialize() {
        bindEvents();

        console.info(
            `Atlas Cockpit Prototype ${VERSION} chargé.`
        );
    }

    window.AtlasCockpitPrototype =
        Object.freeze({
            VERSION,
            openModule,
            openBodyRegion,
            openAtlasConversation
        });

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

    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████

})();
