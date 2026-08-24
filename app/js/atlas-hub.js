"use strict";

(() => {
  const REPORTS_KEY = "atlasHealthPainReports";
  const EVENTS_KEY = "atlasHealthTimelineEvents";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const read = (key) => { try { return JSON.parse(localStorage.getItem(key) || "[]"); } catch { return []; } };
  const write = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const formatDate = (value) => new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));

  const regions = {
    foot: ["Voûte plantaire", "Talon", "Têtes des métatarsiens", "Tendons extenseurs", "Orteils"],
    ankle: ["Tendon d’Achille", "Ligaments externes", "Ligaments internes", "Articulation", "Arrière du talon"],
    leg: ["Bord interne du tibia", "Jambier antérieur", "Tendons releveurs des orteils", "Mollet", "Face externe de la jambe"],
    knee: ["Autour de la rotule", "Tendon rotulien", "Pôle inférieur de la rotule", "Tendon quadricipital", "Face externe / bandelette ilio-tibiale", "Interligne méniscal interne", "Interligne méniscal externe", "Tubérosité tibiale antérieure"],
    thigh: ["Quadriceps", "Ischio-jambiers", "Adducteurs", "Face externe de la cuisse"],
    hip: ["Aine / adducteurs", "Articulation de hanche", "Grand trochanter", "Face antérieure de la hanche"],
    glute: ["Piriforme / région fessière profonde", "Moyen fessier — muscle", "Moyen fessier — tendon", "Grand fessier", "Arrière du grand trochanter"]
  };
  const regionLabels = { foot: "Pied", ankle: "Cheville", leg: "Jambe", knee: "Genou", thigh: "Cuisse", hip: "Hanche / aine", glute: "Région fessière" };
  let selectedRegion = "";
  let selectedSide = "";

  function activate(name) {
    $$('[data-view]').forEach((view) => view.classList.toggle("active", view.dataset.view === name));
    $$('[data-tab]').forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
    history.replaceState(null, "", `#${name}`);
    if (name === "prevention") renderPrevention();
  }

  function selectRegion(region) {
    selectedRegion = region;
    selectedSide = "";
    $$('[data-region]').forEach((button) => button.classList.toggle("active", button.dataset.region === region));
    $$('[data-side]').forEach((button) => button.classList.remove("active"));
    $('[data-pain-empty]').hidden = true;
    $('[data-pain-form]').hidden = false;
    $('[data-region-title]').textContent = regionLabels[region];
    $('[data-zone-options]').innerHTML = regions[region].map((zone, index) => `<label><input type="radio" name="zone" value="${escapeHtml(zone)}" ${index === 0 ? "checked" : ""}><span>${escapeHtml(zone)}</span></label>`).join("");
    $('.pain-detail').scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function advice(report) {
    const alerts = report.redFlags.length;
    if (alerts) return { level: "urgent", title: "Arrêt de la course et avis professionnel recommandé", text: "Un signe d’alerte a été déclaré. Atlas ne propose pas de diagnostic ni de reprise automatique." };
    if (report.intensity >= 7 || report.trigger === "Au repos ou la nuit") return { level: "high", title: "Charge de course à suspendre", text: "Privilégiez une activité sans douleur et demandez un avis si la douleur persiste ou s’aggrave." };
    if (report.intensity >= 4) return { level: "moderate", title: "Charge à réduire temporairement", text: "Évitez l’intensité et surveillez l’évolution à 24–48 h avant toute progression." };
    return { level: "low", title: "Surveillance active", text: "Maintenez seulement les activités indolores et réévaluez après la prochaine séance." };
  }

  function renderReports() {
    const reports = read(REPORTS_KEY).filter((item) => !item.resolved);
    $('[data-pain-count]').textContent = reports.length;
    $('[data-active-reports]').innerHTML = reports.length ? reports.map((report) => {
      const guidance = advice(report);
      return `<article class="pain-report ${guidance.level}"><div><p class="eyebrow">${escapeHtml(formatDate(report.date))}</p><h3>${escapeHtml(regionLabels[report.region])} · ${escapeHtml(report.sideLabel)}</h3><p><strong>${escapeHtml(report.zone)}</strong> · ${report.intensity}/10 · ${escapeHtml(report.trigger)}</p><p>${escapeHtml(guidance.title)} — ${escapeHtml(guidance.text)}</p>${report.notes ? `<small>${escapeHtml(report.notes)}</small>` : ""}</div><button type="button" data-resolve="${report.id}">Marquer comme résolue</button></article>`;
    }).join("") : '<div class="empty-state"><strong>Aucune douleur active</strong><p>Vos futurs signalements apparaîtront ici avec un niveau de prudence.</p></div>';
    $$('[data-resolve]').forEach((button) => button.addEventListener("click", () => {
      const all = read(REPORTS_KEY);
      const item = all.find((report) => report.id === button.dataset.resolve);
      if (item) { item.resolved = true; item.resolvedAt = new Date().toISOString(); write(REPORTS_KEY, all); renderReports(); renderTimeline(); }
    }));
  }

  function savePain(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!selectedSide) { alert("Choisissez le côté douloureux."); return; }
    const report = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), date: new Date().toISOString().slice(0, 10), region: selectedRegion,
      side: selectedSide, sideLabel: { left: "gauche", right: "droite", center: "central" }[selectedSide],
      zone: form.elements.zone.value, intensity: Number(form.elements.intensity.value), onset: form.elements.onset.value,
      trigger: form.elements.trigger.value, redFlags: $$('[name="redFlag"]', form).filter((input) => input.checked).map((input) => input.value),
      notes: form.elements.notes.value.trim(), resolved: false
    };
    const reports = read(REPORTS_KEY); reports.unshift(report); write(REPORTS_KEY, reports);
    const events = read(EVENTS_KEY); events.unshift({ id: `pain-${report.id}`, date: report.date, type: "Douleur ou blessure", title: `${regionLabels[report.region]} ${report.sideLabel} · ${report.zone}`, note: `${report.intensity}/10 — ${advice(report).title}` }); write(EVENTS_KEY, events);
    form.reset(); $('[data-intensity-value]').textContent = "3/10"; renderReports(); renderTimeline();
  }

  function renderTimeline() {
    const events = [...read(EVENTS_KEY)].sort((a, b) => b.date.localeCompare(a.date));
    $('[data-body-timeline]').innerHTML = events.length ? events.map((item) => `<article><time datetime="${item.date}">${escapeHtml(formatDate(item.date))}</time><div><span>${escapeHtml(item.type)}</span><h3>${escapeHtml(item.title)}</h3>${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}</div></article>`).join("") : '<div class="empty-state"><strong>Votre frise commence ici</strong><p>Ajoutez une douleur, une reprise ou un soin utile à votre suivi.</p></div>';
  }

  function executionDate(item) { return item?.activity?.started_at || item?.activity?.start_time || item?.started_at || ""; }
  function activityOf(item) { return item?.activity || item?.normalized_activity || {}; }
  function distanceKm(item) { const a = activityOf(item); return Number(a.distance_km || (a.distance_meters ? a.distance_meters / 1000 : 0) || 0); }
  function isRunning(item) { const a = activityOf(item); return /run|running|course/i.test(`${a.sport || ""} ${a.activity_type || ""} ${item?.planned_workout?.title || ""}`) && !/cycl|vélo|bike/i.test(`${a.sport || ""} ${a.activity_type || ""}`); }
  function isIntense(item) { return /vo2|sv2|seuil|sprint|interval|tempo/i.test(`${item?.planned_workout?.title || ""} ${item?.analysis?.session_type || ""}`); }

  async function renderPrevention() {
    try {
      const response = await fetch('/api/atlas-coach/executions?limit=200', { cache: "no-store" });
      if (!response.ok) throw new Error("API indisponible");
      const payload = await response.json();
      const now = Date.now();
      const runs = (payload.executions || payload || []).filter(isRunning).filter((item) => executionDate(item));
      const recent = runs.filter((item) => now - new Date(executionDate(item)).getTime() <= 7 * 86400000);
      const reference = runs.filter((item) => now - new Date(executionDate(item)).getTime() <= 35 * 86400000);
      const recentKm = recent.reduce((sum, item) => sum + distanceKm(item), 0);
      const referenceKm = reference.reduce((sum, item) => sum + distanceKm(item), 0) / Math.max(1, Math.min(5, Math.ceil(35 / 7)));
      const intense = recent.filter(isIntense).length;
      const pains = read(REPORTS_KEY).filter((item) => !item.resolved).length;
      $('[data-load-7d]').textContent = `${recentKm.toFixed(1).replace('.', ',')} km`;
      $('[data-load-reference]').textContent = `${referenceKm.toFixed(1).replace('.', ',')} km/sem.`;
      $('[data-intensity-count]').textContent = intense;
      const ratio = referenceKm ? recentKm / referenceKm : null;
      let title = "Charge récente cohérente avec votre référence";
      let text = "La lecture reste individualisée et doit être confrontée à vos sensations.";
      const points = [];
      if (ratio !== null && ratio > 1.25) { title = "Hausse de volume à surveiller"; text = "Le volume récent dépasse nettement votre moyenne disponible. Cela signale une progression inhabituelle, pas un seuil de blessure."; points.push("Éviter d’ajouter simultanément volume et intensité."); }
      else if (ratio !== null && ratio < 0.65) points.push("La charge récente est inférieure à votre référence personnelle.");
      if (intense >= 3) points.push("Trois séances intenses ou plus ont été détectées sur sept jours.");
      if (pains) { title = "La charge doit être lue avec vos douleurs actives"; points.push("Une douleur active est prioritaire sur tout indicateur de charge."); }
      if (!points.length) points.push("Aucun signal combiné inhabituel n’est détecté avec les données disponibles.");
      $('[data-prevention-title]').textContent = title; $('[data-prevention-text]').textContent = text;
      $('[data-prevention-points]').innerHTML = points.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
    } catch {
      $('[data-prevention-title]').textContent = "Données d’entraînement indisponibles";
      $('[data-prevention-text]').textContent = "Démarrez le serveur Atlas pour comparer la charge récente à votre historique.";
      $('[data-prevention-points]').innerHTML = "<li>Vos signalements locaux restent conservés sur cet appareil.</li>";
    }
  }

  const shortcuts = $('[data-region-shortcuts]');
  shortcuts.innerHTML = Object.entries(regionLabels).map(([key, label]) => `<button type="button" data-region="${key}">${label}</button>`).join("");
  $$('[data-tab]').forEach((button) => button.addEventListener("click", () => activate(button.dataset.tab)));
  $$('[data-region]').forEach((button) => button.addEventListener("click", () => selectRegion(button.dataset.region)));
  $$('[data-side]').forEach((button) => button.addEventListener("click", () => { selectedSide = button.dataset.side; $$('[data-side]').forEach((item) => item.classList.toggle("active", item === button)); }));
  $('[name="intensity"]').addEventListener("input", (event) => { $('[data-intensity-value]').textContent = `${event.target.value}/10`; });
  $('[data-pain-form]').addEventListener("submit", savePain);
  $('[data-anatomy-toggle]').addEventListener("click", () => { $('[data-anatomy-panel]').hidden = false; const frame = $('[data-anatomy-frame]'); if (!frame.src) frame.src = `./biomecanique.html?region=${encodeURIComponent(selectedRegion)}&embed=1`; $('[data-anatomy-panel]').scrollIntoView({ behavior: "smooth" }); });
  $('[data-anatomy-close]').addEventListener("click", () => { $('[data-anatomy-panel]').hidden = true; });
  $('[data-event-toggle]').addEventListener("click", () => { const form = $('[data-event-form]'); form.hidden = !form.hidden; if (!form.hidden && !form.elements.date.value) form.elements.date.value = new Date().toISOString().slice(0, 10); });
  $('[data-event-form]').addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; const events = read(EVENTS_KEY); events.unshift({ id: String(Date.now()), date: form.elements.date.value, type: form.elements.type.value, title: form.elements.title.value.trim(), note: form.elements.note.value.trim() }); write(EVENTS_KEY, events); form.reset(); form.hidden = true; renderTimeline(); });

  const selectedAvatar = localStorage.getItem("atlasPreselectedAvatar") || "male";
  $('[data-atlas-avatar-image]').src = selectedAvatar === "female" ? "./assets/atlas-avatar-femme-clean-final.png?v=2" : "./assets/atlas-avatar-homme-clean-final.png?v=2";
  renderReports(); renderTimeline();
  const initial = location.hash.slice(1); activate(["injuries", "prevention", "timeline"].includes(initial) ? initial : "injuries");
})();
