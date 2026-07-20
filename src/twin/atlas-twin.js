// ╔════════════════════════════════════════════════════════════════╗
// ║                           ATLAS OS                             ║
// ╠════════════════════════════════════════════════════════════════╣
// ║ Fichier : src/twin/atlas-twin.js                              ║
// ║ Module  : Digital Twin Engine                                 ║
// ║ Cycle   : Genesis                                             ║
// ║ Version : 0.1.0                                               ║
// ║ Statut  : Fondation                                           ║
// ╚════════════════════════════════════════════════════════════════╝

"use strict";

(() => {

    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION ET STRUCTURE DU JUMEAU
    // ████████████████████████████████████████████████████████████

    const ATLAS_TWIN_VERSION = "0.1.0";

    function createIdentifier() {
        if (
            window.crypto &&
            typeof window.crypto.randomUUID === "function"
        ) {
            return window.crypto.randomUUID();
        }

        return [
            "atlas",
            Date.now(),
            Math.random().toString(16).slice(2)
        ].join("-");
    }

    function createEmptyTwin() {
        const now = new Date().toISOString();

        return {
            meta: {
                id: createIdentifier(),
                version: ATLAS_TWIN_VERSION,
                createdAt: now,
                updatedAt: now
            },

            identity: {
                firstName: "",
                lastName: "",
                birthDate: "",
                sex: "",
                heightCm: null,
                weightKg: null,
                laterality: "",
                currentProfession: "",
                pastProfessions: []
            },

            body: {
                mobility: [],
                strength: [],
                painAreas: [],
                injuries: [],
                surgeries: []
            },

            activity: {
                sports: [],
                goals: [],
                devices: []
            },

            context: {
                sleep: [],
                stress: [],
                nutrition: [],
                environment: []
            },

            timeline: [],

            intelligence: {
                observations: [],
                hypotheses: [],
                confidenceIndex: null
            }
        };
    }

    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟩 PARTIE B — B01 — INITIALISATION
    // ████████████████████████████████████████████████████████████

    function initializeTwin(initialData = null) {
        const twin = createEmptyTwin();

        if (
            initialData &&
            typeof initialData === "object" &&
            !Array.isArray(initialData)
        ) {
            return {
                ...twin,
                ...initialData,
                meta: {
                    ...twin.meta,
                    ...(initialData.meta || {}),
                    updatedAt: new Date().toISOString()
                }
            };
        }

        return twin;
    }

    // ████████████████████████████████████████████████████████████
    // 🟩 FIN PARTIE B — B01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — ÉVÉNEMENTS DE VIE
    // ████████████████████████████████████████████████████████████

    function addTimelineEvent(twin, event) {
        if (!isValidTwin(twin)) {
            throw new TypeError("Atlas Twin : jumeau invalide.");
        }

        if (!event || typeof event !== "object") {
            throw new TypeError("Atlas Twin : événement invalide.");
        }

        const normalizedEvent = {
            id: createIdentifier(),
            date: event.date || new Date().toISOString(),
            type: String(event.type || "general"),
            title: String(event.title || "Événement"),
            description: String(event.description || ""),
            source: String(event.source || "manual")
        };

        twin.timeline.push(normalizedEvent);
        twin.meta.updatedAt = new Date().toISOString();

        return normalizedEvent;
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 FIN PARTIE C — C01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟥 PARTIE F — F01 — VALIDATION
    // ████████████████████████████████████████████████████████████

    function isValidTwin(twin) {
        return Boolean(
            twin &&
            typeof twin === "object" &&
            !Array.isArray(twin) &&
            twin.meta &&
            typeof twin.meta.id === "string" &&
            Array.isArray(twin.timeline)
        );
    }

    // ████████████████████████████████████████████████████████████
    // 🟥 FIN PARTIE F — F01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — API PUBLIQUE
    // ████████████████████████████████████████████████████████████

    window.AtlasTwin = Object.freeze({
        VERSION: ATLAS_TWIN_VERSION,
        create: initializeTwin,
        createEmpty: createEmptyTwin,
        addTimelineEvent,
        isValid: isValidTwin
    });

    console.info(
        `Atlas Twin Engine ${ATLAS_TWIN_VERSION} chargé.`
    );

    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████

})();
