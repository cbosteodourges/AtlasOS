"use strict";

(() => {
  const root = document.createElement("div");
  root.className = "atlas-conversation-backdrop";
  root.hidden = true;
  root.innerHTML = `
    <section class="atlas-conversation atlas-adaptation" role="dialog" aria-modal="true" aria-labelledby="atlasAdaptationTitle">
      <button class="atlas-conversation-close" type="button" aria-label="Fermer">×</button>
      <header>
        <span class="atlas-conversation-orb">↻</span>
        <div>
          <strong id="atlasAdaptationTitle">Adapter ma séance</strong>
          <small>Décision locale, calculée et explicable</small>
        </div>
      </header>
      <p class="atlas-conversation-intro">Renseignez votre état du jour. Atlas croise votre ressenti, vos données Wellness et votre programme.</p>
      <form class="atlas-guided-form">
        <div class="atlas-guided-grid">
          <label>Énergie
            <select data-feeling="energy" required>
              <option value="">Choisir…</option><option value="2">Très basse</option><option value="4">Basse</option><option value="6">Moyenne</option><option value="8">Bonne</option><option value="10">Excellente</option>
            </select>
          </label>
          <label>Fatigue
            <select data-feeling="fatigue" required>
              <option value="">Choisir…</option><option value="0">Aucune</option><option value="3">Légère</option><option value="6">Modérée</option><option value="8">Forte</option><option value="10">Très forte</option>
            </select>
          </label>
          <label>Douleur
            <select data-feeling="pain" required>
              <option value="">Choisir…</option><option value="0">Aucune</option><option value="2">Légère</option><option value="5">Modérée</option><option value="8">Importante</option><option value="10">Très importante</option>
            </select>
          </label>
          <label>Séance envisagée
            <select name="preference" required>
              <option value="planned">Suivre le programme</option>
              <option value="endurance">Endurance facile</option>
              <option value="threshold">Seuil</option>
              <option value="vo2max">VO₂max</option>
              <option value="bike">Vélo endurance</option>
              <option value="rest">Repos ou mobilité</option>
            </select>
          </label>
        </div>
        <label class="atlas-guided-note">Précision facultative
          <textarea name="note" maxlength="400" placeholder="Ex. jambes lourdes, douleur au tendon, nuit perturbée…"></textarea>
        </label>
        <button class="atlas-send-button" type="submit">Calculer mes options</button>
      </form>
      <section class="atlas-adaptation-result" hidden aria-live="polite">
        <div class="atlas-adaptation-summary"></div>
        <div class="atlas-adaptation-options"></div>
        <small>Atlas propose et explique. Votre programme n’est jamais modifié sans votre choix.</small>
      </section>
    </section>
  `;
  document.body.appendChild(root);

  const form = root.querySelector(".atlas-guided-form");
  const submit = form.querySelector(".atlas-send-button");
  const result = root.querySelector(".atlas-adaptation-result");
  const summary = root.querySelector(".atlas-adaptation-summary");
  const optionsRoot = root.querySelector(".atlas-adaptation-options");
  let lastPayload = null;

  const post = async payload => {
    const response = await fetch("/api/atlas/conversation", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Atlas indisponible");
    if (!data.assessment || !Array.isArray(data.options)) {
      throw new Error("Le serveur Atlas utilise encore l’ancienne version. Arrêtez-le puis relancez tools\\atlas_web_server.py.");
    }
    return data;
  };

  const recordChoice = async option => {
    optionsRoot.querySelectorAll("button").forEach(button => { button.disabled = true; });
    try {
      const data = await post({...lastPayload, selected_option: option.id});
      localStorage.setItem("atlasAdaptationSelection", JSON.stringify({
        recordedAt: new Date().toISOString(),
        option,
        assessment: data.assessment
      }));
      summary.innerHTML = `<strong>Choix enregistré</strong><p>${data.response}</p>`;
      optionsRoot.replaceChildren();
      window.dispatchEvent(new CustomEvent("atlas:adaptation-selected", {detail: {option, assessment: data.assessment}}));
    } catch (error) {
      summary.innerHTML = `<strong>Enregistrement impossible</strong><p>${error.message}</p>`;
      optionsRoot.querySelectorAll("button").forEach(button => { button.disabled = false; });
    }
  };

  const render = data => {
    result.hidden = false;
    summary.innerHTML = `
      <div class="atlas-adaptation-score"><b>${data.assessment.score}</b><span>/100<br>disponibilité ajustée</span></div>
      <div><strong>${data.assessment.title}</strong><p>${data.response}</p><small>${data.assessment.evidence.join(" · ")}</small></div>
    `;
    optionsRoot.replaceChildren();
    data.options.forEach(option => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = option.recommended ? "is-recommended" : "";
      button.innerHTML = `<span>${option.recommended ? "Recommandé" : "Option"}</span><strong>${option.title}</strong><small>${option.description}</small>`;
      button.addEventListener("click", () => recordChoice(option));
      optionsRoot.appendChild(button);
    });
    result.scrollIntoView({behavior: "smooth", block: "nearest"});
  };

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const feeling = {};
    root.querySelectorAll("[data-feeling]").forEach(select => {
      feeling[select.dataset.feeling] = Number(select.value);
    });
    lastPayload = {
      mode: "guided_adaptation",
      feeling,
      preference: form.elements.preference.value,
      note: form.elements.note.value.trim()
    };
    submit.disabled = true;
    submit.textContent = "Calcul en cours…";
    try {
      render(await post(lastPayload));
    } catch (error) {
      result.hidden = false;
      summary.innerHTML = `<strong>Atlas n’est pas disponible</strong><p>${error.message}</p>`;
      optionsRoot.replaceChildren();
    } finally {
      submit.disabled = false;
      submit.textContent = "Calculer mes options";
    }
  });

  const open = () => {
    root.hidden = false;
    document.body.style.overflow = "hidden";
    result.hidden = true;
    setTimeout(() => form.querySelector("select")?.focus(), 0);
  };
  const close = () => {
    root.hidden = true;
    document.body.style.overflow = "";
  };

  document.addEventListener("click", event => {
    if (event.target.closest("[data-atlas-talk]")) {
      event.preventDefault();
      open();
    }
  });
  window.addEventListener("atlas:conversation-open", open);
  root.querySelector(".atlas-conversation-close").addEventListener("click", close);
  root.addEventListener("click", event => { if (event.target === root) close(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !root.hidden) close(); });
})();
