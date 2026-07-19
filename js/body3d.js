"use strict";

(() => {
  const state = {
    theme: document.body?.dataset?.atlasTheme === "female" ? "female" : "male",
    mode: null,
    container: null,
    scene: null,
    camera: null,
    renderer: null,
    root: null,
    logo: null,
    halo: null,
    animationFrame: null,
    resizeObserver: null,
    clock: null,
    dragging: false,
    previousX: 0,
    targetRotationY: 0,
    targetRotationX: 0,
    targetCameraZ: 6.2,
    currentLayer: "skin"
  };

  const THEMES = {
    male: { primary: 0x38bdf8, secondary: 0x2563eb, light: 0xa5f3fc },
    female: { primary: 0xec4899, secondary: 0x8b5cf6, light: 0xf5d0fe }
  };

  function colors() {
    return THEMES[state.theme] || THEMES.male;
  }

  function disposeMaterial(material) {
    if (!material) return;
    if (Array.isArray(material)) {
      material.forEach(disposeMaterial);
      return;
    }
    if (material.map) material.map.dispose();
    material.dispose?.();
  }

  function destroy() {
    if (state.animationFrame) cancelAnimationFrame(state.animationFrame);
    state.resizeObserver?.disconnect();
    if (state.scene) {
      state.scene.traverse((object) => {
        object.geometry?.dispose?.();
        disposeMaterial(object.material);
      });
    }
    state.renderer?.dispose?.();
    state.renderer?.domElement?.remove();
    Object.assign(state, {
      mode: null,
      container: null,
      scene: null,
      camera: null,
      renderer: null,
      root: null,
      logo: null,
      halo: null,
      animationFrame: null,
      resizeObserver: null,
      clock: null,
      dragging: false
    });
  }

  function removePlaceholder(container) {
    container.querySelectorAll(".viewer-placeholder, .body-placeholder").forEach((node) => node.remove());
  }

  function initialize(containerId, mode) {
    if (typeof THREE === "undefined") {
      console.error("Atlas OS : Three.js n’est pas chargé.");
      return;
    }

    const container = document.getElementById(containerId);
    if (!container) return;

    if (state.container === container && state.renderer) {
      resize();
      return;
    }

    destroy();
    state.container = container;
    state.mode = mode;
    state.clock = new THREE.Clock();
    removePlaceholder(container);

    state.scene = new THREE.Scene();
    state.camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
    state.camera.position.set(0, 0, mode === "intro" ? 6.4 : 6.0);
    state.targetCameraZ = state.camera.position.z;

    state.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    state.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    state.renderer.setClearColor(0x000000, 0);
    state.renderer.outputColorSpace = THREE.SRGBColorSpace;
    state.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    state.renderer.toneMappingExposure = 1.15;
    state.renderer.domElement.style.touchAction = "none";
    state.renderer.domElement.setAttribute("aria-hidden", "true");
    container.appendChild(state.renderer.domElement);

    buildScene();
    bindInteractions();
    resize();

    if (typeof ResizeObserver !== "undefined") {
      state.resizeObserver = new ResizeObserver(resize);
      state.resizeObserver.observe(container);
    }

    animate();
  }

  function buildScene() {
    const c = colors();
    state.root = new THREE.Group();
    state.scene.add(state.root);

    const ambient = new THREE.HemisphereLight(c.light, 0x020713, 1.5);
    const key = new THREE.PointLight(c.primary, 35, 15, 2);
    key.position.set(3.5, 3, 4);
    const fill = new THREE.PointLight(c.secondary, 22, 12, 2);
    fill.position.set(-3, -1, 3);
    state.scene.add(ambient, key, fill);

    const loader = new THREE.TextureLoader();
    loader.load(
      "./assets/images/atlas-logo.jpg",
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = Math.min(8, state.renderer.capabilities.getMaxAnisotropy());

        const aspect = texture.image.width / texture.image.height;
        const height = state.mode === "intro" ? 4.9 : 4.55;
        const width = height * aspect;

        const geometry = new THREE.PlaneGeometry(width, height, 32, 32);
        const material = new THREE.MeshPhysicalMaterial({
          map: texture,
          color: state.theme === "female" ? 0xff8bd0 : 0xffffff,
          transparent: true,
          opacity: 0.98,
          roughness: 0.28,
          metalness: 0.04,
          clearcoat: 0.45,
          clearcoatRoughness: 0.2,
          side: THREE.DoubleSide
        });

        state.logo = new THREE.Mesh(geometry, material);
        state.logo.position.z = 0.03;
        state.root.add(state.logo);
      },
      undefined,
      () => {
        console.error("Atlas OS : impossible de charger assets/images/atlas-logo.jpg");
      }
    );

    const ringMaterial = new THREE.MeshBasicMaterial({
      color: c.primary,
      transparent: true,
      opacity: 0.24,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    state.halo = new THREE.Group();
    for (let i = 0; i < 4; i += 1) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(2.25 + i * 0.27, 0.012, 8, 128),
        ringMaterial.clone()
      );
      ring.rotation.x = i % 2 === 0 ? 0.08 : -0.08;
      ring.rotation.y = i * 0.18;
      state.halo.add(ring);
    }
    state.root.add(state.halo);

    const positions = new Float32Array(180 * 3);
    for (let i = 0; i < 180; i += 1) {
      const radius = 2.5 + Math.random() * 1.6;
      const angle = Math.random() * Math.PI * 2;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = -2.4 + Math.random() * 4.8;
      positions[i * 3 + 2] = Math.sin(angle) * radius * 0.45;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({
        color: c.light,
        size: 0.025,
        transparent: true,
        opacity: 0.65,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    particles.name = "atlas-logo-particles";
    state.root.add(particles);
  }

  function bindInteractions() {
    const canvas = state.renderer.domElement;
    canvas.addEventListener("pointerdown", (event) => {
      state.dragging = true;
      state.previousX = event.clientX;
      canvas.setPointerCapture?.(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!state.dragging) return;
      const deltaX = event.clientX - state.previousX;
      state.targetRotationY += deltaX * 0.006;
      state.targetRotationY = THREE.MathUtils.clamp(state.targetRotationY, -0.48, 0.48);
      state.previousX = event.clientX;
    });
    const release = (event) => {
      state.dragging = false;
      if (event) canvas.releasePointerCapture?.(event.pointerId);
    };
    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", release);
    canvas.addEventListener("pointerleave", release);
    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      state.targetCameraZ = THREE.MathUtils.clamp(state.targetCameraZ + event.deltaY * 0.006, 4.8, 8.5);
    }, { passive: false });
    canvas.addEventListener("dblclick", resetView);
  }

  function animate() {
    if (!state.renderer || !state.scene || !state.camera) return;
    state.animationFrame = requestAnimationFrame(animate);
    const elapsed = state.clock.getElapsedTime();

    if (!state.dragging) {
      state.targetRotationY = Math.sin(elapsed * 0.38) * 0.16;
    }

    if (state.root) {
      state.root.rotation.y += (state.targetRotationY - state.root.rotation.y) * 0.055;
      state.root.rotation.x = Math.sin(elapsed * 0.42) * 0.025;
      state.root.position.y = Math.sin(elapsed * 0.9) * 0.035;
    }

    if (state.logo) {
      const pulse = 1 + Math.sin(elapsed * 1.25) * 0.012;
      state.logo.scale.setScalar(pulse);
    }

    if (state.halo) {
      state.halo.rotation.z = elapsed * 0.035;
      state.halo.children.forEach((ring, index) => {
        ring.rotation.z = elapsed * (index % 2 === 0 ? 0.07 : -0.055);
      });
    }

    const particles = state.scene.getObjectByName("atlas-logo-particles");
    if (particles) particles.rotation.z = elapsed * 0.025;

    state.camera.position.z += (state.targetCameraZ - state.camera.position.z) * 0.08;
    state.camera.lookAt(0, 0, 0);
    state.renderer.render(state.scene, state.camera);
  }

  function resize() {
    if (!state.container || !state.renderer || !state.camera) return;
    const width = Math.max(1, state.container.clientWidth);
    const height = Math.max(1, state.container.clientHeight);
    state.camera.aspect = width / height;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(width, height, false);
  }

  function resetView() {
    state.targetRotationY = 0;
    state.targetRotationX = 0;
    state.targetCameraZ = state.mode === "intro" ? 6.4 : 6.0;
    if (state.root) state.root.rotation.set(0, 0, 0);
  }

  function setTheme(theme) {
    const normalized = theme === "female" ? "female" : "male";
    if (state.theme === normalized) return;
    state.theme = normalized;
    if (state.container?.id && state.mode) initialize(state.container.id, state.mode);
  }

  function setLayer(layer) {
    state.currentLayer = layer;
    const labels = {
      skin: "Vue globale",
      muscles: "Analyse musculaire",
      skeleton: "Structure biomécanique",
      risks: "Zones sensibles"
    };
    window.AtlasOS?.showToast?.(`${labels[layer] || "Vue"} : visualisation du logo Atlas active.`, "info");
  }

  window.AtlasBody3D = {
    initializeIntro: (containerId = "viewer3D") => initialize(containerId, "intro"),
    initializeDashboard: (containerId = "body3dContainer") => initialize(containerId, "dashboard"),
    setTheme,
    setLayer,
    resetView,
    resize,
    destroy,
    getState: () => ({ theme: state.theme, mode: state.mode, currentLayer: state.currentLayer, initialized: Boolean(state.renderer) })
  };
})();
