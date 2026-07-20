// ╔════════════════════════════════════════════════════════════════╗
// ║                           ATLAS OS                             ║
// ╠════════════════════════════════════════════════════════════════╣
// ║ Fichier : src/twin/atlas-twin.js                              ║
// ║ Module  : Digital Twin Engine                                 ║
// ║ Cycle   : Genesis                                             ║
// ║ Version : 0.2.0                                               ║
// ║ Statut  : Développement                                       ║
// ╚════════════════════════════════════════════════════════════════╝

"use strict";

(() => {

    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A01 — CONFIGURATION GÉNÉRALE
    // ████████████████████████████████████████████████████████████

    const VERSION = "0.2.0";

    const EVENT_TYPES = Object.freeze([
        "general",
        "health",
        "injury",
        "surgery",
        "sport",
        "profession",
        "environment",
        "goal"
    ]);

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

    function nowIso() {
        return new Date().toISOString();
    }

    // ████████████████████████████████████████████████████████████
    // 🟦 FIN PARTIE A — A01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟦 PARTIE A — A02 — STRUCTURE DU DIGITAL TWIN
    // ████████████████████████████████████████████████████████████

    function createEmptyTwin() {
        const timestamp = nowIso();

        return {
            meta: {
                id: createIdentifier(),
                version: VERSION,
                createdAt: timestamp,
                updatedAt: timestamp
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
    // 🟦 FIN PARTIE A — A02
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟩 PARTIE B — B01 — INITIALISATION ET COPIE
    // ████████████████████████████████████████████████████████████

    function cloneValue(value) {
        if (typeof structuredClone === "function") {
            return structuredClone(value);
        }

        return JSON.parse(JSON.stringify(value));
    }

    function mergeTwin(baseTwin, initialData) {
        const source = (
            initialData &&
            typeof initialData === "object" &&
            !Array.isArray(initialData)
        )
            ? initialData
            : {};

        return {
            ...baseTwin,
            ...cloneValue(source),

            meta: {
                ...baseTwin.meta,
                ...(source.meta || {}),
                version: VERSION,
                updatedAt: nowIso()
            },

            identity: {
                ...baseTwin.identity,
                ...(source.identity || {})
            },

            body: {
                ...baseTwin.body,
                ...(source.body || {})
            },

            activity: {
                ...baseTwin.activity,
                ...(source.activity || {})
            },

            context: {
                ...baseTwin.context,
                ...(source.context || {})
            },

            intelligence: {
                ...baseTwin.intelligence,
                ...(source.intelligence || {})
            },

            timeline: Array.isArray(source.timeline)
                ? cloneValue(source.timeline)
                : []
        };
    }

    function create(initialData = null) {
        return mergeTwin(
            createEmptyTwin(),
            initialData
        );
    }

    // ████████████████████████████████████████████████████████████
    // 🟩 FIN PARTIE B — B01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C01 — IDENTITÉ
    // ████████████████████████████████████████████████████████████

    function updateIdentity(twin, changes) {
        assertValidTwin(twin);

        if (
            !changes ||
            typeof changes !== "object" ||
            Array.isArray(changes)
        ) {
            throw new TypeError(
                "Atlas Twin : modifications d'identité invalides."
            );
        }

        twin.identity = {
            ...twin.identity,
            ...cloneValue(changes)
        };

        touch(twin);

        return cloneValue(twin.identity);
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 FIN PARTIE C — C01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟨 PARTIE C — C02 — ÉVÉNEMENTS DE VIE
    // ████████████████████████████████████████████████████████████

    function addTimelineEvent(twin, event) {
        assertValidTwin(twin);

        if (
            !event ||
            typeof event !== "object" ||
            Array.isArray(event)
        ) {
            throw new TypeError(
                "Atlas Twin : événement invalide."
            );
        }

        const requestedType = String(
            event.type || "general"
        );

        const normalizedEvent = {
            id: createIdentifier(),
            date: event.date || nowIso(),
            type: EVENT_TYPES.includes(requestedType)
                ? requestedType
                : "general",
            title: String(
                event.title || "Événement"
            ).trim(),
            description: String(
                event.description || ""
            ).trim(),
            source: String(
                event.source || "manual"
            ).trim()
        };

        twin.timeline.push(normalizedEvent);

        twin.timeline.sort((first, second) => {
            return (
                new Date(first.date).getTime() -
                new Date(second.date).getTime()
            );
        });

        touch(twin);

        return cloneValue(normalizedEvent);
    }

    function removeTimelineEvent(twin, eventId) {
        assertValidTwin(twin);

        const index = twin.timeline.findIndex(
            (event) => event.id === eventId
        );

        if (index < 0) {
            return false;
        }

        twin.timeline.splice(index, 1);
        touch(twin);

        return true;
    }

    function getTimeline(twin, options = {}) {
        assertValidTwin(twin);

        const requestedType = options.type || null;

        const events = requestedType
            ? twin.timeline.filter(
                (event) => event.type === requestedType
            )
            : twin.timeline;

        return cloneValue(events);
    }

    // ████████████████████████████████████████████████████████████
    // 🟨 FIN PARTIE C — C02
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟧 PARTIE D — D01 — SYNTHÈSE DU JUMEAU
    // ████████████████████████████████████████████████████████████

    function getSummary(twin) {
        assertValidTwin(twin);

        return {
            id: twin.meta.id,
            version: twin.meta.version,
            displayName: [
                twin.identity.firstName,
                twin.identity.lastName
            ]
                .filter(Boolean)
                .join(" ")
                .trim() || "Utilisateur Atlas",
            eventCount: twin.timeline.length,
            injuryCount: twin.body.injuries.length,
            surgeryCount: twin.body.surgeries.length,
            sportCount: twin.activity.sports.length,
            goalCount: twin.activity.goals.length,
            updatedAt: twin.meta.updatedAt
        };
    }

    // ████████████████████████████████████████████████████████████
    // 🟧 FIN PARTIE D — D01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // 🟥 PARTIE F — F01 — VALIDATION ET SÉCURITÉ
    // ████████████████████████████████████████████████████████████

    function isValid(twin) {
        return Boolean(
            twin &&
            typeof twin === "object" &&
            !Array.isArray(twin) &&
            twin.meta &&
            typeof twin.meta.id === "string" &&
            twin.identity &&
            twin.body &&
            twin.activity &&
            twin.context &&
            twin.intelligence &&
            Array.isArray(twin.timeline)
        );
    }

    function assertValidTwin(twin) {
        if (!isValid(twin)) {
            throw new TypeError(
                "Atlas Twin : jumeau invalide."
            );
        }
    }

    function touch(twin) {
        twin.meta.version = VERSION;
        twin.meta.updatedAt = nowIso();
    }

    // ████████████████████████████████████████████████████████████
    // 🟥 FIN PARTIE F — F01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G01 — IMPORT ET EXPORT
    // ████████████████████████████████████████████████████████████

    function exportJson(twin, spacing = 2) {
        assertValidTwin(twin);

        return JSON.stringify(
            twin,
            null,
            spacing
        );
    }

    function importJson(jsonText) {
        if (typeof jsonText !== "string") {
            throw new TypeError(
                "Atlas Twin : le contenu importé doit être du texte JSON."
            );
        }

        const parsed = JSON.parse(jsonText);
        const twin = create(parsed);

        assertValidTwin(twin);

        return twin;
    }

    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G01
    // ████████████████████████████████████████████████████████████


    // ████████████████████████████████████████████████████████████
    // ⬜ PARTIE G — G02 — API PUBLIQUE
    // ████████████████████████████████████████████████████████████

    window.AtlasTwin = Object.freeze({
        VERSION,
        EVENT_TYPES,
        create,
        createEmpty: createEmptyTwin,
        updateIdentity,
        addTimelineEvent,
        removeTimelineEvent,
        getTimeline,
        getSummary,
        exportJson,
        importJson,
        isValid
    });

    console.info(
        `Atlas Twin Engine ${VERSION} chargé.`
    );

    // ████████████████████████████████████████████████████████████
    // ⬜ FIN PARTIE G — G02
    // ████████████████████████████████████████████████████████████

})();
