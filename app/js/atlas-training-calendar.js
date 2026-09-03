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
  let synchronizedPhysiology = null;
  let workoutDecisions = loadWorkoutDecisions();
  const executionReportCache = new Map();
  let historicalCompletedWorkouts = [];

  function executionSessionLabel(execution) {
    const type = String(
      execution.activity?.session_type ||
      execution.analysis?.session_type || ""
    ).toLowerCase();
    return {
      vo2: "VO₂max",
      vma: "VO₂max / VMA",
      interval: "Fractionné",
      threshold: "Seuil SV2",
      tempo: "Tempo",
      endurance: "Endurance fondamentale",
      recovery: "Récupération",
      long_run: "Sortie longue"
    }[type] || "Séance analysée par Atlas";
  }

  function historicalWorkoutForExecution(execution, archivedWorkouts) {
    const executionDate = String(execution.start_time || "").slice(0, 10);
    const sport = String(execution.activity?.sport || "running");
    const sessionType = String(
      execution.activity?.session_type ||
      execution.analysis?.session_type || ""
    ).toLowerCase();
    const candidates = archivedWorkouts.filter(workout => (
      workout.archived_program &&
      workout.workout_date === executionDate &&
      String(workout.sport || "running") === sport
    ));
    const compatible = candidates.find(workout => {
      const type = String(workout.workout_type || "").toLowerCase();
      if (["vo2", "vma", "interval"].includes(sessionType)) {
        return type.includes("vo2") || type.includes("vma");
      }
      if (sessionType === "threshold") {
        return type.includes("threshold") || type.includes("sv2");
      }
      return false;
    });
    return compatible || candidates[0] || null;
  }

  async function loadHistoricalCompletedWorkouts(program) {
    try {
      const executionsResponse = await fetch(
        `/api/atlas-coach/executions?limit=100&v=${Date.now()}`,
        { cache: "no-store" }
      );
      if (!executionsResponse.ok) return [];

      let historyPayload = {};
      try {
        const historyResponse = await fetch(
          `/api/atlas-coach/historical-workouts?v=${Date.now()}`,
          { cache: "no-store" }
        );
        if (historyResponse.ok) historyPayload = await historyResponse.json();
      } catch (error) {
        console.debug("Archives de programme facultatives indisponibles.", error);
      }
      const executionsPayload = await executionsResponse.json();
      const archived = historyPayload.workouts || [];
      const current = (program.weeks || []).flatMap(
        week => week.workouts || []
      );

      return (executionsPayload.executions || []).flatMap((execution, index) => {
        const executionDate = String(execution.start_time || "").slice(0, 10);
        const activityId = String(execution.activity_id || "");
        const match = execution.workout_match || {};
        const alreadyRepresented = current.some(workout => (
          workout.workout_date === executionDate &&
          match.matched &&
          workout.workout_id === match.workout_id
        ));
        if (alreadyRepresented || !executionDate) return [];

        const archivedWorkout = historicalWorkoutForExecution(
          execution,
          archived
        );
        const activity = execution.activity || {};
        const syntheticId = `completed-${activityId || index}`;
        workoutDecisions[syntheticId] = {
          status: "completed",
          source: "historical_fit",
          activity_id: activityId,
          execution_score: match.execution?.execution_score
        };

        return [{
          ...(archivedWorkout || {}),
          workout_id: syntheticId,
          report_activity_id: activityId,
          workout_date: executionDate,
          title: archivedWorkout?.title || executionSessionLabel(execution),
          sport: activity.sport || archivedWorkout?.sport || "running",
          planned_duration_minutes:
            Number(activity.duration_minutes) ||
            Number(archivedWorkout?.planned_duration_minutes),
          actual_duration_minutes: Number(activity.duration_minutes),
          distance_km: Number(activity.distance_km),
          average_heart_rate_bpm: Number(activity.average_heart_rate_bpm),
          execution_score: Number(match.execution?.execution_score),
          objective: archivedWorkout?.objective ||
            "Séance réellement effectuée, reconstruite depuis Garmin FIT.",
          planned_distance_km: Number(activity.distance_km),
          blocks: (execution.analysis?.blocks || []).map(block => ({
            block_type: block.block_type || "continuous",
            name: `Bloc réalisé · ${String(
              block.block_type || "course"
            ).replaceAll("_", " ")}`,
            duration_seconds: Number(block.duration_seconds),
            distance_meters: Number(block.distance_meters),
            repetitions: 1,
            actual_block: true,
            target: {
              zone: ({
                warm_up: 1, cool_down: 1, recovery: 1, z1: 1,
                z2: 2, z3: 3, tempo: 3, sv2: 3,
                vma: 4, vo2: 4, sprint: 5, acceleration: 5
              })[block.block_type] || 1,
              speed_min_kmh: Number(block.average_speed_kmh),
              speed_max_kmh: Number(block.average_speed_kmh),
              heart_rate_min_bpm: Number(block.average_heart_rate_bpm),
              heart_rate_max_bpm: Number(block.average_heart_rate_bpm)
            }
          })),
          historical_execution: true,
          analysis_available: true
        }];
      });
    } catch (error) {
      console.warn("Séances historiques non réintégrées :", error);
      return [];
    }
  }

  async function loadExecutionReport(workoutId, activityId = "") {
    const cacheKey = activityId
      ? `activity:${activityId}`
      : `workout:${workoutId}`;
    if (executionReportCache.has(cacheKey)) {
      return executionReportCache.get(cacheKey);
    }

    const lookup = activityId
      ? `activity_id=${encodeURIComponent(activityId)}`
      : `workout_id=${encodeURIComponent(workoutId)}`;
    const response = await fetch(
      `/api/atlas-coach/executions?${lookup}&limit=1`,
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
      executionReportCache.set(cacheKey, report);
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
          heat: Number(values.heat) > 0,
          relief: Number(values.relief) > 0,
          overall_sensation_0_to_10: Number(values.sensation),
          perceived_effort_0_to_10: Number(values.effort),
          heat_0_to_10: Number(values.heat),
          relief_0_to_10: Number(values.relief),
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
      const [response, executionsResponse] = await Promise.all([
        fetch(
          `/api/atlas-coach/workout-decisions?v=${Date.now()}`,
          { cache: "no-store" }
        ),
        fetch(
          `/api/atlas-coach/executions?limit=100&v=${Date.now()}`,
          { cache: "no-store" }
        )
      ]);
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Mémoire Atlas indisponible.");
      }

      workoutDecisions = {
        ...workoutDecisions,
        ...(payload.decisions || {})
      };

      if (executionsResponse.ok) {
        const executionsPayload = await executionsResponse.json();
        (executionsPayload.executions || []).forEach((execution) => {
          const match = execution.workout_match || {};
          const workoutId = String(match.workout_id || "");
          const executionDate = String(execution.start_time || "").slice(0, 10);
          const plannedDate = workoutId.slice(0, 10);

          // Une activité supplémentaire peut ressembler à une séance du plan.
          // Elle ne doit la valider que si le moteur a confirmé l'association
          // et si elle a réellement eu lieu le jour prévu.
          if (!match.matched || !workoutId || executionDate !== plannedDate) {
            return;
          }

          workoutDecisions[workoutId] = {
            ...workoutDecisions[workoutId],
            status: "completed",
            source: "fit_execution",
            activity_id: execution.activity_id,
            execution_score: match.execution?.execution_score,
            updated_at: execution.start_time
          };
        });
      }
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
      longitudinal: "Estimation longitudinale",
      longitudinal_estimate: "Estimation longitudinale",
      validated: "Référence validée",
      validated_threshold_reference: "Référence de seuil validée",
      measured: "Mesure validée",
      session_adjusted_estimate: "Ajustement issu de la dernière séance",
      missing: "\u00c0 confirmer"
    }[status] || "Référence Atlas");

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
        width:142px;
        height:142px;
        min-width:142px;
        margin:auto;
        padding:18px;
        text-align:center;
        border:1px solid ${accent};
        border-radius:50%;
        background:
          radial-gradient(circle at 50% 70%, ${glow}, transparent 63%),
          #071728;
        box-shadow:
          0 0 22px ${glow},
          inset 0 0 0 7px #071728,
          inset 0 0 0 8px ${accent}55;
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
        label: "FC maximale",
        value: snapshot.maximum_heart_rate_bpm,
        unit: "bpm",
        note: "R\u00e9f\u00e9rence personnelle",
        accent: "#f4c84a",
        glow: "rgba(244,200,74,.13)"
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
          formatMinutes(
            workout.actual_duration_minutes ||
            workout.planned_duration_minutes
          )
        )}${workout.distance_km ? ` · ${escapeHtml(
          Number(workout.distance_km).toLocaleString("fr-FR", {
            maximumFractionDigits: 2
          })
        )} km` : ""}</small>
        ${workout.historical_execution ? `
          <small class="calendar-session-completed-detail">
            Réalisée${Number.isFinite(workout.execution_score)
              ? ` · score ${Math.round(workout.execution_score)}/100`
              : ""}
          </small>
        ` : ""}
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
    const active = workouts.some(workout => workout.historical_execution) || (
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
    const historical = historicalCompletedWorkouts.filter(workout => (
      workout.workout_date >= week.start_date &&
      workout.workout_date <= week.end_date
    ));
    const displayedWorkouts = [...week.workouts, ...historical];

    displayedWorkouts.forEach(workout => {
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

    const completedMinutes = historical.reduce(
      (total, workout) => total + Number(
        workout.actual_duration_minutes || 0
      ),
      0
    );

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
              formatMinutes(
                Number(week.target_duration_minutes || 0) + completedMinutes
              )
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
    return dialog;
  }

  const DISPLAY_ZONE_COLORS = {
    1: "#38a9ff",
    2: "#49d17d",
    3: "#f0cf4f",
    4: "#ff9f43",
    5: "#ff506c"
  };

  function canonicalBlockType(block = {}) {
    return String(block.block_type || "")
      .toLowerCase()
      .replaceAll("-", "_")
      .replace("warmup", "warm_up")
      .replace("cooldown", "cool_down");
  }

  function workoutBlockIsOptional(block = {}) {
    const description = `${block.name || ""} ${block.instructions || ""}`
      .toLowerCase();
    return (
      description.includes("facultatif") ||
      description.includes("effectuer uniquement")
    );
  }

  function workoutRepetitionRange(block = {}) {
    const minimum = Math.max(1, Number(block.repetitions) || 1);
    const range = String(block.name || "").match(
      /(\d+)\s*(?:à|a|-)\s*(\d+)(?:\s*[×x]|\s+rép)/i
    );
    const maximum = range
      ? Math.max(minimum, Number(range[2]) || minimum)
      : minimum;

    return { minimum, maximum };
  }

  function atlasDisplayZone(workout, block = {}) {
    const blockType = canonicalBlockType(block);
    const workoutType = String(workout?.workout_type || "").toLowerCase();
    const blockName = String(block.name || "").toLowerCase();

    if (["warm_up", "cool_down", "recovery", "rest", "z1"].includes(blockType)) return 1;
    if (blockType === "z2") return 2;
    if (["z3", "tempo", "sv2"].includes(blockType)) return 3;
    if (["vma", "vo2", "vo2max", "z4"].includes(blockType)) return 4;
    if (["sprint", "acceleration", "z5"].includes(blockType)) return 5;

    if (blockName.includes("seuil") || blockName.includes("sv2") || blockName.includes("tempo")) return 3;
    if (blockName.includes("sprint") || blockName.includes("anaérobie")) return 5;
    if (blockName.includes("vo2") || blockName.includes("vo₂")) return 4;
    if (blockName.includes("vma")) {
      const namedDistance = Number(block.distance_meters);
      const namedDurationSeconds = Number(block.duration_seconds) ||
        Number(block.duration_minutes) * 60;
      return (namedDistance > 0 && namedDistance <= 200) ||
        (namedDurationSeconds > 0 && namedDurationSeconds <= 45)
        ? 5
        : 4;
    }

    if (workoutType.includes("sprint")) return 5;
    if (workoutType === "vma_short") {
      const distance = Number(block.distance_meters);
      const durationSeconds = Number(block.duration_seconds) ||
        Number(block.duration_minutes) * 60;
      return (distance > 0 && distance <= 200) ||
        (durationSeconds > 0 && durationSeconds <= 45)
        ? 5
        : 4;
    }
    if (workoutType.includes("vo2") || workoutType === "vma_long") return 4;
    if (workoutType.includes("threshold") || workoutType.includes("tempo")) return 3;
    if (workoutType.includes("endurance") || workoutType === "long_run") return 2;

    const targetZone = Number(block.target?.zone);
    return targetZone >= 1 && targetZone <= 5 ? targetZone : 1;
  }

  function workoutTimelineSegments(workout) {
    const segments = [];
    const blocks = workout.blocks || [];

    const paceMinutesPerKm = value => {
      const match = String(value || "").match(/^(\d+):([0-5]\d)/);
      return match ? Number(match[1]) + Number(match[2]) / 60 : null;
    };
    const blockDuration = block => {
      const explicit = Number(block.duration_minutes) ||
        (Number(block.duration_seconds) || 0) / 60;
      if (explicit > 0) return explicit;

      const distanceKm = Number(block.distance_meters) / 1000;
      if (!(distanceKm > 0)) return 1;
      const target = block.target || {};
      const speeds = [target.speed_min_kmh, target.speed_max_kmh]
        .map(Number)
        .filter(speed => speed > 0);
      if (speeds.length) {
        const representativeSpeed = speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length;
        return distanceKm / representativeSpeed * 60;
      }
      const paces = [target.pace_min_per_km, target.pace_max_per_km]
        .map(paceMinutesPerKm)
        .filter(pace => pace > 0);
      if (paces.length) {
        return distanceKm * (paces.reduce((sum, pace) => sum + pace, 0) / paces.length);
      }

      const vma = Number(
        synchronizedPhysiology?.vma_training_reference_kmh ||
        synchronizedPhysiology?.vma_kmh
      );
      const sv1 = Number(synchronizedPhysiology?.sv1?.speed_kmh);
      const sv2 = Number(synchronizedPhysiology?.sv2?.speed_kmh);
      const zone = Number(target.zone);
      const personalZoneSpeed = {
        1: vma > 0 ? vma * .60 : 8,
        2: vma > 0 ? ((vma * .65) + (sv1 > 0 ? sv1 : vma * .75)) / 2 : 10,
        3: vma > 0 ? ((sv1 > 0 ? sv1 : vma * .75) + (sv2 > 0 ? sv2 : vma * .92)) / 2 : 12,
        4: vma > 0 ? ((sv2 > 0 ? sv2 : vma * .92) + vma) / 2 : 14,
        5: vma > 0 ? vma * 1.05 : 16,
      }[zone];
      const sport = String(workout.sport || "running").toLowerCase();
      if (personalZoneSpeed > 0 && ["running", "run", "road_running", "trail"].includes(sport)) {
        return distanceKm / personalZoneSpeed * 60;
      }

      const totalDistance = blocks.reduce((sum, candidate) => (
        sum + Number(candidate.distance_meters || 0) * workoutRepetitionRange(candidate).maximum
      ), 0);
      const plannedDuration = Number(workout.planned_duration_minutes);
      if (totalDistance > 0 && plannedDuration > 0) {
        return plannedDuration * Number(block.distance_meters) / totalDistance;
      }
      return distanceKm / 10 * 60;
    };

    blocks.forEach((block, blockIndex) => {
      const repetitions = workoutRepetitionRange(block);
      const duration = blockDuration(block);
      const recovery = Number(block.recovery_minutes) ||
        (Number(block.recovery_seconds) || 0) / 60;
      const laterWorkBlock = blocks.slice(blockIndex + 1).some(
        candidate => ["work", "interval"].includes(
          canonicalBlockType(candidate)
        )
      );

      for (let index = 0; index < repetitions.maximum; index += 1) {
        const optional = (
          index >= repetitions.minimum ||
          workoutBlockIsOptional(block)
        );
        segments.push({
          zone: atlasDisplayZone(workout, block),
          duration,
          label: optional
            ? `${block.name || "Fraction"} · facultative`
            : block.name || block.block_type || "Étape",
          optional
        });

        if (
          recovery > 0 &&
          (
            index < repetitions.maximum - 1 ||
            laterWorkBlock
          )
        ) {
          segments.push({
            zone: 1,
            duration: recovery,
            label: optional
              ? "Récupération si fraction facultative réalisée"
              : "Récupération avant la fraction suivante"
          });
        }
      }
    });

    return segments;
  }

  function reportTimelineSegments(workout, blocks, dominantType) {
    const segments = (blocks || []).map(block => ({
      zone: atlasDisplayZone(workout, {
        ...block,
        block_type: block.block_type === dominantType
          ? dominantType
          : block.block_type
      }),
      duration: Math.max((Number(block.duration_seconds) || 0) / 60, .25),
      label: block.block_type || "Bloc réalisé"
    }));

    // Santé Connect peut découper une même phase en plusieurs fragments
    // contigus. La frise les rassemble pour montrer la structure utile de
    // la séance plutôt que chaque variation instantanée de zone.
    return segments.reduce((result, segment) => {
      const previous = result[result.length - 1];
      if (previous && previous.zone === segment.zone) {
        previous.duration += segment.duration;
        previous.label = "Phase continue";
      } else {
        result.push({ ...segment });
      }
      return result;
    }, []);
  }

  function structuredReportTimelineSegments(
    workout,
    fallbackBlocks,
    dominantType,
    intervals,
    activityDurationMinutes
  ) {
    if (!intervals.length || !Number.isFinite(Number(intervals[0].start_seconds))) {
      return reportTimelineSegments(workout, fallbackBlocks, dominantType);
    }

    const segments = [];
    const sessionSeconds = Math.max(0, Number(activityDurationMinutes) * 60);
    const firstStart = Math.max(0, Number(intervals[0].start_seconds));
    if (firstStart > 0) {
      segments.push({ zone: 2, duration: firstStart / 60, label: "Échauffement" });
    }

    intervals.forEach((interval, index) => {
      const speed = Number(interval.average_speed_kmh);
      const durationSeconds = Math.max(0, Number(interval.duration_seconds));
      segments.push({
        zone: atlasDisplayZone(workout, interval),
        duration: durationSeconds / 60,
        label: `Fraction ${index + 1}${Number.isFinite(speed) ? ` · ${reportNumber(speed, 2)} km/h` : ""}`,
        optional: index >= (workout.blocks || []).filter(
          block => ["work", "interval"].includes(block.block_type)
        ).reduce((total, block) => total + (Number(block.repetitions) || 1), 0)
      });
      const recoverySeconds = Math.max(0, Number(interval.recovery_seconds));
      if (recoverySeconds > 0) {
        segments.push({
          zone: 1,
          duration: recoverySeconds / 60,
          label: `Récupération ${index + 1}`
        });
      }
    });

    const last = intervals[intervals.length - 1];
    const lastEnd = Number.isFinite(Number(last.end_seconds))
      ? Number(last.end_seconds)
      : Number(last.start_seconds) + Number(last.duration_seconds);
    const coolDownSeconds = Math.max(0, sessionSeconds - lastEnd);
    if (coolDownSeconds > 5) {
      segments.push({ zone: 1, duration: coolDownSeconds / 60, label: "Retour au calme" });
    }
    return segments;
  }

  function timelineHtml(segments, label) {
    if (!segments.length) return "";

    return `
      <section class="atlas-workout-timeline" aria-label="${escapeHtml(label)}">
        <header>
          <strong>Déroulé de la séance</strong>
          <small>La largeur représente la durée · la couleur représente votre zone</small>
        </header>
        <div class="workout-timeline-bars">
          ${segments.map((segment, index) => `
            <i
              class="timeline-zone-${segment.zone}${segment.optional ? " timeline-segment-optional" : ""}"
              style="--segment-weight:${Math.max(segment.duration, .5)};--segment-color:${DISPLAY_ZONE_COLORS[segment.zone]}"
              tabindex="0"
              data-step="${index + 1}"
              data-label="${escapeHtml(segment.label)} · ${readableWorkTime(segment.duration)} · Z${segment.zone}"
              aria-label="Étape ${index + 1} · ${escapeHtml(segment.label)} · ${readableWorkTime(segment.duration)} · Zone ${segment.zone}"
            ></i>
          `).join("")}
        </div>
        <div class="workout-timeline-caption" aria-hidden="true">
          <span>Départ</span><span>Fin de séance</span>
        </div>
      </section>
    `;
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
      const displayZone = atlasDisplayZone(workout, block);

      if (DISPLAY_ZONE_COLORS[displayZone]) return DISPLAY_ZONE_COLORS[displayZone];

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

    const compactTargetLine = block => {
      const blockTarget = block.target || {};
      const displayZone = atlasDisplayZone(workout, block);
      const values = [`Z${displayZone}`];
      const minimum = Number(blockTarget.speed_min_kmh);
      const maximum = Number(blockTarget.speed_max_kmh);

      if (Number.isFinite(minimum) && Number.isFinite(maximum)) {
        values.push(
          `${minimum.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}` +
          `–${maximum.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} km/h`
        );
        const fastPace = paceFromSpeed(maximum);
        const slowPace = paceFromSpeed(minimum);
        if (workout.sport !== "cycling" && fastPace && slowPace) {
          values.push(`${fastPace.replace("/km", "")}–${slowPace}`);
        }
      } else if (blockTarget.pace_min_per_km) {
        values.push(`${blockTarget.pace_min_per_km}/km`);
      }

      return values.join(" · ");
    };

    const compactStep = (block, options = {}) => {
      const repetitions = Number(block.repetitions) || 1;
      const distance = blockDistance({ ...block, repetitions: 1 });
      const totalDistance = blockDistance(block);
      const displayZone = atlasDisplayZone(workout, block);
      const type = canonicalBlockType(block);
      const title = options.title || ({
        warm_up: "Échauffement",
        recovery: "Récupération",
        cool_down: "Retour au calme",
        work: workout.workout_type === "threshold_sv2"
          ? "Travail au seuil"
          : "Bloc de travail",
        interval: workout.workout_type === "threshold_sv2"
          ? "Travail au seuil"
          : "Bloc de travail",
        continuous: "Course"
      }[type] || block.name || "Étape");
      const durationBlock = options.duration != null
        ? { ...block, repetitions: 1, duration_minutes: options.duration, recovery_minutes: null }
        : { ...block, repetitions: 1, recovery_minutes: null };

      return `
        <article class="garmin-step-card timeline-zone-${displayZone}" style="--step-accent:${DISPLAY_ZONE_COLORS[displayZone]}">
          <div>
            <strong>${escapeHtml(title)}</strong>
            <b>${escapeHtml(blockDuration(durationBlock))}</b>
          </div>
          <span>${escapeHtml(options.target || compactTargetLine(block))}</span>
          ${distance ? `<small>${repetitions > 1 ? `Distance estimée : ${distance.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} km par répétition · ${totalDistance.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} km au total` : `Distance estimée : ${distance.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} km`}</small>` : ""}
          ${block.instructions ? `<small class="step-instruction">${escapeHtml(block.instructions)}</small>` : ""}
        </article>
      `;
    };

    const orderedStepsHtml = blocks.map(block => {
      const repetitions = workoutRepetitionRange(block);
      const recoveryMinutes = Number(block.recovery_minutes) ||
        (Number(block.recovery_seconds) || 0) / 60;
      const isWork = ["work", "interval"].includes(
        canonicalBlockType(block)
      );
      const optionalBlock = workoutBlockIsOptional(block);
      const needsStructuredGroup = isWork && (
        repetitions.maximum > 1 ||
        recoveryMinutes > 0 ||
        optionalBlock
      );
      if (!needsStructuredGroup) return compactStep(block);

      const repetitionLabel = optionalBlock
        ? "1 fraction facultative"
        : repetitions.maximum === repetitions.minimum
          ? repetitions.minimum === 1
            ? "1 fraction"
            : `${repetitions.minimum} répétitions`
          : `${repetitions.minimum} obligatoire + ${repetitions.maximum - repetitions.minimum} facultative`;

      return `
        <section class="garmin-repeat-group" style="--repeat-accent:${accentFor(block)}">
          <h4>
            <span>${escapeHtml(block.name || "Série")}</span>
            <small>${escapeHtml(repetitionLabel)}</small>
          </h4>
          ${compactStep(block, { title: "Fraction à réaliser" })}
          ${recoveryMinutes > 0 ? compactStep(
            { block_type: "recovery", duration_minutes: recoveryMinutes },
            {
              title: "Récupération avant la fraction suivante",
              duration: recoveryMinutes,
              target: "Z1 · récupération active"
            }
          ) : ""}
        </section>
      `;
    }).join("");
    const pyramidGuideHtml =
      String(workout.workout_type || "") === "triangular_vo2"
        ? `
          <section class="pyramid-session-guide">
            <h3>Mode d’emploi de la pyramide</h3>
            <ol>
              <li><strong>2 × 3 min</strong><span>1 min 30 s de récupération active après chaque fraction.</span></li>
              <li><strong>2 × 2 min</strong><span>1 min 30 s de récupération active après chaque fraction.</span></li>
              <li><strong>1 × 1 min 30 obligatoire</strong><span>Puis 1 min 30 s de récupération active.</span></li>
              <li class="optional"><strong>1 × 1 min 30 facultative</strong><span>Uniquement si la foulée reste propre et le RPE ne dépasse pas 7/10.</span></li>
            </ol>
            <p>Compléter en endurance très facile pour obtenir une durée totale proche de 50 min, puis terminer par le retour au calme.</p>
          </section>
        `
        : "";

    const avatarIsFemale = (
      localStorage.getItem("atlasPreselectedAvatar") || "male"
    ) === "female";
    const sessionAvatarSource = avatarIsFemale
      ? "./assets/atlas-avatar-femme-clean-final.png?v=2"
      : "./assets/atlas-avatar-homme-clean-final.png?v=2";

    return `
      <header class="dialog-session-header" style="--session-accent:${mainBlock ? accentFor(mainBlock) : '#39d98a'}">
        <div>
          <span>${escapeHtml(new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(parseDate(workout.workout_date)).replace(/^./, letter => letter.toUpperCase()))}</span>
          <h2>${escapeHtml(workout.title)}</h2>
          <p>${escapeHtml(workout.objective)}</p>
        </div>
        <img
          class="session-mini-avatar"
          src="${sessionAvatarSource}"
          alt="Votre jumeau numérique Atlas"
        >
        <i class="difficulty-pill difficulty-${level}">
          ${escapeHtml(difficultyLabel(level))}
        </i>
      </header>

        ${timelineHtml(workoutTimelineSegments(workout), "Organisation de la séance prévue")}

        <section class="session-overview garmin-overview">
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
          </div>
        </section>

        <section class="session-notes">
          <h3>Notes</h3>
          <p>${escapeHtml(workout.objective)}</p>
        </section>

        ${pyramidGuideHtml}

        <section class="session-steps garmin-steps">
          <h3>Étapes</h3>
          <div class="session-step-list">
            ${orderedStepsHtml}
          </div>
        </section>

        <details class="planned-technical-details">
          <summary>Voir les données physiologiques et les conseils Atlas</summary>
          <div class="planned-technical-grid">
            <span>Charge <strong>${escapeHtml(response.physiological_load_0_100 ?? "—")}/100</strong></span>
            <span>Récupération <strong>${escapeHtml(response.recovery_min_hours ?? "—")}–${escapeHtml(response.recovery_max_hours ?? "—")} h</strong></span>
          </div>
          ${blocks.map(block => `
            <article>
              <strong>${escapeHtml(stepName(block))}</strong>
              ${targetCards({
                ...block,
                target: {
                  ...(block.target || {}),
                  zone: atlasDisplayZone(workout, block)
                }
              })}
              ${block.instructions ? `<p>${escapeHtml(block.instructions)}</p>` : ""}
            </article>
          `).join("")}
        </details>

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

  function reportMeasuredValue(value, digits, unit) {
    const numeric = Number(value);
    return Number.isFinite(numeric) && numeric > 0
      ? `${reportNumber(numeric, digits)} ${unit}`
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

  function mergeReportBlocks(blocks) {
    const validBlocks = blocks.filter(Boolean);
    if (!validBlocks.length) return {};

    const durationSeconds = validBlocks.reduce(
      (total, block) => total + Number(block.duration_seconds || 0),
      0
    );
    const weightedMean = field => {
      const weighted = validBlocks.reduce((result, block) => {
        const value = Number(block[field]);
        const duration = Number(block.duration_seconds);
        if (!Number.isFinite(value) || !(duration > 0)) return result;
        result.total += value * duration;
        result.weight += duration;
        return result;
      }, { total: 0, weight: 0 });
      return weighted.weight > 0
        ? weighted.total / weighted.weight
        : Number.NaN;
    };
    const maximumHeartRates = validBlocks.map(
      block => Number(block.maximum_heart_rate_bpm)
    ).filter(Number.isFinite);

    return {
      ...validBlocks[0],
      duration_seconds: durationSeconds,
      distance_meters: validBlocks.reduce(
        (total, block) => total + Number(block.distance_meters || 0),
        0
      ),
      average_speed_kmh: weightedMean("average_speed_kmh"),
      average_heart_rate_bpm: weightedMean("average_heart_rate_bpm"),
      maximum_heart_rate_bpm: maximumHeartRates.length
        ? Math.max(...maximumHeartRates)
        : Number.NaN,
      average_power_watts: weightedMean("average_power_watts"),
      average_cadence_spm: weightedMean("average_cadence_spm")
    };
  }

  function reportIntervalGroups(blocks, workTypes) {
    const groups = [];
    let currentWork = [];

    const finishWork = () => {
      if (!currentWork.length) return;
      groups.push({
        block: mergeReportBlocks(currentWork),
        sources: [...currentWork],
        recovery: null
      });
      currentWork = [];
    };

    blocks.forEach(block => {
      if (workTypes.has(block.block_type)) {
        currentWork.push(block);
        return;
      }

      finishWork();
      if (block.block_type === "recovery" && groups.length) {
        const previous = groups[groups.length - 1];
        if (!previous.recovery) previous.recovery = block;
      }
    });
    finishWork();
    return groups;
  }

  function contextRange(name, label, value, lowLabel = "Aucun", highLabel = "Maximum") {
    const currentValue = Number.isFinite(Number(value)) ? Number(value) : 0;
    return `
      <label class="context-range-card">
        <span><b>${escapeHtml(label)}</b><output data-range-output>${currentValue}/10</output></span>
        <input type="range" name="${escapeHtml(name)}" min="0" max="10" step="1" value="${currentValue}" aria-valuetext="${currentValue} sur 10" data-context-range>
        <span class="context-range-ticks" aria-hidden="true">
          ${Array.from({ length: 11 }, (_, score) => `<i>${score}</i>`).join("")}
        </span>
        <small><span>${escapeHtml(lowLabel)}</span><span>${escapeHtml(highLabel)}</span></small>
      </label>
    `;
  }

  function cyclingExecutionReportHtml(report, workout) {
    const match = report.workout_match || {};
    const execution = match.execution || {};
    const activity = report.activity || {};
    const analysis = report.analysis || {};
    const block = Array.isArray(analysis.blocks) ? analysis.blocks[0] || {} : {};
    const duration = Number(activity.duration_minutes) ||
      Number(block.duration_seconds) / 60;
    const distance = Number(activity.distance_km) ||
      Number(block.distance_meters) / 1000;
    const speed = Number(activity.average_speed_kmh) ||
      Number(block.average_speed_kmh);
    const averageHeartRate = Number(activity.average_heart_rate_bpm) ||
      Number(block.average_heart_rate_bpm);
    const integrity = analysis.data_integrity || {};
    const maximumHeartRate = Number(integrity.corrected_maximum_heart_rate_bpm) ||
      Number(block.maximum_heart_rate_bpm) || Number(activity.maximum_heart_rate_bpm);
    const rawMaximumHeartRate = Number(integrity.raw_maximum_heart_rate_bpm) ||
      Number(activity.maximum_heart_rate_bpm);
    const heartRateSpikeFiltered = Boolean(integrity.heart_rate_spike_filtered);
    const elevation = Number(activity.elevation_gain_m);
    const confidence = Number(match.match_confidence_score);
    const plannedDuration = Number(workout.planned_duration_minutes);
    const durationDifference = duration - plannedDuration;
    const closeToPlan = Number.isFinite(durationDifference) &&
      Math.abs(durationDifference) <= 15;

    return `
      <section class="execution-report execution-report-narrative">
        <header class="report-cockpit-header">
          <div>
            <span>ANALYSE ATLAS · SORTIE VÉLO</span>
            <h2>${escapeHtml(workout.title || "Sortie vélo")}</h2>
            <p>
              Effort continu · les tours automatiques Garmin ont été neutralisés.
              ${Number.isFinite(confidence) ? `Confiance d’association : ${reportScore(confidence)}.` : ""}
            </p>
          </div>
          <div class="report-main-score">
            <strong>${Number.isFinite(Number(execution.execution_score)) ? reportScore(execution.execution_score) : "—"}</strong>
            <span>Score d’exécution</span>
          </div>
        </header>

        ${timelineHtml([{
          zone: 1,
          duration: Math.max(duration || 1, 1),
          label: "Sortie vélo continue"
        }], "Sortie vélo réalisée")}

        <section class="interval-result-summary">
          <div class="report-heading">
            <span class="report-kicker">RÉSULTAT</span>
            <h3>${closeToPlan
              ? "La séance vélo de récupération est cohérente avec le plan."
              : "La sortie vélo est enregistrée comme un effort continu."}</h3>
            <p>
              ${closeToPlan
                ? `Durée réalisée proche des ${reportNumber(plannedDuration, 0)} min prévues.`
                : "Atlas n’interprète plus les tours de 5 km comme des sprints."}
            </p>
          </div>
          <div class="interval-result-grid">
            <article><span>Temps roulé</span><strong>${reportBlockTime(duration * 60)}</strong><small>${reportNumber(distance, 2)} km</small></article>
            <article><span>Vitesse moyenne</span><strong>${reportNumber(speed, 2)} km/h</strong><small>Aucune allure course à pied</small></article>
            <article><span>Fréquence cardiaque</span><strong>${reportNumber(averageHeartRate, 0)} bpm</strong><small>max. ${reportNumber(maximumHeartRate, 0)} bpm${heartRateSpikeFiltered ? ` · pic capteur ${reportNumber(rawMaximumHeartRate, 0)} neutralisé` : ""}</small></article>
            <article><span>Dénivelé positif</span><strong>${reportNumber(elevation, 0)} m</strong><small>Contrainte externe</small></article>
          </div>
        </section>

        <details class="report-more">
          <summary>Voir l’analyse physiologique complète</summary>
          <div class="report-analysis-layout"><main>
            <section class="narrative-analysis-section">
              <div class="report-heading"><span class="report-kicker">LECTURE ATLAS</span><h3>Une charge croisée sans impact de course</h3></div>
              <p>
                Cette activité est analysée avec ses données propres au cyclisme : durée,
                distance, vitesse, fréquence cardiaque, puissance et dénivelé lorsqu’ils
                sont disponibles. Les zones VMA et les allures au kilomètre de course à
                pied ne sont pas utilisées.
              </p>
            </section>
          </main></div>
        </details>
      </section>
    `;
  }

  function executionReportHtml(report, workout, userContext = null) {
    if (!report) {
      return `
        <section class="execution-report-empty">
          <strong>Aucun compte-rendu d’activité associé</strong>
          <p>
            Après la synchronisation, Atlas comparera ici la séance réalisée
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
    const isCycling = String(activity.sport || workout.sport || "") === "cycling" ||
      String(analysis.session_type || "") === "cycling";
    if (isCycling) {
      return cyclingExecutionReportHtml(report, workout);
    }
    const dominantType = String(
      analysis.dominant_work_type || ""
    );
    const plannedWorkBlocks = (workout.blocks || []).filter(
      block => ["work", "interval"].includes(block.block_type)
    );
    const plannedMainBlock = plannedWorkBlocks[0];
    const plannedIntervalDefinitions = plannedWorkBlocks.flatMap(block =>
      Array.from({ length: Number(block.repetitions) || 1 }, () => ({
        block,
        durationSeconds: Number(block.duration_minutes) * 60 ||
          Number(block.duration_seconds) || 0
      }))
    );
    const plannedRepetitions = plannedIntervalDefinitions.length || Number(
      execution.planned_repetition_count || 1
    );
    const plannedWorkDurationSeconds = Number(
      plannedMainBlock?.duration_minutes
    ) * 60 || Number(plannedMainBlock?.duration_seconds) || 0;
    const expectedReportWorkTypes = {
      threshold_sv2: new Set(["z3", "sv2"]),
      vma_short: new Set(["sv2", "vma"]),
      vma_long: new Set(["sv2", "vma"]),
      mixed_threshold_vo2: new Set(["z3", "sv2", "vma"]),
      triangular_vo2: new Set(["z3", "sv2", "vma"]),
      long_run: new Set(["z3", "sv2"])
    }[String(workout.workout_type || "")];
    const matchingWorkBlocks = detailedBlocks.filter(
      block => expectedReportWorkTypes
        ? expectedReportWorkTypes.has(block.block_type)
        : block.block_type === dominantType
    );
    const rawWorkBlocks = matchingWorkBlocks.length
      ? matchingWorkBlocks
      : detailedBlocks.filter(block => ![
          "warm_up",
          "cool_down",
          "recovery",
          "z1"
        ].includes(block.block_type));
    const workTypes = new Set(rawWorkBlocks.map(block => block.block_type));
    const detectedIntervalGroups = reportIntervalGroups(
      detailedBlocks,
      workTypes
    );
    const alignedIntervalDetails = Array.isArray(execution.interval_details)
      ? execution.interval_details
      : [];
    const optionalMetric = value => {
      if (value == null || value === "") return undefined;
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : undefined;
    };
    let intervalGroups = alignedIntervalDetails.length
      ? alignedIntervalDetails.map(item => ({
          block: item,
          sources: [],
          recovery: optionalMetric(item.recovery_seconds) > 0
            ? {
                duration_seconds: optionalMetric(item.recovery_seconds),
                distance_meters: optionalMetric(item.recovery_distance_meters),
                average_speed_kmh: optionalMetric(item.recovery_average_speed_kmh),
                average_heart_rate_bpm: optionalMetric(item.recovery_average_heart_rate_bpm),
                ending_heart_rate_bpm: optionalMetric(item.recovery_ending_heart_rate_bpm),
                heart_rate_drop_bpm: optionalMetric(item.recovery_heart_rate_drop_bpm),
                average_power_watts: optionalMetric(item.recovery_average_power_watts),
                average_cadence_spm: optionalMetric(item.recovery_average_cadence_spm)
              }
            : null
        }))
      : detectedIntervalGroups;

    // Une montée progressive pendant l'endurance peut traverser brièvement
    // Z3/SV2. Ces passages courts ne sont pas des répétitions structurées.
    // Quand une durée est prescrite, Atlas conserve en priorité le nombre
    // prévu de groupes dont la durée est la plus proche de la cible.
    if (
      !alignedIntervalDetails.length &&
      plannedWorkDurationSeconds > 0 &&
      detectedIntervalGroups.length > plannedRepetitions
    ) {
      const minimumCompleteDuration = Math.max(
        10,
        plannedWorkDurationSeconds * 0.45
      );
      const compatibleGroups = detectedIntervalGroups.filter(
        group => Number(group.block.duration_seconds) >= minimumCompleteDuration
      );
      const candidates = compatibleGroups.length >= plannedRepetitions
        ? compatibleGroups
        : detectedIntervalGroups;
      const selected = new Set(
        [...candidates]
          .sort((left, right) => (
            Math.abs(
              Number(left.block.duration_seconds) -
              plannedWorkDurationSeconds
            ) -
            Math.abs(
              Number(right.block.duration_seconds) -
              plannedWorkDurationSeconds
            )
          ))
          .slice(0, plannedRepetitions)
      );
      intervalGroups = detectedIntervalGroups.filter(
        group => selected.has(group)
      );
    }

    const workBlocks = intervalGroups.length
      ? intervalGroups.map(group => group.block)
      : rawWorkBlocks;
    const selectedWorkSources = new Set(
      intervalGroups.flatMap(group => group.sources || [])
    );
    const timelineBlocks = detailedBlocks.map(block => {
      const duration = Number(block.duration_seconds) || 0;
      const isRejectedWorkFragment = !alignedIntervalDetails.length &&
        workTypes.has(block.block_type) &&
        !selectedWorkSources.has(block);
      const isShortTransition = (
        String(workout.workout_type || "") === "threshold_sv2" &&
        ["acceleration", "vma"].includes(block.block_type) &&
        duration <= 30
      );
      if (isRejectedWorkFragment || isShortTransition) {
        return { ...block, block_type: "z2" };
      }
      return block;
    });
    // Les blocs reconstruits et affichés dans le tableau constituent la
    // référence visuelle. Le compteur de la source peut rester inférieur
    // quand un tour automatique a fragmenté une étape chronométrée.
    const validatedRepetitions = workBlocks.length;
    const optionalFractionCompleted = validatedRepetitions > plannedRepetitions &&
      (plannedWorkBlocks.some(block => /facultative/i.test(
        `${block.name || ""} ${block.instructions || ""}`
      )) || /1\s*à\s*2\s*[×x]/i.test(String(workout.title || "")));
    const authorizedRepetitions = optionalFractionCompleted
      ? validatedRepetitions
      : plannedRepetitions;
    const incompleteRepetitions = Math.max(
      authorizedRepetitions - validatedRepetitions,
      0
    );
    const completeBlockSources = new Set(rawWorkBlocks);
    const plannedWorkZone = atlasDisplayZone(workout, plannedMainBlock);
    const partialWorkBlocks = incompleteRepetitions > 0 &&
      plannedWorkDurationSeconds > 0
      ? detailedBlocks.filter(block => {
          const duration = Number(block.duration_seconds) || 0;
          return !completeBlockSources.has(block) &&
            atlasDisplayZone(workout, block) === plannedWorkZone &&
            duration > 0 &&
            duration < plannedWorkDurationSeconds - 5;
        })
      : [];
    const detectedPartialWorkDuration = Number(
      analysis.partial_work_duration_seconds
    );
    const partialWorkDurationSeconds = Number.isFinite(
      detectedPartialWorkDuration
    ) && detectedPartialWorkDuration > 0
      ? detectedPartialWorkDuration
      : Math.min(partialWorkBlocks.reduce(
        (total, block) => total + Number(block.duration_seconds || 0),
        0
      ), incompleteRepetitions * plannedWorkDurationSeconds);
    const workDistanceKm = workBlocks.reduce(
      (total, block) => total + Number(block.distance_meters || 0),
      0
    ) / 1000;
    const workDurationSeconds = workBlocks.reduce(
      (total, block) => total + Number(block.duration_seconds || 0),
      0
    );
    const totalSpecificDurationSeconds = workDurationSeconds +
      partialWorkDurationSeconds;
    let plannedSpecificDurationSeconds = plannedIntervalDefinitions.reduce(
      (total, item) => total + item.durationSeconds,
      0
    ) || plannedWorkDurationSeconds * plannedRepetitions;
    if (optionalFractionCompleted && plannedIntervalDefinitions.length) {
      plannedSpecificDurationSeconds +=
        plannedIntervalDefinitions[plannedIntervalDefinitions.length - 1]
          .durationSeconds;
    }
    const specificCompletionPercent = plannedSpecificDurationSeconds > 0
      ? Math.round(
          totalSpecificDurationSeconds /
          plannedSpecificDurationSeconds * 100
        )
      : Number.NaN;
    const mergedWork = mergeReportBlocks(workBlocks);
    const averageWorkSpeed = Number(mergedWork.average_speed_kmh);
    const averageWorkHeartRate = Number(
      mergedWork.average_heart_rate_bpm
    );
    const workMaximumHeartRates = workBlocks.map(
      block => Number(block.maximum_heart_rate_bpm)
    ).filter(Number.isFinite);
    const maximumWorkHeartRate = workMaximumHeartRates.length
      ? Math.max(...workMaximumHeartRates)
      : Number.NaN;
    const averageWorkPower = Number(mergedWork.average_power_watts);
    const averageWorkCadence = Number(mergedWork.average_cadence_spm);
    const workSpeeds = workBlocks.map(
      block => Number(block.average_speed_kmh)
    ).filter(speed => Number.isFinite(speed) && speed > 0);
    const speedSpread = workSpeeds.length
      ? Math.max(...workSpeeds) - Math.min(...workSpeeds)
      : Number.NaN;
    const workPaces = workSpeeds.map(speed => 3600 / speed);
    const paceSpread = workPaces.length
      ? Math.max(...workPaces) - Math.min(...workPaces)
      : Number.NaN;
    const isIntervalSession = plannedRepetitions > 1 &&
      workBlocks.length > 1;
    const firstWorkBlock = workBlocks[0] || {};
    const lastWorkBlock = workBlocks[workBlocks.length - 1] || {};
    const fastestWorkBlock = workBlocks.reduce(
      (fastest, block) => (
        Number(block.average_speed_kmh) >
        Number(fastest?.average_speed_kmh ?? -Infinity)
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
    const isHybridThresholdSession =
      String(workout.workout_type || "") === "long_run" &&
      isIntervalSession &&
      /(?:sous|au)\s+SV2/i.test(String(workout.title || ""));
    const analyzedSessionLabel = isHybridThresholdSession
      ? "Travail structuré sous SV2"
      : ({
          threshold_sv2: "Travail structuré sous SV2",
          vma_short: "Intervalles VO₂max",
          vma_long: "Intervalles VO₂max",
          mixed_threshold_vo2: "Séance mixte seuil et VO₂max",
          triangular_vo2: "Séance VO₂max triangulaire",
          long_run: "Sortie longue"
        }[String(workout.workout_type || "")] || ({
      vma: "Intervalles VO₂max",
      sv2: "Travail au seuil",
      z3: "Tempo",
      z2: "Endurance fondamentale",
      z1: "Récupération",
      sprint: "Sprints",
      acceleration: "Accélérations"
    }[dominantType] || sessionTypeLabel(activity.session_type)));
    const activityProvider = String(
      report.provider || activity.provider || ""
    ).toLowerCase();
    const activitySourceLabel = activityProvider === "health_connect"
      ? "données Santé Connect issues de Garmin"
      : activityProvider.includes("fit") || activityProvider === "garmin"
        ? "fichier FIT Garmin"
        : "données d’activité";
    const durationDelta = actualDuration - plannedDuration;
    const distanceDelta = actualDistance - plannedDistance;
    const executionScore = Number(execution.execution_score);
    const targetScore = Number(match.target_compliance_score);
    const temperature = Number(activity.temperature_c);
    const elevation = Number(activity.elevation_gain_m);
    const hillSamples = Number(drift.excluded_hill_sample_count);
    const learningAllowed =
      report.automatic_learning_allowed === true;
    const contextInterpretation = userContext?.atlas_interpretation || null;
    const contextActionLabels = {
      maintain: "Maintien proposé",
      monitor: "Maintien sous surveillance",
      reduce_next_intensity: "Allègement proposé",
      recovery_priority: "Récupération prioritaire"
    };

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
    const hasIntervalPower = workBlocks.some(block =>
      Number.isFinite(Number(block.average_power_watts)) && Number(block.average_power_watts) > 0
    );
    const hasIntervalCadence = workBlocks.some(block =>
      Number.isFinite(Number(block.average_cadence_spm)) && Number(block.average_cadence_spm) > 0
    );
    const intervalGrid = [
      "48px", "90px", "90px", "105px", "115px", "115px",
      ...(hasIntervalPower ? ["105px"] : []),
      ...(hasIntervalCadence ? ["95px"] : []),
      "minmax(210px, 1fr)"
    ].join(" ");
    const intervalRows = workBlocks.map((block, index) => {
      const speed = Number(block.average_speed_kmh);
      const recovery = intervalGroups[index]?.recovery || null;

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
          ${hasIntervalPower ? `<span>${reportMeasuredValue(block.average_power_watts, 0, "W")}</span>` : ""}
          ${hasIntervalCadence ? `<span>${reportMeasuredValue(block.average_cadence_spm, 0, "ppm")}</span>` : ""}
          <span class="interval-recovery-detail">
            ${recovery ? `
              <b>${reportBlockTime(recovery.duration_seconds)} · ${reportNumber(recovery.distance_meters, 0)} m</b>
              <small>${reportPace(3600 / Number(recovery.average_speed_kmh))} · ${reportNumber(recovery.average_speed_kmh, 2)} km/h</small>
              <small>FC moy. ${reportNumber(recovery.average_heart_rate_bpm, 0)} bpm</small>
              <small>FC fin ${reportNumber(recovery.ending_heart_rate_bpm, 0)} bpm · baisse ${reportNumber(recovery.heart_rate_drop_bpm, 0)} bpm</small>
            ` : "—"}
          </span>
        </div>
      `;
    }).join("");
    const plannedPattern = plannedWorkBlocks.map(block => {
      const repetitions = Number(block.repetitions) || 1;
      const seconds = Number(block.duration_minutes) * 60 ||
        Number(block.duration_seconds) || 0;
      const optionalSecond = /facultative/i.test(
        `${block.name || ""} ${block.instructions || ""}`
      ) && /(?:seconde|1\s*à\s*2)/i.test(
        `${block.name || ""} ${block.instructions || ""}`
      );
      return `${optionalSecond ? "1 à 2" : repetitions} × ${reportBlockTime(seconds)}`;
    }).join(" + ");
    const heterogeneousIntervals = new Set(
      plannedIntervalDefinitions.map(item => item.durationSeconds)
    ).size > 1;
    const completedIntervalLabel = heterogeneousIntervals
      ? `${validatedRepetitions} fractions (${plannedPattern})`
      : Number(plannedMainBlock?.duration_minutes) > 0
        ? `${validatedRepetitions} blocs de ${reportNumber(
            plannedMainBlock.duration_minutes,
            0
          )} min`
        : `${validatedRepetitions} répétitions`;
    const intervalCompletionSummary = optionalFractionCompleted
      ? `${validatedRepetitions} fractions réalisées · noyau complet + fraction facultative`
      : heterogeneousIntervals
      ? `${validatedRepetitions} fractions réalisées sur ${plannedRepetitions} prévues`
      : Number(plannedMainBlock?.duration_minutes) > 0
        ? `${completedIntervalLabel} réalisés sur ${plannedRepetitions} prévus`
        : `${completedIntervalLabel} réalisées sur ${plannedRepetitions} prévues`;
    const avatarIsFemale = (
      localStorage.getItem("atlasPreselectedAvatar") || "male"
    ) === "female";
    const reportAvatarSource = avatarIsFemale
      ? "./assets/atlas-avatar-femme-clean-final.png?v=2"
      : "./assets/atlas-avatar-homme-clean-final.png?v=2";

    return `
      <section class="execution-report execution-report-narrative">
        <header class="report-cockpit-header">
          <div>
            <span>ANALYSE ATLAS · DONNÉES RÉELLES</span>
            <h2>${escapeHtml(execution.workout_name || workout.title)}</h2>
            <p>
              ${escapeHtml(analyzedSessionLabel)}
              · ${activitySourceLabel} reconnues avec une confiance de
              ${reportScore(match.match_confidence_score)}.
            </p>
          </div>
          <div class="report-main-score">
            <strong>${reportScore(execution.execution_score)}</strong>
            <span>Score d’exécution</span>
          </div>
          <img
            class="report-mini-avatar"
            src="${reportAvatarSource}"
            alt="Votre jumeau numérique Atlas"
          >
        </header>

        <section class="execution-score-explanation">
          <div>
            <span class="report-kicker">LECTURE DU SCORE</span>
            <strong>Ce score mesure le respect de la prescription, pas votre niveau de forme.</strong>
            <p>Les portions faciles ajoutées avant ou après les fractions sont conservées dans la séance, mais ne diminuent plus le respect de la cible spécifique.</p>
          </div>
          <dl>
            <div><dt>Durée globale</dt><dd>${reportScore(match.duration_compliance_score)}</dd></div>
            <div><dt>Cible spécifique</dt><dd>${reportScore(match.target_compliance_score)}</dd></div>
            <div><dt>Durées de récupération</dt><dd>${Number.isFinite(Number(execution.recovery_compliance_score)) ? reportScore(execution.recovery_compliance_score) : "Non notées"}</dd></div>
          </dl>
        </section>

        ${timelineHtml(
          structuredReportTimelineSegments(
            workout,
            timelineBlocks,
            dominantType,
            alignedIntervalDetails,
            actualDuration
          ),
          "Organisation de la séance réalisée"
        )}

        <section class="interval-result-summary">
          <div class="report-heading">
            <span class="report-kicker">RÉSULTAT</span>
            <h3>
              ${isIntervalSession
                ? intervalCompletionSummary
                : executionConclusion}
            </h3>
            <p>
              ${isIntervalSession
                ? `Bloc principal exécuté avec une conformité de ${reportScore(targetScore)}.`
                : targetConclusion}
            </p>
            ${isIntervalSession && incompleteRepetitions > 0 ? `
              <p class="report-interval-warning">
                ${incompleteRepetitions} répétition${incompleteRepetitions > 1 ? "s" : ""}
                interrompue${incompleteRepetitions > 1 ? "s" : ""} ou incomplète${incompleteRepetitions > 1 ? "s" : ""} :
                conservée${incompleteRepetitions > 1 ? "s" : ""} dans la chronologie,
                mais exclue${incompleteRepetitions > 1 ? "s" : ""} des moyennes ci-dessous.
                ${partialWorkDurationSeconds > 0 ? `Durée retenue pour cette répétition :
                  ${reportBlockTime(partialWorkDurationSeconds)}.` : ""}
              </p>
            ` : ""}
          </div>

          <div class="interval-result-grid">
            <article>
              <span>${dominantType === "sv2" ? "Volume spécifique" : "Travail rapide"}</span>
              <strong>${reportBlockTime(totalSpecificDurationSeconds)}</strong>
              <small>
                ${plannedSpecificDurationSeconds > 0
                  ? `${reportBlockTime(plannedSpecificDurationSeconds)} prévus · ${reportNumber(specificCompletionPercent, 0)} %`
                  : `${reportNumber(workDistanceKm, 2)} km`}
              </small>
            </article>
            <article>
              <span>Allure moyenne</span>
              <strong>${reportPace(3600 / averageWorkSpeed)}</strong>
              <small>${reportNumber(averageWorkSpeed, 2)} km/h</small>
            </article>
            <article>
              <span>Régularité</span>
              <strong>${reportNumber(speedSpread, 2)} km/h</strong>
              <small>${reportNumber(paceSpread, 0)} s/km d’écart</small>
            </article>
            <article>
              <span>Fréquence cardiaque</span>
              <strong>${reportNumber(averageWorkHeartRate, 0)} bpm</strong>
              <small>max. ${reportNumber(maximumWorkHeartRate, 0)} bpm</small>
            </article>
          </div>
        </section>

        ${isIntervalSession ? `
          <details class="interval-details-section compact-interval-details" open>
            <summary>
              <span class="report-kicker">TABLEAU RÉCAPITULATIF</span>
              <strong>Détail des ${workBlocks.length} fractions et de leurs récupérations</strong>
            </summary>
            <div class="interval-detail-table" style="--interval-grid:${intervalGrid}">
              <div class="interval-detail-row interval-detail-header">
                <span>N°</span><span>Distance</span><span>Temps</span>
                <span>Allure</span><span>Vitesse</span><span>FC moy.</span>
                ${hasIntervalPower ? "<span>Puissance</span>" : ""}
                ${hasIntervalCadence ? "<span>Cadence</span>" : ""}
                <span>Récupération</span>
              </div>
              ${intervalRows}
            </div>
          </details>
        ` : ""}
        <details class="report-more">
          <summary>Voir l’analyse physiologique complète</summary>
        <div class="report-analysis-layout">
          <main>
              ${isIntervalSession ? `
                <section class="narrative-analysis-section interval-analysis-section">
                  <div class="report-heading">
                    <span class="report-kicker">LECTURE ATLAS</span>
                    <h3>${heterogeneousIntervals
                      ? "Une pyramide complète avec progression sur les fractions courtes"
                      : "Une série régulière jusqu’au dernier bloc"}</h3>
                  </div>
                  <p>
                    Les blocs complets (${completedIntervalLabel})
                    ont été réalisés à ${reportPace(3600 / averageWorkSpeed)}
                    de moyenne. L’écart d’allure de ${reportNumber(paceSpread, 0)} s/km
                    ${heterogeneousIntervals
                      ? "reflète les durées différentes de la pyramide."
                      : "confirme une exécution homogène."}
                  </p>
                  ${incompleteRepetitions > 0 ? `
                    <p>
                      ${incompleteRepetitions} répétition${incompleteRepetitions > 1 ? "s" : ""}
                      prévue${incompleteRepetitions > 1 ? "s" : ""} n’a pas été validée${incompleteRepetitions > 1 ? "s" : ""}
                      comme complète${incompleteRepetitions > 1 ? "s" : ""}.
                      ${incompleteRepetitions > 1 ? "Ces répétitions restent visibles" : "Cette répétition reste visible"}
                      dans la chronologie sans fausser les statistiques des blocs complets.
                      ${partialWorkDurationSeconds > 0 ? `Le volume spécifique total atteint
                        ${reportBlockTime(totalSpecificDurationSeconds)} sur
                        ${reportBlockTime(plannedSpecificDurationSeconds)} prévus.` : ""}
                    </p>
                  ` : ""}
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
                    Entre le premier et le dernier bloc, la vitesse évolue de
                    ${reportSignedNumber(intervalSpeedChangePercent, 1, " %")}
                    et la fréquence cardiaque de
                    ${reportSignedNumber(intervalHeartRateChange, 0, " bpm")}.
                    Les récupérations n’ont pas dégradé la qualité des blocs au seuil.
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
                      ${userContext.overall_sensation_0_to_10 != null ? `Sensation générale : ${escapeHtml(userContext.overall_sensation_0_to_10)}/10. ` : ""}
                      ${userContext.perceived_effort_0_to_10 != null ? `Effort perçu : ${escapeHtml(userContext.perceived_effort_0_to_10)}/10. ` : ""}
                      ${userContext.heat ? "Vous signalez une chaleur importante. " : ""}
                      ${userContext.relief ? "Le parcours comportait du relief ou des faux plats. " : ""}
                      ${userContext.pain_0_to_10 != null ? `La douleur ressentie était évaluée à ${escapeHtml(userContext.pain_0_to_10)}/10. ` : ""}
                      ${userContext.fatigue_0_to_10 != null ? `La fatigue était évaluée à ${escapeHtml(userContext.fatigue_0_to_10)}/10. ` : ""}
                      ${userContext.comment ? escapeHtml(userContext.comment) : ""}
                    </p>
                    <p class="context-interpretation">
                      ${contextInterpretation
                        ? `<strong>${escapeHtml(contextActionLabels[contextInterpretation.action] || "Analyse prudente")}</strong> · ${escapeHtml((contextInterpretation.reasons || []).join(" "))}`
                        : userContext.heat || userContext.relief
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
                  <div class="context-self-evaluation">
                    <div class="context-form-heading">
                      <span>Auto-évaluation</span>
                      <h4>Comment vous êtes-vous senti ?</h4>
                    </div>
                    <div class="context-feeling-scale" role="radiogroup" aria-label="Sensation générale">
                      <input type="hidden" name="sensation" value="${escapeHtml(userContext?.overall_sensation_0_to_10 ?? 5)}" data-sensation-value>
                      ${[
                        [1, "😫", "Très faible"],
                        [3, "🙁", "Faible"],
                        [5, "😐", "Normal"],
                        [7, "🙂", "Fort"],
                        [9, "😄", "Très fort"]
                      ].map(([score, icon, label]) => `
                        <button
                          type="button"
                          role="radio"
                          aria-checked="${Number(userContext?.overall_sensation_0_to_10 ?? 5) === score}"
                          class="${Number(userContext?.overall_sensation_0_to_10 ?? 5) === score ? "selected" : ""}"
                          data-sensation-score="${score}"
                        >
                          <span aria-hidden="true">${icon}</span>
                          <small>${label}</small>
                        </button>
                      `).join("")}
                    </div>
                  </div>
                  <div class="context-primary-range">
                    ${contextRange("effort", "Effort perçu", userContext?.perceived_effort_0_to_10 ?? 5, "Très facile", "Maximum")}
                  </div>
                  <details class="context-constraints">
                    <summary>Préciser les contraintes de la séance</summary>
                    <div class="context-range-grid">
                      ${contextRange("heat", "Chaleur ressentie", userContext?.heat_0_to_10 ?? (userContext?.heat ? 5 : 0))}
                      ${contextRange("relief", "Relief contraignant", userContext?.relief_0_to_10 ?? (userContext?.relief ? 5 : 0))}
                      ${contextRange("pain", "Douleur ressentie", userContext?.pain_0_to_10 ?? 0)}
                      ${contextRange("fatigue", "Fatigue ressentie", userContext?.fatigue_0_to_10 ?? 0)}
                    </div>
                  </details>
                  <div class="context-score-summary" aria-live="polite">
                    <span>Chaleur <b data-context-score="heat">${userContext?.heat_0_to_10 ?? (userContext?.heat ? 5 : 0)}/10</b></span>
                    <span>Relief <b data-context-score="relief">${userContext?.relief_0_to_10 ?? (userContext?.relief ? 5 : 0)}/10</b></span>
                    <span>Douleur <b data-context-score="pain">${userContext?.pain_0_to_10 ?? 0}/10</b></span>
                    <span>Fatigue <b data-context-score="fatigue">${userContext?.fatigue_0_to_10 ?? 0}/10</b></span>
                  </div>
                  <label class="context-comment-field">
                    <span>Votre lecture de la séance</span>
                    <textarea name="comment" maxlength="1200" rows="3" placeholder="Ex. allure volontairement constante, jambes lourdes, vent, mauvaise nuit…">${escapeHtml(userContext?.comment || "")}</textarea>
                  </label>
                  <div class="context-form-footer">
                    <small>Cette déclaration est enregistrée séparément des données d’activité et reste historisée.</small>
                    <button type="submit">Enregistrer mon contexte</button>
                  </div>
                  <p class="context-form-status" data-context-form-status aria-live="polite"></p>
                </form>
              </div>
            </section>
          </main>

          <aside class="atlas-decision-column">
            <span class="report-kicker">DÉCISION ATLAS</span>
            <h3>${contextInterpretation
              ? escapeHtml(contextActionLabels[contextInterpretation.action] || "Analyse conservée avec prudence")
              : learningAllowed ? "Séance retenue pour l’apprentissage" : "Analyse conservée avec prudence"}</h3>
            <p>
              ${contextInterpretation
                ? escapeHtml((contextInterpretation.reasons || []).join(" "))
                : learningAllowed
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
        </details>
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

        <section class="workout-prescription-decision">
          <div>
            <span>AVANT LA SÉANCE</span>
            <strong>Quelle séance choisissez-vous ?</strong>
            <p>Comparez la prescription prévue avec l’adaptation proposée à partir de votre état du jour.</p>
          </div>
          <div class="workout-prescription-buttons">
            <button type="button" data-daily-selection="keep_original">
              Suivre la séance initiale
            </button>
            <button type="button" data-daily-selection="accept_adaptation">
              Choisir la proposition Atlas
            </button>
          </div>
        </section>

        <div class="workout-outcome-heading">
          <span>APRÈS LA SÉANCE</span>
          <strong>Qu’avez-vous réellement effectué ?</strong>
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
        ` : `
          <button class="reschedule-workout" type="button" data-reschedule-workout>
            <b>↔</b> Déplacer cette séance
          </button>
        `}

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

  function openReschedulePanel(workout) {
    const dialog = ensureDialog();
    const content = dialog.querySelector(".dialog-content");
    const source = parseDate(workout.workout_date);
    const monday = addDays(source, -((source.getDay() + 6) % 7));
    const days = Array.from({ length: 14 }, (_, index) => {
      const value = isoDate(addDays(monday, index));
      return `
        <button type="button" data-reschedule-date="${value}"
          ${value === workout.workout_date ? "disabled" : ""}>
          <span>${DAY_LABELS[index % DAY_LABELS.length]}</span>
          <strong>${formatDate(value)}</strong>
          ${value === workout.workout_date ? "<small>Jour actuel</small>" : ""}
        </button>`;
    }).join("");

    content.innerHTML = `
      <section class="reschedule-panel">
        <button type="button" class="reschedule-back" data-reschedule-back>← Retour à la séance</button>
        <span class="session-kicker">ORGANISATION INTELLIGENTE</span>
        <h2>Déplacer « ${escapeHtml(workout.title)} »</h2>
        <p>Choisissez un jour de cette semaine ou de la suivante. Atlas vérifiera les séances difficiles voisines avant tout enregistrement.</p>
        <div class="reschedule-days">${days}</div>
        <div class="reschedule-preview" data-reschedule-preview aria-live="polite">
          <p>Sélectionnez une nouvelle journée pour afficher les conséquences.</p>
        </div>
      </section>`;

    const preview = content.querySelector("[data-reschedule-preview]");
    let selectedDate = null;

    const request = async (apply, rebalance = true, replaceTargetEasy = false) => {
      const response = await fetch("/api/atlas-coach/reschedule-workout", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({
          workout_id: workout.workout_id,
          target_date: selectedDate,
          apply,
          rebalance,
          replace_target_easy: replaceTargetEasy
        })
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Déplacement Atlas indisponible.");
      }
      return payload;
    };

    content.onclick = async event => {
      if (event.target.closest("[data-reschedule-back]")) {
        openWorkout(workout, dailyPreparationCache.get(workout.workout_id) || null);
        return;
      }
      const dayButton = event.target.closest("[data-reschedule-date]");
      if (dayButton) {
        selectedDate = dayButton.dataset.rescheduleDate;
        content.querySelectorAll("[data-reschedule-date]").forEach(button => {
          button.classList.toggle("selected", button === dayButton);
        });
        preview.innerHTML = "<p>Atlas vérifie la cohérence de la semaine…</p>";
        try {
          const result = await request(false);
          const replaceable = (
            result.target_conflicts || []
          ).filter(item => !item.is_hard);
          const replacementOption = replaceable.length
            ? `
              <article class="reschedule-option reschedule-option-replace">
                <span>CHOIX ÉQUILIBRÉ</span>
                <h4>Remplacer la séance facile prévue</h4>
                <p>
                  La séance déplacée remplace
                  ${replaceable.map(item => escapeHtml(item.title)).join(", ")}.
                  Sa charge métabolique et biomécanique reste supérieure à
                  une endurance Z2 : Atlas conseille de raccourcir la durée
                  totale ou le volume sous SV2, puis de réévaluer la
                  récupération le lendemain.
                </p>
                <button type="button" data-reschedule-replace>
                  Déplacer et remplacer
                  ${replaceable.map(item => escapeHtml(item.title)).join(", ")}
                </button>
              </article>`
            : "";
          const atlasConsequences = result.changes.slice(1);
          const atlasAdvice = atlasConsequences.length
            ? `Atlas décalera ${atlasConsequences.length} séance${atlasConsequences.length > 1 ? "s" : ""} difficile${atlasConsequences.length > 1 ? "s" : ""} suivante${atlasConsequences.length > 1 ? "s" : ""} : ${atlasConsequences.map(change => `${escapeHtml(change.title)} (${formatDate(change.from)} → ${formatDate(change.to)})`).join(" ; ")}.`
            : "Atlas ne prévoit aucun autre déplacement pour cette organisation.";
          preview.innerHTML = `
            <h3>${escapeHtml(result.summary)}</h3>
            <ul>${result.changes.map(change => `
              <li><strong>${escapeHtml(change.title)}</strong><span>${formatDate(change.from)} → ${formatDate(change.to)}</span><small>${escapeHtml(change.reason)}</small></li>
            `).join("")}</ul>
            <p>Aucune modification n’est encore enregistrée.</p>
            <div class="reschedule-options">
              <article class="reschedule-option reschedule-option-keep">
                <span>CHARGE ÉLEVÉE</span>
                <h4>Conserver toutes les séances prévues</h4>
                <p>
                  Ce choix ajoute une deuxième séance au même jour et
                  augmente fortement les charges métabolique, physiologique
                  et biomécanique. Il sort du programme initial. Si tu le
                  conserves, réduis nettement la durée ou le volume sous SV2.
                </p>
                <button type="button" data-reschedule-only>
                  Déplacer et conserver les séances déjà prévues
                </button>
              </article>
              ${replacementOption}
              <article class="reschedule-option reschedule-option-atlas">
                <span>PRUDENCE ATLAS</span>
                <h4>Rééquilibrer les séances difficiles</h4>
                <p>${atlasAdvice}</p>
                <button type="button" data-reschedule-confirm>
                  Appliquer les conseils Atlas
                  (décaler les séances difficiles suivantes)
                </button>
              </article>
            </div>`;
        } catch (error) {
          preview.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
        }
        return;
      }
      const undoButton = event.target.closest("[data-reschedule-undo]");
      if (undoButton) {
        const backup = undoButton.dataset.backup;
        if (!backup) return;
        undoButton.disabled = true;
        undoButton.textContent = "Restauration en cours…";
        try {
          const response = await fetch(
            "/api/atlas-coach/undo-reschedule",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json; charset=utf-8"
              },
              body: JSON.stringify({ backup })
            }
          );
          const payload = await response.json();
          if (!response.ok || !payload.ok) {
            throw new Error(
              payload.error || "Annulation Atlas indisponible."
            );
          }
          await loadProgram();
          preview.innerHTML = `
            <h3>Modification annulée</h3>
            <p>${escapeHtml(payload.summary)}</p>
            <button type="button" data-reschedule-close>Fermer</button>
          `;
        } catch (error) {
          undoButton.disabled = false;
          undoButton.textContent = "Annuler cette modification";
          preview.insertAdjacentHTML(
            "beforeend",
            `<p class="error">${escapeHtml(error.message)}</p>`
          );
        }
        return;
      }

      if (event.target.closest("[data-reschedule-close]")) {
        dialog.close();
        return;
      }
      const onlyButton = event.target.closest("[data-reschedule-only]");
      const replaceButton = event.target.closest(
        "[data-reschedule-replace]"
      );
      const confirmButton = event.target.closest("[data-reschedule-confirm]");
      const actionButton = onlyButton || replaceButton || confirmButton;
      if (!actionButton || !selectedDate) return;
      actionButton.disabled = true;
      actionButton.textContent = "Enregistrement…";
      try {
        const result = await request(
          true,
          Boolean(confirmButton),
          Boolean(replaceButton)
        );
        await loadProgram();
        preview.innerHTML = `
          <h3>Organisation enregistrée</h3>
          <p>${escapeHtml(result.summary)}</p>
          <small>
            Sauvegarde créée :
            ${escapeHtml(result.backup || "programme protégé")}
          </small>
          <div class="reschedule-actions">
            <button
              type="button"
              data-reschedule-undo
              data-backup="${escapeHtml(result.backup || "")}"
              ${result.backup ? "" : "disabled"}
            >
              Annuler cette modification
            </button>
            <button type="button" data-reschedule-close>
              Fermer
            </button>
          </div>
        `;
      } catch (error) {
        actionButton.disabled = false;
        actionButton.textContent = "Valider cette organisation";
        preview.insertAdjacentHTML("beforeend", `<p class="error">${escapeHtml(error.message)}</p>`);
      }
    };
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
          <strong>${
            decision.action === "maintain"
              ? "Pourquoi Atlas maintient la séance"
              : "Pourquoi Atlas adapte la séance"
          }</strong>
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
    const hasAdaptation = Boolean(
      !cancelled &&
      preparation?.adaptation?.adapted_workout &&
      preparation?.decision?.action &&
      preparation.decision.action !== "maintain"
    );

    content.innerHTML = `
      <nav class="session-dialog-tabs${hasAdaptation ? " has-adaptation" : ""}" aria-label="Fiche de séance">
        <button
          type="button"
          class="active"
          data-session-tab="planned"
          aria-selected="true"
        >
          Séance initiale
        </button>
        ${hasAdaptation ? `
          <button
            type="button"
            data-session-tab="adapted"
            aria-selected="false"
          >
            Proposition Atlas
          </button>
        ` : ""}
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
          ${detailHtml(workout)}
          ${dailyPreparationDetailHtml(preparation, workout)}
          ${workoutActionsHtml(workout)}
      </section>

      ${hasAdaptation ? `
        <section
          class="session-tab-panel"
          data-session-panel="adapted"
          hidden
        >
          <div class="adapted-session-heading">
            <span>PROPOSITION ADAPTÉE À LA RÉCUPÉRATION DU JOUR</span>
            <p>Cette proposition n’efface jamais la séance initialement programmée.</p>
          </div>
          ${detailHtml(adaptedWorkout)}
        </section>
      ` : ""}

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
      const sensationButton = event.target.closest(
        "[data-sensation-score]"
      );
      if (sensationButton) {
        event.preventDefault();
        event.stopPropagation();
        const form = sensationButton.closest(
          "[data-workout-context-form]"
        );
        const selectedScore = sensationButton.dataset.sensationScore;
        const valueField = form?.querySelector("[data-sensation-value]");
        if (valueField) valueField.value = selectedScore;
        form?.querySelectorAll("[data-sensation-score]").forEach(button => {
          const selected = button === sensationButton;
          button.classList.toggle("selected", selected);
          button.setAttribute("aria-checked", String(selected));
        });
        return;
      }

      if (event.target.closest("[data-workout-context-form]")) {
        return;
      }

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

      if (event.target.closest("[data-reschedule-workout]")) {
        openReschedulePanel(workout);
        return;
      }

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

    content.oninput = event => {
      const range = event.target.closest("[data-context-range]");
      if (!range) return;

      const cardOutput = range.closest(".context-range-card")
        ?.querySelector("[data-range-output]");
      const summaryOutput = content.querySelector(
        `[data-context-score="${range.name}"]`
      );
      if (cardOutput) cardOutput.textContent = `${range.value}/10`;
      if (summaryOutput) summaryOutput.textContent = `${range.value}/10`;
      range.setAttribute("aria-valuetext", `${range.value} sur 10`);
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
            sensation: values.get("sensation") || "5",
            effort: values.get("effort") || "0",
            heat: values.get("heat") || "0",
            relief: values.get("relief") || "0",
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
      loadExecutionReport(
        workout.workout_id,
        workout.report_activity_id || ""
      ),
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

          const refreshed = await loadExecutionReport(
            workout.workout_id,
            workout.report_activity_id || ""
          );
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
    ["mobility", "Mobilité", "Amplitude articulaire", false],
    ["stretching", "Étirements", "Souplesse des tissus", false],
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
    stretching: {
      title: "Étirements", sport: "mobility", duration: 20,
      objective: "Entretenir la souplesse des tissus sans provoquer de douleur.",
      physiological: 6, biomechanical: 8, recovery: [2, 8]
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

    if (type === "stretching") {
      return [{
        name: "Souplesse tissulaire",
        block_type: "mobility",
        repetitions: 1,
        duration_minutes: 20,
        recovery_minutes: null,
        target: {
          zone: null, rpe_0_10: 2,
          intensity_pattern: "progressive"
        },
        instructions: (
          "À distance de la séance intense, explorer doucement les tensions " +
          "des mollets, cuisses, hanches et chaîne postérieure. Ne jamais " +
          "forcer une douleur vive, croissante ou inhabituelle."
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

  async function render(program, historyLoaded = false) {
    activeProgram = program;
    workoutIndex.clear();
    const embeddedHistory = program.historical_completed_workouts || [];
    const historyByActivity = new Map();
    embeddedHistory.forEach(workout => {
      historyByActivity.set(
        workout.report_activity_id || workout.workout_id,
        workout
      );
    });
    historicalCompletedWorkouts = [...historyByActivity.values()];
    renderCoachZones(program);
    physiologicalRibbon(
      synchronizedPhysiology || program.athlete_snapshot
    );
    renderOverview(program);

    const access = program.access_control || {};
    const lockedWeeks = program.locked_weeks || [];
    const rollingLabel = access.rolling_weeks === 1
      ? "1 semaine glissante"
      : `${access.rolling_weeks} semaines glissantes`;
    const accessBanner = access.tier === "monthly"
      ? `<section class="program-access-banner">
          <strong>Atlas Performance mensuel · ${rollingLabel}</strong>
          <span>Atlas recalcule la suite selon votre progression et vos données physiologiques, biomécaniques et de récupération.</span>
        </section>`
      : access.tier === "founder_admin"
        ? `<section class="program-access-banner is-founder">
            <strong>Accès Fondateur Atlas · programme intégral</strong>
            <span>Vous pouvez consulter, tester, imprimer et exporter toutes les semaines.</span>
          </section>`
        : "";

    const lockedMarkup = lockedWeeks.map(week => `
      <section class="premium-week locked-program-week">
        <div>
          <span>SEMAINE ${escapeHtml(week.week_number ?? "—")}</span>
          <h3>La suite de votre programme est en cours d’adaptation</h3>
          <p>${escapeHtml(week.start_date || "")}
            ${week.unlock_date
              ? ` · disponible le ${escapeHtml(week.unlock_date)}`
              : ""}
          </p>
        </div>
        <strong aria-label="Semaine verrouillée">🔒</strong>
      </section>
    `).join("");

    calendar.innerHTML = `
      ${accessBanner}
      ${program.weeks.map(
        week => renderWeek(week, program)
      ).join("")}
      ${lockedMarkup}
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

    // Le calendrier principal ne doit jamais dépendre de la vitesse de
    // reconstruction de l'historique Garmin. On affiche d'abord le programme
    // actif, puis on enrichit les semaines en arrière-plan lorsque les
    // exécutions historiques sont disponibles.
    if (!historyLoaded) {
      Promise.all([
        restoreOptional(program),
        loadHistoricalCompletedWorkouts(program)
      ]).then(([, browserHistory]) => {
        const mergedHistory = new Map();
        [...embeddedHistory, ...browserHistory].forEach(workout => {
          mergedHistory.set(
            workout.report_activity_id || workout.workout_id,
            workout
          );
        });
        render({
          ...program,
          historical_completed_workouts: [...mergedHistory.values()]
        }, true).catch(error => {
          console.warn("Historique Atlas non ajouté au calendrier.", error);
        });
      }).catch(error => {
        console.warn("Historique Atlas non ajouté au calendrier.", error);
      });
    }
  }

  window.addEventListener("atlas:athlete-profile-loaded", event => {
    const payload = event.detail || {};
    const physiology = payload.physiological || payload;

    if (!physiology || typeof physiology !== "object") return;

    synchronizedPhysiology = {
      ...physiology,
      age_years:
        physiology.age_years ?? payload.age_years ??
        payload.demographics?.age_years,
      sex:
        physiology.sex ?? payload.sex ?? payload.demographics?.sex,
      profile_confidence_score:
        physiology.profile_confidence_score ??
        payload.profile_confidence_score ??
        payload.confidence_score ?? 90
    };
    physiologicalRibbon(synchronizedPhysiology);
  });

  window.addEventListener("atlas:training-program-loaded", event => {
    const program = event.detail;
    if (program?.athlete_snapshot) {
      physiologicalRibbon(
        synchronizedPhysiology || program.athlete_snapshot
      );
    }
    if (program?.weeks && program?.goal && !activeProgram) {
      render(program).catch(error => {
        console.warn("Programme Atlas non affiché.", error);
      });
    }
  });

  window.addEventListener("atlas:open-history-workout", event => {
    const workout = event.detail?.workout;
    if (!workout?.workout_id) return;
    openWorkout(workout, null);
  });

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
      "/api/atlas-coach/program"
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

  if (window.ATLAS_ACTIVE_PROGRAM?.weeks &&
      window.ATLAS_ACTIVE_PROGRAM?.goal) {
    render(window.ATLAS_ACTIVE_PROGRAM).catch(error => {
      console.warn("Programme Atlas non affiché.", error);
    });
  } else {
    loadProgram();
  }
})();
/* FIN GRILLE HEBDOMADAIRE PREMIUM ATLAS COACH */
