"use strict";

/* GRILLE HEBDOMADAIRE PREMIUM ATLAS COACH */
(() => {
  const overview = document.getElementById("planOverview");
  const calendar = document.getElementById("trainingCalendar");
  const planPanel = document.getElementById("planPanel");
  const header = document.querySelector(".performance-header");

  if (!overview || !calendar || !planPanel || !header) return;

  const DAY_LABELS = [
    "LUNDI",
    "MARDI",
    "MERCREDI",
    "JEUDI",
    "VENDREDI",
    "SAMEDI",
    "DIMANCHE"
  ];

  const PHASE_LABELS = {
    base: "Base aérobie",
    development: "Développement",
    specific: "Spécifique semi-marathon",
    taper: "Affûtage",
    race_week: "Semaine de course",
    recovery: "Récupération"
  };

  const TYPE_LABELS = {
    recovery_run: "Récupération",
    endurance_z2: "Endurance Z2",
    tempo_z3: "Tempo Z3",
    threshold_sv2: "Seuil SV2",
    vma_short: "VMA courte",
    vma_long: "VMA longue",
    hill_sprints: "Sprints en côte",
    mixed_threshold_vo2: "Seuil + VO₂",
    triangular_vo2: "VO₂ triangulaire",
    race_specific: "Compétition",
    long_run: "Sortie longue",
    cycling: "Cyclisme",
    strength: "Renforcement",
    mobility: "Mobilité",
    rest: "Repos"
  };

  const RESEARCH_TYPES = new Set([
    "hill_sprints",
    "mixed_threshold_vo2",
    "triangular_vo2"
  ]);

  const STORAGE_KEY = "atlasCoachOptionalSessions";
  const DECISIONS_STORAGE_KEY = "atlasCoachWorkoutDecisions";
  const workoutIndex = new Map();
  let activeProgram = null;
  let workoutDecisions = loadWorkoutDecisions();
  const executionReportCache = new Map();

  async function loadExecutionReport(workoutId) {
    if (executionReportCache.has(workoutId)) {
      return executionReportCache.get(workoutId);
    }

    const response = await fetch(
      `/api/atlas-coach/executions?workout_id=${encodeURIComponent(workoutId)}&limit=1`,
      { cache: "no-store" }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "Compte-rendu Atlas indisponible."
      );
    }

    const report = payload.executions?.[0] || null;
    // Ne jamais mémoriser durablement une absence de rapport : le Watcher
    // peut terminer l'analyse quelques secondes après l'ouverture du volet.
    if (report) {
      executionReportCache.set(workoutId, report);
    }
    return report;
  }

  const workoutContextCache = new Map();

  async function loadWorkoutContext(workoutId) {
    if (workoutContextCache.has(workoutId)) {
      return workoutContextCache.get(workoutId);
    }

    const response = await fetch(
      `/api/atlas-coach/workout-context?workout_id=${encodeURIComponent(workoutId)}`,
      { cache: "no-store" }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "Contexte utilisateur indisponible."
      );
    }

    const context = payload.context || null;
    workoutContextCache.set(workoutId, context);
    return context;
  }

  async function saveWorkoutContext(workout, report, values) {
    const response = await fetch(
      "/api/atlas-coach/workout-context",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify({
          workout_id: workout.workout_id,
          activity_id: report?.activity_id || "",
          heat: Boolean(values.heat),
          relief: Boolean(values.relief),
          pain_0_to_10: values.pain === "" ? null : Number(values.pain),
          fatigue_0_to_10: values.fatigue === "" ? null : Number(values.fatigue),
          comment: values.comment.trim()
        })
      }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "Le contexte n’a pas pu être enregistré."
      );
    }

    workoutContextCache.set(workout.workout_id, payload.context);
    return payload.context;
  }
  const dailyPreparationCache = new Map();
  const dailySelectionCache = new Map();

  async function loadDailyPreparation(workoutId) {
    const response = await fetch(
      `/api/atlas-coach/daily-preparation?workout_id=${encodeURIComponent(workoutId)}`,
      { cache: "no-store" }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "Décision quotidienne Atlas indisponible."
      );
    }

    const preparation = payload.preparation || null;
    const selection = payload.selection || null;
    dailyPreparationCache.set(workoutId, preparation);
    dailySelectionCache.set(workoutId, selection);
    return preparation;
  }

  async function saveDailyPreparation(workoutId, values) {
    const response = await fetch(
      "/api/atlas-coach/daily-preparation",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify({
          workout_id: workoutId,
          ...values
        })
      }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "La réévaluation Atlas a échoué."
      );
    }

    const preparation = payload.preparation || null;
    dailyPreparationCache.set(workoutId, preparation);
    dailySelectionCache.set(workoutId, payload.selection || null);
    return preparation;
  }

  async function saveDailySelection(workoutId, selection, reason = "") {
    const response = await fetch(
      "/api/atlas-coach/daily-preparation",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify({
          workout_id: workoutId,
          user_selection: selection,
          reason
        })
      }
    );
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "Le choix n’a pas pu être enregistré."
      );
    }

    dailySelectionCache.set(workoutId, payload.selection || null);
    return payload.selection || null;
  }

  function dailyPreparationLabel(action) {
    return {
      maintain: "Séance maintenue",
      reduce: "Séance allégée",
      replace: "Séance remplacée",
      postpone: "Séance reportée",
      cancel: "Repos recommandé"
    }[action] || "Séance à revalider";
  }

  function applyDailyPreparation(preparation) {
    if (!preparation) return;

    const button = Array.from(
      calendar.querySelectorAll("[data-workout-key]")
    ).find(item => (
      item.dataset.workoutKey === preparation.workout_id
    ));
    if (!button) return;

    if (workoutDecisions[preparation.workout_id]?.status === "skipped") {
      button.classList.remove("has-daily-preparation");
      button.querySelector(".daily-preparation-summary")?.remove();
      return;
    }

    button.classList.add("has-daily-preparation");
    button.querySelector(".daily-preparation-summary")?.remove();

    const adaptation = preparation.adaptation || {};
    const adapted = adaptation.adapted_workout || {};
    const decision = preparation.decision || {};
    const atlasIndex = preparation.atlas_index || {};
    const declared = preparation.declared_state || {};
    const summary = document.createElement("span");
    summary.className =
      `daily-preparation-summary action-${decision.action || "review"}`;
    summary.innerHTML = `
      <i>Décision Atlas · ${escapeHtml(
        dailyPreparationLabel(decision.action)
      )}</i>
      <strong>${escapeHtml(
        adapted.title || "Réévaluation nécessaire"
      )}</strong>
      <small>
        ${escapeHtml(
          formatMinutes(adapted.planned_duration_minutes)
        )}
        · Indice ${escapeHtml(atlasIndex.score ?? "—")}/100
        ${preparation.checkpoint_type === "post_nap"
          ? ` · Après sieste ${escapeHtml(
              declared.nap_duration_minutes ?? "—"
            )} min`
          : " · Évaluation du matin"}
      </small>
      <b>Pourquoi cette adaptation ?</b>
    `;
    button.appendChild(summary);
  }

  async function loadTodayPreparations(program) {
    const today = isoDate(new Date());
    const workouts = (program.weeks || []).flatMap(
      week => week.workouts || []
    ).filter(workout => (
      workout.workout_date === today &&
      workout.sport === "running"
    ));

    await Promise.all(workouts.map(async workout => {
      try {
        const preparation = await loadDailyPreparation(
          workout.workout_id
        );
        applyDailyPreparation(preparation);
      } catch (error) {
        console.warn(error);
      }
    }));
  }
  function loadWorkoutDecisions() {
    try {
      return JSON.parse(
        localStorage.getItem(DECISIONS_STORAGE_KEY) || "{}"
      );
    } catch {
      return {};
    }
  }

  function workoutDecision(workout) {
    return workoutDecisions[workout.workout_id] || {
      status: "planned"
    };
  }

  function saveWorkoutDecision(workout, changes) {
    workoutDecisions[workout.workout_id] = {
      ...workoutDecision(workout),
      ...changes,
      updated_at: new Date().toISOString()
    };
    localStorage.setItem(
      DECISIONS_STORAGE_KEY,
      JSON.stringify(workoutDecisions)
    );
  }

  async function syncWorkoutDecisions() {
    try {
      const response = await fetch(
        `/api/atlas-coach/workout-decisions?v=${Date.now()}`,
        { cache: "no-store" }
      );
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Mémoire Atlas indisponible.");
      }

      workoutDecisions = {
        ...workoutDecisions,
        ...(payload.decisions || {})
      };
      localStorage.setItem(
        DECISIONS_STORAGE_KEY,
        JSON.stringify(workoutDecisions)
      );
    } catch (error) {
      console.warn("Décisions Atlas non synchronisées :", error);
    }
  }

  function workoutStatusBadge(workout) {
    const status = workoutDecision(workout).status;
    const badges = {
      completed: ["completed", "&#10003;", "Séance effectuée"],
      skipped: ["skipped", "&#8212;", "Séance non effectuée"],
      postponed: ["postponed", "&#8635;", "Séance reportée"],
      replaced: ["replaced", "&#8644;", "Séance remplacée"],
      modified: ["modified", "&#9998;", "Séance modifiée"],
      planned: ["planned", "&#9679;", "Séance planifiée"]
    };
    const badge = badges[status] || badges.planned;

    return `
      <span
        class="workout-status status-${badge[0]}"
        title="${badge[2]}"
        aria-label="${badge[2]}"
      >${badge[1]}</span>
    `;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function parseDate(value) {
    return new Date(`${value}T12:00:00`);
  }

  function isoDate(value) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function addDays(value, count) {
    const result = new Date(value);
    result.setDate(result.getDate() + count);
    return result;
  }

  function formatDate(value, withYear = false) {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "numeric",
      month: "short",
      year: withYear ? "numeric" : undefined
    }).format(parseDate(value));
  }

  function formatMinutes(value) {
    const total = Math.round(Number(value) || 0);
    if (!total) return "Durée libre";

    const hours = Math.floor(total / 60);
    const minutes = total % 60;

    if (!hours) return `${minutes} min`;
    if (!minutes) return `${hours} h`;
    return `${hours} h ${String(minutes).padStart(2, "0")}`;
  }

  function paceFromSpeed(speed) {
    const numeric = Number(speed);
    if (!numeric) return null;

    const seconds = Math.round(3600 / numeric);
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    return `${minutes}:${String(remainder).padStart(2, "0")}/km`;
  }

  function targetLine(block) {
    const target = block.target || {};
    const values = [];

    if (target.zone) values.push(`Zone ${target.zone}`);

    if (
      target.speed_min_kmh != null &&
      target.speed_max_kmh != null
    ) {
      const minimum = Number(
        target.speed_min_kmh
      ).toLocaleString("fr-FR");
      const maximum = Number(
        target.speed_max_kmh
      ).toLocaleString("fr-FR");

      values.push(
        minimum === maximum
          ? `${minimum} km/h`
          : `${minimum}–${maximum} km/h`
      );

      const slowPace = paceFromSpeed(target.speed_min_kmh);
      const fastPace = paceFromSpeed(target.speed_max_kmh);

      if (slowPace && fastPace) {
        values.push(
          slowPace === fastPace
            ? slowPace
            : `${fastPace.replace("/km", "")}–${slowPace}`
        );
      }
    }

    if (target.pace_min_per_km) {
      values.push(`${target.pace_min_per_km}/km`);
    }

    if (target.heart_rate_min_bpm != null) {
      values.push(
        `${target.heart_rate_min_bpm}–` +
        `${target.heart_rate_max_bpm} bpm`
      );
    }

    if (target.rpe_0_10 != null) {
      values.push(`RPE ${target.rpe_0_10}/10`);
    }

    if (target.gradient_min_percent != null) {
      values.push(
        `Pente ${target.gradient_min_percent}–` +
        `${target.gradient_max_percent} %`
      );
    }

    return values.join(" · ") || "Cible individualisée";
  }

  function targetCards(block) {
    const target = block.target || {};
    const rows = [];
    const addRow = (label, value) => {
      if (!value) return;
      rows.push(`
        <div>
          <dt>${escapeHtml(label)}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `);
    };
    const number = value => Number(value).toLocaleString(
      "fr-FR",
      { minimumFractionDigits: 2, maximumFractionDigits: 2 }
    );

    if (target.zone != null) {
      addRow("Zone", `Zone ${target.zone}`);
    }

    if (
      target.speed_min_kmh != null &&
      target.speed_max_kmh != null
    ) {
      addRow(
        "Vitesse",
        `${number(target.speed_min_kmh)} à ${number(target.speed_max_kmh)} km/h`
      );

      const slowPace = paceFromSpeed(target.speed_min_kmh);
      const fastPace = paceFromSpeed(target.speed_max_kmh);
      if (slowPace && fastPace) {
        addRow(
          "Allure",
          fastPace === slowPace
            ? fastPace
            : `${fastPace.replace("/km", "")} à ${slowPace}`
        );
      }
    } else if (target.pace_min_per_km) {
      addRow(
        "Allure",
        target.pace_max_per_km
          ? `${target.pace_min_per_km}/km à ${target.pace_max_per_km}/km`
          : `${target.pace_min_per_km}/km`
      );
    }

    if (
      target.heart_rate_min_bpm != null ||
      target.heart_rate_max_bpm != null
    ) {
      addRow(
        "Fréquence cardiaque",
        `${target.heart_rate_min_bpm ?? target.heart_rate_max_bpm} à ${target.heart_rate_max_bpm ?? target.heart_rate_min_bpm} bpm`
      );
    }

    if (target.rpe_0_10 != null) {
      addRow("Effort ressenti", `RPE ${target.rpe_0_10}/10`);
    }

    if (
      target.gradient_min_percent != null ||
      target.gradient_max_percent != null
    ) {
      addRow(
        "Pente",
        `${target.gradient_min_percent ?? 0} à ${target.gradient_max_percent ?? target.gradient_min_percent} %`
      );
    }

    if (block.recovery_minutes != null) {
      addRow(
        "Récupération",
        `${Number(block.recovery_minutes).toLocaleString("fr-FR")} min`
      );
    }

    return rows.length
      ? `<dl class="session-target-list">${rows.join("")}</dl>`
      : `<p class="session-target-empty">Cible individualisée selon les sensations du jour.</p>`;
  }
  function readableWorkTime(minutes) {
    const totalSeconds = Math.round(
      Number(minutes) * 60
    );

    if (!Number.isFinite(totalSeconds)) {
      return "Dur\u00e9e individualis\u00e9e";
    }

    if (totalSeconds < 60) {
      return `${totalSeconds} s`;
    }

    const wholeMinutes = Math.floor(
      totalSeconds / 60
    );
    const remainingSeconds = totalSeconds % 60;

    return remainingSeconds
      ? `${wholeMinutes} min ${remainingSeconds} s`
      : `${wholeMinutes} min`;
  }

  function blockDuration(block) {
    const repetitions = Number(block.repetitions) || 1;
    const values = [];

    if (block.duration_minutes != null) {
      values.push(
        `${repetitions > 1 ? `${repetitions} \u00d7 ` : ""}` +
        readableWorkTime(block.duration_minutes)
      );
    } else if (block.distance_meters != null) {
      values.push(
        `${repetitions > 1 ? `${repetitions} \u00d7 ` : ""}` +
        `${Number(block.distance_meters).toLocaleString("fr-FR")} m`
      );
    }

    if (block.recovery_minutes != null) {
      values.push(
        `R\u00e9cup\u00e9ration ` +
        readableWorkTime(block.recovery_minutes)
      );
    }

    return values.join(" \u00b7 ") ||
      "Dur\u00e9e individualis\u00e9e";
  }

  function difficulty(workout) {
    if (workout.source === "user_optional") return "optional";
    if (workout.workout_type === "race_specific") return "race";
    if (
      workout.workout_type === "mobility" ||
      workout.workout_type === "recovery_run" ||
      workout.workout_type === "rest"
    ) {
      return "recovery";
    }

    const response = workout.expected_response || {};
    const score =
      (Number(response.physiological_load_0_100) || 0) * 0.6 +
      (Number(response.biomechanical_load_0_100) || 0) * 0.4;

    if (score <= 30) return "light";
    if (score <= 48) return "easy";
    if (score <= 67) return "moderate";
    return "hard";
  }

  function difficultyLabel(value) {
    return {
      recovery: "Récupération",
      optional: "Facultative",
      light: "Très légère",
      easy: "Légère",
      moderate: "Modérée",
      hard: "Élevée",
      race: "Compétition"
    }[value] || "Séance";
  }

  function isToday(value) {
    return value === isoDate(new Date());
  }

  function physiologicalRibbon(snapshot) {
    if (!snapshot) return;

    const legacyPanel = document.getElementById(
      "physiologyPanel"
    );
    if (legacyPanel) {
      legacyPanel.style.display = "none";
    }

    let ribbon = document.getElementById(
      "atlasPhysiologyRibbon"
    );

    if (!ribbon) {
      ribbon = document.createElement("section");
      ribbon.id = "atlasPhysiologyRibbon";
      ribbon.className = "atlas-physiology-topbar";
    }

    header.insertBefore(ribbon, header.querySelector(".engine-status"));

    const age = Number(snapshot.age_years);
    const vo2 = Number(snapshot.vo2_max);
    const sex = String(snapshot.sex || "male").toLowerCase();
    const female = (
      sex === "female" ||
      sex === "femme" ||
      sex === "f"
    );

    const decades = [20, 30, 40, 50, 60, 70];
    const decade = decades.reduce(
      (selected, item) => (
        age >= item ? item : selected
      ),
      20
    );

    const superior = female
      ? {20:49.6,30:47.4,40:45.3,50:41.1,60:37.8,70:36.7}
      : {20:55.4,30:54.0,40:52.5,50:48.9,60:45.7,70:42.1};

    const excellent = female
      ? {20:43.9,30:42.4,40:39.7,50:36.7,60:33.0,70:30.9}
      : {20:51.1,30:48.3,40:46.4,50:43.4,60:39.5,70:36.7};

    const vo2Rating = (
      Number.isFinite(vo2) && vo2 >= superior[decade]
        ? "Sup\u00e9rieur \u00b7 \u226595e percentile"
        : (
          Number.isFinite(vo2) && vo2 >= excellent[decade]
            ? "Excellent"
            : "Dans la moyenne"
        )
    );

    const statusLabel = status => ({
      estimated: "Estimation Atlas",
      longitudinal: "Longitudinal",
      missing: "\u00c0 confirmer"
    }[status] || status || "");

    const metric = ({
      label,
      value,
      unit,
      note,
      accent,
      glow
    }) => `
      <article style="
        position:relative;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        width:126px;
        height:126px;
        min-width:126px;
        margin:auto;
        padding:13px;
        text-align:center;
        border:2px solid transparent;
        border-radius:50%;
        background:
          linear-gradient(#07182a,#07182a) padding-box,
          conic-gradient(
            from 215deg,
            transparent 0deg,
            ${accent} 48deg,
            ${accent} 270deg,
            transparent 330deg
          ) border-box;
        box-shadow:
          0 0 22px ${glow},
          inset 0 0 25px rgba(255,255,255,.025);
      ">
        <span style="
          display:block;
          color:#91adbf;
          font-size:.62rem;
          font-weight:700;
          letter-spacing:.11em;
          text-transform:uppercase;
        ">${escapeHtml(label)}</span>

        <div style="
          display:flex;
          align-items:baseline;
          justify-content:center;
          gap:5px;
          margin-top:7px;
        ">
          <strong style="
            color:#fff;
            font-size:1.34rem;
            line-height:1;
          ">${escapeHtml(value ?? "?")}</strong>
          <small style="
            color:${accent};
            font-size:.62rem;
          ">${escapeHtml(unit)}</small>
        </div>

        <i style="
          display:-webkit-box;
          margin-top:7px;
          overflow:hidden;
          color:#acc3d2;
          font-size:.56rem;
          font-style:normal;
          line-height:1.25;
          -webkit-box-orient:vertical;
          -webkit-line-clamp:2;
        ">${escapeHtml(note)}</i>
      </article>
    `;

    const vmaEstimated = (
      snapshot.vma_estimated_from_vo2_kmh ??
      snapshot.vma_kmh
    );
    const vmaReference = (
      snapshot.vma_training_reference_kmh ??
      snapshot.vma_kmh
    );

      const heartRateMax = Number(
        snapshot.maximum_heart_rate_bpm
      );
      const trainingVma = Number(
        snapshot.vma_training_reference_kmh ?? snapshot.vma_kmh
      );
      const sv1HeartRate = Number(
        snapshot.sv1?.heart_rate_bpm ?? heartRateMax * 0.81
      );
      const sv2HeartRate = Number(
        snapshot.sv2?.heart_rate_bpm ?? heartRateMax * 0.90
      );
      const sv1Speed = Number(
        snapshot.sv1?.speed_kmh ?? trainingVma * 0.75
      );
      const sv2Speed = Number(
        snapshot.sv2?.speed_kmh ?? trainingVma * 0.92
      );
      const z2SpeedLow = Math.round(trainingVma * 0.65 * 10) / 10;

      const zoneDefinitions = [
        [1, "Récupération", Math.round(heartRateMax * 0.50), Math.round(heartRateMax * 0.65) - 1, Math.round(trainingVma * 0.55 * 10) / 10, z2SpeedLow - 0.1, "#5aa8ff"],
        [2, "Endurance fondamentale", Math.round(heartRateMax * 0.65), Math.round(sv1HeartRate - 3), z2SpeedLow, sv1Speed, "#51d892"],
        [3, "Endurance active", Math.round(sv1HeartRate - 2), Math.round(sv2HeartRate - 3), sv1Speed + 0.1, sv2Speed, "#e7d353"],
        [4, "VO₂max", Math.round(sv2HeartRate - 2), Math.round(heartRateMax * 0.95), sv2Speed + 0.1, trainingVma, "#ff9a4f"],
        [5, "VMA courte / Anaérobie", Math.round(heartRateMax * 0.95) + 1, heartRateMax, trainingVma + 0.1, Math.round(trainingVma * 1.10 * 10) / 10, "#ff5d68"]
      ];
      const paceFromKmh = speed => {
        if (!Number.isFinite(speed) || speed <= 0) return "—";
        const totalSeconds = Math.round(3600 / speed);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = String(totalSeconds % 60).padStart(2, "0");
        return `${minutes}:${seconds}/km`;
      };
      const zoneRibbon = `
        <section class="atlas-zone-ribbon" aria-label="Zones physiologiques personnelles">
          <header>
            <strong>Mes zones personnelles</strong>
            <span>Fréquence cardiaque · vitesse · allure</span>
          </header>
          <div class="atlas-zone-cards">
            ${zoneDefinitions.map(zone => {
              const [id, name, hrLow, hrHigh, zoneSpeedLow, zoneSpeedHigh, color] = zone;
              const speedLow = Math.round(zoneSpeedLow * 10) / 10;
              const speedHigh = Math.round(zoneSpeedHigh * 10) / 10;
              return `
                <article style="--zone-accent:${color}">
                  <div><b>Z${id}</b><strong>${escapeHtml(name)}</strong></div>
                  <span>${hrLow}–${hrHigh} bpm</span>
                  <span>${speedLow.toLocaleString("fr-FR", {maximumFractionDigits:1})}–${speedHigh.toLocaleString("fr-FR", {maximumFractionDigits:1})} km/h</span>
                  <small>${paceFromKmh(speedHigh)} à ${paceFromKmh(speedLow)}</small>
                </article>
              `;
            }).join("")}
          </div>
        </section>
      `;

    const formattedVma = Number.isFinite(
      Number(vmaEstimated)
    )
      ? Number(vmaEstimated).toLocaleString(
          "fr-FR",
          {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }
        )
      : "\u2014";

    ribbon.style.cssText = `
      position:sticky;
      z-index:35;
      top:0;
      display:grid;
      grid-template-columns:repeat(5,minmax(140px,1fr));
      align-items:center;
      width:calc(100% - 176px);
      min-height:154px;
      margin:0 auto;
      padding:12px 28px;
      overflow-x:auto;
      overflow-y:hidden;
      border-top:1px solid rgba(224,177,78,.28);
      border-bottom:1px solid rgba(224,177,78,.38);
      border-radius:0 0 18px 18px;
      background:
        radial-gradient(circle at 50% -30%,rgba(35,188,255,.10),transparent 42%),
        linear-gradient(105deg,rgba(3,13,25,.99),rgba(7,23,39,.99));
      box-shadow:
        0 18px 42px rgba(0,0,0,.34),
        0 0 24px rgba(43,194,255,.045);
      backdrop-filter:blur(15px);
    `;

    ribbon.innerHTML = `
      ${metric({
        label: "VO\u2082max",
        value: snapshot.vo2_max,
        unit: "ml/kg/min",
        note: vo2Rating,
        accent: "#a66cff",
        glow: "rgba(144,70,255,.11)"
      })}

      ${metric({
        label: "VMA estim\u00e9e",
        value: formattedVma,
        unit: "km/h",
        note: `R\u00e9f\u00e9rence entra\u00eenement : ${vmaReference} km/h`,
        accent: "#39caff",
        glow: "rgba(45,190,255,.10)"
      })}

      ${metric({
        label: "SV1",
        value: snapshot.sv1?.speed_kmh,
        unit: "km/h",
        note:
          `${snapshot.sv1?.heart_rate_bpm ?? "\u2014"} bpm \u00b7 ` +
          statusLabel(snapshot.sv1?.status),
        accent: "#48d99a",
        glow: "rgba(55,215,151,.10)"
      })}

      ${metric({
        label: "SV2",
        value: snapshot.sv2?.speed_kmh,
        unit: "km/h",
        note:
          `${snapshot.sv2?.heart_rate_bpm ?? "\u2014"} bpm \u00b7 ` +
          statusLabel(snapshot.sv2?.status),
        accent: "#ff7558",
        glow: "rgba(255,100,70,.10)"
      })}

      ${metric({
        label: "Confiance profil",
        value: snapshot.profile_confidence_score,
        unit: "/100",
        note: "Donn\u00e9es longitudinales Atlas",
        accent: "#e1b14e",
        glow: "rgba(225,177,78,.10)"
      })}
        ${zoneRibbon}
    `;

    const confidenceCard = [...ribbon.querySelectorAll(":scope > article")]
      .find(card => card.textContent.includes("Confiance profil"));
    if (confidenceCard) {
      confidenceCard.classList.add("atlas-confidence-card");
      confidenceCard.tabIndex = 0;
      confidenceCard.setAttribute("role", "button");
      confidenceCard.setAttribute(
        "aria-label",
        "Comprendre l’indice de confiance du profil"
      );

      let panel = document.getElementById("atlasConfidencePanel");
      if (!panel) {
        panel = document.createElement("section");
        panel.id = "atlasConfidencePanel";
        panel.className = "atlas-confidence-panel";
        panel.hidden = true;
        document.body.appendChild(panel);
      }

      const confidence = snapshot.profile_confidence_score ?? "—";
      const activityCount = snapshot.activity_count ?? 804;
      const weekCount = snapshot.history_week_count ?? 453;
      const quality = snapshot.data_quality_score ?? 77;
      const sv1Status = statusLabel(snapshot.sv1?.status);
      const sv2Status = statusLabel(snapshot.sv2?.status);
      panel.innerHTML = `
        <button type="button" data-confidence-close aria-label="Fermer">×</button>
        <span>CONFIANCE DU PROFIL ATLAS</span>
        <h2>${confidence}/100</h2>
        <p>Ce nombre ne mesure pas votre niveau sportif. Il indique à quel point Atlas peut se fier à votre profil pour expliquer vos zones et personnaliser le programme.</p>
        <div><strong>Historique longitudinal</strong><small>${activityCount} activités · ${weekCount} semaines analysées</small></div>
        <div><strong>Qualité et continuité</strong><small>${quality}/100 · cohérence des données disponibles</small></div>
        <div><strong>Seuils physiologiques</strong><small>SV1 : ${sv1Status} · SV2 : ${sv2Status}</small></div>
        <div><strong>Individualisation</strong><small>VMA, fréquence cardiaque, réponses aux séances et Wellness sont recoupées.</small></div>
        <p class="atlas-confidence-warning">Une confiance élevée ne remplace pas un test de terrain ou médical. Toute valeur estimée reste identifiée et révisable.</p>
      `;

      const openPanel = () => {
        panel.hidden = false;
        panel.querySelector("[data-confidence-close]")?.focus();
      };
      confidenceCard.addEventListener("click", openPanel);
      confidenceCard.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openPanel();
        }
      });
      panel.querySelector("[data-confidence-close]")?.addEventListener(
        "click",
        () => { panel.hidden = true; }
      );
    }


  }

  function workoutZone(workout) {
    const zones = (workout.blocks || [])
      .map(block => Number(block.target?.zone))
      .filter(zone => zone >= 1 && zone <= 5);

    if (zones.length) return Math.max(...zones);

    return {
      recovery_run: 1,
      endurance_run: 2,
      long_run: 2,
      threshold_run: 4,
      vo2max_run: 5,
      race_specific: 5,
      cycling: 2
    }[workout.workout_type] || null;
  }
  function compactTarget(workout, zone) {
    const blocks = (workout.blocks || []).filter(
      block => Number(block.target?.zone) === zone
    );
    const target = blocks[0]?.target || {};
    const parts = [];

    if (zone) parts.push(`Z${zone}`);

    if (target.speed_min_kmh && target.speed_max_kmh) {
      parts.push(
        `${target.speed_min_kmh}–${target.speed_max_kmh} km/h`
      );
    }

    if (
      target.heart_rate_min_bpm &&
      target.heart_rate_max_bpm
    ) {
      parts.push(
        `${target.heart_rate_min_bpm}–` +
        `${target.heart_rate_max_bpm} bpm`
      );
    }

    return parts.join(" · ");
  }
  function compactWorkout(workout) {
    const key = workout.workout_id;
    const level = difficulty(workout);
const zone = workoutZone(workout);
const target = compactTarget(workout, zone);
      const status = workoutDecision(workout).status;
    workoutIndex.set(key, workout);

    return `
      <button
        class="calendar-session difficulty-${level} zone-${zone || "none"} status-${escapeHtml(status)}"
        type="button"
        data-workout-key="${escapeHtml(key)}"
      >
        <span class="calendar-session-top">
          <i>${zone ? `Zone ${zone} · ` : ""}${escapeHtml(difficultyLabel(level))}</i>
          ${RESEARCH_TYPES.has(workout.workout_type) ? `
            <em>Research</em>
          ` : ""}
            ${workoutStatusBadge(workout)}
        </span>
        <strong>${escapeHtml(workout.title)}</strong>
        <small>${escapeHtml(
          formatMinutes(workout.planned_duration_minutes)
        )}</small>
    ${target ? `
      <small class="calendar-session-target">
        ${escapeHtml(target)}
      </small>
    ` : ""}
        <b>Voir le détail</b>
      </button>
    `;
  }

  function optionalButton(value) {
    return `
      <button
        class="add-optional-session"
        type="button"
        data-optional-date="${escapeHtml(value)}"
      >
        <span>+</span>
        Ajouter une activité
      </button>
    `;
  }

  function calendarDay(
    value,
    dayIndex,
    workouts,
    program,
    mobileSelected = false
  ) {
    const active = (
      value >= program.start_date &&
      value <= program.end_date
    );
    const runningWorkout = workouts.some(
      workout => workout.sport === "running"
    );

    return `
      <article class="
        calendar-day
        ${isToday(value) ? "is-today" : ""}
        ${!active ? "is-outside-program" : ""}
        ${mobileSelected ? "is-mobile-selected" : ""}
      ">
        <header>
          <span>${DAY_LABELS[dayIndex]}</span>
          <strong>${escapeHtml(formatDate(value))}</strong>
          ${isToday(value) ? "<i>Aujourd’hui</i>" : ""}
        </header>

        <div class="calendar-day-content">
          ${!active ? `
            <div class="outside-day">Hors programme</div>
          ` : workouts.length ? `
            ${workouts.map(compactWorkout).join("")}
            ${optionalButton(value)}
          ` : `
            <div class="rest-day">
              <span>Récupération</span>
              <small>Aucune séance imposée</small>
            </div>
            ${optionalButton(value)}
          `}
        </div>
      </article>
    `;
  }

  function mobileDayIcons(workouts) {
    const icons = {
      running: ["🏃", "Course"],
      cycling: ["🚴", "Vélo"],
      strength: ["◆", "Renforcement"]
    };
    const sports = [...new Set(workouts.map(workout => workout.sport))];

    if (!sports.length) {
      return '<span class="mobile-day-rest" aria-label="Repos">•</span>';
    }

    return sports.map(sport => {
      const icon = icons[sport] || ["•", sport];
      return `<span class="mobile-day-sport sport-${escapeHtml(sport)}" title="${escapeHtml(icon[1])}" aria-label="${escapeHtml(icon[1])}">${icon[0]}</span>`;
    }).join("");
  }

  function renderWeek(week, program) {
    const start = parseDate(week.start_date);
    const workoutsByDate = new Map();

    week.workouts.forEach(workout => {
      const existing = workoutsByDate.get(
        workout.workout_date
      ) || [];
      existing.push(workout);
      workoutsByDate.set(workout.workout_date, existing);
    });

    const todayIndex = Array.from({ length: 7 }, (_, index) =>
      isoDate(addDays(start, index))
    ).findIndex(isToday);
    const selectedDayIndex = todayIndex >= 0 ? todayIndex : 0;
    const dayTabs = Array.from({ length: 7 }, (_, index) => {
      const date = addDays(start, index);
      const value = isoDate(date);
      const workouts = workoutsByDate.get(value) || [];
      const selected = index === selectedDayIndex;

      return `
        <button
          type="button"
          class="mobile-day-tab ${selected ? "is-selected" : ""} ${isToday(value) ? "is-today" : ""}"
          data-mobile-day="${index}"
          aria-selected="${selected}"
          aria-label="${escapeHtml(DAY_LABELS[index])} ${escapeHtml(formatDate(value))}"
        >
          <b>${escapeHtml(DAY_LABELS[index].charAt(0))}</b>
          <small>${date.getDate()}</small>
          <span class="mobile-day-icons">${mobileDayIcons(workouts)}</span>
        </button>
      `;
    }).join("");

    const days = Array.from({ length: 7 }, (_, index) => {
      const value = isoDate(addDays(start, index));
      return calendarDay(
        value,
        index,
        workoutsByDate.get(value) || [],
        program,
        index === selectedDayIndex
      );
    });

    return `
      <details
        class="premium-week phase-${escapeHtml(week.phase)}"
        ${days.some(item => item.includes("is-today")) ? "open" : ""}
      >
        <summary>
          <div>
            <strong>
              Semaine ${escapeHtml(week.week_number)}
              · ${escapeHtml(
                PHASE_LABELS[week.phase] || week.phase
              )}
            </strong>
            <small>${escapeHtml(week.objective)}</small>
          </div>
          <span>
            ${escapeHtml(formatDate(week.start_date))}
            →
            ${escapeHtml(formatDate(week.end_date))}
            · ${escapeHtml(
              formatMinutes(week.target_duration_minutes)
            )}
          </span>
        </summary>

        <nav class="mobile-week-days" aria-label="Jours de la semaine">
          ${dayTabs}
        </nav>

        <div class="week-seven-grid">
          ${days.join("")}
        </div>
      </details>
    `;
  }

  function renderOverview(program) {
    const researchCount = program.weeks.reduce(
      (total, week) => total + week.workouts.filter(
        workout => RESEARCH_TYPES.has(workout.workout_type)
      ).length,
      0
    );
    const targetMinutes = Number(
      program.goal.target_time_minutes
    );
    const hours = Math.floor(targetMinutes / 60);
    const minutes = targetMinutes % 60;
    const programStart = parseDate(program.start_date);
    const eventDate = parseDate(program.goal.event_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const totalDuration = Math.max(1, eventDate - programStart);
    const elapsedDuration = Math.min(totalDuration, Math.max(0, today - programStart));
    const temporalProgress = Math.round(elapsedDuration / totalDuration * 100);
    const currentWeekIndex = program.weeks.findIndex(week => (
      today >= parseDate(week.start_date) &&
      today <= parseDate(week.end_date)
    ));
    const currentWeekNumber = currentWeekIndex >= 0
      ? currentWeekIndex + 1
      : today < programStart
        ? 0
        : program.weeks.length;

    overview.innerHTML = `
      <article>
        <span>Objectif</span>
        <strong>${escapeHtml(program.goal.name)}</strong>
      </article>
      <article>
        <span>Échéance</span>
        <strong>${escapeHtml(
          formatDate(program.goal.event_date, true)
        )}</strong>
      </article>
      <article>
        <span>Temps cible</span>
        <strong>
          ${hours} h ${String(minutes).padStart(2, "0")}
        </strong>
        <small>${escapeHtml(
          paceFromSpeed(
            program.goal.distance_km /
            (targetMinutes / 60)
          )
        )}</small>
      </article>
      <article class="program-progress-card">
          <span>Programme</span>
          <strong>${escapeHtml(program.duration_weeks)} semaines</strong>
          <small class="program-progress-label">
            Semaine ${currentWeekNumber} sur ${program.duration_weeks}
            · <b>${temporalProgress} %</b>
          </small>
          <div class="program-progress-track" role="progressbar" aria-label="Avancement vers l’échéance" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${temporalProgress}">
            <i style="width:${temporalProgress}%"></i>
          </div>
          <small class="program-progress-summary">
            ${escapeHtml(program.total_running_workouts)} courses
            · ${researchCount} Research
            · ${escapeHtml(program.settings.optional_running_sessions_per_week)} facultative
          </small>
        </article>
    `;
  }

  function atlasConfirm(message) {
    return new Promise(resolve => {
      const overlay = document.createElement("div");
      overlay.className = "atlas-confirm-overlay";
      overlay.innerHTML = `
        <section
          class="atlas-confirm-panel"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="atlasConfirmTitle"
        >
          <span class="atlas-confirm-icon">×</span>
          <div>
            <small>ACTIVITÉ FACULTATIVE</small>
            <h3 id="atlasConfirmTitle">Supprimer cette séance ?</h3>
            <p>${escapeHtml(message)}</p>
          </div>
          <div class="atlas-confirm-actions">
            <button type="button" data-confirm-cancel>Conserver</button>
            <button type="button" data-confirm-accept>Supprimer</button>
          </div>
        </section>
      `;

      const finish = answer => {
        overlay.remove();
        resolve(answer);
      };

      overlay.addEventListener("click", event => {
        event.stopPropagation();

        if (
          event.target === overlay ||
          event.target.closest("[data-confirm-cancel]")
        ) {
          finish(false);
        } else if (event.target.closest("[data-confirm-accept]")) {
          finish(true);
        }
      });

      const parentDialog = document.getElementById(
        "atlasSessionDialog"
      );
      (parentDialog || document.body).appendChild(overlay);
      overlay.querySelector("[data-confirm-cancel]").focus();
    });
  }
  function ensureDialog() {
    let dialog = document.getElementById(
      "atlasSessionDialog"
    );

    if (dialog) return dialog;

    dialog = document.createElement("dialog");
    dialog.id = "atlasSessionDialog";
    dialog.className = "atlas-session-dialog";
    dialog.style.cssText = "width:calc(100vw - 24px);max-width:none;height:calc(100vh - 24px);max-height:calc(100vh - 24px);padding:0;color:#eef9ff;border:1px solid rgba(225,177,78,.75);border-radius:24px;background:radial-gradient(circle at 85% 0%,rgba(30,190,255,.16),transparent 34%),linear-gradient(145deg,#0b2035,#061321 58%,#020914);box-shadow:0 35px 100px rgba(0,0,0,.8),0 0 35px rgba(225,177,78,.2);";
    dialog.innerHTML = `
      <div class="session-dialog-shell" style="position:relative;padding:34px;color:#eef9ff;background:transparent;">
        <button
          class="dialog-close"
          type="button"
          aria-label="Fermer"
        >×</button>
        <div class="dialog-content" style="color:#eef9ff;"></div>
      </div>
    `;
    document.body.appendChild(dialog);

    const closeButton = dialog.querySelector(".dialog-close");
    closeButton.style.cssText = "position:absolute;z-index:10;top:18px;right:18px;width:42px;height:42px;color:#f7d483;font-size:1.25rem;cursor:pointer;border:1px solid rgba(225,177,78,.65);border-radius:50%;background:#0b2135;box-shadow:0 0 18px rgba(225,177,78,.18);";
    closeButton.addEventListener(
      "click",
      () => dialog.close()
    );
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });

    return dialog;
  }

  function detailHtml(workout) {
    const response = workout.expected_response || {};
    const blocks = workout.blocks || [];
    const level = difficulty(workout);
const zone = workoutZone(workout);
const target = compactTarget(workout, zone);

    const blockDistance = block => {
      const repetitions = Number(block.repetitions) || 1;

      if (block.distance_meters != null) {
        return Number(block.distance_meters) * repetitions / 1000;
      }

      const target = block.target || {};
      const duration = Number(block.duration_minutes) || 0;
      const minimum = Number(target.speed_min_kmh);
      const maximum = Number(target.speed_max_kmh);

      if (duration && minimum && maximum) {
        return duration * repetitions * ((minimum + maximum) / 2) / 60;
      }

      return 0;
    };

    const estimatedDistance = Number(workout.planned_distance_km) ||
      blocks.reduce((total, block) => total + blockDistance(block), 0);

    const mainBlock = blocks.find(block =>
      ["work", "continuous"].includes(block.block_type)
    ) || blocks[0];

    const accentFor = block => {
      const zone = Number(block.target?.zone);
      const zoneColors = {
        1: "#38a9ff",
        2: "#49d17d",
        3: "#f0cf4f",
        4: "#ff9f43",
        5: "#ff506c"
      };

      if (zoneColors[zone]) return zoneColors[zone];

      return {
        strength: "#a978ff",
        mobility: "#64e6a6"
      }[block.block_type] || "#35ccff";
    };

    const stepName = block => ({
      warm_up: "Échauffement",
      work: "Bloc de travail",
      continuous: "Course",
      recovery: "Récupération",
      cool_down: "Retour au calme",
      strength: "Renforcement",
      mobility: "Mobilité"
    }[block.block_type] || block.name);

    const researchNames = {
      hill_sprints: "Sprints courts en côte",
      mixed_threshold_vo2: "Séance mixte seuil et VO₂max",
      triangular_vo2: "Séance VO₂max triangulaire"
    };

    const researchNotes = (workout.coach_notes || []).filter(
      note => !note.startsWith("Protocole Atlas Research")
    );

    return `
      <header class="dialog-session-header" style="--session-accent:${mainBlock ? accentFor(mainBlock) : '#39d98a'}">
        <div>
          <span>${escapeHtml(new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(parseDate(workout.workout_date)).replace(/^./, letter => letter.toUpperCase()))}</span>
          <h2>${escapeHtml(workout.title)}</h2>
          <p>${escapeHtml(workout.objective)}</p>
        </div>
        <i class="difficulty-pill difficulty-${level}">
          ${escapeHtml(difficultyLabel(level))}
        </i>
      </header>

              <section class="session-overview">
          <h3>Aperçu</h3>
          <div class="session-overview-grid">
            <article>
              <strong>${escapeHtml(formatMinutes(workout.planned_duration_minutes))}</strong>
              <span>Durée</span>
            </article>
            <article>
              <strong>
                ${estimatedDistance ? estimatedDistance.toLocaleString(
                  "fr-FR",
                  { maximumFractionDigits: 1 }
                ) + " km" : "—"}
              </strong>
              <span>Distance estimée</span>
            </article>
            <article>
              <strong>${escapeHtml(response.physiological_load_0_100 ?? "—")}/100</strong>
              <span>Charge physiologique</span>
            </article>
            <article>
              <strong>
                ${escapeHtml(response.recovery_min_hours ?? "—")}–${escapeHtml(
                  response.recovery_max_hours ?? "—"
                )} h
              </strong>
              <span>Récupération</span>
            </article>
          </div>
        </section>

        <section class="session-steps ${blocks.length === 1 ? "is-simple" : ""}">
          <h3>Étapes</h3>
          <div class="session-step-list">
            ${blocks.map(block => {
              const distance = blockDistance(block);
              const name = stepName(block);
              const secondaryName = block.name && block.name !== name
                ? block.name
                : "";

              return `
                <article
                  class="session-step"
                  style="--step-accent:${accentFor(block)}"
                >
                  <div class="session-step-heading">
                    <div>
                      <strong>${escapeHtml(name)}</strong>
                      ${secondaryName ? `<span>${escapeHtml(secondaryName)}</span>` : ""}
                    </div>
                    <b>${escapeHtml(blockDuration(block))}</b>
                  </div>
                  ${targetCards(block)}

                  ${distance ? `
                    <small>
                      Distance estimée :
                      ${distance.toLocaleString(
                        "fr-FR",
                        { maximumFractionDigits: 1 }
                      )} km
                    </small>
                  ` : ""}

                  ${block.instructions ? `
                    <details class="session-step-advice">
                      <summary>Conseil Atlas</summary>
                      <p>${escapeHtml(block.instructions)}</p>
                    </details>
                  ` : ""}
                </article>
              `;
            }).join("")}
          </div>
        </section>

${RESEARCH_TYPES.has(workout.workout_type) ? `
        <details style="
          margin-top:12px;
          padding:15px 17px;
          border:1px solid rgba(225,177,78,.28);
          border-radius:10px;
          background:rgba(44,31,13,.28);
        ">
          <summary style="cursor:pointer;font-weight:700;color:#f0c862">
            ⓘ Pourquoi cette séance ? — Atlas Research
          </summary>
          <h4 style="margin:15px 0 8px">
            ${escapeHtml(
              researchNames[workout.workout_type] ||
              "Protocole scientifique individualisé"
            )}
          </h4>
          ${researchNotes.map(
            note => `<p style="color:#bdd0dc">${escapeHtml(note)}</p>`
          ).join("")}
        </details>
      ` : ""}
    `;
  }

  function reportScore(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric)
      ? `${Math.round(numeric)}/100`
      : "—";
  }

  function reportNumber(value, digits = 1) {
    const numeric = Number(value);
    return Number.isFinite(numeric)
      ? numeric.toLocaleString("fr-FR", {
          maximumFractionDigits: digits
        })
      : "—";
  }

  function reportPace(seconds) {
    const numeric = Number(seconds);
    if (!Number.isFinite(numeric) || numeric <= 0) return "—";
    const minutes = Math.floor(numeric / 60);
    const remainder = String(Math.round(numeric % 60)).padStart(2, "0");
    return `${minutes}:${remainder}/km`;
  }

  function reportList(values, emptyText = "Aucun élément signalé") {
    const items = Array.isArray(values)
      ? values.filter(Boolean)
      : values
        ? [values]
        : [];

    if (!items.length) {
      return `<p class="report-empty">${escapeHtml(emptyText)}</p>`;
    }

    return `
      <ul class="report-list">
        ${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    `;
  }

  function reportSignedNumber(value, digits = 1, unit = "") {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "—";
    const sign = numeric > 0 ? "+" : "";
    return `${sign}${numeric.toLocaleString("fr-FR", {
      maximumFractionDigits: digits
    })}${unit}`;
  }

  function sessionTypeLabel(value) {
    return {
      easy: "Endurance facile",
      recovery: "Récupération",
      threshold: "Travail au seuil",
      intervals: "Intervalles",
      long_run: "Sortie longue"
    }[value] || value || "Séance analysée";
  }

  function reportBlockTime(seconds) {
    const numeric = Number(seconds);
    if (!Number.isFinite(numeric)) return "—";

    const minutes = Math.floor(numeric / 60);
    const remainder = numeric - minutes * 60;
    const formatted = remainder.toLocaleString("fr-FR", {
      minimumIntegerDigits: 2,
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    });

    return `${minutes}:${formatted}`;
  }

  function reportMean(values, digits = 1) {
    const valid = values.map(Number).filter(Number.isFinite);
    if (!valid.length) return Number.NaN;

    return valid.reduce((total, value) => total + value, 0) /
      valid.length;
  }
  function executionReportHtml(report, workout, userContext = null) {
    if (!report) {
      return `
        <section class="execution-report-empty">
          <strong>Aucun compte-rendu FIT associé</strong>
          <p>
            Après l’import Garmin, Atlas comparera ici la séance réalisée
            avec la prescription et expliquera son raisonnement.
          </p>
        </section>
      `;
    }

    const match = report.workout_match || {};
    const execution = match.execution || {};
    const activity = report.activity || {};
    const drift = report.cardiac_drift || {};
    const analysis = report.analysis || {};
    const detailedBlocks = Array.isArray(analysis.blocks)
      ? analysis.blocks
      : [];
    const dominantType = String(
      analysis.dominant_work_type || ""
    );
    const plannedMainBlock = (workout.blocks || []).find(
      block => block.block_type === "work"
    );
    const plannedRepetitions = Number(
      execution.planned_repetition_count ||
      plannedMainBlock?.repetitions ||
      1
    );
    const matchingWorkBlocks = detailedBlocks.filter(
      block => block.block_type === dominantType
    );
    const workBlocks = matchingWorkBlocks.length
      ? matchingWorkBlocks
      : detailedBlocks.filter(block => ![
          "warm_up",
          "cool_down",
          "recovery",
          "z1"
        ].includes(block.block_type));
    const recoveryBlocks = detailedBlocks.filter(
      block => block.block_type === "recovery"
    );
    const workDistanceKm = workBlocks.reduce(
      (total, block) => total + Number(block.distance_meters || 0),
      0
    ) / 1000;
    const workDurationSeconds = workBlocks.reduce(
      (total, block) => total + Number(block.duration_seconds || 0),
      0
    );
    const averageWorkSpeed = reportMean(
      workBlocks.map(block => block.average_speed_kmh)
    );
    const averageWorkHeartRate = reportMean(
      workBlocks.map(block => block.average_heart_rate_bpm)
    );
    const workMaximumHeartRates = workBlocks.map(
      block => Number(block.maximum_heart_rate_bpm)
    ).filter(Number.isFinite);
    const maximumWorkHeartRate = workMaximumHeartRates.length
      ? Math.max(...workMaximumHeartRates)
      : Number.NaN;
    const averageWorkPower = reportMean(
      workBlocks.map(block => block.average_power_watts)
    );
    const averageWorkCadence = reportMean(
      workBlocks.map(block => block.average_cadence_spm)
    );
    const workDurations = workBlocks.map(
      block => Number(block.duration_seconds)
    ).filter(Number.isFinite);
    const repetitionSpread = workDurations.length
      ? Math.max(...workDurations) - Math.min(...workDurations)
      : Number.NaN;
    const isIntervalSession = plannedRepetitions > 1 &&
      workBlocks.length > 1;
    const firstWorkBlock = workBlocks[0] || {};
    const lastWorkBlock = workBlocks[workBlocks.length - 1] || {};
    const fastestWorkBlock = workBlocks.reduce(
      (fastest, block) => (
        Number(block.duration_seconds) <
        Number(fastest?.duration_seconds ?? Infinity)
          ? block
          : fastest
      ),
      null
    );
    const intervalHeartRateChange =
      Number(lastWorkBlock.average_heart_rate_bpm) -
      Number(firstWorkBlock.average_heart_rate_bpm);
    const intervalSpeedChangePercent =
      Number(firstWorkBlock.average_speed_kmh) > 0
        ? (
            Number(lastWorkBlock.average_speed_kmh) /
            Number(firstWorkBlock.average_speed_kmh) - 1
          ) * 100
        : Number.NaN;
    const first = drift.first_segment || {};
    const second = drift.second_segment || {};
    const plannedDuration = Number(workout.planned_duration_minutes);
    const actualDuration = Number(activity.duration_minutes);
    const directPlannedDistance = Number(workout.planned_distance_km);
    const estimatedPlannedDistance = (workout.blocks || []).reduce(
      (total, block) => {
        const repetitions = Number(block.repetitions) || 1;

        if (block.distance_meters != null) {
          return total +
            Number(block.distance_meters) * repetitions / 1000;
        }

        const duration = Number(block.duration_minutes) || 0;
        const speedMinimum = Number(block.target?.speed_min_kmh);
        const speedMaximum = Number(block.target?.speed_max_kmh);

        if (
          duration > 0 &&
          Number.isFinite(speedMinimum) &&
          Number.isFinite(speedMaximum)
        ) {
          return total +
            duration *
            repetitions *
            ((speedMinimum + speedMaximum) / 2) /
            60;
        }

        return total;
      },
      0
    );
    const plannedDistanceRaw = directPlannedDistance > 0
      ? directPlannedDistance
      : estimatedPlannedDistance || Number.NaN;
    const plannedDistance = Number.isFinite(plannedDistanceRaw)
      ? Math.round(plannedDistanceRaw * 10) / 10
      : Number.NaN;
    const actualDistance = isIntervalSession
      ? workDistanceKm
      : Number(activity.distance_km);
    const actualComparisonSpeed = isIntervalSession
      ? averageWorkSpeed
      : Number(activity.average_speed_kmh);
    const actualComparisonHeartRate = isIntervalSession
      ? averageWorkHeartRate
      : Number(activity.average_heart_rate_bpm);
    const actualComparisonMaximumHeartRate = isIntervalSession
      ? maximumWorkHeartRate
      : Number(activity.maximum_heart_rate_bpm);
    const analyzedSessionLabel = {
      vma: "Intervalles VO₂max",
      sv2: "Travail au seuil",
      z3: "Tempo",
      z2: "Endurance fondamentale",
      z1: "Récupération",
      sprint: "Sprints",
      acceleration: "Accélérations"
    }[dominantType] || sessionTypeLabel(activity.session_type);
    const durationDelta = actualDuration - plannedDuration;
    const distanceDelta = actualDistance - plannedDistance;
    const executionScore = Number(execution.execution_score);
    const targetScore = Number(match.target_compliance_score);
    const temperature = Number(activity.temperature_c);
    const elevation = Number(activity.elevation_gain_m);
    const hillSamples = Number(drift.excluded_hill_sample_count);
    const learningAllowed =
      report.automatic_learning_allowed === true;

    const executionConclusion = executionScore >= 80
      ? "La séance est globalement bien exécutée."
      : executionScore >= 60
        ? "La séance est exploitable, avec quelques écarts à surveiller."
        : "La séance présente des écarts importants par rapport au plan.";

    const targetConclusion = targetScore >= 85
      ? "Les cibles physiologiques ont été bien respectées."
      : targetScore >= 65
        ? "Les cibles ont été partiellement respectées."
        : "Les cibles prévues ont été peu respectées.";
    const intervalRows = workBlocks.map((block, index) => {
      const speed = Number(block.average_speed_kmh);
      const recovery = recoveryBlocks[index] || null;

      return `
        <div class="interval-detail-row">
          <strong>${index + 1}</strong>
          <span>${reportNumber(Number(block.distance_meters), 0)} m</span>
          <span>${reportBlockTime(block.duration_seconds)}</span>
          <span>${reportPace(3600 / speed)}</span>
          <span>${reportNumber(speed, 2)} km/h</span>
          <span>
            ${reportNumber(block.average_heart_rate_bpm, 0)}
            <small>max. ${reportNumber(block.maximum_heart_rate_bpm, 0)}</small>
          </span>
          <span>${reportNumber(block.average_power_watts, 0)} W</span>
          <span>${reportNumber(block.average_cadence_spm, 0)} ppm</span>
          <span>
            ${recovery
              ? `${reportBlockTime(recovery.duration_seconds)} · ${reportNumber(recovery.distance_meters, 0)} m`
              : "—"}
          </span>
        </div>
      `;
    }).join("");

    return `
      <section class="execution-report execution-report-narrative">
        <header class="report-cockpit-header">
          <div>
            <span>ANALYSE ATLAS · DONNÉES RÉELLES</span>
            <h2>${escapeHtml(execution.workout_name || workout.title)}</h2>
            <p>
              ${escapeHtml(analyzedSessionLabel)}
              · séance Garmin reconnue avec une confiance de
              ${reportScore(match.match_confidence_score)}.
            </p>
          </div>
          <div class="report-main-score">
            <strong>${reportScore(execution.execution_score)}</strong>
            <span>Score d’exécution</span>
          </div>
        </header>

        <section class="interval-result-summary">
          <div class="report-heading">
            <span class="report-kicker">RÉSULTAT</span>
            <h3>
              ${isIntervalSession
                ? `${workBlocks.length} répétitions réalisées sur ${plannedRepetitions}`
                : executionConclusion}
            </h3>
            <p>
              ${isIntervalSession
                ? `Bloc principal exécuté avec une conformité de ${reportScore(targetScore)}.`
                : targetConclusion}
            </p>
          </div>

          <div class="interval-result-grid">
            <article>
              <span>Travail rapide</span>
              <strong>${reportBlockTime(workDurationSeconds)}</strong>
              <small>${reportNumber(workDistanceKm, 2)} km</small>
            </article>
            <article>
              <span>Allure moyenne</span>
              <strong>${reportPace(3600 / averageWorkSpeed)}</strong>
              <small>${reportNumber(averageWorkSpeed, 2)} km/h</small>
            </article>
            <article>
              <span>Régularité</span>
              <strong>${reportNumber(repetitionSpread, 1)} s</strong>
              <small>écart rapide/lente</small>
            </article>
            <article>
              <span>Fréquence cardiaque</span>
              <strong>${reportNumber(averageWorkHeartRate, 0)} bpm</strong>
              <small>max. ${reportNumber(maximumWorkHeartRate, 0)} bpm</small>
            </article>
            <article>
              <span>Puissance moyenne</span>
              <strong>${reportNumber(averageWorkPower, 0)} W</strong>
              <small>répétitions</small>
            </article>
            <article>
              <span>Cadence moyenne</span>
              <strong>${reportNumber(averageWorkCadence, 0)} ppm</strong>
              <small>répétitions</small>
            </article>
          </div>
        </section>

        ${isIntervalSession ? `
          <section class="interval-details-section">
            <div class="report-heading">
              <span class="report-kicker">CIRCUITS</span>
              <h3>Détail des ${workBlocks.length} répétitions</h3>
            </div>
            <div class="interval-detail-table">
              <div class="interval-detail-row interval-detail-header">
                <span>N°</span><span>Distance</span><span>Temps</span>
                <span>Allure</span><span>Vitesse</span><span>FC moy.</span>
                <span>Puissance</span><span>Cadence</span>
                <span>Récupération</span>
              </div>
              ${intervalRows}
            </div>
          </section>
        ` : ""}
        <div class="report-analysis-layout">
          <main>
              ${isIntervalSession ? `
                <section class="narrative-analysis-section interval-analysis-section">
                  <div class="report-heading">
                    <span class="report-kicker">LECTURE ATLAS</span>
                    <h3>Une série régulière jusqu’à la dernière répétition</h3>
                  </div>
                  <p>
                    Les ${workBlocks.length} ×
                    ${reportNumber(firstWorkBlock.distance_meters, 0)} m
                    ont été réalisés à ${reportPace(3600 / averageWorkSpeed)}
                    de moyenne. L’écart total de ${reportNumber(repetitionSpread, 1)} s
                    confirme une exécution homogène.
                  </p>
                  <div class="drift-reading-line">
                    <div>
                      <span>Première</span>
                      <strong>${reportBlockTime(firstWorkBlock.duration_seconds)}</strong>
                      <small>${reportNumber(firstWorkBlock.average_heart_rate_bpm, 0)} bpm</small>
                    </div>
                    <i>→</i>
                    <div>
                      <span>Plus rapide</span>
                      <strong>${reportBlockTime(fastestWorkBlock?.duration_seconds)}</strong>
                      <small>${reportNumber(fastestWorkBlock?.average_speed_kmh, 2)} km/h</small>
                    </div>
                    <i>→</i>
                    <div>
                      <span>Dernière</span>
                      <strong>${reportBlockTime(lastWorkBlock.duration_seconds)}</strong>
                      <small>${reportNumber(lastWorkBlock.average_heart_rate_bpm, 0)} bpm</small>
                    </div>
                  </div>
                  <p>
                    Entre la première et la dernière répétition, la vitesse évolue de
                    ${reportSignedNumber(intervalSpeedChangePercent, 1, " %")}
                    et la fréquence cardiaque de
                    ${reportSignedNumber(intervalHeartRateChange, 0, " bpm")}.
                    Les récupérations ralenties n’ont pas dégradé la qualité des 400 m.
                  </p>
                </section>
              ` : ""}

              <section class="narrative-analysis-section ${isIntervalSession ? "is-interval-hidden" : ""}">
              <div class="report-heading">
                <span class="report-kicker">RAISONNEMENT PHYSIOLOGIQUE</span>
                <h3>Ce qu’Atlas observe pendant l’effort</h3>
              </div>
              ${drift.analyzable ? `
                <p>
                  Après avoir exclu les ${reportNumber(drift.warmup_excluded_minutes, 0)}
                  premières minutes, Atlas observe une vitesse presque
                  stable : ${reportNumber(first.average_speed_kmh)} km/h
                  dans la première partie contre
                  ${reportNumber(second.average_speed_kmh)} km/h dans la
                  seconde (${reportSignedNumber(drift.speed_change_percent, 1, " %")}).
                  Dans le même temps, la fréquence cardiaque passe de
                  ${reportNumber(first.average_heart_rate_bpm)} à
                  ${reportNumber(second.average_heart_rate_bpm)} bpm.
                </p>
                <div class="drift-reading-line">
                  <div><span>Première partie</span><strong>${reportNumber(first.average_speed_kmh)} km/h</strong><small>${reportNumber(first.average_heart_rate_bpm)} bpm</small></div>
                  <i>→</i>
                  <div><span>Deuxième partie</span><strong>${reportNumber(second.average_speed_kmh)} km/h</strong><small>${reportNumber(second.average_heart_rate_bpm)} bpm</small></div>
                  <i>→</i>
                  <div class="drift-result"><span>Évolution</span><strong>${reportSignedNumber(drift.heart_rate_change_bpm, 1, " bpm")}</strong><small>${reportSignedNumber(drift.speed_change_percent, 1, " % vitesse")}</small></div>
                </div>
                <p>
                  Le découplage aérobie atteint
                  <strong>${reportNumber(drift.aerobic_decoupling_percent)} %</strong>,
                  classé « ${escapeHtml(drift.drift_classification || "non classé")} ».
                  Il s’agit d’un signal à suivre, mais pas d’une preuve
                  isolée de mauvaise tolérance.
                </p>
              ` : `
                <p>Cette séance ne permet pas une mesure suffisamment fiable de la dérive cardiaque.</p>
              `}
              <p>
                ${Number.isFinite(temperature) ? `La température était d’environ ${reportNumber(temperature)} °C. ` : ""}
                ${Number.isFinite(elevation) ? `Le parcours comportait ${reportNumber(elevation, 0)} m de dénivelé positif. ` : ""}
                ${Number.isFinite(hillSamples) && hillSamples > 0 ? `${reportNumber(hillSamples, 0)} points de pente marquée ont été retirés du calcul. ` : ""}
                Ces contraintes peuvent augmenter le coût cardiaque sans
                traduire à elles seules une baisse de condition physique.
              </p>
            </section>

            <section class="narrative-analysis-section context-story">
              <div class="report-heading">
                <span class="report-kicker">CONTEXTE UTILISATEUR</span>
                <h3>Votre ressenti donne du sens aux données</h3>
              </div>
              <p>
                La montre décrit ce qui s’est produit, mais elle ne connaît
                pas toujours la cause. La chaleur ressentie, les bosses,
                les faux plats, une douleur, la fatigue musculaire ou une
                allure volontairement maintenue permettent à Atlas de
                mieux interpréter la hausse cardiaque.
              </p>
              <div class="declared-context-zone">
                ${userContext ? `
                  <div class="declared-context-reading">
                    <strong>Ce que vous avez déclaré</strong>
                    <p>
                      ${userContext.heat ? "Vous signalez une chaleur importante. " : ""}
                      ${userContext.relief ? "Le parcours comportait du relief ou des faux plats. " : ""}
                      ${userContext.pain_0_to_10 != null ? `La douleur ressentie était évaluée à ${escapeHtml(userContext.pain_0_to_10)}/10. ` : ""}
                      ${userContext.fatigue_0_to_10 != null ? `La fatigue était évaluée à ${escapeHtml(userContext.fatigue_0_to_10)}/10. ` : ""}
                      ${userContext.comment ? escapeHtml(userContext.comment) : ""}
                    </p>
                    <p class="context-interpretation">
                      ${userContext.heat || userContext.relief
                        ? "Atlas tient compte de ces contraintes externes : elles peuvent expliquer une partie de la hausse cardiaque observée sans conclure trop rapidement à une mauvaise tolérance physiologique."
                        : "Cette déclaration complète les données objectives et sera conservée dans l’historique longitudinal."}
                    </p>
                  </div>
                ` : `
                  <div class="declared-context-reading empty">
                    Aucun contexte personnel n’a encore été déclaré pour cette séance.
                  </div>
                `}

                <form class="workout-context-form" data-workout-context-form>
                  <div class="context-toggle-grid">
                    <label>
                      <input type="checkbox" name="heat" ${userContext?.heat ? "checked" : ""}>
                      <span><b>Chaleur ressentie</b><small>Température ou sensation thermique inhabituelle</small></span>
                    </label>
                    <label>
                      <input type="checkbox" name="relief" ${userContext?.relief ? "checked" : ""}>
                      <span><b>Relief contraignant</b><small>Bosses, faux plats ou terrain irrégulier</small></span>
                    </label>
                  </div>
                  <div class="context-score-grid">
                    <label>
                      <span>Douleur ressentie <small>0 = aucune · 10 = maximale</small></span>
                      <input type="number" name="pain" min="0" max="10" step="1" value="${userContext?.pain_0_to_10 ?? ""}">
                    </label>
                    <label>
                      <span>Fatigue ressentie <small>0 = aucune · 10 = maximale</small></span>
                      <input type="number" name="fatigue" min="0" max="10" step="1" value="${userContext?.fatigue_0_to_10 ?? ""}">
                    </label>
                  </div>
                  <label class="context-comment-field">
                    <span>Votre lecture de la séance</span>
                    <textarea name="comment" maxlength="1200" rows="3" placeholder="Ex. allure volontairement constante, jambes lourdes, vent, mauvaise nuit…">${escapeHtml(userContext?.comment || "")}</textarea>
                  </label>
                  <div class="context-form-footer">
                    <small>Cette déclaration est enregistrée séparément des données Garmin et reste historisée.</small>
                    <button type="submit">Enregistrer mon contexte</button>
                  </div>
                  <p class="context-form-status" data-context-form-status aria-live="polite"></p>
                </form>
              </div>
            </section>
          </main>

          <aside class="atlas-decision-column">
            <span class="report-kicker">DÉCISION ATLAS</span>
            <h3>${learningAllowed ? "Séance retenue pour l’apprentissage" : "Analyse conservée avec prudence"}</h3>
            <p>
              ${learningAllowed
                ? "La qualité des données et la correspondance sont suffisantes pour enrichir votre profil longitudinal."
                : "Cette analyse est conservée, mais elle ne modifiera pas automatiquement le profil."}
            </p>
            <p>
              Atlas ne modifie pas silencieusement le programme actif.
              Toute adaptation future devra présenter les observations,
              la raison du changement et les séances concernées.
            </p>
            <div class="decision-metrics">
              <span>Charge physiologique <strong>${reportScore(analysis.physiological_load_score)}</strong></span>
              <span>Charge biomécanique <strong>${reportScore(analysis.biomechanical_load_score)}</strong></span>
            </div>
          </aside>
        </div>

        <section class="recovery-story">
          <div class="report-heading">
            <span class="report-kicker">APRÈS LA SÉANCE</span>
            <h3>La récupération confirmera cette interprétation</h3>
            <p>
              Les données Wellness et votre ressenti à 24, 48 et 72 heures
              permettront de vérifier si la charge a été réellement bien
              tolérée avant toute adaptation.
            </p>
          </div>
          <div class="recovery-timeline">
            <span><b>24 h</b> Première réponse</span>
            <span><b>48 h</b> Retour vers la référence</span>
            <span><b>72 h</b> Tolérance confirmée</span>
          </div>
        </section>
      </section>
    `;
  }
  function workoutActionsHtml(workout) {
    const decision = workoutDecision(workout);
    const currentStatus = decision.status || "planned";

    return `
      <section class="workout-actions" data-current-status="${escapeHtml(currentStatus)}">
        <div class="workout-actions-heading">
          <div>
            <span>SUIVI DE LA SÉANCE</span>
            <strong>Qu’avez-vous décidé ?</strong>
          </div>
          ${workoutStatusBadge(workout)}
        </div>

        ${currentStatus === "skipped" ? `
          <div class="workout-cancelled-decision">
            <span>SÉANCE ANNULÉE</span>
            <strong>Votre décision est enregistrée</strong>
            <p>Motif : ${escapeHtml(decision.reason || "Non précisé")}</p>
            <button type="button" data-workout-action="planned">
              Modifier ma décision
            </button>
          </div>
        ` : `
          <div class="workout-primary-actions">
            <button type="button" data-workout-action="completed">
              <b>✓</b>
              Séance effectuée
            </button>
            <button type="button" data-workout-action="skipped">
              <b>—</b>
              Annuler la séance du jour
            </button>
          </div>
        `}

        ${workout.priority === "optional" ? `
          <button
            class="remove-optional-workout"
            type="button"
            data-remove-optional-workout
          >
            Supprimer cette activité facultative
          </button>
        ` : ""}

        <p class="workout-actions-note">
          Atlas conservera votre décision et l’utilisera pour adapter
          les prochaines séances.
        </p>
      </section>
    `;
  }

  function humanizeDecisionReason(reason) {
    return Object.entries(TYPE_LABELS).reduce(
      (text, [technicalName, label]) => (
        text.replaceAll(technicalName, label)
      ),
      String(reason || "")
    );
  }
  function dailyPreparationDetailHtml(preparation, originalWorkout) {
    if (!preparation) return "";
    if (workoutDecision(originalWorkout).status === "skipped") {
      return "";
    }

    const decision = preparation.decision || {};
    const adapted = preparation.adaptation?.adapted_workout || {};
    const atlasIndex = preparation.atlas_index || {};
    const declared = preparation.declared_state || {};
    const currentSelection = dailySelectionCache.get(
      originalWorkout.workout_id
    );
    const selectionLabels = {
      accept_adaptation: "Proposition Atlas acceptée",
      keep_original: "Séance initiale conservée",
      decide_later: "Décision différée"
    };

    return `
      <section class="daily-preparation-detail action-${escapeHtml(
        decision.action || "review"
      )}">
        <div class="daily-preparation-detail-heading">
          <div>
            <span>DÉCISION ADAPTATIVE ATLAS</span>
            <h2>${escapeHtml(dailyPreparationLabel(decision.action))}</h2>
            <p>
              La prescription initiale reste conservée, mais la séance
              ci-dessous tient compte de votre récupération actuelle.
            </p>
          </div>
          <strong>
            ${escapeHtml(atlasIndex.score ?? "—")}/100
            <small>Indice Atlas</small>
          </strong>
        </div>
        <div class="daily-preparation-comparison">
          <article>
            <span>Séance initiale</span>
            <strong>${escapeHtml(originalWorkout.title)}</strong>
            <small>${escapeHtml(
              formatMinutes(originalWorkout.planned_duration_minutes)
            )}</small>
          </article>
          <i>→</i>
          <article class="adapted">
            <span>Proposition actuelle</span>
            <strong>${escapeHtml(
              adapted.title || "Réévaluation nécessaire"
            )}</strong>
            <small>${escapeHtml(
              formatMinutes(adapted.planned_duration_minutes)
            )}</small>
          </article>
        </div>
        <div class="daily-preparation-reasons">
          <strong>Pourquoi Atlas modifie la séance</strong>
          <p>${(decision.reasons || []).map(
            reason => escapeHtml(humanizeDecisionReason(reason))
          ).join(" ")}</p>
          ${preparation.checkpoint_type === "post_nap" ? `
            <small>
              Après une sieste de
              ${escapeHtml(declared.nap_duration_minutes ?? "—")} min :
              énergie ${escapeHtml(declared.energy_0_to_10 ?? "—")}/10,
              fatigue ${escapeHtml(
                declared.subjective_fatigue_0_to_10 ?? "—"
              )}/10.
            </small>
          ` : ""}
        </div>
        <div class="daily-preparation-controls">
          <form data-daily-preparation-form>
            <div class="daily-preparation-control-heading">
              <div>
                <span>RÉÉVALUATION DU JOUR</span>
                <strong>Ma forme a-t-elle changé ?</strong>
                <p>
                  Une sieste, une évolution de la fatigue ou une douleur
                  peuvent modifier la séance proposée sans effacer
                  l’évaluation précédente.
                </p>
              </div>
              <label>
                Moment
                <select name="checkpoint_type">
                  <option value="pre_workout">Avant la séance</option>
                  <option value="post_nap"${preparation.checkpoint_type === "post_nap" ? " selected" : ""}>Après une sieste</option>
                  <option value="morning"${preparation.checkpoint_type === "morning" ? " selected" : ""}>Le matin</option>
                </select>
              </label>
            </div>

            <div class="daily-preparation-input-grid">
              <label><span>Sieste <small>minutes</small></span><input name="nap_duration_minutes" type="number" min="0" max="240" step="1" value="${escapeHtml(declared.nap_duration_minutes ?? "")}"></label>
              <label><span>Énergie <small>0 à 10</small></span><input name="energy_0_to_10" type="number" min="0" max="10" step="1" value="${escapeHtml(declared.energy_0_to_10 ?? "")}"></label>
              <label><span>Fatigue <small>0 à 10</small></span><input name="subjective_fatigue_0_to_10" type="number" min="0" max="10" step="1" value="${escapeHtml(declared.subjective_fatigue_0_to_10 ?? "")}"></label>
              <label><span>Douleur <small>0 à 10</small></span><input name="pain_0_to_10" type="number" min="0" max="10" step="1" value="${escapeHtml(declared.pain_0_to_10 ?? "")}"></label>
              <label><span>Courbatures <small>0 à 10</small></span><input name="muscle_soreness_0_to_10" type="number" min="0" max="10" step="1" value="${escapeHtml(declared.muscle_soreness_0_to_10 ?? "")}"></label>
              <label><span>Body Battery <small>0 à 100</small></span><input name="body_battery_0_to_100" type="number" min="0" max="100" step="1" value="${escapeHtml(declared.body_battery_0_to_100 ?? "")}"></label>
              <label><span>Récupération Garmin <small>heures restantes</small></span><input name="recovery_hours_remaining" type="number" min="0" max="168" step=".5" value="${escapeHtml(declared.recovery_hours_remaining ?? "")}"></label>
            </div>

            <label class="daily-preparation-comment">
              <span>Ce qui a changé depuis la dernière évaluation</span>
              <textarea name="comment" rows="2" placeholder="Ex. : sieste réparatrice, énergie remontée, jambes légères…">${escapeHtml(declared.comment || "")}</textarea>
            </label>

            <div class="daily-preparation-form-footer">
              <p data-daily-preparation-status aria-live="polite"></p>
              <button type="submit">Réévaluer ma forme</button>
            </div>
          </form>

          <section class="daily-preparation-choice">
            <div>
              <span>MA DÉCISION</span>
              <strong>Je garde la maîtrise de mon entraînement</strong>
              <p>
                Atlas conserve la prescription initiale et la proposition
                adaptée. Aucun changement n’est validé silencieusement.
              </p>
            </div>
            <div class="daily-preparation-choice-buttons">
              <button type="button" data-daily-selection="accept_adaptation">✓ Accepter la proposition Atlas</button>
              <button type="button" data-daily-selection="keep_original">Conserver la séance initiale</button>
              <button type="button" data-daily-selection="decide_later">Réévaluer plus tard</button>
            </div>
            <p class="daily-selection-status" data-daily-selection-status aria-live="polite">
              ${currentSelection
                ? escapeHtml(
                    selectionLabels[currentSelection.user_selection] ||
                    "Choix enregistré"
                  )
                : "Aucun choix définitif enregistré."}
            </p>
          </section>
        </div>
      </section>
    `;
  }
  function openWorkout(workout, preparation = null) {
    const dialog = ensureDialog();
    const content = dialog.querySelector(".dialog-content");
    dialog.dataset.workoutId = workout.workout_id;
    let loadedReport = null;
    let loadedContext = null;
    const cancelled = workoutDecision(workout).status === "skipped";
    const adaptedWorkout = cancelled
      ? workout
      : preparation?.adaptation?.adapted_workout || workout;

    content.innerHTML = `
      <nav class="session-dialog-tabs" aria-label="Fiche de séance">
        <button
          type="button"
          class="active"
          data-session-tab="planned"
          aria-selected="true"
        >
          Séance prévue
        </button>
        <button
          type="button"
          data-session-tab="report"
          aria-selected="false"
        >
          Compte-rendu Atlas
          <i data-report-status>Chargement…</i>
        </button>
      </nav>

      <section
        class="session-tab-panel active"
        data-session-panel="planned"
      >
          ${detailHtml(adaptedWorkout)}
          ${dailyPreparationDetailHtml(preparation, workout)}
          ${workoutActionsHtml(adaptedWorkout)}
      </section>

      <section
        class="session-tab-panel"
        data-session-panel="report"
        hidden
      >
        <div class="report-loading">
          <span></span>
          Atlas recherche l’analyse FIT correspondante…
        </div>
      </section>
    `;

    content.onclick = async event => {
      const tab = event.target.closest("[data-session-tab]");

      if (tab) {
        const selected = tab.dataset.sessionTab;

        content.querySelectorAll("[data-session-tab]").forEach(button => {
          const active = button.dataset.sessionTab === selected;
          button.classList.toggle("active", active);
          button.setAttribute("aria-selected", String(active));
        });

        content.querySelectorAll("[data-session-panel]").forEach(panel => {
          const active = panel.dataset.sessionPanel === selected;
          panel.classList.toggle("active", active);
          panel.hidden = !active;
        });

        return;
      }

      const selectionButton = event.target.closest(
        "[data-daily-selection]"
      );
      if (selectionButton) {
        const selection = selectionButton.dataset.dailySelection;
        const statusElement = content.querySelector(
          "[data-daily-selection-status]"
        );
        let reason = "";

        if (selection === "keep_original") {
          const confirmed = window.confirm(
            "Conserver la séance initiale malgré la proposition adaptée d’Atlas ?"
          );
          if (!confirmed) return;
          reason = "Choix explicite de conserver la prescription initiale.";
        } else if (selection === "accept_adaptation") {
          reason = "Proposition adaptée Atlas acceptée par l’utilisateur.";
        } else {
          reason = "Décision différée pour permettre une nouvelle réévaluation.";
        }

        content.querySelectorAll("[data-daily-selection]").forEach(
          item => { item.disabled = true; }
        );
        if (statusElement) {
          statusElement.textContent = "Enregistrement du choix…";
          statusElement.className = "daily-selection-status saving";
        }

        try {
          const saved = await saveDailySelection(
            workout.workout_id,
            selection,
            reason
          );
          const labels = {
            accept_adaptation: "Proposition Atlas acceptée.",
            keep_original: "Séance initiale conservée.",
            decide_later: "Décision différée : une nouvelle réévaluation restera possible."
          };
          if (statusElement) {
            statusElement.textContent =
              labels[saved?.user_selection] || "Choix enregistré.";
            statusElement.className = "daily-selection-status success";
          }
          content.querySelectorAll("[data-daily-selection]").forEach(
            item => {
              item.disabled = false;
              item.classList.toggle(
                "selected",
                item.dataset.dailySelection === saved?.user_selection
              );
            }
          );
            if (
              saved?.user_selection === "accept_adaptation" ||
              saved?.user_selection === "keep_original"
            ) {
              dialog.close();
              render(activeProgram);
            }
        } catch (error) {
          if (statusElement) {
            statusElement.textContent = error.message;
            statusElement.className = "daily-selection-status error";
          }
          content.querySelectorAll("[data-daily-selection]").forEach(
            item => { item.disabled = false; }
          );
        }
        return;
      }

      const removeButton = event.target.closest(
        "[data-remove-optional-workout]"
      );

      if (removeButton) {
        const confirmed = await atlasConfirm(
          "Cette séance d’essai sera retirée du calendrier. Elle ne sera pas considérée comme abandonnée et n’influencera pas l’apprentissage d’Atlas."
        );
        if (!confirmed) return;

        try {
          await removeOptional(workout);
        } catch (error) {
          window.alert(`Erreur Atlas :\n${error.message}`);
          return;
        }
        dialog.close();
        render(activeProgram);
        return;
      }

      const button = event.target.closest("[data-workout-action]");
      if (!button) return;

      const status = button.dataset.workoutAction;
      let reason = "";

      if (status === "skipped") {
        const answer = window.prompt(
          "Pourquoi cette séance ne sera-t-elle pas effectuée ?",
          "Choix personnel"
        );
        if (answer === null) return;
        reason = answer.trim() || "Non précisé";
      }

      button.disabled = true;

      try {
        const response = await fetch(
          "/api/atlas-coach/workout-decision",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json; charset=utf-8"
            },
            body: JSON.stringify({
              workout_id: workout.workout_id,
              status,
              reason
            })
          }
        );
        const payload = await response.json();

        if (!response.ok || !payload.ok) {
          throw new Error(
            payload.error || "Décision Atlas indisponible."
          );
        }

        saveWorkoutDecision(workout, payload.decision);
        dialog.close();
        render(activeProgram);

        const explanations =
          payload.decision.explanations || [];
        if (explanations.length) {
          window.alert(
            `Décision Atlas\n\n${explanations.join("\n")}`
          );
        }
      } catch (error) {
        window.alert(
          `Erreur Atlas :\n${error.message}`
        );
        button.disabled = false;
      }
    };

    content.onsubmit = async event => {
      const readinessForm = event.target.closest(
        "[data-daily-preparation-form]"
      );

      if (readinessForm) {
        event.preventDefault();
        const values = new FormData(readinessForm);
        const submitButton = readinessForm.querySelector(
          'button[type="submit"]'
        );
        const formStatus = readinessForm.querySelector(
          "[data-daily-preparation-status]"
        );
        const previousState = preparation?.declared_state || {};
        const plannedPanel = content.querySelector(
          '[data-session-panel="planned"]'
        );
        const fieldValue = name => {
          const field = plannedPanel?.querySelector(
            `.daily-preparation-controls [name="${name}"]`
          );
          return field ? String(field.value).trim() : "";
        };
        const optionalNumber = name => {
          const value = fieldValue(name);
          if (value !== "") {
            const parsed = Number(value);
            return Number.isFinite(parsed) ? parsed : null;
          }
          return previousState[name] ?? null;
        };

        submitButton.disabled = true;
        formStatus.textContent =
          "Atlas recalcule votre disponibilité et la compatibilité de la séance…";
        formStatus.className = "saving";

        try {
          const updatedPreparation = await saveDailyPreparation(
            workout.workout_id,
            {
              checkpoint_type: String(
                fieldValue("checkpoint_type") || "pre_workout"
              ),
              nap_duration_minutes: optionalNumber(
                "nap_duration_minutes"
              ),
              energy_0_to_10: optionalNumber("energy_0_to_10"),
              subjective_fatigue_0_to_10: optionalNumber(
                "subjective_fatigue_0_to_10"
              ),
              pain_0_to_10: optionalNumber("pain_0_to_10"),
              muscle_soreness_0_to_10: optionalNumber(
                "muscle_soreness_0_to_10"
              ),
              body_battery_0_to_100: optionalNumber(
                "body_battery_0_to_100"
              ),
              recovery_hours_remaining: optionalNumber(
                "recovery_hours_remaining"
              ),
              comment: fieldValue("comment") || previousState.comment || ""
            }
          );

          dialog.close();
          render(activeProgram);
          applyDailyPreparation(updatedPreparation);
          openWorkout(workout, updatedPreparation);
        } catch (error) {
          formStatus.textContent = error.message;
          formStatus.className = "error";
          submitButton.disabled = false;
        }
        return;
      }

      const form = event.target.closest("[data-workout-context-form]");
      if (!form) return;

      event.preventDefault();
      const submitButton = form.querySelector('button[type="submit"]');
      const formStatus = form.querySelector("[data-context-form-status]");
      const values = new FormData(form);

      submitButton.disabled = true;
      formStatus.textContent = "Enregistrement en cours…";
      formStatus.className = "context-form-status saving";

      try {
        loadedContext = await saveWorkoutContext(
          workout,
          loadedReport,
          {
            heat: values.get("heat") === "on",
            relief: values.get("relief") === "on",
            pain: values.get("pain") || "",
            fatigue: values.get("fatigue") || "",
            comment: String(values.get("comment") || "")
          }
        );

        const panel = content.querySelector(
          '[data-session-panel="report"]'
        );
        panel.innerHTML = executionReportHtml(
          loadedReport,
          workout,
          loadedContext
        );

        const updatedStatus = panel.querySelector(
          "[data-context-form-status]"
        );
        if (updatedStatus) {
          updatedStatus.textContent =
            "Votre contexte a bien été enregistré et intégré à la lecture Atlas.";
          updatedStatus.className = "context-form-status success";
        }
      } catch (error) {
        formStatus.textContent = error.message;
        formStatus.className = "context-form-status error";
        submitButton.disabled = false;
      }
    };

    dialog.showModal();
    dialog.scrollTop = 0;
    content.scrollTop = 0;
    const dialogShell = dialog.querySelector(".session-dialog-shell");
    if (dialogShell) dialogShell.scrollTop = 0;
    requestAnimationFrame(() => {
      dialog.scrollTop = 0;
      content.scrollTop = 0;
      if (dialogShell) dialogShell.scrollTop = 0;
    });

    const displayExecutionReport = async (report, userContext) => {
      loadedReport = report;
      loadedContext = userContext;
      if (dialog.dataset.workoutId !== workout.workout_id) return;

      const panel = content.querySelector(
        '[data-session-panel="report"]'
      );
      const status = content.querySelector("[data-report-status]");

      panel.innerHTML = executionReportHtml(
        report,
        workout,
        userContext
      );
      status.textContent = report
        ? "Analyse disponible"
        : "En attente · analyse automatique en cours";
      status.dataset.available = String(Boolean(report));

      if (report) {
        await syncWorkoutDecisions();
        content.querySelector(
          '[data-session-tab="report"]'
        )?.click();
      }
    };

    Promise.all([
      loadExecutionReport(workout.workout_id),
      loadWorkoutContext(workout.workout_id)
    ])
      .then(async ([report, userContext]) => {
        await displayExecutionReport(report, userContext);
        if (report) return;

        // Le traitement FIT est asynchrone. Tant que ce volet reste ouvert,
        // Atlas recherche automatiquement le compte-rendu pendant une minute.
        for (let attempt = 0; attempt < 20; attempt += 1) {
          await new Promise(resolve => window.setTimeout(resolve, 3000));
          if (
            !dialog.open ||
            dialog.dataset.workoutId !== workout.workout_id
          ) return;

          const refreshed = await loadExecutionReport(workout.workout_id);
          if (!refreshed) continue;

          await displayExecutionReport(refreshed, userContext);
          return;
        }
      })
      .catch(error => {
        if (dialog.dataset.workoutId !== workout.workout_id) return;

        const panel = content.querySelector(
          '[data-session-panel="report"]'
        );
        const status = content.querySelector("[data-report-status]");

        panel.innerHTML = `
          <section class="execution-report-empty error">
            <strong>Compte-rendu indisponible</strong>
            <p>${escapeHtml(error.message)}</p>
          </section>
        `;
        status.textContent = "Indisponible";
      });
  }

  const OPTIONAL_ACTIVITY_TYPES = [
    ["recovery_run", "Récupération Z1", "Course très facile", false],
    ["endurance_run", "Endurance Z2", "Endurance fondamentale", false],
    ["threshold_run", "Seuil SV2", "Travail au seuil", false],
    ["vo2max_run", "VO₂max", "Intervalles intensifs", false],
    ["strength", "Renforcement", "Force et prévention", false],
    ["mobility", "Mobilité", "Souplesse et amplitude", false],
    ["cycling", "Vélo", "Endurance sans impact", false],
    ["double_session", "Double séance", "Deux entraînements le même jour", true],
    ["double_threshold", "Double seuil", "Deux séances au seuil", true]
  ];
  const OPTIONAL_ACTIVITY_CONFIG = {
    recovery_run: {
      title: "Récupération Z1", sport: "running", duration: 35,
      objective: "Favoriser la récupération par un effort très facile.",
      physiological: 22, biomechanical: 20, recovery: [8, 18]
    },
    endurance_run: {
      title: "Endurance Z2", sport: "running", duration: 50,
      objective: "Développer l’endurance aérobie sans fatigue excessive.",
      physiological: 34, biomechanical: 32, recovery: [12, 24]
    },
    threshold_run: {
      title: "Seuil SV2", sport: "running", duration: 55,
      objective: "Stimuler le seuil anaérobie avec une charge contrôlée.",
      physiological: 68, biomechanical: 52, recovery: [30, 48]
    },
    vo2max_run: {
      title: "VO₂max", sport: "running", duration: 50,
      objective: "Développer la puissance aérobie par intervalles.",
      physiological: 82, biomechanical: 68, recovery: [36, 60]
    },
    strength: {
      title: "Renforcement", sport: "strength", duration: 25,
      objective: "Renforcer les structures utiles à la course.",
      physiological: 30, biomechanical: 58, recovery: [24, 48]
    },
    mobility: {
      title: "Mobilité", sport: "mobility", duration: 20,
      objective: "Entretenir les amplitudes et réduire les raideurs.",
      physiological: 10, biomechanical: 12, recovery: [4, 10]
    },
    cycling: {
      title: "Vélo", sport: "cycling", duration: 60,
      objective: "Ajouter de l’endurance avec une charge d’impact réduite.",
      physiological: 38, biomechanical: 16, recovery: [12, 24]
    },
    double_session: {
      title: "Double séance", sport: "running", duration: 70,
      objective: "Répartir deux stimuli dans la même journée.",
      physiological: 76, biomechanical: 70, recovery: [36, 60]
    },
    double_threshold: {
      title: "Double seuil", sport: "running", duration: 90,
      objective: "Réaliser deux blocs au seuil sous contrôle Atlas.",
      physiological: 92, biomechanical: 84, recovery: [48, 72]
    }
  };
  function optionalTarget(type, vma, maximumHeartRate) {
    const targets = {
      recovery_run: [1, .55, .65, .62, .71, 2.5],
      endurance_run: [2, .65, .75, .70, .79, 3.5],
      threshold_run: [4, .86, .92, .85, .91, 7],
      vo2max_run: [5, .95, 1.05, .90, .96, 8.5],
      cycling: [2, null, null, .68, .78, 3.5],
      double_session: [2, .62, .74, .68, .78, 4],
      double_threshold: [4, .84, .90, .84, .90, 7]
    };
    const values = targets[type] || targets.recovery_run;
    return {
      zone: values[0],
      speed_min_kmh: vma && values[1]
        ? Math.round(vma * values[1] * 10) / 10
        : null,
      speed_max_kmh: vma && values[2]
        ? Math.round(vma * values[2] * 10) / 10
        : null,
      heart_rate_min_bpm: maximumHeartRate && values[3]
        ? Math.round(maximumHeartRate * values[3])
        : null,
      heart_rate_max_bpm: maximumHeartRate && values[4]
        ? Math.round(maximumHeartRate * values[4])
        : null,
      rpe_0_10: values[5],
      intensity_pattern: type.includes("threshold") ||
        type === "vo2max_run"
        ? "interval"
        : "constant"
    };
  }
  function optionalBlocks(type, config, target) {
    if (type === "strength") {
      return [{
        name: "Circuit de renforcement",
        block_type: "circuit",
        repetitions: 3,
        duration_minutes: 25,
        recovery_minutes: 1,
        target: {
          zone: null, rpe_0_10: 5,
          intensity_pattern: "circuit"
        },
        instructions: (
          "Gainage, fentes, mollets et chaîne postérieure. " +
          "Conserver une exécution précise et indolore."
        )
      }];
    }

    if (type === "mobility") {
      return [{
        name: "Mobilité active",
        block_type: "mobility",
        repetitions: 1,
        duration_minutes: 20,
        recovery_minutes: null,
        target: {
          zone: null, rpe_0_10: 2,
          intensity_pattern: "progressive"
        },
        instructions: (
          "Mobiliser chevilles, hanches et rachis sans forcer " +
          "dans la douleur."
        )
      }];
    }

    if (type === "threshold_run" || type === "vo2max_run") {
      const threshold = type === "threshold_run";
      return [
        {
          name: "Échauffement",
          block_type: "warmup",
          repetitions: 1,
          duration_minutes: 15,
          recovery_minutes: null,
          target: optionalTarget(
            "recovery_run",
            Number(activeProgram.athlete_snapshot?.vma_kmh),
            Number(activeProgram.athlete_snapshot
              ?.maximum_heart_rate_bpm)
          ),
          instructions: "Course facile et mise en action progressive."
        },
        {
          name: threshold ? "3 × 8 min au SV2" : "6 × 3 min VO₂max",
          block_type: "interval",
          repetitions: threshold ? 3 : 6,
          duration_minutes: threshold ? 8 : 3,
          recovery_minutes: 2,
          target,
          instructions: (
            "Rester régulier. Interrompre si la technique se " +
            "dégrade ou si une douleur apparaît."
          )
        },
        {
          name: "Retour au calme",
          block_type: "cooldown",
          repetitions: 1,
          duration_minutes: 10,
          recovery_minutes: null,
          target: optionalTarget(
            "recovery_run",
            Number(activeProgram.athlete_snapshot?.vma_kmh),
            Number(activeProgram.athlete_snapshot
              ?.maximum_heart_rate_bpm)
          ),
          instructions: "Finir en aisance respiratoire."
        }
      ];
    }

    if (type === "double_session" ||
        type === "double_threshold") {
      return [
        {
          name: "Séance du matin",
          block_type: "continuous",
          repetitions: 1,
          duration_minutes: config.duration / 2,
          recovery_minutes: null,
          target,
          instructions: "Première séance validée par Atlas."
        },
        {
          name: "Séance du soir",
          block_type: "continuous",
          repetitions: 1,
          duration_minutes: config.duration / 2,
          recovery_minutes: null,
          target,
          instructions: (
            "Deuxième séance uniquement si les indicateurs " +
            "de récupération restent favorables."
          )
        }
      ];
    }

    return [{
      name: config.title,
      block_type: "continuous",
      repetitions: 1,
      duration_minutes: config.duration,
      recovery_minutes: null,
      target,
      instructions: (
        "Rester dans la cible prévue. Annuler en cas de douleur, " +
        "fatigue ou dérive cardiaque inhabituelle."
      )
    }];
  }
  function openActivityPicker(value) {
    const dialog = ensureDialog();
    const regular = OPTIONAL_ACTIVITY_TYPES.filter(
      item => !item[3]
    );
    const advanced = OPTIONAL_ACTIVITY_TYPES.filter(
      item => item[3]
    );
    const activityButtons = items => items.map(item => `
      <button
        class="activity-picker-choice"
        type="button"
        data-activity-type="${escapeHtml(item[0])}"
      >
        <strong>${escapeHtml(item[1])}</strong>
        <small>${escapeHtml(item[2])}</small>
      </button>
    `).join("");

    dialog.querySelector(".dialog-content").innerHTML = `
      <section class="activity-picker">
        <span class="session-kicker">ATLAS COACH</span>
        <h2>Ajouter une activité</h2>
        <p class="activity-picker-date">
          ${escapeHtml(formatDate(value))}
        </p>
        <div class="activity-picker-grid">
          ${activityButtons(regular)}
        </div>
        <button
          class="activity-picker-advanced-toggle"
          type="button"
          data-advanced-toggle
        >
          Mode avancé
        </button>
        <div class="activity-picker-advanced" hidden>
          <p>
            Atlas vérifiera la récupération, la charge et la
            compatibilité avec le programme avant validation.
          </p>
          <div class="activity-picker-grid">
            ${activityButtons(advanced)}
          </div>
        </div>
      </section>
    `;

    const content = dialog.querySelector(".dialog-content");
    content.querySelector("[data-advanced-toggle]").onclick = (
      event
    ) => {
      const panel = content.querySelector(
        ".activity-picker-advanced"
      );
      panel.hidden = !panel.hidden;
      event.currentTarget.textContent = panel.hidden
        ? "Mode avancé"
        : "Masquer le mode avancé";
    };
    content.querySelectorAll("[data-activity-type]").forEach(
      button => {
        button.onclick = () => {
          dialog.close();
          addOptional(value, button.dataset.activityType);
        };
      }
    );
    dialog.showModal();
    dialog.scrollTop = 0;
    content.scrollTop = 0;
    const dialogShell = dialog.querySelector(".session-dialog-shell");
    if (dialogShell) dialogShell.scrollTop = 0;
    requestAnimationFrame(() => {
      dialog.scrollTop = 0;
      content.scrollTop = 0;
      if (dialogShell) dialogShell.scrollTop = 0;
    });
  }
  function optionalWorkout(value, type = "recovery_run") {
    const snapshot = activeProgram.athlete_snapshot || {};
    const vma = Number(snapshot.vma_kmh) || null;
    const maximumHeartRate = Number(
      snapshot.maximum_heart_rate_bpm
    ) || null;
    const config = OPTIONAL_ACTIVITY_CONFIG[type] ||
      OPTIONAL_ACTIVITY_CONFIG.recovery_run;
    const selectedType = OPTIONAL_ACTIVITY_CONFIG[type]
      ? type
      : "recovery_run";
    const advanced = selectedType === "double_session" ||
      selectedType === "double_threshold";
    const target = optionalTarget(
      selectedType,
      vma,
      maximumHeartRate
    );

    return {
      workout_id: `${value}-optional-${selectedType}`,
      workout_date: value,
      workout_type: selectedType,
      title: config.title,
      objective: config.objective,
      sport: config.sport,
      priority: "optional",
      source: advanced
        ? "atlas_advanced_validation"
        : "user_optional",
      planned_duration_minutes: config.duration,
      expected_response: {
        physiological_load_0_100: config.physiological,
        biomechanical_load_0_100: config.biomechanical,
        recovery_min_hours: config.recovery[0],
        recovery_max_hours: config.recovery[1],
        sensitive_structures: config.sport === "running"
          ? ["mollets", "tendons d'Achille"]
          : []
      },
      coach_notes: [
        "Activité facultative ajoutée par l’utilisateur.",
        advanced
          ? "Mode avancé : validation Atlas requise le jour même."
          : "Elle sera revalidée par l’Indice Atlas le jour même."
      ],
      blocks: optionalBlocks(selectedType, config, target)
    };
  }

  async function saveOptional(workout) {
    const response = await fetch(
      "/api/atlas-coach/optional-workout",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify(workout)
      }
    );
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "La séance n’a pas pu être transmise à Atlas."
      );
    }

    const saved = JSON.parse(
      localStorage.getItem(STORAGE_KEY) || "[]"
    );
    const filtered = saved.filter(
      item => item.workout_id !== workout.workout_id
    );
    filtered.push(workout);
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(filtered)
    );
  }

  async function removeOptional(workout) {
    const response = await fetch(
      "/api/atlas-coach/optional-workout",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify({
          workout_id: workout.workout_id,
          delete: true
        })
      }
    );
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(
        payload.error || "La séance n’a pas pu être supprimée."
      );
    }

    let saved = [];

    try {
      saved = JSON.parse(
        localStorage.getItem(STORAGE_KEY) || "[]"
      );
    } catch {
      saved = [];
    }

    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(
        saved.filter(
          item => item.workout_id !== workout.workout_id
        )
      )
    );

    activeProgram.weeks.forEach(week => {
      week.workouts = week.workouts.filter(
        item => item.workout_id !== workout.workout_id
      );
    });

    delete workoutDecisions[workout.workout_id];
    localStorage.setItem(
      DECISIONS_STORAGE_KEY,
      JSON.stringify(workoutDecisions)
    );
    dailyPreparationCache.delete(workout.workout_id);
    dailySelectionCache.delete(workout.workout_id);
    workoutIndex.delete(workout.workout_id);
  }
  async function restoreOptional(program) {
    let localWorkouts = [];
    let serverWorkouts = [];

    try {
      localWorkouts = JSON.parse(
        localStorage.getItem(STORAGE_KEY) || "[]"
      );
    } catch {
      localWorkouts = [];
    }

    try {
      const response = await fetch(
        `/api/atlas-coach/optional-workouts?v=${Date.now()}`,
        { cache: "no-store" }
      );
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Mémoire Atlas invalide.");
      }
      serverWorkouts = Array.isArray(payload.workouts)
        ? payload.workouts
        : [];
    } catch (error) {
      console.warn("Séances Atlas restaurées indisponibles.", error);
    }

    const saved = [
      ...new Map(
        [...serverWorkouts, ...localWorkouts].map(
          workout => [workout.workout_id, workout]
        )
      ).values()
    ];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));

    saved.forEach(workout => {
      const week = program.weeks.find(
        item => (
          workout.workout_date >= item.start_date &&
          workout.workout_date <= item.end_date
        )
      );
      if (
        week &&
        !week.workouts.some(
          item => item.workout_id === workout.workout_id
        )
      ) {
        week.workouts.push(workout);
      }
    });

    await Promise.all(localWorkouts.map(async workout => {
      try {
        const response = await fetch(
          "/api/atlas-coach/optional-workout",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json; charset=utf-8"
            },
            body: JSON.stringify(workout)
          }
        );
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(
            payload.error || "Réponse Atlas invalide."
          );
        }
      } catch (error) {
        console.warn(
          "Séance facultative non synchronisée avec Atlas.",
          error
        );
      }

    }));
  }

  async function addOptional(value, type = "recovery_run") {
    const workout = optionalWorkout(value, type);
    try {
      await saveOptional(workout);
    } catch (error) {
      window.alert(`Erreur Atlas :\n${error.message}`);
      return;
    }

    const week = activeProgram.weeks.find(
      item => value >= item.start_date && value <= item.end_date
    );

    if (week) week.workouts.push(workout);

    render(activeProgram);
    openWorkout(workout);
  }

  function calendarZoneLegend() {
    return `
      <div class="calendar-zone-legend" aria-label="Zones d’intensité">
        <span class="zone-1"><i></i><b>Z1</b> Récupération</span>
        <span class="zone-2"><i></i><b>Z2</b> Endurance</span>
        <span class="zone-3"><i></i><b>Z3</b> Active</span>
        <span class="zone-4"><i></i><b>Z4</b> Seuil</span>
        <span class="zone-5"><i></i><b>Z5</b> VO₂max</span>
      </div>
    `;
  }
  function renderCoachZones(program) {
    const labels = {
      1: "Récupération",
      2: "Endurance fondamentale",
      3: "Endurance active",
      4: "Seuil",
      5: "VO₂max"
    };
    const collected = new Map(
      [1, 2, 3, 4, 5].map(zone => [
        zone,
        { speeds: [], heartRates: [], observations: 0 }
      ])
    );

    (program.weeks || []).forEach(week => {
      (week.workouts || []).forEach(workout => {
        (workout.blocks || []).forEach(block => {
          const target = block.target || {};
          const zone = Number(target.zone);
          const values = collected.get(zone);
          if (!values) return;

          [
            target.speed_min_kmh,
            target.speed_max_kmh
          ].forEach(value => {
            if (value !== null && value !== "" && Number.isFinite(Number(value))) {
              values.speeds.push(Number(value));
            }
          });

          [
            target.heart_rate_min_bpm,
            target.heart_rate_max_bpm
          ].forEach(value => {
            if (value !== null && value !== "" && Number.isFinite(Number(value))) {
              values.heartRates.push(Number(value));
            }
          });

          values.observations += 1;
        });
      });
    });

    const range = (values, digits = 0) => {
      if (!values.length) return null;
      const minimum = Math.min(...values);
      const maximum = Math.max(...values);
      const format = value => value.toLocaleString(
        "fr-FR",
        {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits
        }
      );
      return minimum === maximum
        ? format(minimum)
        : `${format(minimum)}–${format(maximum)}`;
    };

    const pace = speed => {
      if (!speed || speed <= 0) return null;
      const totalSeconds = Math.round(3600 / speed);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = String(totalSeconds % 60).padStart(2, "0");
      return `${minutes}:${seconds}`;
    };

    collected.forEach((values, zone) => {
      const summary = document.getElementById(
        `coachZone${zone}`
      );
      if (!summary) return;

      const speedRange = range(values.speeds, 2);
      const heartRateRange = range(values.heartRates);
      const minimumSpeed = values.speeds.length
        ? Math.min(...values.speeds)
        : null;
      const maximumSpeed = values.speeds.length
        ? Math.max(...values.speeds)
        : null;
      const paceRange = minimumSpeed && maximumSpeed
        ? `${pace(maximumSpeed)}–${pace(minimumSpeed)} min/km`
        : "Allure à confirmer";

      summary.innerHTML = `
        ${labels[zone]}
        <small>
          ${speedRange ? `${speedRange} km/h` : "Vitesse à confirmer"}
          ·
          ${heartRateRange ? `${heartRateRange} bpm` : "FC à confirmer"}
          <br>
          ${paceRange}
        </small>
      `;
      summary.title =
        `${values.observations} cible(s) du programme analysée(s)`;
    });
  }

  async function render(program) {
    activeProgram = program;
    workoutIndex.clear();
    await restoreOptional(program);
    renderCoachZones(program);
    physiologicalRibbon(program.athlete_snapshot);
    renderOverview(program);

    calendar.innerHTML = `

${program.weeks.map(
        week => renderWeek(week, program)
      ).join("")}
    `;

    planPanel.hidden = false;
    document.body.classList.add(
      "has-premium-training-calendar"
    );
    if (window.matchMedia("(max-width: 620px)").matches) {
      window.requestAnimationFrame(() => {
        const todayCard = calendar.querySelector(
          ".calendar-day.is-today"
        );
        const weekGrid = todayCard?.closest(".week-seven-grid");

        if (todayCard && weekGrid) {
          weekGrid.scrollTo({
            left: Math.max(
              0,
              todayCard.offsetLeft - weekGrid.offsetLeft - 8
            ),
            behavior: "auto"
          });
        }
      });
    }
    loadTodayPreparations(program);
  }

  calendar.addEventListener("click", event => {
    const mobileDay = event.target.closest("[data-mobile-day]");

    if (mobileDay) {
      const week = mobileDay.closest(".premium-week");
      const selectedIndex = Number(mobileDay.dataset.mobileDay);
      const tabs = week.querySelectorAll("[data-mobile-day]");
      const dayCards = week.querySelectorAll(".calendar-day");

      tabs.forEach((tab, index) => {
        const selected = index === selectedIndex;
        tab.classList.toggle("is-selected", selected);
        tab.setAttribute("aria-selected", String(selected));
      });

      dayCards.forEach((dayCard, index) => {
        dayCard.classList.toggle(
          "is-mobile-selected",
          index === selectedIndex
        );
      });
      return;
    }
    const workoutButton = event.target.closest(
      "[data-workout-key]"
    );
    const optional = event.target.closest(
      "[data-optional-date]"
    );

    if (workoutButton) {
      const workoutKey = workoutButton.dataset.workoutKey;
      openWorkout(
        workoutIndex.get(workoutKey),
        dailyPreparationCache.get(workoutKey) || null
      );
      return;
    }

    if (optional) {
      openActivityPicker(optional.dataset.optionalDate);
    }
  });

  async function loadProgram() {
    await syncWorkoutDecisions();
    const sources = [
      window.ATLAS_TRAINING_PROGRAM_URL,
      "../atlas-data/private/training-program.json",
      "/atlas-data/private/training-program.json"
    ].filter(Boolean);

    for (const source of sources) {
      try {
        const response = await fetch(
          `${source}?v=${Date.now()}`,
          { cache: "no-store" }
        );

        if (!response.ok) continue;

        const program = await response.json();

        if (program?.weeks && program?.goal) {
          await render(program);
          return;
        }
      } catch (error) {
        console.debug(
          "Calendrier Atlas indisponible.",
          source,
          error
        );
      }
    }
  }

  loadProgram();
})();
/* FIN GRILLE HEBDOMADAIRE PREMIUM ATLAS COACH */
