/* ==========================================================
   ATLAS OS V2
   JUMEAU BIOMÉCANIQUE 3D
   Fichier : js/body3d.js
========================================================== */

"use strict";

(() => {

    /* ======================================================
       1. CONFIGURATION
    ====================================================== */

    const CONFIG = {

        colors: {

            male: {

                primary: 0x38bdf8,

                secondary: 0x2563eb,

                light: 0xa5f3fc,

                dark: 0x031321,

                muscle: 0xff365f,

                bone: 0xe8f4ff,

                risk: 0xff355e

            },

            female: {

                primary: 0xec4899,

                secondary: 0x8b5cf6,

                light: 0xf5d0fe,

                dark: 0x19091b,

                muscle: 0xff416c,

                bone: 0xf7ecff,

                risk: 0xffcc33

            }

        },

        intro: {

            cameraZ: 8.6,

            cameraY: 0.05,

            autoRotationSpeed: 0.0032,

            bodyScale: 1.05

        },

        dashboard: {

            cameraZ: 8.2,

            cameraY: 0.05,

            autoRotationSpeed: 0.0016,

            bodyScale: 1.13

        },

        interaction: {

            rotationSpeed: 0.006,

            zoomSpeed: 0.008,

            minZoom: 5.4,

            maxZoom: 11.5,

            damping: 0.88

        }

    };


    /* ======================================================
       2. ÉTAT GLOBAL
    ====================================================== */

    const state = {

        theme: "male",

        currentLayer: "skin",

        activeMode: null,

        renderer: null,

        scene: null,

        camera: null,

        container: null,

        bodyRoot: null,

        bodyGroups: {

            skin: null,

            muscles: null,

            skeleton: null,

            risks: null,

            energy: null

        },

        animationFrame: null,

        resizeObserver: null,

        clock: null,

        isDragging: false,

        previousPointer: {

            x: 0,

            y: 0

        },

        rotationVelocity: {

            x: 0,

            y: 0

        },

        targetCameraZ: 8,

        autoRotationEnabled: true,

        pointerInside: false,

        initializedContainers: new WeakSet()

    };


    /* ======================================================
       3. UTILITAIRES
    ====================================================== */

    function getThemeColors() {

        return CONFIG.colors[state.theme] ||
            CONFIG.colors.male;

    }


    function disposeMaterial(material) {

        if (!material) {

            return;

        }

        if (Array.isArray(material)) {

            material.forEach(disposeMaterial);

            return;

        }

        Object.keys(material).forEach((key) => {

            const value = material[key];

            if (
                value &&
                typeof value === "object" &&
                typeof value.dispose === "function"
            ) {

                value.dispose();

            }

        });

        material.dispose?.();

    }


    function disposeObject(object) {

        if (!object) {

            return;

        }

        object.traverse((child) => {

            if (child.geometry) {

                child.geometry.dispose();

            }

            if (child.material) {

                disposeMaterial(child.material);

            }

        });

    }


    function removePlaceholder(container) {

        const placeholders = container.querySelectorAll(
            ".viewer-placeholder, .body-placeholder"
        );

        placeholders.forEach((placeholder) => {

            placeholder.remove();

        });

    }


    function createMaterial(options = {}) {

        return new THREE.MeshPhysicalMaterial({

            color: options.color ?? 0xffffff,

            transparent:
                options.transparent ?? true,

            opacity:
                options.opacity ?? 1,

            roughness:
                options.roughness ?? 0.25,

            metalness:
                options.metalness ?? 0.1,

            transmission:
                options.transmission ?? 0,

            thickness:
                options.thickness ?? 0.5,

            clearcoat:
                options.clearcoat ?? 0.2,

            clearcoatRoughness:
                options.clearcoatRoughness ?? 0.2,

            emissive:
                options.emissive ?? 0x000000,

            emissiveIntensity:
                options.emissiveIntensity ?? 0,

            side:
                options.side ?? THREE.FrontSide,

            depthWrite:
                options.depthWrite ?? true

        });

    }


    function createGlowMaterial(
        color,
        opacity = 0.7
    ) {

        return new THREE.MeshBasicMaterial({

            color,

            transparent: true,

            opacity,

            blending: THREE.AdditiveBlending,

            depthWrite: false,

            side: THREE.DoubleSide

        });

    }


    function createSphere(
        radius,
        material,
        segments = 32
    ) {

        return new THREE.Mesh(

            new THREE.SphereGeometry(
                radius,
                segments,
                Math.max(16, segments / 2)
            ),

            material

        );

    }


    function createCapsule(
        radius,
        length,
        material,
        radialSegments = 20,
        capSegments = 10
    ) {

        if (THREE.CapsuleGeometry) {

            return new THREE.Mesh(

                new THREE.CapsuleGeometry(
                    radius,
                    length,
                    capSegments,
                    radialSegments
                ),

                material

            );

        }

        return new THREE.Mesh(

            new THREE.CylinderGeometry(
                radius,
                radius,
                length + radius * 2,
                radialSegments
            ),

            material

        );

    }


    function createCylinderBetween(
        start,
        end,
        radius,
        material,
        segments = 16
    ) {

        const direction = new THREE.Vector3()
            .subVectors(end, start);

        const length = direction.length();

        const geometry = new THREE.CylinderGeometry(
            radius,
            radius,
            length,
            segments
        );

        const mesh = new THREE.Mesh(
            geometry,
            material
        );

        const midpoint = new THREE.Vector3()
            .addVectors(start, end)
            .multiplyScalar(0.5);

        mesh.position.copy(midpoint);

        mesh.quaternion.setFromUnitVectors(

            new THREE.Vector3(0, 1, 0),

            direction.clone().normalize()

        );

        return mesh;

    }


    function addMesh(
        group,
        mesh,
        position,
        scale = null,
        rotation = null
    ) {

        mesh.position.set(
            position.x,
            position.y,
            position.z
        );

        if (scale) {

            mesh.scale.set(
                scale.x,
                scale.y,
                scale.z
            );

        }

        if (rotation) {

            mesh.rotation.set(
                rotation.x,
                rotation.y,
                rotation.z
            );

        }

        group.add(mesh);

        return mesh;

    }


    /* ======================================================
       4. NETTOYAGE
    ====================================================== */

    function destroyCurrentScene() {

        if (state.animationFrame) {

            cancelAnimationFrame(
                state.animationFrame
            );

            state.animationFrame = null;

        }

        if (state.resizeObserver) {

            state.resizeObserver.disconnect();

            state.resizeObserver = null;

        }

        if (
            state.renderer &&
            state.container
        ) {

            state.renderer.domElement.remove();

        }

        if (state.scene) {

            disposeObject(state.scene);

        }

        state.renderer?.dispose();

        state.renderer = null;

        state.scene = null;

        state.camera = null;

        state.bodyRoot = null;

        state.container = null;

        state.clock = null;

        state.bodyGroups = {

            skin: null,

            muscles: null,

            skeleton: null,

            risks: null,

            energy: null

        };

    }


    /* ======================================================
       5. INITIALISATION DU MOTEUR
    ====================================================== */

    function initialize(
        containerId,
        mode
    ) {

        if (typeof THREE === "undefined") {

            console.error(
                "Atlas OS : Three.js n’est pas chargé."
            );

            return;

        }

        const container =
            document.getElementById(containerId);

        if (!container) {

            console.warn(
                `Atlas OS : conteneur 3D introuvable : ${containerId}`
            );

            return;

        }

        if (
            state.container === container &&
            state.renderer
        ) {

            state.activeMode = mode;

            resize();

            return;

        }

        destroyCurrentScene();

        state.container = container;

        state.activeMode = mode;

        state.currentLayer = "skin";

        state.autoRotationEnabled = true;

        removePlaceholder(container);

        createScene();

        createCamera();

        createRenderer();

        createLights();

        createEnvironment();

        createBiomechanicalTwin();

        configureCamera();

        bindInteractionEvents();

        observeContainer();

        resize();

        animate();

        state.initializedContainers.add(container);

    }


    function createScene() {

        state.scene = new THREE.Scene();

        state.scene.fog = new THREE.FogExp2(
            0x020713,
            0.045
        );

        state.clock = new THREE.Clock();

    }


    function createCamera() {

        state.camera = new THREE.PerspectiveCamera(
            38,
            1,
            0.1,
            100
        );

        state.scene.add(
            state.camera
        );

    }


    function createRenderer() {

        state.renderer =
            new THREE.WebGLRenderer({

                antialias: true,

                alpha: true,

                powerPreference:
                    "high-performance"

            });

        state.renderer.setPixelRatio(

            Math.min(
                window.devicePixelRatio || 1,
                2
            )

        );

        state.renderer.setClearColor(
            0x000000,
            0
        );

        state.renderer.outputColorSpace =
            THREE.SRGBColorSpace;

        state.renderer.toneMapping =
            THREE.ACESFilmicToneMapping;

        state.renderer.toneMappingExposure =
            1.15;

        state.renderer.shadowMap.enabled = true;

        state.renderer.shadowMap.type =
            THREE.PCFSoftShadowMap;

        state.renderer.domElement.setAttribute(
            "aria-hidden",
            "true"
        );

        state.renderer.domElement.style.touchAction =
            "none";

        state.container.appendChild(
            state.renderer.domElement
        );

    }


    function createLights() {

        const colors = getThemeColors();

        const ambientLight =
            new THREE.HemisphereLight(

                colors.light,

                0x020713,

                1.8

            );

        state.scene.add(
            ambientLight
        );

        const keyLight =
            new THREE.DirectionalLight(

                colors.primary,

                3.4

            );

        keyLight.position.set(
            4,
            6,
            6
        );

        keyLight.castShadow = true;

        keyLight.shadow.mapSize.set(
            1024,
            1024
        );

        state.scene.add(
            keyLight
        );

        const fillLight =
            new THREE.PointLight(

                colors.secondary,

                55,

                15,

                2

            );

        fillLight.position.set(
            -4,
            1,
            3
        );

        state.scene.add(
            fillLight
        );

        const backLight =
            new THREE.PointLight(

                colors.light,

                38,

                14,

                2

            );

        backLight.position.set(
            1,
            4,
            -5
        );

        state.scene.add(
            backLight
        );

        const lowerLight =
            new THREE.PointLight(

                colors.primary,

                28,

                12,

                2

            );

        lowerLight.position.set(
            0,
            -4,
            2
        );

        state.scene.add(
            lowerLight
        );

    }


    /* ======================================================
       6. ENVIRONNEMENT FUTURISTE
    ====================================================== */

    function createEnvironment() {

        const colors = getThemeColors();

        const environmentGroup =
            new THREE.Group();

        environmentGroup.name =
            "atlas-environment";

        const floorMaterial =
            new THREE.MeshBasicMaterial({

                color: colors.primary,

                transparent: true,

                opacity: 0.11,

                blending:
                    THREE.AdditiveBlending,

                depthWrite: false

            });

        const floorGeometry =
            new THREE.RingGeometry(
                1.8,
                3.05,
                96
            );

        const floor =
            new THREE.Mesh(
                floorGeometry,
                floorMaterial
            );

        floor.rotation.x =
            -Math.PI / 2;

        floor.position.y = -3.5;

        environmentGroup.add(floor);

        for (
            let index = 0;
            index < 4;
            index += 1
        ) {

            const ringGeometry =
                new THREE.TorusGeometry(

                    2.25 + index * 0.47,

                    0.008,

                    8,

                    96

                );

            const ring =
                new THREE.Mesh(

                    ringGeometry,

                    createGlowMaterial(
                        index % 2 === 0
                            ? colors.primary
                            : colors.secondary,
                        0.18 - index * 0.025
                    )

                );

            ring.rotation.x =
                Math.PI / 2;

            ring.position.y =
                -3.47 + index * 0.015;

            environmentGroup.add(ring);

        }

        const verticalRing =
            new THREE.Mesh(

                new THREE.TorusGeometry(
                    3.35,
                    0.012,
                    8,
                    128
                ),

                createGlowMaterial(
                    colors.primary,
                    0.13
                )

            );

        verticalRing.rotation.y =
            Math.PI / 2;

        verticalRing.position.y =
            0.1;

        environmentGroup.add(
            verticalRing
        );

        const secondVerticalRing =
            verticalRing.clone();

        secondVerticalRing.material =
            createGlowMaterial(
                colors.secondary,
                0.09
            );

        secondVerticalRing.rotation.y =
            0;

        environmentGroup.add(
            secondVerticalRing
        );

        createParticleField(
            environmentGroup,
            colors
        );

        state.scene.add(
            environmentGroup
        );

    }


    function createParticleField(
        group,
        colors
    ) {

        const particleCount =
            state.activeMode === "intro"
                ? 170
                : 120;

        const positions =
            new Float32Array(
                particleCount * 3
            );

        for (
            let index = 0;
            index < particleCount;
            index += 1
        ) {

            const radius =
                2.4 +
                Math.random() * 3.4;

            const angle =
                Math.random() *
                Math.PI *
                2;

            const height =
                -3.2 +
                Math.random() * 7;

            positions[index * 3] =
                Math.cos(angle) *
                radius;

            positions[index * 3 + 1] =
                height;

            positions[index * 3 + 2] =
                Math.sin(angle) *
                radius;

        }

        const geometry =
            new THREE.BufferGeometry();

        geometry.setAttribute(

            "position",

            new THREE.BufferAttribute(
                positions,
                3
            )

        );

        const material =
            new THREE.PointsMaterial({

                color: colors.light,

                size: 0.025,

                transparent: true,

                opacity: 0.48,

                blending:
                    THREE.AdditiveBlending,

                depthWrite: false

            });

        const particles =
            new THREE.Points(
                geometry,
                material
            );

        particles.name =
            "atlas-particles-3d";

        group.add(particles);

    }


    /* ======================================================
       7. CONSTRUCTION DU JUMEAU
    ====================================================== */

    function createBiomechanicalTwin() {

        state.bodyRoot =
            new THREE.Group();

        state.bodyRoot.name =
            "atlas-biomechanical-twin";

        state.scene.add(
            state.bodyRoot
        );

        state.bodyGroups.skin =
            new THREE.Group();

        state.bodyGroups.muscles =
            new THREE.Group();

        state.bodyGroups.skeleton =
            new THREE.Group();

        state.bodyGroups.risks =
            new THREE.Group();

        state.bodyGroups.energy =
            new THREE.Group();

        state.bodyGroups.skin.name =
            "skin-layer";

        state.bodyGroups.muscles.name =
            "muscle-layer";

        state.bodyGroups.skeleton.name =
            "skeleton-layer";

        state.bodyGroups.risks.name =
            "risk-layer";

        state.bodyGroups.energy.name =
            "energy-layer";

        state.bodyRoot.add(

            state.bodyGroups.skin,

            state.bodyGroups.muscles,

            state.bodyGroups.skeleton,

            state.bodyGroups.risks,

            state.bodyGroups.energy

        );

        createSkinLayer();

        createMuscleLayer();

        createSkeletonLayer();

        createRiskLayer();

        createEnergyLayer();

        applyLayerVisibility();

        const modeConfig =
            state.activeMode === "intro"
                ? CONFIG.intro
                : CONFIG.dashboard;

        state.bodyRoot.scale.setScalar(
            modeConfig.bodyScale
        );

        state.bodyRoot.position.y =
            -0.05;

    }


    /* ======================================================
       8. COUCHE PEAU
    ====================================================== */

    function createSkinLayer() {

        const group =
            state.bodyGroups.skin;

        const colors =
            getThemeColors();

        const skinMaterial =
            createMaterial({

                color: colors.primary,

                transparent: true,

                opacity: 0.32,

                roughness: 0.2,

                metalness: 0.05,

                transmission: 0.28,

                thickness: 1,

                clearcoat: 0.8,

                emissive: colors.primary,

                emissiveIntensity: 0.08,

                side: THREE.DoubleSide

            });

        const shellMaterial =
            createMaterial({

                color: colors.light,

                transparent: true,

                opacity: 0.08,

                roughness: 0.1,

                transmission: 0.35,

                thickness: 0.8,

                side: THREE.DoubleSide

            });

        createHead(
            group,
            skinMaterial,
            shellMaterial
        );

        createTorso(
            group,
            skinMaterial
        );

        createPelvis(
            group,
            skinMaterial
        );

        createArms(
            group,
            skinMaterial
        );

        createLegs(
            group,
            skinMaterial
        );

        createBodyOutline(
            group,
            colors
        );

    }


    function createHead(
        group,
        material,
        shellMaterial
    ) {

        const head =
            createSphere(
                0.47,
                material,
                38
            );

        addMesh(
            group,
            head,
            {
                x: 0,
                y: 3.02,
                z: 0
            },
            {
                x: 0.88,
                y: 1.08,
                z: 0.94
            }
        );

        const shell =
            createSphere(
                0.5,
                shellMaterial,
                38
            );

        addMesh(
            group,
            shell,
            {
                x: 0,
                y: 3.02,
                z: 0
            },
            {
                x: 0.9,
                y: 1.1,
                z: 0.96
            }
        );

        const neck =
            createCapsule(
                0.2,
                0.35,
                material
            );

        addMesh(
            group,
            neck,
            {
                x: 0,
                y: 2.48,
                z: 0
            }
        );

    }


    function createTorso(
        group,
        material
    ) {

        const upperTorso =
            createCapsule(
                0.72,
                1.16,
                material,
                28,
                14
            );

        addMesh(
            group,
            upperTorso,
            {
                x: 0,
                y: 1.55,
                z: 0
            },
            {
                x: state.theme === "female"
                    ? 0.9
                    : 1.04,

                y: 1,

                z: 0.58
            }
        );

        const chest =
            createSphere(
                0.76,
                material,
                36
            );

        addMesh(
            group,
            chest,
            {
                x: 0,
                y: 1.95,
                z: 0
            },
            {
                x: state.theme === "female"
                    ? 0.92
                    : 1.12,

                y: 0.7,

                z: 0.62
            }
        );

        const abdomen =
            createCapsule(
                0.48,
                0.78,
                material,
                24,
                12
            );

        addMesh(
            group,
            abdomen,
            {
                x: 0,
                y: 0.62,
                z: 0
            },
            {
                x: 0.92,
                y: 1,
                z: 0.72
            }
        );

    }


    function createPelvis(
        group,
        material
    ) {

        const pelvis =
            createSphere(
                0.65,
                material,
                32
            );

        addMesh(
            group,
            pelvis,
            {
                x: 0,
                y: -0.13,
                z: 0
            },
            {
                x: state.theme === "female"
                    ? 1.12
                    : 1,

                y: 0.58,

                z: 0.72
            }
        );

    }


    function createArms(
        group,
        material
    ) {

        const shoulderY = 2.05;

        [
            -1,
            1
        ].forEach((side) => {

            const shoulder =
                createSphere(
                    0.3,
                    material,
                    26
                );

            addMesh(
                group,
                shoulder,
                {
                    x: side * 0.93,
                    y: shoulderY,
                    z: 0
                },
                {
                    x: 1,
                    y: 1,
                    z: 0.9
                }
            );

            const upperArm =
                createCapsule(
                    0.21,
                    0.92,
                    material
                );

            addMesh(
                group,
                upperArm,
                {
                    x: side * 1.12,
                    y: 1.35,
                    z: 0
                },
                {
                    x: 0.95,
                    y: 1,
                    z: 0.9
                },
                {
                    x: 0,
                    y: 0,
                    z: side * -0.13
                }
            );

            const elbow =
                createSphere(
                    0.205,
                    material,
                    24
                );

            addMesh(
                group,
                elbow,
                {
                    x: side * 1.23,
                    y: 0.73,
                    z: 0
                }
            );

            const forearm =
                createCapsule(
                    0.17,
                    0.91,
                    material
                );

            addMesh(
                group,
                forearm,
                {
                    x: side * 1.27,
                    y: 0.05,
                    z: 0
                },
                {
                    x: 0.88,
                    y: 1,
                    z: 0.82
                },
                {
                    x: 0,
                    y: 0,
                    z: side * -0.04
                }
            );

            const hand =
                createCapsule(
                    0.14,
                    0.3,
                    material
                );

            addMesh(
                group,
                hand,
                {
                    x: side * 1.3,
                    y: -0.6,
                    z: 0
                },
                {
                    x: 0.8,
                    y: 1,
                    z: 0.65
                }
            );

        });

    }


    function createLegs(
        group,
        material
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const hip =
                createSphere(
                    0.31,
                    material,
                    28
                );

            addMesh(
                group,
                hip,
                {
                    x: side * 0.37,
                    y: -0.42,
                    z: 0
                }
            );

            const thigh =
                createCapsule(
                    0.28,
                    1.25,
                    material,
                    22,
                    12
                );

            addMesh(
                group,
                thigh,
                {
                    x: side * 0.39,
                    y: -1.18,
                    z: 0
                },
                {
                    x: 0.95,
                    y: 1,
                    z: 0.9
                },
                {
                    x: 0,
                    y: 0,
                    z: side * 0.015
                }
            );

            const knee =
                createSphere(
                    0.255,
                    material,
                    26
                );

            addMesh(
                group,
                knee,
                {
                    x: side * 0.4,
                    y: -2.02,
                    z: 0.02
                }
            );

            const lowerLeg =
                createCapsule(
                    0.205,
                    1.18,
                    material,
                    22,
                    12
                );

            addMesh(
                group,
                lowerLeg,
                {
                    x: side * 0.4,
                    y: -2.77,
                    z: 0
                },
                {
                    x: 0.93,
                    y: 1,
                    z: 0.86
                }
            );

            const foot =
                createCapsule(
                    0.18,
                    0.43,
                    material
                );

            addMesh(
                group,
                foot,
                {
                    x: side * 0.4,
                    y: -3.49,
                    z: 0.19
                },
                {
                    x: 0.9,
                    y: 0.8,
                    z: 1.45
                },
                {
                    x: Math.PI / 2,
                    y: 0,
                    z: 0
                }
            );

        });

    }


    function createBodyOutline(
        group,
        colors
    ) {

        const outlineMaterial =
            createGlowMaterial(
                colors.light,
                0.17
            );

        const outlinePoints = [

            new THREE.Vector3(
                0,
                3.5,
                0
            ),

            new THREE.Vector3(
                0,
                2.46,
                0
            ),

            new THREE.Vector3(
                0,
                1.65,
                0
            ),

            new THREE.Vector3(
                0,
                0.7,
                0
            ),

            new THREE.Vector3(
                0,
                -0.2,
                0
            ),

            new THREE.Vector3(
                0,
                -1.1,
                0
            ),

            new THREE.Vector3(
                0,
                -2.1,
                0
            ),

            new THREE.Vector3(
                0,
                -3.5,
                0
            )

        ];

        const curve =
            new THREE.CatmullRomCurve3(
                outlinePoints
            );

        const tube =
            new THREE.Mesh(

                new THREE.TubeGeometry(
                    curve,
                    64,
                    0.018,
                    8,
                    false
                ),

                outlineMaterial

            );

        group.add(tube);

    }


    /* ======================================================
       9. COUCHE MUSCULAIRE
    ====================================================== */

    function createMuscleLayer() {

        const group =
            state.bodyGroups.muscles;

        const colors =
            getThemeColors();

        const muscleMaterial =
            createMaterial({

                color: colors.muscle,

                opacity: 0.82,

                roughness: 0.38,

                metalness: 0.05,

                clearcoat: 0.3,

                emissive: colors.muscle,

                emissiveIntensity: 0.12

            });

        const tendonMaterial =
            createMaterial({

                color: 0xffb2c3,

                opacity: 0.72,

                roughness: 0.5,

                emissive: colors.muscle,

                emissiveIntensity: 0.04

            });

        createChestMuscles(
            group,
            muscleMaterial
        );

        createAbdominalMuscles(
            group,
            muscleMaterial
        );

        createArmMuscles(
            group,
            muscleMaterial,
            tendonMaterial
        );

        createLegMuscles(
            group,
            muscleMaterial,
            tendonMaterial
        );

        createBackMuscles(
            group,
            muscleMaterial
        );

    }


    function createChestMuscles(
        group,
        material
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const chestMuscle =
                createSphere(
                    0.43,
                    material,
                    28
                );

            addMesh(
                group,
                chestMuscle,
                {
                    x: side * 0.31,
                    y: 1.9,
                    z: 0.28
                },
                {
                    x: 1.15,
                    y: 0.58,
                    z: 0.37
                },
                {
                    x: 0,
                    y: side * 0.05,
                    z: side * -0.06
                }
            );

            const shoulder =
                createSphere(
                    0.3,
                    material,
                    26
                );

            addMesh(
                group,
                shoulder,
                {
                    x: side * 0.91,
                    y: 2.02,
                    z: 0
                },
                {
                    x: 1,
                    y: 0.9,
                    z: 0.9
                }
            );

        });

    }


    function createAbdominalMuscles(
        group,
        material
    ) {

        const positions = [

            1.25,
            0.88,
            0.5,
            0.12

        ];

        positions.forEach((y) => {

            [
                -1,
                1
            ].forEach((side) => {

                const abdominal =
                    createSphere(
                        0.19,
                        material,
                        22
                    );

                addMesh(
                    group,
                    abdominal,
                    {
                        x: side * 0.19,
                        y,
                        z: 0.32
                    },
                    {
                        x: 0.95,
                        y: 0.66,
                        z: 0.36
                    }
                );

            });

        });

        [
            -1,
            1
        ].forEach((side) => {

            const oblique =
                createCapsule(
                    0.13,
                    0.72,
                    material
                );

            addMesh(
                group,
                oblique,
                {
                    x: side * 0.43,
                    y: 0.61,
                    z: 0.12
                },
                {
                    x: 0.8,
                    y: 1,
                    z: 0.55
                },
                {
                    x: 0,
                    y: 0,
                    z: side * -0.18
                }
            );

        });

    }


    function createArmMuscles(
        group,
        material,
        tendonMaterial
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const biceps =
                createCapsule(
                    0.15,
                    0.61,
                    material
                );

            addMesh(
                group,
                biceps,
                {
                    x: side * 1.12,
                    y: 1.37,
                    z: 0.18
                },
                {
                    x: 1,
                    y: 1,
                    z: 0.72
                },
                {
                    x: 0,
                    y: 0,
                    z: side * -0.13
                }
            );

            const triceps =
                createCapsule(
                    0.14,
                    0.62,
                    material
                );

            addMesh(
                group,
                triceps,
                {
                    x: side * 1.12,
                    y: 1.34,
                    z: -0.16
                },
                {
                    x: 0.9,
                    y: 1,
                    z: 0.7
                },
                {
                    x: 0,
                    y: 0,
                    z: side * -0.13
                }
            );

            const forearm =
                createCapsule(
                    0.125,
                    0.72,
                    material
                );

            addMesh(
                group,
                forearm,
                {
                    x: side * 1.27,
                    y: 0.05,
                    z: 0.06
                },
                {
                    x: 0.9,
                    y: 1,
                    z: 0.73
                }
            );

            const wristTendon =
                createCapsule(
                    0.055,
                    0.27,
                    tendonMaterial
                );

            addMesh(
                group,
                wristTendon,
                {
                    x: side * 1.3,
                    y: -0.48,
                    z: 0.08
                }
            );

        });

    }


    function createLegMuscles(
        group,
        material,
        tendonMaterial
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const quadriceps =
                createCapsule(
                    0.22,
                    0.91,
                    material,
                    20,
                    10
                );

            addMesh(
                group,
                quadriceps,
                {
                    x: side * 0.39,
                    y: -1.16,
                    z: 0.16
                },
                {
                    x: 1,
                    y: 1,
                    z: 0.7
                }
            );

            const hamstring =
                createCapsule(
                    0.19,
                    0.9,
                    material,
                    20,
                    10
                );

            addMesh(
                group,
                hamstring,
                {
                    x: side * 0.39,
                    y: -1.17,
                    z: -0.15
                },
                {
                    x: 0.95,
                    y: 1,
                    z: 0.68
                }
            );

            const calf =
                createCapsule(
                    0.17,
                    0.75,
                    material
                );

            addMesh(
                group,
                calf,
                {
                    x: side * 0.4,
                    y: -2.72,
                    z: -0.09
                },
                {
                    x: 1,
                    y: 1,
                    z: 0.75
                }
            );

            const shin =
                createCapsule(
                    0.095,
                    0.75,
                    tendonMaterial
                );

            addMesh(
                group,
                shin,
                {
                    x: side * 0.4,
                    y: -2.73,
                    z: 0.16
                },
                {
                    x: 0.85,
                    y: 1,
                    z: 0.7
                }
            );

        });

    }


    function createBackMuscles(
        group,
        material
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const latissimus =
                createCapsule(
                    0.2,
                    0.82,
                    material
                );

            addMesh(
                group,
                latissimus,
                {
                    x: side * 0.39,
                    y: 1.14,
                    z: -0.28
                },
                {
                    x: 1.15,
                    y: 1,
                    z: 0.48
                },
                {
                    x: 0,
                    y: 0,
                    z: side * 0.1
                }
            );

        });

    }


    /* ======================================================
       10. COUCHE SQUELETTE
    ====================================================== */

    function createSkeletonLayer() {

        const group =
            state.bodyGroups.skeleton;

        const colors =
            getThemeColors();

        const boneMaterial =
            createMaterial({

                color: colors.bone,

                opacity: 0.92,

                roughness: 0.56,

                metalness: 0.03,

                emissive: colors.light,

                emissiveIntensity: 0.045

            });

        const jointMaterial =
            createMaterial({

                color: colors.light,

                opacity: 0.88,

                roughness: 0.35,

                emissive: colors.primary,

                emissiveIntensity: 0.14

            });

        createSkull(
            group,
            boneMaterial
        );

        createSpine(
            group,
            boneMaterial,
            jointMaterial
        );

        createRibCage(
            group,
            boneMaterial
        );

        createPelvisBones(
            group,
            boneMaterial
        );

        createArmBones(
            group,
            boneMaterial,
            jointMaterial
        );

        createLegBones(
            group,
            boneMaterial,
            jointMaterial
        );

    }


    function createSkull(
        group,
        material
    ) {

        const skull =
            createSphere(
                0.38,
                material,
                30
            );

        addMesh(
            group,
            skull,
            {
                x: 0,
                y: 3.03,
                z: 0
            },
            {
                x: 0.86,
                y: 1.06,
                z: 0.9
            }
        );

        const jaw =
            createCapsule(
                0.13,
                0.25,
                material
            );

        addMesh(
            group,
            jaw,
            {
                x: 0,
                y: 2.71,
                z: 0.08
            },
            {
                x: 1.4,
                y: 0.8,
                z: 0.8
            }
        );

    }


    function createSpine(
        group,
        boneMaterial,
        jointMaterial
    ) {

        const vertebraCount = 24;

        for (
            let index = 0;
            index < vertebraCount;
            index += 1
        ) {

            const ratio =
                index /
                (vertebraCount - 1);

            const y =
                2.53 -
                ratio * 2.65;

            const curve =
                Math.sin(
                    ratio * Math.PI * 1.8
                ) * 0.065;

            const vertebra =
                createSphere(
                    0.09 +
                    ratio * 0.015,
                    index % 3 === 0
                        ? jointMaterial
                        : boneMaterial,
                    18
                );

            addMesh(
                group,
                vertebra,
                {
                    x: 0,
                    y,
                    z: -0.06 + curve
                },
                {
                    x: 1.18,
                    y: 0.52,
                    z: 0.86
                }
            );

        }

        const spinalCord =
            createCylinderBetween(

                new THREE.Vector3(
                    0,
                    2.53,
                    -0.06
                ),

                new THREE.Vector3(
                    0,
                    -0.12,
                    -0.06
                ),

                0.025,

                jointMaterial,

                10

            );

        group.add(spinalCord);

    }


    function createRibCage(
        group,
        material
    ) {

        const ribLevels = 9;

        for (
            let index = 0;
            index < ribLevels;
            index += 1
        ) {

            const ratio =
                index /
                (ribLevels - 1);

            const y =
                2.13 -
                ratio * 1.28;

            const width =
                0.73 -
                Math.abs(
                    ratio - 0.42
                ) * 0.38;

            const depth =
                0.37 -
                ratio * 0.08;

            const ribGeometry =
                new THREE.TorusGeometry(

                    Math.max(
                        0.3,
                        width
                    ),

                    0.025,

                    8,

                    48,

                    Math.PI * 1.65

                );

            const rib =
                new THREE.Mesh(
                    ribGeometry,
                    material
                );

            rib.position.set(
                0,
                y,
                -0.03
            );

            rib.scale.z =
                depth / width;

            rib.rotation.z =
                Math.PI * 0.675;

            group.add(rib);

        }

        const sternum =
            createCapsule(
                0.045,
                1.13,
                material
            );

        addMesh(
            group,
            sternum,
            {
                x: 0,
                y: 1.48,
                z: 0.32
            }
        );

        const leftClavicle =
            createCylinderBetween(

                new THREE.Vector3(
                    -0.04,
                    2.26,
                    0.16
                ),

                new THREE.Vector3(
                    -0.82,
                    2.12,
                    0.03
                ),

                0.04,

                material

            );

        const rightClavicle =
            createCylinderBetween(

                new THREE.Vector3(
                    0.04,
                    2.26,
                    0.16
                ),

                new THREE.Vector3(
                    0.82,
                    2.12,
                    0.03
                ),

                0.04,

                material

            );

        group.add(
            leftClavicle,
            rightClavicle
        );

    }


    function createPelvisBones(
        group,
        material
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const pelvisBone =
                new THREE.Mesh(

                    new THREE.TorusGeometry(
                        0.36,
                        0.07,
                        10,
                        40,
                        Math.PI * 1.6
                    ),

                    material

                );

            pelvisBone.position.set(
                side * 0.27,
                -0.1,
                0
            );

            pelvisBone.scale.set(
                1,
                0.85,
                0.72
            );

            pelvisBone.rotation.set(
                Math.PI / 2,
                side * 0.18,
                side > 0
                    ? -0.64
                    : 0.64
            );

            group.add(pelvisBone);

        });

        const sacrum =
            createCapsule(
                0.12,
                0.35,
                material
            );

        addMesh(
            group,
            sacrum,
            {
                x: 0,
                y: -0.14,
                z: -0.08
            }
        );

    }


    function createArmBones(
        group,
        boneMaterial,
        jointMaterial
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const shoulder =
                createSphere(
                    0.11,
                    jointMaterial,
                    20
                );

            addMesh(
                group,
                shoulder,
                {
                    x: side * 0.91,
                    y: 2.02,
                    z: 0
                }
            );

            const upperArm =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 0.91,
                        2.02,
                        0
                    ),

                    new THREE.Vector3(
                        side * 1.23,
                        0.73,
                        0
                    ),

                    0.055,

                    boneMaterial

                );

            group.add(upperArm);

            const elbow =
                createSphere(
                    0.105,
                    jointMaterial,
                    20
                );

            addMesh(
                group,
                elbow,
                {
                    x: side * 1.23,
                    y: 0.73,
                    z: 0
                }
            );

            const radiusBone =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 1.18,
                        0.63,
                        0.045
                    ),

                    new THREE.Vector3(
                        side * 1.27,
                        -0.51,
                        0.055
                    ),

                    0.033,

                    boneMaterial

                );

            const ulnaBone =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 1.27,
                        0.63,
                        -0.04
                    ),

                    new THREE.Vector3(
                        side * 1.34,
                        -0.51,
                        -0.035
                    ),

                    0.032,

                    boneMaterial

                );

            group.add(
                radiusBone,
                ulnaBone
            );

            const wrist =
                createSphere(
                    0.075,
                    jointMaterial,
                    18
                );

            addMesh(
                group,
                wrist,
                {
                    x: side * 1.3,
                    y: -0.54,
                    z: 0
                }
            );

        });

    }


    function createLegBones(
        group,
        boneMaterial,
        jointMaterial
    ) {

        [
            -1,
            1
        ].forEach((side) => {

            const hip =
                createSphere(
                    0.125,
                    jointMaterial,
                    20
                );

            addMesh(
                group,
                hip,
                {
                    x: side * 0.37,
                    y: -0.42,
                    z: 0
                }
            );

            const femur =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 0.37,
                        -0.42,
                        0
                    ),

                    new THREE.Vector3(
                        side * 0.4,
                        -2.02,
                        0
                    ),

                    0.065,

                    boneMaterial

                );

            group.add(femur);

            const knee =
                createSphere(
                    0.13,
                    jointMaterial,
                    22
                );

            addMesh(
                group,
                knee,
                {
                    x: side * 0.4,
                    y: -2.02,
                    z: 0.03
                }
            );

            const tibia =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 0.37,
                        -2.11,
                        0.035
                    ),

                    new THREE.Vector3(
                        side * 0.38,
                        -3.4,
                        0.035
                    ),

                    0.055,

                    boneMaterial

                );

            const fibula =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 0.48,
                        -2.1,
                        -0.015
                    ),

                    new THREE.Vector3(
                        side * 0.47,
                        -3.37,
                        -0.015
                    ),

                    0.027,

                    boneMaterial

                );

            group.add(
                tibia,
                fibula
            );

            const ankle =
                createSphere(
                    0.095,
                    jointMaterial,
                    18
                );

            addMesh(
                group,
                ankle,
                {
                    x: side * 0.4,
                    y: -3.42,
                    z: 0.02
                }
            );

            const footBone =
                createCylinderBetween(

                    new THREE.Vector3(
                        side * 0.4,
                        -3.43,
                        0.02
                    ),

                    new THREE.Vector3(
                        side * 0.4,
                        -3.48,
                        0.49
                    ),

                    0.045,

                    boneMaterial

                );

            group.add(footBone);

        });

    }


    /* ======================================================
       11. COUCHE ZONES SENSIBLES
    ====================================================== */

    function createRiskLayer() {

        const group =
            state.bodyGroups.risks;

        const colors =
            getThemeColors();

        const riskLocations = [

            {
                name: "Épaule gauche",
                position: {
                    x: -0.91,
                    y: 2.03,
                    z: 0.03
                },
                scale: 0.34,
                intensity: 0.55
            },

            {
                name: "Zone lombaire",
                position: {
                    x: 0,
                    y: 0.42,
                    z: -0.27
                },
                scale: 0.42,
                intensity: 0.78
            },

            {
                name: "Genou droit",
                position: {
                    x: 0.4,
                    y: -2.02,
                    z: 0.04
                },
                scale: 0.32,
                intensity: 0.67
            },

            {
                name: "Cheville gauche",
                position: {
                    x: -0.4,
                    y: -3.4,
                    z: 0.04
                },
                scale: 0.24,
                intensity: 0.45
            }

        ];

        riskLocations.forEach(
            (
                risk,
                index
            ) => {

                const riskGroup =
                    new THREE.Group();

                riskGroup.name =
                    `risk-${index}`;

                riskGroup.userData = {

                    baseScale: risk.scale,

                    phase:
                        Math.random() *
                        Math.PI *
                        2,

                    intensity:
                        risk.intensity,

                    label:
                        risk.name

                };

                riskGroup.position.set(

                    risk.position.x,

                    risk.position.y,

                    risk.position.z

                );

                const core =
                    createSphere(

                        risk.scale * 0.36,

                        createGlowMaterial(
                            colors.risk,
                            0.72
                        ),

                        24

                    );

                const halo =
                    createSphere(

                        risk.scale,

                        createGlowMaterial(
                            colors.risk,
                            0.11
                        ),

                        28

                    );

                const ring =
                    new THREE.Mesh(

                        new THREE.TorusGeometry(
                            risk.scale * 0.72,
                            0.012,
                            8,
                            48
                        ),

                        createGlowMaterial(
                            colors.risk,
                            0.5
                        )

                    );

                ring.rotation.x =
                    Math.PI / 2;

                riskGroup.add(
                    halo,
                    ring,
                    core
                );

                group.add(
                    riskGroup
                );

            }
        );

    }


    /* ======================================================
       12. ÉNERGIE ET COLONNE LUMINEUSE
    ====================================================== */

    function createEnergyLayer() {

        const group =
            state.bodyGroups.energy;

        const colors =
            getThemeColors();

        const energyMaterial =
            createGlowMaterial(
                colors.primary,
                0.7
            );

        const energyPoints = [];

        for (
            let index = 0;
            index < 28;
            index += 1
        ) {

            const ratio =
                index / 27;

            energyPoints.push(

                new THREE.Vector3(

                    0,

                    2.56 -
                    ratio * 2.72,

                    -0.02 +
                    Math.sin(
                        ratio *
                        Math.PI *
                        1.7
                    ) * 0.055

                )

            );

        }

        const energyCurve =
            new THREE.CatmullRomCurve3(
                energyPoints
            );

        const energyTube =
            new THREE.Mesh(

                new THREE.TubeGeometry(
                    energyCurve,
                    100,
                    0.027,
                    10,
                    false
                ),

                energyMaterial

            );

        energyTube.name =
            "atlas-energy-spine";

        group.add(
            energyTube
        );

        for (
            let index = 0;
            index < 7;
            index += 1
        ) {

            const ratio =
                index / 6;

            const node =
                createSphere(

                    0.07 +
                    index * 0.004,

                    createGlowMaterial(
                        index % 2 === 0
                            ? colors.primary
                            : colors.secondary,
                        0.8
                    ),

                    18

                );

            const point =
                energyCurve.getPoint(
                    ratio
                );

            node.position.copy(point);

            node.userData = {

                phase:
                    index * 0.7,

                baseScale:
                    1

            };

            group.add(node);

        }

        createEnergyArcs(
            group,
            colors
        );

    }


    function createEnergyArcs(
        group,
        colors
    ) {

        const arcMaterial =
            new THREE.LineBasicMaterial({

                color: colors.primary,

                transparent: true,

                opacity: 0.3,

                blending:
                    THREE.AdditiveBlending

            });

        const lines = [

            [
                new THREE.Vector3(
                    0,
                    2.15,
                    0
                ),
                new THREE.Vector3(
                    -0.92,
                    2.02,
                    0
                )
            ],

            [
                new THREE.Vector3(
                    0,
                    2.15,
                    0
                ),
                new THREE.Vector3(
                    0.92,
                    2.02,
                    0
                )
            ],

            [
                new THREE.Vector3(
                    0,
                    -0.04,
                    0
                ),
                new THREE.Vector3(
                    -0.39,
                    -2.02,
                    0
                )
            ],

            [
                new THREE.Vector3(
                    0,
                    -0.04,
                    0
                ),
                new THREE.Vector3(
                    0.39,
                    -2.02,
                    0
                )
            ]

        ];

        lines.forEach((points) => {

            const curve =
                new THREE.QuadraticBezierCurve3(

                    points[0],

                    new THREE.Vector3(

                        (
                            points[0].x +
                            points[1].x
                        ) / 2,

                        (
                            points[0].y +
                            points[1].y
                        ) / 2 +
                        0.14,

                        0.22

                    ),

                    points[1]

                );

            const geometry =
                new THREE.BufferGeometry()
                    .setFromPoints(

                        curve.getPoints(30)

                    );

            const line =
                new THREE.Line(
                    geometry,
                    arcMaterial.clone()
                );

            group.add(line);

        });

    }


    /* ======================================================
       13. VISIBILITÉ DES COUCHES
    ====================================================== */

    function applyLayerVisibility() {

        if (!state.bodyRoot) {

            return;

        }

        const groups =
            state.bodyGroups;

        groups.skin.visible =
            state.currentLayer === "skin";

        groups.muscles.visible =
            state.currentLayer === "muscles";

        groups.skeleton.visible =
            state.currentLayer === "skeleton";

        groups.risks.visible =
            state.currentLayer === "risks";

        groups.energy.visible = true;

        if (
            state.currentLayer === "risks"
        ) {

            groups.skin.visible = true;

            setGroupOpacity(
                groups.skin,
                0.12
            );

        } else {

            restoreSkinOpacity();

        }

    }


    function setGroupOpacity(
        group,
        opacity
    ) {

        group.traverse((child) => {

            if (
                child.material &&
                "opacity" in child.material
            ) {

                if (
                    child.userData
                        .originalOpacity ===
                    undefined
                ) {

                    child.userData.originalOpacity =
                        child.material.opacity;

                }

                child.material.opacity =
                    opacity;

                child.material.transparent =
                    true;

            }

        });

    }


    function restoreSkinOpacity() {

        const skinGroup =
            state.bodyGroups.skin;

        if (!skinGroup) {

            return;

        }

        skinGroup.traverse((child) => {

            if (
                child.material &&
                child.userData
                    .originalOpacity !==
                undefined
            ) {

                child.material.opacity =
                    child.userData
                        .originalOpacity;

            }

        });

    }


    function setLayer(layer) {

        const allowedLayers = [

            "skin",

            "muscles",

            "skeleton",

            "risks"

        ];

        if (
            !allowedLayers.includes(layer)
        ) {

            return;

        }

        state.currentLayer = layer;

        applyLayerVisibility();

    }


    /* ======================================================
       14. THÈME
    ====================================================== */

    function setTheme(theme) {

        if (
            theme !== "male" &&
            theme !== "female"
        ) {

            return;

        }

        if (state.theme === theme) {

            return;

        }

        state.theme = theme;

        if (
            state.container &&
            state.activeMode
        ) {

            const containerId =
                state.container.id;

            initialize(
                containerId,
                state.activeMode
            );

        }

    }


    /* ======================================================
       15. CAMÉRA
    ====================================================== */

    function configureCamera() {

        const modeConfig =
            state.activeMode === "intro"
                ? CONFIG.intro
                : CONFIG.dashboard;

        state.camera.position.set(

            0,

            modeConfig.cameraY,

            modeConfig.cameraZ

        );

        state.targetCameraZ =
            modeConfig.cameraZ;

        state.camera.lookAt(
            0,
            0,
            0
        );

    }


    function resetView() {

        if (
            !state.camera ||
            !state.bodyRoot
        ) {

            return;

        }

        const modeConfig =
            state.activeMode === "intro"
                ? CONFIG.intro
                : CONFIG.dashboard;

        state.bodyRoot.rotation.set(
            0,
            0,
            0
        );

        state.camera.position.set(

            0,

            modeConfig.cameraY,

            modeConfig.cameraZ

        );

        state.targetCameraZ =
            modeConfig.cameraZ;

        state.rotationVelocity.x = 0;

        state.rotationVelocity.y = 0;

        state.autoRotationEnabled = true;

    }


    /* ======================================================
       16. INTERACTIONS SOURIS ET TACTILES
    ====================================================== */

    function bindInteractionEvents() {

        const canvas =
            state.renderer.domElement;

        canvas.addEventListener(
            "pointerdown",
            handlePointerDown
        );

        canvas.addEventListener(
            "pointermove",
            handlePointerMove
        );

        canvas.addEventListener(
            "pointerup",
            handlePointerUp
        );

        canvas.addEventListener(
            "pointercancel",
            handlePointerUp
        );

        canvas.addEventListener(
            "pointerenter",
            () => {

                state.pointerInside = true;

            }
        );

        canvas.addEventListener(
            "pointerleave",
            () => {

                state.pointerInside = false;

                handlePointerUp();

            }
        );

        canvas.addEventListener(
            "wheel",
            handleWheel,
            {
                passive: false
            }
        );

        canvas.addEventListener(
            "dblclick",
            resetView
        );

    }


    function handlePointerDown(event) {

        if (!state.renderer) {

            return;

        }

        state.isDragging = true;

        state.autoRotationEnabled = false;

        state.previousPointer.x =
            event.clientX;

        state.previousPointer.y =
            event.clientY;

        state.renderer.domElement
            .setPointerCapture?.(
                event.pointerId
            );

    }


    function handlePointerMove(event) {

        if (
            !state.isDragging ||
            !state.bodyRoot
        ) {

            return;

        }

        const deltaX =
            event.clientX -
            state.previousPointer.x;

        const deltaY =
            event.clientY -
            state.previousPointer.y;

        state.rotationVelocity.y =
            deltaX *
            CONFIG.interaction.rotationSpeed;

        state.rotationVelocity.x =
            deltaY *
            CONFIG.interaction.rotationSpeed;

        state.bodyRoot.rotation.y +=
            state.rotationVelocity.y;

        state.bodyRoot.rotation.x +=
            state.rotationVelocity.x;

        state.bodyRoot.rotation.x =
            THREE.MathUtils.clamp(

                state.bodyRoot.rotation.x,

                -0.45,

                0.45

            );

        state.previousPointer.x =
            event.clientX;

        state.previousPointer.y =
            event.clientY;

    }


    function handlePointerUp(event) {

        state.isDragging = false;

        if (
            event &&
            state.renderer
        ) {

            state.renderer.domElement
                .releasePointerCapture?.(
                    event.pointerId
                );

        }

    }


    function handleWheel(event) {

        if (!state.camera) {

            return;

        }

        event.preventDefault();

        state.targetCameraZ +=

            event.deltaY *
            CONFIG.interaction.zoomSpeed;

        state.targetCameraZ =
            THREE.MathUtils.clamp(

                state.targetCameraZ,

                CONFIG.interaction.minZoom,

                CONFIG.interaction.maxZoom

            );

    }


    /* ======================================================
       17. REDIMENSIONNEMENT
    ====================================================== */

    function observeContainer() {

        if (
            typeof ResizeObserver ===
            "undefined"
        ) {

            return;

        }

        state.resizeObserver =
            new ResizeObserver(() => {

                resize();

            });

        state.resizeObserver.observe(
            state.container
        );

    }


    function resize() {

        if (
            !state.container ||
            !state.renderer ||
            !state.camera
        ) {

            return;

        }

        const width =
            Math.max(
                1,
                state.container.clientWidth
            );

        const height =
            Math.max(
                1,
                state.container.clientHeight
            );

        state.camera.aspect =
            width / height;

        state.camera.updateProjectionMatrix();

        state.renderer.setSize(
            width,
            height,
            false
        );

    }


    /* ======================================================
       18. ANIMATION
    ====================================================== */

    function animate() {

        if (
            !state.renderer ||
            !state.scene ||
            !state.camera
        ) {

            return;

        }

        state.animationFrame =
            requestAnimationFrame(
                animate
            );

        const elapsed =
            state.clock.getElapsedTime();

        animateBody(elapsed);

        animateEnvironment(elapsed);

        animateCamera();

        state.renderer.render(

            state.scene,

            state.camera

        );

    }


    function animateBody(elapsed) {

        if (!state.bodyRoot) {

            return;

        }

        const modeConfig =
            state.activeMode === "intro"
                ? CONFIG.intro
                : CONFIG.dashboard;

        if (
            state.autoRotationEnabled &&
            !state.isDragging
        ) {

            state.bodyRoot.rotation.y +=
                modeConfig.autoRotationSpeed;

        }

        if (!state.isDragging) {

            state.rotationVelocity.x *=
                CONFIG.interaction.damping;

            state.rotationVelocity.y *=
                CONFIG.interaction.damping;

            state.bodyRoot.rotation.x +=
                state.rotationVelocity.x;

            state.bodyRoot.rotation.y +=
                state.rotationVelocity.y;

        }

        state.bodyRoot.position.y =
            -0.05 +
            Math.sin(
                elapsed * 1.25
            ) * 0.028;

        const breathingScale =
            1 +
            Math.sin(
                elapsed * 1.45
            ) * 0.008;

        const baseScale =
            modeConfig.bodyScale;

        state.bodyRoot.scale.set(

            baseScale *
            breathingScale,

            baseScale,

            baseScale *
            breathingScale

        );

        animateEnergyLayer(elapsed);

        animateRiskLayer(elapsed);

    }


    function animateEnergyLayer(elapsed) {

        const energyGroup =
            state.bodyGroups.energy;

        if (!energyGroup) {

            return;

        }

        energyGroup.children.forEach(
            (
                child,
                index
            ) => {

                if (
                    child.userData &&
                    child.userData.baseScale
                ) {

                    const pulse =

                        1 +
                        Math.sin(

                            elapsed * 3 +
                            child.userData.phase

                        ) * 0.22;

                    child.scale.setScalar(
                        pulse
                    );

                }

                if (
                    child.material &&
                    "opacity" in child.material
                ) {

                    const baseOpacity =
                        index === 0
                            ? 0.7
                            : 0.35;

                    child.material.opacity =

                        baseOpacity +
                        Math.sin(
                            elapsed * 2.3 +
                            index
                        ) * 0.1;

                }

            }
        );

    }


    function animateRiskLayer(elapsed) {

        const riskGroup =
            state.bodyGroups.risks;

        if (
            !riskGroup ||
            !riskGroup.visible
        ) {

            return;

        }

        riskGroup.children.forEach(
            (
                risk,
                index
            ) => {

                const pulse =

                    1 +
                    Math.sin(

                        elapsed * 2.8 +
                        risk.userData.phase

                    ) *
                    0.12 *
                    risk.userData.intensity;

                risk.scale.setScalar(
                    pulse
                );

                risk.rotation.y =
                    elapsed *
                    (
                        index % 2 === 0
                            ? 0.42
                            : -0.36
                    );

            }
        );

    }


    function animateEnvironment(elapsed) {

        if (!state.scene) {

            return;

        }

        const environment =
            state.scene.getObjectByName(
                "atlas-environment"
            );

        if (environment) {

            environment.rotation.y =
                elapsed * 0.025;

        }

        const particles =
            state.scene.getObjectByName(
                "atlas-particles-3d"
            );

        if (particles) {

            particles.rotation.y =
                elapsed * 0.035;

            particles.position.y =
                Math.sin(
                    elapsed * 0.5
                ) * 0.08;

        }

    }


    function animateCamera() {

        if (!state.camera) {

            return;

        }

        state.camera.position.z +=

            (
                state.targetCameraZ -
                state.camera.position.z
            ) * 0.08;

        state.camera.lookAt(
            0,
            0,
            0
        );

    }


    /* ======================================================
       19. API PUBLIQUE
    ====================================================== */

    window.AtlasBody3D = {

        initializeIntro(containerId = "viewer3D") {

            initialize(
                containerId,
                "intro"
            );

        },

        initializeDashboard(
            containerId = "body3dContainer"
        ) {

            initialize(
                containerId,
                "dashboard"
            );

        },

        setLayer,

        setTheme,

        resetView,

        resize,

        destroy: destroyCurrentScene,

        getState() {

            return {

                theme:
                    state.theme,

                currentLayer:
                    state.currentLayer,

                activeMode:
                    state.activeMode,

                initialized:
                    Boolean(
                        state.renderer
                    )

            };

        }

    };


    /* ======================================================
       20. SYNCHRONISATION DU THÈME INITIAL
    ====================================================== */

    const initialTheme =
        document.body?.dataset
            ?.atlasTheme;

    if (
        initialTheme === "male" ||
        initialTheme === "female"
    ) {

        state.theme = initialTheme;

    }

})();
