"use strict";

(() => {
  const REPORTS_KEY = "atlas.health.pain_reports.v2";
  const LEGACY_REPORT_KEYS = ["atlasHealthPainReports", "atlas.running_pain_reports.v2", "atlas.running_pain_reports.v1"];
  const EVENTS_KEY = "atlasHealthTimelineEvents";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const read = (key) => { try { const value = JSON.parse(localStorage.getItem(key) || "[]"); return Array.isArray(value) ? value : []; } catch { return []; } };
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
    glute: ["Piriforme / région fessière profonde", "Moyen fessier — muscle", "Moyen fessier — tendon", "Grand fessier", "Arrière du grand trochanter"],
    back: ["Région lombaire", "Sacrum / bassin", "Articulation sacro-iliaque"]
  };
  const regionLabels = { foot: "Pied", ankle: "Cheville", leg: "Jambe", knee: "Genou", thigh: "Cuisse", hip: "Hanche / aine", glute: "Région fessière", back: "Dos / bassin" };
  const sideLabels = { left: "gauche", right: "droite", center: "central", gauche: "gauche", droite: "droite", bilatéral: "bilatéral", central: "central" };
  let selectedRegion = "";
  let selectedSide = "";

  function normalizeReport(item = {}) {
    const date = String(item.date || item.recorded_at || new Date().toISOString()).slice(0, 10);
    const region = item.region || item.region_id || "leg";
    const rawSide = String(item.side || "center");
    const effort = Number(item.intensity ?? item.effort_intensity ?? item.rest_intensity ?? 0);
    const rest = Number(item.rest_intensity ?? (item.trigger === "Au repos ou la nuit" ? effort : 0));
    const flags = Array.isArray(item.redFlags) ? item.redFlags : (Array.isArray(item.flags) ? item.flags : []);
    const trigger = item.trigger || (rest >= effort && rest > 0 ? "Au repos ou la nuit" : "Pendant la course");
    return {
      id: String(item.id || `${date}-${region}-${item.zone_id || item.zone || Date.now()}`),
      date,
      recorded_at: item.recorded_at || `${date}T12:00:00`,
      region,
      regionLabel: item.regionLabel || item.region_label || regionLabels[region] || "Zone signalée",
      side: rawSide,
      sideLabel: item.sideLabel || sideLabels[rawSide.toLowerCase()] || rawSide.toLowerCase(),
      zone: item.zone || item.zone_label || item.zone_id || "Emplacement à préciser",
      zoneId: item.zoneId || item.zone_id || null,
      intensity: Math.max(effort, rest),
      effortIntensity: effort,
      restIntensity: rest,
      onset: item.onset || "À préciser",
      trigger,
      redFlags: flags,
      notes: item.notes || item.note || "",
      resolved: Boolean(item.resolved),
      resolvedAt: item.resolvedAt || null,
      triageLevel: item.triageLevel || item.triage_level || null
    };
  }

  function reportSignature(item) {
    return [item.id, item.date, item.region, item.zone, item.side, item.intensity].join("|");
  }

  function migrateReports() {
    const merged = [];
    [REPORTS_KEY, ...LEGACY_REPORT_KEYS].forEach((key) => read(key).forEach((item) => merged.push(normalizeReport(item))));
    const unique = [...new Map(merged.map((item) => [reportSignature(item), item])).values()]
      .sort((a, b) => String(b.recorded_at).localeCompare(String(a.recorded_at)));
    write(REPORTS_KEY, unique);
    write("atlasHealthPainReports", unique);
    return unique;
  }

  function allReports() { return migrateReports(); }
  function saveReports(value) {
    const normalized = value.map(normalizeReport);
    write(REPORTS_KEY, normalized);
    write("atlasHealthPainReports", normalized);
  }

  function activate(name) {
    $$("[data-view]").forEach((view) => view.classList.toggle("active", view.dataset.view === name));
    $$("[data-tab]").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
    history.replaceState(null, "", `#${name}`);
    if (name === "prevention") renderPrevention();
  }

  function selectRegion(region) {
    selectedRegion = region;
    selectedSide = "";
    $$("[data-region]").forEach((button) => button.classList.toggle("active", button.dataset.region === region));
    $$("[data-side]").forEach((button) => button.classList.remove("active"));
    $("[data-pain-empty]").hidden = true;
    $("[data-pain-form]").hidden = false;
    $("[data-region-title]").textContent = regionLabels[region];
    $("[data-zone-options]").innerHTML = regions[region].map((zone, index) => `<label><input type="radio" name="zone" value="${escapeHtml(zone)}" ${index === 0 ? "checked" : ""}><span>${escapeHtml(zone)}</span></label>`).join("");
    $(".pain-detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function advice(report) {
    const alerts = report.redFlags.length;
    if (alerts) return { level: "urgent", title: "Arrêt de la course et avis professionnel recommandé", text: "Un signe d’alerte a été déclaré. Atlas ne propose pas de diagnostic ni de reprise automatique.", coach: "Suspendre les séances avec impacts. Une activité alternative ne peut être proposée que si elle est indolore.", review: "Réévaluation avant toute reprise." };
    if (report.intensity >= 7 || report.trigger === "Au repos ou la nuit") return { level: "high", title: "Charge de course à suspendre", text: "Privilégiez une activité sans douleur et demandez un avis si la douleur persiste ou s’aggrave.", coach: "Préparer le remplacement temporaire des séances de course par du repos ou une activité sans impact.", review: "Contrôle à 24–48 h." };
    if (report.intensity >= 4) return { level: "moderate", title: "Charge à réduire temporairement", text: "Évitez l’intensité et surveillez l’évolution à 24–48 h avant toute progression.", coach: "Conserver uniquement l’endurance facile tolérée et retirer provisoirement intensité, côtes et pliométrie.", review: "Réévaluation dans 24 h et après la prochaine activité." };
    return { level: "low", title: "Surveillance active", text: "Maintenez seulement les activités indolores et réévaluez après la prochaine séance.", coach: "Programme conservé ; surveillance de la douleur et de la réponse à la charge.", review: "Réévaluation après la prochaine séance." };
  }

  function renderReports() {
    const reports = allReports().filter((item) => !item.resolved);
    const count = $("[data-pain-count]"); if (count) count.textContent = reports.length;
    $("[data-active-reports]").innerHTML = reports.length ? reports.map((report) => {
      const guidance = advice(report);
      return `<article class="pain-report ${guidance.level}">
        <div class="pain-report-main"><p class="eyebrow">${escapeHtml(formatDate(report.date))}</p>
          <h3>${escapeHtml(report.regionLabel)} · ${escapeHtml(report.sideLabel)}</h3>
          <p><strong>${escapeHtml(report.zone)}</strong> · ${report.intensity}/10 · ${escapeHtml(report.trigger)}</p>
          <p>${escapeHtml(guidance.title)} — ${escapeHtml(guidance.text)}</p>
          ${report.notes ? `<small>${escapeHtml(report.notes)}</small>` : ""}
          <section class="pain-coach-impact"><span>IMPACT PROPOSÉ SUR ATLAS COACH</span><strong>${escapeHtml(guidance.coach)}</strong><small>${escapeHtml(guidance.review)}</small><em>Aucune modification automatique : toute adaptation doit être expliquée puis validée.</em></section>
        </div><button type="button" data-resolve="${report.id}">Marquer comme résolue</button></article>`;
    }).join("") : '<div class="empty-state"><strong>Aucune douleur active</strong><p>Vos futurs signalements apparaîtront ici avec un niveau de prudence et leur incidence proposée sur Atlas Coach.</p></div>';
    $$("[data-resolve]").forEach((button) => button.addEventListener("click", () => {
      const all = allReports();
      const item = all.find((report) => report.id === button.dataset.resolve);
      if (item) { item.resolved = true; item.resolvedAt = new Date().toISOString(); saveReports(all); renderReports(); renderTimeline(); }
    }));
  }

  function savePain(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!selectedSide) { alert("Choisissez le côté douloureux."); return; }
    const report = normalizeReport({
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), date: new Date().toISOString().slice(0, 10), region: selectedRegion,
      side: selectedSide, sideLabel: sideLabels[selectedSide],
      zone: form.elements.zone.value, intensity: Number(form.elements.intensity.value), onset: form.elements.onset.value,
      trigger: form.elements.trigger.value, redFlags: $$('[name="redFlag"]', form).filter((input) => input.checked).map((input) => input.value),
      notes: form.elements.notes.value.trim(), resolved: false
    });
    const reports = allReports(); reports.unshift(report); saveReports(reports);
    const guidance = advice(report);
    const events = read(EVENTS_KEY); events.unshift({ id: `pain-${report.id}`, date: report.date, type: "Douleur ou blessure", title: `${report.regionLabel} ${report.sideLabel} · ${report.zone}`, note: `${report.intensity}/10 — ${guidance.title}. Atlas Coach : ${guidance.coach}` }); write(EVENTS_KEY, events);
    window.dispatchEvent(new CustomEvent("atlas:health-report-updated", { detail: report }));
    form.reset(); $("[data-intensity-value]").textContent = "3/10"; renderReports(); renderTimeline();
  }

  function renderTimeline() {
    const reportEvents = allReports().map((report) => ({ id: `canonical-${report.id}`, date: report.date, type: report.resolved ? "Douleur résolue" : "Douleur suivie", title: `${report.regionLabel} ${report.sideLabel} · ${report.zone}`, note: `${report.intensity}/10 — ${advice(report).title}` }));
    const events = [...read(EVENTS_KEY), ...reportEvents];
    const unique = [...new Map(events.map((item) => [`${item.date}|${item.type}|${item.title}`, item])).values()].sort((a, b) => b.date.localeCompare(a.date));
    $("[data-body-timeline]").innerHTML = unique.length ? unique.map((item) => `<article><time datetime="${item.date}">${escapeHtml(formatDate(item.date))}</time><div><span>${escapeHtml(item.type)}</span><h3>${escapeHtml(item.title)}</h3>${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}</div></article>`).join("") : '<div class="empty-state"><strong>Votre frise commence ici</strong><p>Ajoutez une douleur, une reprise ou un soin utile à votre suivi.</p></div>';
  }

  function executionDate(item) { return item?.activity?.started_at || item?.activity?.start_time || item?.started_at || ""; }
  function activityOf(item) { return item?.activity || item?.normalized_activity || {}; }
  function distanceKm(item) { const a = activityOf(item); return Number(a.distance_km || (a.distance_meters ? a.distance_meters / 1000 : 0) || 0); }
  function isRunning(item) { const a = activityOf(item); return /run|running|course/i.test(`${a.sport || ""} ${a.activity_type || ""} ${item?.planned_workout?.title || ""}`) && !/cycl|vélo|bike/i.test(`${a.sport || ""} ${a.activity_type || ""}`); }
  function isIntense(item) { return /vo2|sv2|seuil|sprint|interval|tempo/i.test(`${item?.planned_workout?.title || ""} ${item?.analysis?.session_type || ""}`); }

  async function renderPrevention() {
    try {
      const response = await fetch("/api/atlas-coach/executions?limit=200", { cache: "no-store" });
      if (!response.ok) throw new Error("API indisponible");
      const payload = await response.json();
      const now = Date.now();
      const runs = (payload.executions || payload || []).filter(isRunning).filter((item) => executionDate(item));
      const recent = runs.filter((item) => now - new Date(executionDate(item)).getTime() <= 7 * 86400000);
      const reference = runs.filter((item) => now - new Date(executionDate(item)).getTime() <= 35 * 86400000);
      const recentKm = recent.reduce((sum, item) => sum + distanceKm(item), 0);
      const referenceKm = reference.reduce((sum, item) => sum + distanceKm(item), 0) / Math.max(1, Math.min(5, Math.ceil(35 / 7)));
      const intense = recent.filter(isIntense).length;
      const pains = allReports().filter((item) => !item.resolved).length;
      $("[data-load-7d]").textContent = `${recentKm.toFixed(1).replace(".", ",")} km`;
      $("[data-load-reference]").textContent = `${referenceKm.toFixed(1).replace(".", ",")} km/sem.`;
      $("[data-intensity-count]").textContent = intense;
      const ratio = referenceKm ? recentKm / referenceKm : null;
      let title = "Charge récente cohérente avec votre référence";
      let text = "La lecture reste individualisée et doit être confrontée à vos sensations.";
      const points = [];
      if (ratio !== null && ratio > 1.25) { title = "Hausse de volume à surveiller"; text = "Le volume récent dépasse nettement votre moyenne disponible. Cela signale une progression inhabituelle, pas un seuil de blessure."; points.push("Éviter d’ajouter simultanément volume et intensité."); }
      else if (ratio !== null && ratio < 0.65) points.push("La charge récente est inférieure à votre référence personnelle.");
      if (intense >= 3) points.push("Trois séances intenses ou plus ont été détectées sur sept jours.");
      if (pains) { title = "La charge doit être lue avec vos douleurs actives"; points.push(`${pains} douleur(s) active(s) : leur évolution est prioritaire sur l’indicateur de charge.`); }
      if (!points.length) points.push("Aucun signal combiné inhabituel n’est détecté avec les données disponibles.");
      $("[data-prevention-title]").textContent = title; $("[data-prevention-text]").textContent = text;
      $("[data-prevention-points]").innerHTML = points.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
    } catch {
      $("[data-prevention-title]").textContent = "Données d’entraînement indisponibles";
      $("[data-prevention-text]").textContent = "Démarrez le serveur Atlas pour comparer la charge récente à votre historique.";
      $("[data-prevention-points]").innerHTML = "<li>Vos signalements locaux restent conservés sur cet appareil.</li>";
    }
  }

  const shortcuts = $("[data-region-shortcuts]");
  shortcuts.innerHTML = Object.entries(regionLabels).map(([key, label]) => `<button type="button" data-region="${key}">${label}</button>`).join("");
  $$("[data-tab]").forEach((button) => button.addEventListener("click", () => activate(button.dataset.tab)));
  $$("[data-region]").forEach((button) => button.addEventListener("click", () => selectRegion(button.dataset.region)));
  $$("[data-side]").forEach((button) => button.addEventListener("click", () => { selectedSide = button.dataset.side; $$("[data-side]").forEach((item) => item.classList.toggle("active", item === button)); }));
  $('[name="intensity"]').addEventListener("input", (event) => { $("[data-intensity-value]").textContent = `${event.target.value}/10`; });
  $("[data-pain-form]").addEventListener("submit", savePain);
  $("[data-anatomy-toggle]").addEventListener("click", () => { $("[data-anatomy-panel]").hidden = false; const frame = $("[data-anatomy-frame]"); if (!frame.src) frame.src = `./biomecanique.html?region=${encodeURIComponent(selectedRegion)}&embed=1`; $("[data-anatomy-panel]").scrollIntoView({ behavior: "smooth" }); });
  $("[data-anatomy-close]").addEventListener("click", () => { $("[data-anatomy-panel]").hidden = true; });
  $("[data-event-toggle]").addEventListener("click", () => { const form = $("[data-event-form]"); form.hidden = !form.hidden; if (!form.hidden && !form.elements.date.value) form.elements.date.value = new Date().toISOString().slice(0, 10); });
  $("[data-event-form]").addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; const events = read(EVENTS_KEY); events.unshift({ id: String(Date.now()), date: form.elements.date.value, type: form.elements.type.value, title: form.elements.title.value.trim(), note: form.elements.note.value.trim() }); write(EVENTS_KEY, events); form.reset(); form.hidden = true; renderTimeline(); });

  window.addEventListener("atlas:pain-report-saved", () => { migrateReports(); renderReports(); renderTimeline(); });
  window.addEventListener("storage", (event) => { if ([REPORTS_KEY, ...LEGACY_REPORT_KEYS].includes(event.key)) { migrateReports(); renderReports(); renderTimeline(); } });

  const selectedAvatar = localStorage.getItem("atlasPreselectedAvatar") || "male";
  $("[data-atlas-avatar-image]").src = selectedAvatar === "female" ? "./assets/atlas-avatar-femme-clean-final.png?v=2" : "./assets/atlas-avatar-homme-clean-final.png?v=2";
  migrateReports(); renderReports(); renderTimeline();
  const initial = location.hash.slice(1); activate(["injuries", "prevention", "timeline"].includes(initial) ? initial : "injuries");
})();
