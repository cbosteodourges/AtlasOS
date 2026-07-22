// ╔════════════════════════════════════════════════════════════════╗
// ║ ATLAS OS — Hub Body 0.8.0                                    ║
// ╚════════════════════════════════════════════════════════════════╝

"use strict";

(() => {

  // ████████████████████████████████████████████████████████████
  // 🟦 PARTIE A — A01 — CONFIGURATION
  // ████████████████████████████████████████████████████████████

  const VERSION = "0.8.0";
  const DESIGN_WIDTH = 1536;
  const DESIGN_HEIGHT = 1024;

  const elements = {
    canvas: document.getElementById("atlasCanvas"),
    dialog: document.getElementById("atlasDialog"),
    dialogTitle: document.getElementById("dialogTitle"),
    dialogText: document.getElementById("dialogText"),
    dialogAction: document.getElementById("dialogAction")
  };

  // ████████████████████████████████████████████████████████████
  // 🟩 PARTIE B — B01 — MISE À L'ÉCHELLE EXACTE
  // ████████████████████████████████████████████████████████████

  function updateScale() {
    const scaleX = window.innerWidth / DESIGN_WIDTH;
    const scaleY = window.innerHeight / DESIGN_HEIGHT;
    const scale = Math.min(scaleX, scaleY);

    elements.canvas.style.setProperty(
      "--atlas-scale",
      String(scale)
    );
  }

  // ████████████████████████████████████████████████████████████
  // 🟨 PARTIE C — C01 — INTERACTIONS
  // ████████████████████████████████████████████████████████████

  function openDialog(title, text) {
    elements.dialogTitle.textContent = title;
    elements.dialogText.textContent = text;
    elements.dialog.showModal();
  }

  function bindHotspots() {
    document
      .querySelectorAll(".atlas-hotspot")
      .forEach((hotspot) => {
        hotspot.addEventListener("click", () => {
          openDialog(
            hotspot.dataset.title || "Atlas",
            hotspot.dataset.text || ""
          );
        });
      });

    elements.dialogAction.addEventListener("click", () => {
      elements.dialog.close();
    });
  }

  // ████████████████████████████████████████████████████████████
  // ⬜ PARTIE G — G01 — DÉMARRAGE
  // ████████████████████████████████████████████████████████████

  function initialize() {
    updateScale();
    bindHotspots();

    window.addEventListener("resize", updateScale);

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
