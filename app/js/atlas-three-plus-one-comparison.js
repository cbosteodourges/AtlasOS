"use strict";

(() => {
  const root = document.getElementById("threePlusOneComparison");
  if (!root) return;

  const esc = value => String(value ?? "—")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");

  const minutes = value => Number.isFinite(Number(value))
    ? `${Math.round(Number(value))} min`
    : "Non calculé";

  const activeWeekByDate = (weeks, startDate) => {
    const start = new Date(`${startDate}T12:00:00`);
    return (weeks || []).find(week => (week.sessions || []).some(session => {
      const day = new Date(`${session.date}T12:00:00`);
      return day >= start && day < new Date(start.getTime() + 7 * 86400000);
    }));
  };

  const sessionList = (sessions, pilot = false) => (sessions || []).map(session => {
    const date = session.workout_date || session.date;
    const label = date ? new Date(`${date}T12:00:00`).toLocaleDateString("fr-FR", {
      weekday: "short", day: "numeric"
    }) : "—";
    const specific = session.is_specific ? '<i title="Séance spécifique">SPÉCIFIQUE</i>' : "";
    return `<li><span>${esc(label)}</span><div><strong>${esc(session.title)}</strong><small>${minutes(session.duration_minutes)}${pilot && session.specific_minutes ? ` · ${esc(session.specific_minutes)} min spécifiques` : ""}</small></div>${specific}</li>`;
  }).join("");

  const totalDuration = sessions => (sessions || []).reduce(
    (sum, session) => sum + (Number(session.duration_minutes) || 0), 0
  );

  const render = payload => {
    const pilot = payload?.pilot;
    if (!payload?.comparison_only || !pilot?.weeks) {
      throw new Error("Prévisualisation comparative invalide.");
    }

    const activeWeeks = payload.active?.weeks || [];
    const cards = pilot.weeks.map((week, index) => {
      const active = activeWeekByDate(activeWeeks, week.start_date);
      const activeSessions = active?.sessions || [];
      const activeSpecific = Number(active?.specific_session_count) || 0;
      const activeTotal = Number(active?.total_duration_minutes) || totalDuration(activeSessions);
      const phase = active?.phase || "hors fenêtre active";
      return `
        <article class="pilot-week-card">
          <header>
            <div><span>SEMAINE ${index + 1}</span><strong>${week.is_consolidation ? "Consolidation" : "Multistimulus"}</strong></div>
            <small>${esc(new Date(`${week.start_date}T12:00:00`).toLocaleDateString("fr-FR", {day:"numeric", month:"short"}))}</small>
          </header>
          <div class="pilot-week-metrics">
            <div><span>Programme actuel</span><strong>${activeSpecific} spécifique${activeSpecific > 1 ? "s" : ""}</strong><small>${minutes(activeTotal)} · ${esc(phase)}</small></div>
            <div><span>Pilote 3+1</span><strong>${week.specific_session_count} spécifique${week.specific_session_count > 1 ? "s" : ""}</strong><small>${minutes(week.total_duration_minutes)} · ${esc(week.specific_minutes)} min ciblées</small></div>
          </div>
          <details>
            <summary>Comparer les séances</summary>
            <div class="pilot-session-columns">
              <section><h4>Programme actuel</h4><ul>${sessionList(activeSessions) || "<li>Aucune séance active dans cette fenêtre.</li>"}</ul></section>
              <section><h4>Proposition 3+1</h4><ul>${sessionList(week.sessions, true)}</ul></section>
            </div>
          </details>
        </article>`;
    }).join("");

    root.innerHTML = `
      <section class="pilot-comparison" aria-labelledby="pilotComparisonTitle">
        <header class="pilot-comparison-header">
          <div><span>ATLAS RESEARCH · PRÉVISUALISATION</span><h3 id="pilotComparisonTitle">Programme actuel ou Norwegian Singles 3+1</h3><p>Comparaison du ${esc(payload.window?.start)} au ${esc(payload.window?.end)}. Le pilote reste isolé et ne remplace aucune séance.</p></div>
          <strong class="pilot-status">NON ACTIVÉ</strong>
        </header>
        <div class="pilot-safety">
          <span>Plafond : ${esc(pilot.specific_minutes_cap)} min spécifiques/semaine</span>
          <span>Wellness : ${esc(pilot.wellness_status)}</span>
          <span>Surface : ${esc(pilot.goal_surface)}</span>
        </div>
        <div class="pilot-week-grid">${cards}</div>
        <footer><strong>Validation obligatoire</strong><p>${esc(payload.activation?.message || "Votre validation est requise avant toute modification.")}</p></footer>
      </section>`;
  };

  const load = async () => {
    const sources = [
      window.ATLAS_THREE_PLUS_ONE_PREVIEW_URL,
      "../atlas-data/private/three-plus-one-pilot-preview.json",
      "/atlas-data/private/three-plus-one-pilot-preview.json"
    ].filter(Boolean);
    for (const source of sources) {
      try {
        const response = await fetch(`${source}?v=${Date.now()}`, {cache:"no-store"});
        if (!response.ok) continue;
        render(await response.json());
        return;
      } catch (error) {
        console.debug("Comparaison 3+1 indisponible.", source, error);
      }
    }
    root.innerHTML = '<div class="pilot-comparison-unavailable"><strong>Comparaison 3+1 à générer</strong><span>Exécutez le script de prévisualisation puis rechargez cette page.</span></div>';
  };

  load();
})();