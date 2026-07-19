/**
 * ==========================================================
 * ATLAS OS
 * Twin Storage
 * Version : 1.0.0
 * ==========================================================
 *
 * Rôle :
 * - créer le Digital Twin
 * - sauvegarder les données dans le navigateur
 * - lire et modifier les données
 * - créer une sauvegarde automatique
 * - importer et exporter le Twin en JSON
 * - notifier l'application lors d'une modification
 */

"use strict";

(function initializeAtlasTwinStorage(globalScope) {

    const STORAGE_VERSION = "1.0.0";

    const DEFAULT_STORAGE_KEY = "atlas.digital.twin";
    const DEFAULT_BACKUP_KEY = "atlas.digital.twin.backup";

    /**
     * Vérifie qu'une valeur est un objet JavaScript simple.
     */
    function isPlainObject(value) {

        return (
            value !== null &&
            typeof value === "object" &&
            !Array.isArray(value)
        );

    }

    /**
     * Crée une copie indépendante d'une valeur.
     */
    function clone(value) {

        if (value === undefined) {
            return undefined;
        }

        return JSON.parse(JSON.stringify(value));

    }

    /**
     * Fusionne deux objets.
     *
     * Les objets sont fusionnés récursivement.
     * Les tableaux sont remplacés.
     */
    function deepMerge(target, source) {

        const result = isPlainObject(target)
            ? clone(target)
            : {};

        Object.keys(source).forEach((key) => {

            const sourceValue = source[key];
            const targetValue = result[key];

            if (
                isPlainObject(sourceValue) &&
                isPlainObject(targetValue)
            ) {

                result[key] = deepMerge(
                    targetValue,
                    sourceValue
                );

            } else {

                result[key] = clone(sourceValue);

            }

        });

        return result;

    }

    class AtlasTwinStorage {

        /**
         * @param {Object} options
         */
        constructor(options = {}) {

            this.version = STORAGE_VERSION;

            this.storageKey =
                options.storageKey ||
                DEFAULT_STORAGE_KEY;

            this.backupKey =
                options.backupKey ||
                DEFAULT_BACKUP_KEY;

            this.debug =
                options.debug === true;

            this.listeners = new Set();

            this.memoryStorage = {};

        }

        /**
         * Affiche un message uniquement lorsque le mode debug est actif.
         */
        log(message, data = null) {

            if (!this.debug) {
                return;
            }

            if (data !== null) {

                console.log(
                    `[AtlasTwinStorage] ${message}`,
                    data
                );

            } else {

                console.log(
                    `[AtlasTwinStorage] ${message}`
                );

            }

        }

        /**
         * Vérifie si localStorage est disponible.
         */
        isAvailable() {

            try {

                const testKey = "__atlas_storage_test__";

                globalScope.localStorage.setItem(
                    testKey,
                    "available"
                );

                globalScope.localStorage.removeItem(
                    testKey
                );

                return true;

            } catch (error) {

                this.log(
                    "localStorage indisponible. Utilisation de la mémoire temporaire.",
                    error
                );

                return false;

            }

        }

        /**
         * Retourne la date actuelle au format ISO.
         */
        now() {

            return new Date().toISOString();

        }

        /**
         * Crée un Digital Twin vide.
         */
        createEmptyTwin() {

            const now = this.now();

            return {

                metadata: {

                    storageVersion: STORAGE_VERSION,

                    schemaVersion: 1,

                    revision: 0,

                    createdAt: now,

                    updatedAt: now

                },

                identity: {

                    displayName: null,

                    birthDate: null,

                    biologicalSex: null,

                    gender: null,

                    dominantSide: null,

                    heightCm: null,

                    weightKg: null

                },

                anatomy: {

                    bodyRegions: {},

                    structures: {},

                    limitations: []

                },

                function: {

                    mobility: {},

                    strength: {},

                    pain: [],

                    fatigue: null,

                    recovery: null,

                    sleep: {},

                    heart: {}

                },

                lifestyle: {

                    activityLevel: null,

                    sleepHabits: {},

                    nutrition: {},

                    hydration: {},

                    stress: null,

                    smoking: null,

                    alcohol: null

                },

                profession: {

                    current: null,

                    previous: [],

                    exposures: [],

                    schedule: null,

                    physicalLoad: null

                },

                performance: {

                    running: {

                        level: null,

                        vma: null,

                        vo2max: null,

                        criticalSpeed: null,

                        heartRateZones: {},

                        personalBests: {},

                        weeklyVolumeKm: null,

                        trainingHistory: [],

                        currentLoad: {},

                        readiness: {},

                        activePlanId: null

                    }

                },

                medical: {

                    conditions: [],

                    injuries: [],

                    surgeries: [],

                    consultations: [],

                    examinations: [],

                    treatments: [],

                    medications: []

                },

                prevention: {

                    risks: [],

                    alerts: [],

                    recommendations: []

                },

                context: {

                    location: {},

                    weather: {},

                    environment: {},

                    altitude: {},

                    terrain: {},

                    availability: {},

                    professionalLoad: {}

                },

                devices: [],

                goals: [],

                plans: [],

                events: [],

                observations: [],

                knowledge: [],

                settings: {

                    language: "fr",

                    units: "metric",

                    privacy: {}

                }

            };

        }

        /**
         * Lit une valeur brute dans le stockage.
         */
        readRaw(key) {

            if (this.isAvailable()) {

                return globalScope.localStorage.getItem(key);

            }

            return Object.prototype.hasOwnProperty.call(
                this.memoryStorage,
                key
            )
                ? this.memoryStorage[key]
                : null;

        }

        /**
         * Écrit une valeur brute dans le stockage.
         */
        writeRaw(key, value) {

            if (this.isAvailable()) {

                globalScope.localStorage.setItem(
                    key,
                    value
                );

                return true;

            }

            this.memoryStorage[key] = value;

            return true;

        }

        /**
         * Supprime une valeur du stockage.
         */
        removeRaw(key) {

            if (this.isAvailable()) {

                globalScope.localStorage.removeItem(key);

                return;

            }

            delete this.memoryStorage[key];

        }

        /**
         * Charge le Digital Twin.
         */
        load() {

            const json = this.readRaw(
                this.storageKey
            );

            if (!json) {

                return this.createEmptyTwin();

            }

            try {

                const twin = JSON.parse(json);

                return this.normalizeTwin(twin);

            } catch (error) {

                console.error(
                    "Atlas n'a pas pu lire le Digital Twin.",
                    error
                );

                const restored = this.restoreBackup();

                if (restored) {

                    return restored;

                }

                return this.createEmptyTwin();

            }

        }

        /**
         * Complète les anciennes données avec le schéma actuel.
         */
        normalizeTwin(twin) {

            if (!isPlainObject(twin)) {

                return this.createEmptyTwin();

            }

            const emptyTwin =
                this.createEmptyTwin();

            const normalized =
                deepMerge(emptyTwin, twin);

            if (
                !normalized.metadata.createdAt
            ) {

                normalized.metadata.createdAt =
                    this.now();

            }

            normalized.metadata.storageVersion =
                STORAGE_VERSION;

            normalized.metadata.schemaVersion = 1;

            return normalized;

        }

        /**
         * Sauvegarde le Digital Twin complet.
         */
        save(twin, options = {}) {

            if (!isPlainObject(twin)) {

                throw new Error(
                    "Le Digital Twin doit être un objet JavaScript."
                );

            }

            const existingJson =
                this.readRaw(this.storageKey);

            if (
                existingJson &&
                options.createBackup !== false
            ) {

                this.writeRaw(
                    this.backupKey,
                    existingJson
                );

            }

            const normalized =
                this.normalizeTwin(twin);

            const currentRevision =
                Number(
                    normalized.metadata.revision
                ) || 0;

            normalized.metadata.revision =
                currentRevision + 1;

            normalized.metadata.updatedAt =
                this.now();

            this.writeRaw(
                this.storageKey,
                JSON.stringify(normalized)
            );

            this.notify({

                type: "save",

                revision:
                    normalized.metadata.revision,

                updatedAt:
                    normalized.metadata.updatedAt,

                reason:
                    options.reason || "manual"

            });

            return clone(normalized);

        }

        /**
         * Lit une donnée grâce à un chemin.
         *
         * Exemple :
         * storage.get("performance.running.vma")
         */
        get(path = null, defaultValue = null) {

            const twin = this.load();

            if (!path) {

                return clone(twin);

            }

            if (typeof path !== "string") {

                throw new Error(
                    "Le chemin doit être une chaîne de caractères."
                );

            }

            const keys = path.split(".");

            let current = twin;

            for (const key of keys) {

                if (
                    current === null ||
                    current === undefined ||
                    !Object.prototype.hasOwnProperty.call(
                        current,
                        key
                    )
                ) {

                    return clone(defaultValue);

                }

                current = current[key];

            }

            return clone(current);

        }

        /**
         * Modifie une donnée grâce à un chemin.
         *
         * Exemple :
         * storage.set(
         *   "identity.displayName",
         *   "Christophe"
         * );
         */
        set(path, value) {

            if (
                typeof path !== "string" ||
                path.trim() === ""
            ) {

                throw new Error(
                    "Un chemin valide est obligatoire."
                );

            }

            const twin = this.load();

            const keys = path.split(".");

            let current = twin;

            for (
                let index = 0;
                index < keys.length - 1;
                index += 1
            ) {

                const key = keys[index];

                if (!isPlainObject(current[key])) {

                    current[key] = {};

                }

                current = current[key];

            }

            const finalKey =
                keys[keys.length - 1];

            current[finalKey] =
                clone(value);

            return this.save(twin, {

                reason: `set:${path}`

            });

        }

        /**
         * Fusionne plusieurs données dans le Twin.
         */
        update(data) {

            if (!isPlainObject(data)) {

                throw new Error(
                    "Les données à fusionner doivent être un objet."
                );

            }

            const twin = this.load();

            const updatedTwin =
                deepMerge(twin, data);

            return this.save(updatedTwin, {

                reason: "update"

            });

        }

        /**
         * Supprime une propriété.
         */
        remove(path) {

            if (
                typeof path !== "string" ||
                path.trim() === ""
            ) {

                throw new Error(
                    "Un chemin valide est obligatoire."
                );

            }

            const twin = this.load();

            const keys = path.split(".");

            let current = twin;

            for (
                let index = 0;
                index < keys.length - 1;
                index += 1
            ) {

                const key = keys[index];

                if (!isPlainObject(current[key])) {

                    return clone(twin);

                }

                current = current[key];

            }

            const finalKey =
                keys[keys.length - 1];

            delete current[finalKey];

            return this.save(twin, {

                reason: `remove:${path}`

            });

        }

        /**
         * Ajoute un élément dans un tableau du Twin.
         *
         * Exemple :
         * storage.push("events", event)
         */
        push(path, value) {

            const currentValue =
                this.get(path, []);

            if (!Array.isArray(currentValue)) {

                throw new Error(
                    `La propriété "${path}" n'est pas un tableau.`
                );

            }

            currentValue.push(
                clone(value)
            );

            return this.set(
                path,
                currentValue
            );

        }

        /**
         * Crée une sauvegarde manuelle.
         */
        createBackup() {

            const json =
                this.readRaw(this.storageKey);

            if (!json) {

                return false;

            }

            this.writeRaw(
                this.backupKey,
                json
            );

            this.notify({

                type: "backup",

                updatedAt: this.now()

            });

            return true;

        }

        /**
         * Restaure la dernière sauvegarde.
         */
        restoreBackup() {

            const backupJson =
                this.readRaw(this.backupKey);

            if (!backupJson) {

                return null;

            }

            try {

                const backupTwin =
                    JSON.parse(backupJson);

                const normalized =
                    this.normalizeTwin(backupTwin);

                this.writeRaw(
                    this.storageKey,
                    JSON.stringify(normalized)
                );

                this.notify({

                    type: "restore",

                    updatedAt: this.now()

                });

                return clone(normalized);

            } catch (error) {

                console.error(
                    "Atlas n'a pas pu restaurer la sauvegarde.",
                    error
                );

                return null;

            }

        }

        /**
         * Exporte le Digital Twin en JSON.
         */
        exportJSON(pretty = true) {

            const twin = this.load();

            return JSON.stringify(
                twin,
                null,
                pretty ? 2 : 0
            );

        }

        /**
         * Télécharge le Digital Twin.
         */
        downloadJSON(
            filename = "atlas-digital-twin.json"
        ) {

            const json =
                this.exportJSON(true);

            const blob = new Blob(
                [json],
                {
                    type:
                        "application/json;charset=utf-8"
                }
            );

            const url =
                URL.createObjectURL(blob);

            const link =
                document.createElement("a");

            link.href = url;

            link.download = filename;

            document.body.appendChild(link);

            link.click();

            document.body.removeChild(link);

            URL.revokeObjectURL(url);

        }

        /**
         * Importe un Digital Twin depuis un objet ou du JSON.
         */
        importJSON(input, options = {}) {

            let importedTwin = input;

            if (typeof input === "string") {

                try {

                    importedTwin =
                        JSON.parse(input);

                } catch (error) {

                    throw new Error(
                        "Le fichier JSON Atlas est invalide."
                    );

                }

            }

            if (!isPlainObject(importedTwin)) {

                throw new Error(
                    "Les données importées doivent être un objet."
                );

            }

            if (options.merge === true) {

                return this.update(
                    importedTwin
                );

            }

            return this.save(
                importedTwin,
                {
                    reason: "import"
                }
            );

        }

        /**
         * Efface le Twin principal.
         */
        clear(options = {}) {

            this.removeRaw(
                this.storageKey
            );

            if (
                options.keepBackup !== true
            ) {

                this.removeRaw(
                    this.backupKey
                );

            }

            this.notify({

                type: "clear",

                updatedAt: this.now()

            });

            return this.createEmptyTwin();

        }

        /**
         * Réinitialise le Twin avec une structure vide.
         */
        reset() {

            const emptyTwin =
                this.createEmptyTwin();

            return this.save(
                emptyTwin,
                {
                    reason: "reset"
                }
            );

        }

        /**
         * Retourne un diagnostic du stockage.
         */
        diagnose() {

            const twinJson =
                this.readRaw(this.storageKey);

            const backupJson =
                this.readRaw(this.backupKey);

            let valid = true;
            let error = null;
            let revision = null;

            if (twinJson) {

                try {

                    const twin =
                        JSON.parse(twinJson);

                    revision =
                        twin.metadata?.revision ??
                        null;

                } catch (caughtError) {

                    valid = false;

                    error =
                        caughtError.message;

                }

            }

            return {

                module:
                    "AtlasTwinStorage",

                version:
                    STORAGE_VERSION,

                storageKey:
                    this.storageKey,

                backupKey:
                    this.backupKey,

                localStorageAvailable:
                    this.isAvailable(),

                twinExists:
                    twinJson !== null,

                backupExists:
                    backupJson !== null,

                valid,

                error,

                revision,

                twinSize:
                    twinJson
                        ? twinJson.length
                        : 0,

                backupSize:
                    backupJson
                        ? backupJson.length
                        : 0

            };

        }

        /**
         * Écoute les modifications.
         *
         * Retourne une fonction permettant d'arrêter l'écoute.
         */
        subscribe(callback) {

            if (typeof callback !== "function") {

                throw new Error(
                    "Le listener doit être une fonction."
                );

            }

            this.listeners.add(callback);

            return () => {

                this.listeners.delete(
                    callback
                );

            };

        }

        /**
         * Informe les listeners qu'une modification a eu lieu.
         */
        notify(event) {

            const detail = {

                module:
                    "AtlasTwinStorage",

                ...event

            };

            this.listeners.forEach(
                (listener) => {

                    try {

                        listener(detail);

                    } catch (error) {

                        console.error(
                            "Erreur dans un listener Atlas.",
                            error
                        );

                    }

                }
            );

            if (
                typeof globalScope.dispatchEvent ===
                    "function" &&
                typeof globalScope.CustomEvent ===
                    "function"
            ) {

                globalScope.dispatchEvent(

                    new CustomEvent(
                        "atlasstoragechange",
                        {
                            detail
                        }
                    )

                );

            }

        }

    }

    AtlasTwinStorage.VERSION =
        STORAGE_VERSION;

    globalScope.AtlasTwinStorage =
        AtlasTwinStorage;

})(
    typeof window !== "undefined"
        ? window
        : globalThis
);
