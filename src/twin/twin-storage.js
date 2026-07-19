
/**
 * ==========================================================
 * ATLAS OS
 * Twin Storage
 * Version : 1.0.0
 * ==========================================================
 */

"use strict";

class AtlasTwinStorage {

    constructor() {

        this.version = "1.0.0";

        this.storageKey = "atlas.digital.twin";

        this.backupKey = "atlas.digital.twin.backup";

        this.listeners = [];

    }

    /**
     * Vérifie la disponibilité du localStorage
     */

    isAvailable() {

        try {

            const key = "__atlas_test__";

            localStorage.setItem(key, key);

            localStorage.removeItem(key);

            return true;

        }

        catch (e) {

            console.error("LocalStorage indisponible.");

            return false;

        }

    }

    /**
     * Crée un Digital Twin vide
     */

    createEmptyTwin() {

        return {

            metadata: {

                version: 1,

                createdAt: new Date().toISOString(),

                updatedAt: new Date().toISOString()

            },

            identity: {},

            anatomy: {},

            function: {},

            lifestyle: {},

            profession: {},

            performance: {},

            medical: {},

            prevention: {},

            context: {},

            devices: {},

            goals: [],

            events: [],

            observations: [],

            knowledge: []

        };

    }

    /**
     * Retourne le Twin
     */

    load() {

        if (!this.isAvailable()) {

            return this.createEmptyTwin();

        }

        const json = localStorage.getItem(this.storageKey);

        if (!json) {

            return this.createEmptyTwin();

        }

        try {

            return JSON.parse(json);

        }

        catch (e) {

            console.error("Erreur lecture Twin.");

            return this.createEmptyTwin();

        }

    }

    /**
     * Sauvegarde complète
     */

    save(twin) {

        if (!this.isAvailable()) {

            return false;

        }

        twin.metadata.updatedAt = new Date().toISOString();

        localStorage.setItem(

            this.storageKey,

            JSON.stringify(twin)

        );

        this.notify();

        return true;

    }
    notify() {

        this.listeners.forEach(listener => {

            listener();

        });

    }

    subscribe(callback) {

        this.listeners.push(callback);

    }

}

window.AtlasTwinStorage = AtlasTwinStorage;
