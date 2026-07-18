/* ==========================================================
   ATLAS OS V2
   PARTICULES D’ARRIÈRE-PLAN
   Fichier : js/particles.js
========================================================== */

"use strict";

(() => {

    /* ======================================================
       1. CONFIGURATION
    ====================================================== */

    const CONFIG = {

        density: 0.000075,

        minimumParticles: 46,

        maximumParticles: 150,

        connectionDistance: 125,

        pointerDistance: 165,

        baseSpeed: 0.16,

        maxDevicePixelRatio: 1.8,

        particleRadius: {

            min: 0.7,

            max: 2.1

        },

        opacity: {

            min: 0.18,

            max: 0.72

        }

    };


    /* ======================================================
       2. ÉTAT
    ====================================================== */

    const state = {

        canvas: null,

        context: null,

        particles: [],

        width: 0,

        height: 0,

        pixelRatio: 1,

        animationFrame: null,

        resizeTimeout: null,

        visible: true,

        reducedMotion: false,

        theme: "male",

        pointer: {

            x: 0,

            y: 0,

            active: false

        },

        colors: {

            primary: {

                r: 56,

                g: 189,

                b: 248

            },

            secondary: {

                r: 37,

                g: 99,

                b: 235

            },

            light: {

                r: 165,

                g: 243,

                b: 252

            }

        }

    };


    /* ======================================================
       3. PARTICULE
    ====================================================== */

    class Particle {

        constructor() {

            this.reset(true);

        }


        reset(initial = false) {

            this.x = Math.random() * state.width;

            this.y = initial
                ? Math.random() * state.height
                : state.height + 10;

            this.radius = randomBetween(

                CONFIG.particleRadius.min,

                CONFIG.particleRadius.max

            );

            this.opacity = randomBetween(

                CONFIG.opacity.min,

                CONFIG.opacity.max

            );

            this.baseOpacity = this.opacity;

            this.velocityX = randomBetween(
                -CONFIG.baseSpeed,
                CONFIG.baseSpeed
            );

            this.velocityY = randomBetween(
                -CONFIG.baseSpeed * 0.6,
                -CONFIG.baseSpeed * 1.8
            );

            this.drift = randomBetween(
                0.002,
                0.008
            );

            this.phase = Math.random() *
                Math.PI *
                2;

            this.colorType = Math.random();

            this.pulseSpeed = randomBetween(
                0.5,
                1.4
            );

        }


        update(time) {

            this.x += this.velocityX;

            this.y += this.velocityY;

            this.x += Math.sin(
                time * this.drift +
                this.phase
            ) * 0.08;

            this.opacity =
                this.baseOpacity +
                Math.sin(
                    time *
                    0.001 *
                    this.pulseSpeed +
                    this.phase
                ) * 0.08;

            if (this.y < -12) {

                this.reset(false);

                this.y = state.height + 12;

            }

            if (this.x < -15) {

                this.x = state.width + 15;

            }

            if (this.x > state.width + 15) {

                this.x = -15;

            }

            this.reactToPointer();

        }


        reactToPointer() {

            if (!state.pointer.active) {

                return;

            }

            const deltaX =
                this.x - state.pointer.x;

            const deltaY =
                this.y - state.pointer.y;

            const distanceSquared =
                deltaX * deltaX +
                deltaY * deltaY;

            const maximumDistanceSquared =
                CONFIG.pointerDistance *
                CONFIG.pointerDistance;

            if (
                distanceSquared === 0 ||
                distanceSquared >
                maximumDistanceSquared
            ) {

                return;

            }

            const distance =
                Math.sqrt(distanceSquared);

            const strength =
                (
                    1 -
                    distance /
                    CONFIG.pointerDistance
                ) * 0.06;

            this.x +=
                deltaX /
                distance *
                strength;

            this.y +=
                deltaY /
                distance *
                strength;

        }


        draw() {

            const context = state.context;

            if (!context) {

                return;

            }

            const color =
                getParticleColor(
                    this.colorType
                );

            const opacity = clamp(
                this.opacity,
                0.08,
                0.9
            );

            context.beginPath();

            context.arc(
                this.x,
                this.y,
                this.radius,
                0,
                Math.PI * 2
            );

            context.fillStyle =
                `rgba(${color.r}, ${color.g}, ${color.b}, ${opacity})`;

            context.shadowBlur =
                this.radius * 7;

            context.shadowColor =
                `rgba(${color.r}, ${color.g}, ${color.b}, ${opacity})`;

            context.fill();

        }

    }


    /* ======================================================
       4. INITIALISATION
    ====================================================== */

    function initializeParticles() {

        state.canvas =
            document.getElementById("particles");

        if (!state.canvas) {

            return;

        }

        state.context =
            state.canvas.getContext(
                "2d",
                {
                    alpha: true
                }
            );

        if (!state.context) {

            console.warn(
                "Atlas OS : le contexte 2D des particules est indisponible."
            );

            return;

        }

        state.reducedMotion =
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches;

        syncTheme();

        bindEvents();

        resizeCanvas();

        createParticles();

        if (state.reducedMotion) {

            drawStaticFrame();

        } else {

            animate(0);

        }

    }


    /* ======================================================
       5. CRÉATION DES PARTICULES
    ====================================================== */

    function createParticles() {

        const area =
            state.width *
            state.height;

        const particleCount =
            clamp(

                Math.round(
                    area *
                    CONFIG.density
                ),

                CONFIG.minimumParticles,

                CONFIG.maximumParticles

            );

        state.particles = Array.from(

            {
                length: particleCount
            },

            () => new Particle()

        );

    }


    /* ======================================================
       6. REDIMENSIONNEMENT
    ====================================================== */

    function resizeCanvas() {

        if (
            !state.canvas ||
            !state.context
        ) {

            return;

        }

        state.width =
            window.innerWidth;

        state.height =
            window.innerHeight;

        state.pixelRatio =
            Math.min(

                window.devicePixelRatio || 1,

                CONFIG.maxDevicePixelRatio

            );

        state.canvas.width =
            Math.round(
                state.width *
                state.pixelRatio
            );

        state.canvas.height =
            Math.round(
                state.height *
                state.pixelRatio
            );

        state.canvas.style.width =
            `${state.width}px`;

        state.canvas.style.height =
            `${state.height}px`;

        state.context.setTransform(

            state.pixelRatio,

            0,

            0,

            state.pixelRatio,

            0,

            0

        );

    }


    function handleResize() {

        if (state.resizeTimeout) {

            window.clearTimeout(
                state.resizeTimeout
            );

        }

        state.resizeTimeout =
            window.setTimeout(() => {

                resizeCanvas();

                createParticles();

                if (state.reducedMotion) {

                    drawStaticFrame();

                }

            }, 120);

    }


    /* ======================================================
       7. THÈME
    ====================================================== */

    function syncTheme() {

        const theme =
            document.body?.dataset
                ?.atlasTheme;

        setTheme(
            theme === "female"
                ? "female"
                : "male"
        );

    }


    function setTheme(theme) {

        state.theme =
            theme === "female"
                ? "female"
                : "male";

        if (state.theme === "female") {

            state.colors = {

                primary: {

                    r: 236,

                    g: 72,

                    b: 153

                },

                secondary: {

                    r: 139,

                    g: 92,

                    b: 246

                },

                light: {

                    r: 245,

                    g: 208,

                    b: 254

                }

            };

        } else {

            state.colors = {

                primary: {

                    r: 56,

                    g: 189,

                    b: 248

                },

                secondary: {

                    r: 37,

                    g: 99,

                    b: 235

                },

                light: {

                    r: 165,

                    g: 243,

                    b: 252

                }

            };

        }

        if (
            state.reducedMotion &&
            state.context
        ) {

            drawStaticFrame();

        }

    }


    function observeThemeChanges() {

        if (
            !document.body ||
            typeof MutationObserver ===
            "undefined"
        ) {

            return;

        }

        const observer =
            new MutationObserver(
                (mutations) => {

                    const themeChanged =
                        mutations.some(
                            (mutation) => {

                                return (
                                    mutation.type ===
                                    "attributes" &&
                                    mutation.attributeName ===
                                    "data-atlas-theme"
                                );

                            }
                        );

                    if (themeChanged) {

                        syncTheme();

                    }

                }
            );

        observer.observe(
            document.body,
            {
                attributes: true,
                attributeFilter: [
                    "data-atlas-theme"
                ]
            }
        );

    }


    /* ======================================================
       8. INTERACTION AVEC LE POINTEUR
    ====================================================== */

    function updatePointer(event) {

        state.pointer.x =
            event.clientX;

        state.pointer.y =
            event.clientY;

        state.pointer.active = true;

    }


    function disablePointer() {

        state.pointer.active = false;

    }


    /* ======================================================
       9. VISIBILITÉ DE LA PAGE
    ====================================================== */

    function handleVisibilityChange() {

        state.visible =
            !document.hidden;

        if (
            state.visible &&
            !state.animationFrame &&
            !state.reducedMotion
        ) {

            animate(
                performance.now()
            );

        }

    }


    /* ======================================================
       10. DESSIN
    ====================================================== */

    function clearCanvas() {

        if (!state.context) {

            return;

        }

        state.context.clearRect(

            0,

            0,

            state.width,

            state.height

        );

    }


    function drawParticles(time) {

        state.context.save();

        state.context.globalCompositeOperation =
            "lighter";

        state.particles.forEach(
            (particle) => {

                particle.update(time);

                particle.draw();

            }
        );

        state.context.restore();

    }


    function drawConnections() {

        const context = state.context;

        if (!context) {

            return;

        }

        const particles =
            state.particles;

        const maximumDistance =
            CONFIG.connectionDistance;

        const maximumDistanceSquared =
            maximumDistance *
            maximumDistance;

        context.save();

        context.lineWidth = 0.55;

        context.globalCompositeOperation =
            "lighter";

        for (
            let firstIndex = 0;
            firstIndex <
            particles.length;
            firstIndex += 1
        ) {

            const first =
                particles[firstIndex];

            for (
                let secondIndex =
                    firstIndex + 1;

                secondIndex <
                particles.length;

                secondIndex += 1
            ) {

                const second =
                    particles[secondIndex];

                const deltaX =
                    first.x - second.x;

                const deltaY =
                    first.y - second.y;

                const distanceSquared =
                    deltaX * deltaX +
                    deltaY * deltaY;

                if (
                    distanceSquared >
                    maximumDistanceSquared
                ) {

                    continue;

                }

                const distance =
                    Math.sqrt(
                        distanceSquared
                    );

                const opacity =
                    (
                        1 -
                        distance /
                        maximumDistance
                    ) * 0.085;

                const color =
                    first.colorType > 0.5
                        ? state.colors.primary
                        : state.colors.secondary;

                context.beginPath();

                context.moveTo(
                    first.x,
                    first.y
                );

                context.lineTo(
                    second.x,
                    second.y
                );

                context.strokeStyle =
                    `rgba(${color.r}, ${color.g}, ${color.b}, ${opacity})`;

                context.stroke();

            }

        }

        context.restore();

    }


    function drawPointerGlow() {

        if (
            !state.pointer.active ||
            !state.context
        ) {

            return;

        }

        const color =
            state.colors.primary;

        const gradient =
            state.context.createRadialGradient(

                state.pointer.x,

                state.pointer.y,

                0,

                state.pointer.x,

                state.pointer.y,

                CONFIG.pointerDistance

            );

        gradient.addColorStop(

            0,

            `rgba(${color.r}, ${color.g}, ${color.b}, 0.075)`

        );

        gradient.addColorStop(

            0.42,

            `rgba(${color.r}, ${color.g}, ${color.b}, 0.025)`

        );

        gradient.addColorStop(

            1,

            `rgba(${color.r}, ${color.g}, ${color.b}, 0)`

        );

        state.context.save();

        state.context.fillStyle =
            gradient;

        state.context.fillRect(

            state.pointer.x -
            CONFIG.pointerDistance,

            state.pointer.y -
            CONFIG.pointerDistance,

            CONFIG.pointerDistance * 2,

            CONFIG.pointerDistance * 2

        );

        state.context.restore();

    }


    function drawStaticFrame() {

        clearCanvas();

        state.particles.forEach(
            (particle) => {

                particle.draw();

            }
        );

        drawConnections();

    }


    /* ======================================================
       11. BOUCLE D’ANIMATION
    ====================================================== */

    function animate(time) {

        if (
            !state.visible ||
            state.reducedMotion
        ) {

            state.animationFrame = null;

            return;

        }

        state.animationFrame =
            window.requestAnimationFrame(
                animate
            );

        clearCanvas();

        drawPointerGlow();

        drawConnections();

        drawParticles(time);

    }


    /* ======================================================
       12. ÉVÉNEMENTS
    ====================================================== */

    function bindEvents() {

        window.addEventListener(
            "resize",
            handleResize
        );

        window.addEventListener(
            "pointermove",
            updatePointer,
            {
                passive: true
            }
        );

        document.addEventListener(
            "pointerleave",
            disablePointer
        );

        window.addEventListener(
            "blur",
            disablePointer
        );

        document.addEventListener(
            "visibilitychange",
            handleVisibilityChange
        );

        const motionQuery =
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            );

        motionQuery.addEventListener?.(
            "change",
            (event) => {

                state.reducedMotion =
                    event.matches;

                if (state.reducedMotion) {

                    if (state.animationFrame) {

                        window.cancelAnimationFrame(
                            state.animationFrame
                        );

                        state.animationFrame =
                            null;

                    }

                    drawStaticFrame();

                } else if (
                    !state.animationFrame
                ) {

                    animate(
                        performance.now()
                    );

                }

            }
        );

        observeThemeChanges();

    }


    /* ======================================================
       13. UTILITAIRES
    ====================================================== */

    function randomBetween(
        minimum,
        maximum
    ) {

        return (
            minimum +
            Math.random() *
            (
                maximum -
                minimum
            )
        );

    }


    function clamp(
        value,
        minimum,
        maximum
    ) {

        return Math.min(

            maximum,

            Math.max(
                minimum,
                value
            )

        );

    }


    function getParticleColor(
        colorType
    ) {

        if (colorType < 0.48) {

            return state.colors.primary;

        }

        if (colorType < 0.82) {

            return state.colors.secondary;

        }

        return state.colors.light;

    }


    /* ======================================================
       14. API PUBLIQUE
    ====================================================== */

    window.AtlasParticles = {

        setTheme,

        resize: handleResize,

        regenerate() {

            createParticles();

        },

        getState() {

            return {

                theme:
                    state.theme,

                particleCount:
                    state.particles.length,

                reducedMotion:
                    state.reducedMotion,

                visible:
                    state.visible

            };

        }

    };


    /* ======================================================
       15. DÉMARRAGE
    ====================================================== */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initializeParticles,
            {
                once: true
            }
        );

    } else {

        initializeParticles();

    }

})();
