"use strict";
(() => {
  const one = selector => document.querySelector(selector);
  const setText = (selector, value) => { const node = one(selector); if (node) node.textContent = value; };
  const bounded = value => Math.max(0, Math.min(100, Number(value) || 0));
  const percent = (value, target) => target ? bounded((Number(value || 0) / Number(target)) * 100) : 0;

  const render = payload => {
    if (!payload?.access?.enabled) {
      setText("[data-day-status]", "Le module n’est pas encore activé.");
      return;
    }
    const today = payload.today || {};
    const targets = payload.targets || {};
    const progress = payload.progress || {};
    const hydrationPercent = bounded(progress.hydration_percent ?? percent(today.hydration_ml, targets.hydration_ml));
    const count = Number(today.record_count || 0);

    setText("[data-hydration-value]", Math.round(today.hydration_ml || 0));
    setText("[data-energy-value]", count ? Math.round(today.energy_kcal || 0) : "—");
    setText("[data-protein-value]", count ? Math.round(today.protein_g || 0) : "—");
    setText("[data-carbs-value]", count ? Math.round(today.carbohydrate_g || 0) : "—");
    setText("[data-hydration-target]", targets.hydration_ml ? `Repère personnel : ${targets.hydration_ml} ml` : "Ajoutez votre poids pour personnaliser le repère");
    setText("[data-protein-target]", targets.protein_g ? `repère ${targets.protein_g} g` : "repère à personnaliser");
    setText("[data-carbs-target]", targets.carbohydrate_g ? `repère ${targets.carbohydrate_g} g` : "repère à personnaliser");
    setText("[data-fuel-source]", today.sources?.length ? today.sources.join(" + ") : "Atlas + Santé Connect");
    setText("[data-fuel-guidance]", payload.recommendations?.[0] || "Aucun apport enregistré aujourd’hui : Atlas ne conclut pas à un déficit.");
    setText("[data-day-status]", count ? `${count} apport${count > 1 ? "s" : ""} enregistré${count > 1 ? "s" : ""}` : "Aucun apport déclaré aujourd’hui");

    const bar = one("[data-hydration-progress]");
    if (bar) bar.style.width = `${hydrationPercent}%`;
    const ring = one("[data-hydration-ring]");
    if (ring) ring.style.setProperty("--progress", hydrationPercent);
    const values = [
      ["[data-energy-progress]", percent(today.energy_kcal, targets.energy_kcal)],
      ["[data-protein-progress]", percent(today.protein_g, targets.protein_g)],
      ["[data-carbs-progress]", percent(today.carbohydrate_g, targets.carbohydrate_g)]
    ];
    values.forEach(([selector, value]) => one(selector)?.style.setProperty("--value", `${value}%`));
  };

  const load = () => fetch("/api/atlas/nutrition-hydration", { cache: "no-store" })
    .then(response => response.ok ? response.json() : Promise.reject(new Error("Données indisponibles")))
    .then(render)
    .catch(error => setText("[data-day-status]", error.message));

  const save = body => fetch("/api/atlas/nutrition-hydration", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(async response => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Enregistrement impossible");
    render(payload.summary);
  });

  document.querySelectorAll("[data-water]").forEach(button => button.addEventListener("click", async () => {
    setText("[data-nutrition-status]", "Enregistrement…");
    try {
      await save({ type: "hydration", volume_ml: Number(button.dataset.water), name: "Eau" });
      setText("[data-nutrition-status]", `+${button.dataset.water} ml enregistrés.`);
    } catch (error) {
      setText("[data-nutrition-status]", error.message);
    }
  }));

  one("[data-nutrition-form]")?.addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    Object.keys(values).forEach(key => { if (key !== "name" && values[key] !== "") values[key] = Number(values[key]); });
    setText("[data-nutrition-status]", "Enregistrement…");
    try {
      await save({ type: "nutrition", ...values });
      form.reset();
      setText("[data-nutrition-status]", "Apport enregistré.");
    } catch (error) {
      setText("[data-nutrition-status]", error.message);
    }
  });

  load();
})();