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
  const workoutIndex = new Map();
  let activeProgram = null;

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
    const cards = [];

    const addCard = (label, value, accent) => {
      if (!value) return;

      cards.push(`
        <article style="
          padding:12px 14px;
          border:1px solid ${accent};
          border-radius:12px;
          background:rgba(7,25,43,.88);
          box-shadow:inset 0 0 18px rgba(47,196,255,.025);
        ">
          <span style="
            display:block;
            margin-bottom:5px;
            color:#84acc5;
            font-size:.68rem;
            letter-spacing:.08em;
            text-transform:uppercase;
          ">${escapeHtml(label)}</span>
          <strong style="
            display:block;
            color:#f4fbff;
            font-size:.92rem;
          ">${escapeHtml(value)}</strong>
        </article>
      `);
    };

    if (target.zone != null) {
      addCard(
        "Zone physiologique",
        `Zone ${target.zone}`,
        "rgba(47,199,255,.35)"
      );
    }

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

      addCard(
        "Vitesse cible",
        minimum === maximum
          ? `${minimum} km/h`
          : `${minimum} à ${maximum} km/h`,
        "rgba(44,203,255,.42)"
      );

      const slowPace = paceFromSpeed(
        target.speed_min_kmh
      );
      const fastPace = paceFromSpeed(
        target.speed_max_kmh
      );

      if (slowPace && fastPace) {
        addCard(
          "Allure cible",
          slowPace === fastPace
            ? slowPace
            : `${fastPace.replace("/km", "")} à ${slowPace}`,
          "rgba(77,218,154,.42)"
        );
      }
    } else if (target.pace_min_per_km) {
      const maximumPace = target.pace_max_per_km
        ? ` à ${target.pace_max_per_km}/km`
        : "";

      addCard(
        "Allure cible",
        `${target.pace_min_per_km}/km${maximumPace}`,
        "rgba(77,218,154,.42)"
      );
    }

    if (
      target.heart_rate_min_bpm != null ||
      target.heart_rate_max_bpm != null
    ) {
      const minimum = target.heart_rate_min_bpm;
      const maximum = target.heart_rate_max_bpm;

      addCard(
        "Fréquence cardiaque",
        minimum != null && maximum != null
          ? `${minimum} à ${maximum} bpm`
          : `${minimum ?? maximum} bpm`,
        "rgba(255,94,103,.42)"
      );
    }

    if (target.rpe_0_10 != null) {
      addCard(
        "Effort ressenti",
        `RPE ${target.rpe_0_10}/10`,
        "rgba(240,211,78,.42)"
      );
    }

    if (
      target.gradient_min_percent != null ||
      target.gradient_max_percent != null
    ) {
      addCard(
        "Pente cible",
        `${target.gradient_min_percent ?? 0} à ` +
          `${target.gradient_max_percent ?? target.gradient_min_percent} %`,
        "rgba(255,156,72,.42)"
      );
    }

    if (block.recovery_minutes != null) {
      addCard(
        "Récupération entre efforts",
        `${Number(block.recovery_minutes).toLocaleString("fr-FR")} min`,
        "rgba(135,114,255,.42)"
      );
    }

    return cards.length
      ? `<div style="
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
          gap:9px;
          margin:13px 0;
        ">${cards.join("")}</div>`
      : `<p style="color:#9fc5dc;">Cible individualisée selon les sensations du jour.</p>`;
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

    header.insertAdjacentElement("afterend", ribbon);

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
    `;
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
    workoutIndex.set(key, workout);

    return `
      <button
        class="calendar-session difficulty-${level} zone-${zone || "none"}"
        type="button"
        data-workout-key="${escapeHtml(key)}"
      >
        <span class="calendar-session-top">
          <i>${zone ? `Zone ${zone} · ` : ""}${escapeHtml(difficultyLabel(level))}</i>
          ${RESEARCH_TYPES.has(workout.workout_type) ? `
            <em>Research</em>
          ` : ""}
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
    program
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

    const days = Array.from({ length: 7 }, (_, index) => {
      const value = isoDate(addDays(start, index));
      return calendarDay(
        value,
        index,
        workoutsByDate.get(value) || [],
        program
      );
    });

    return `
      <details
        class="premium-week phase-${escapeHtml(week.phase)}"
        ${week.week_number === 1 ||
          days.some(item => item.includes("is-today"))
          ? "open"
          : ""}
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
      <article>
        <span>Programme</span>
        <strong>${escapeHtml(program.duration_weeks)} semaines</strong>
        <small>
          ${escapeHtml(program.total_running_workouts)} courses
          · ${researchCount} Research
          · ${escapeHtml(
            program.settings
              .optional_running_sessions_per_week
          )} facultative
        </small>
      </article>
    `;
  }

  function ensureDialog() {
    let dialog = document.getElementById(
      "atlasSessionDialog"
    );

    if (dialog) return dialog;

    dialog = document.createElement("dialog");
    dialog.id = "atlasSessionDialog";
    dialog.className = "atlas-session-dialog";
    dialog.style.cssText = "width:min(900px,calc(100vw - 40px));max-width:900px;max-height:88vh;padding:0;color:#eef9ff;border:1px solid rgba(225,177,78,.75);border-radius:24px;background:radial-gradient(circle at 85% 0%,rgba(30,190,255,.16),transparent 34%),linear-gradient(145deg,#0b2035,#061321 58%,#020914);box-shadow:0 35px 100px rgba(0,0,0,.8),0 0 35px rgba(225,177,78,.2);";
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
      <header class="dialog-session-header">
        <div>
          <span>${escapeHtml(formatDate(workout.workout_date, true))}</span>
          <h2>${escapeHtml(workout.title)}</h2>
          <p>${escapeHtml(workout.objective)}</p>
        </div>
        <i class="difficulty-pill difficulty-${level}">
          ${escapeHtml(difficultyLabel(level))}
        </i>
      </header>

      <section style="margin-top:26px">
        <h3 style="margin-bottom:16px">Aperçu</h3>
        <div style="
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:1px;
          overflow:hidden;
          border-top:1px solid rgba(255,255,255,.16);
          border-bottom:1px solid rgba(255,255,255,.16);
          background:rgba(255,255,255,.08);
        ">
          <article style="padding:18px;background:#071827">
            <strong style="display:block;font-size:1.45rem">
              ${escapeHtml(formatMinutes(workout.planned_duration_minutes))}
            </strong>
            <span style="color:#8faabd">Durée totale</span>
          </article>
          <article style="padding:18px;background:#071827">
            <strong style="display:block;font-size:1.45rem">
              ${estimatedDistance ? estimatedDistance.toLocaleString(
                "fr-FR",
                { maximumFractionDigits: 1 }
              ) + " km" : "—"}
            </strong>
            <span style="color:#8faabd">Distance estimée</span>
          </article>
          <article style="padding:18px;background:#071827">
            <strong style="display:block;font-size:1.45rem">
              ${escapeHtml(response.physiological_load_0_100 ?? "—")}/100
            </strong>
            <span style="color:#8faabd">Charge physiologique</span>
          </article>
          <article style="padding:18px;background:#071827">
            <strong style="display:block;font-size:1.45rem">
              ${escapeHtml(response.recovery_min_hours ?? "—")}–${escapeHtml(
                response.recovery_max_hours ?? "—"
              )} h
            </strong>
            <span style="color:#8faabd">Récupération estimée</span>
          </article>
        </div>
      </section>

      ${mainBlock ? `
        <section style="
          margin-top:24px;
          padding:17px 19px;
          border-left:4px solid ${accentFor(mainBlock)};
          background:rgba(255,255,255,.035);
        ">
          <span style="
            display:block;
            margin-bottom:6px;
            color:#8faabd;
            font-size:.72rem;
            letter-spacing:.09em;
            text-transform:uppercase;
          ">Cible principale</span>
          <strong>${escapeHtml(targetLine(mainBlock))}</strong>
        </section>
      ` : ""}

      <section style="margin-top:28px">
        <h3 style="margin-bottom:14px">Étapes</h3>
        <div style="display:grid;gap:10px">
          ${blocks.map(block => {
            const distance = blockDistance(block);

            return `
              <article style="
                padding:16px 18px;
                border-left:7px solid ${accentFor(block)};
                border-radius:8px;
                background:rgba(255,255,255,.065);
              ">
                <div style="
                  display:flex;
                  justify-content:space-between;
                  gap:18px;
                  align-items:flex-start;
                ">
                  <div>
                    <strong style="display:block;font-size:1.05rem">
                      ${escapeHtml(stepName(block))}
                    </strong>
                    <span style="display:block;margin-top:3px;color:#a9bdca">
                      ${escapeHtml(block.name)}
                    </span>
                  </div>
                  <b style="white-space:nowrap">
                    ${escapeHtml(blockDuration(block))}
                  </b>
                </div>

                <p style="margin:11px 0 0;color:#dcecf5">
                  ${escapeHtml(targetLine(block))}
                </p>

                ${distance ? `
                  <small style="display:block;margin-top:5px;color:#86a5b9">
                    Distance estimée :
                    ${distance.toLocaleString(
                      "fr-FR",
                      { maximumFractionDigits: 1 }
                    )} km
                  </small>
                ` : ""}

                ${block.instructions ? `
                  <p style="margin:11px 0 0;color:#9eb5c4">
                    ${escapeHtml(block.instructions)}
                  </p>
                ` : ""}
              </article>
            `;
          }).join("")}
        </div>
      </section>

      ${(response.sensitive_structures || []).length ? `
        <details style="
          margin-top:20px;
          padding:15px 17px;
          border:1px solid rgba(53,204,255,.18);
          border-radius:10px;
          background:rgba(5,20,34,.7);
        ">
          <summary style="cursor:pointer;font-weight:700">
            ⓘ Vigilance biomécanique
          </summary>
          <p style="margin:13px 0 0;color:#b5c9d5">
            ${response.sensitive_structures.map(
              item => escapeHtml(item)
            ).join(" · ")}
          </p>
        </details>
      ` : ""}

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

  function openWorkout(workout) {
    const dialog = ensureDialog();
    dialog.querySelector(".dialog-content").innerHTML =
      detailHtml(workout);
    dialog.showModal();
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

  function saveOptional(workout) {
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

  function restoreOptional(program) {
    let saved = [];

    try {
      saved = JSON.parse(
        localStorage.getItem(STORAGE_KEY) || "[]"
      );
    } catch {
      saved = [];
    }

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
  }

  function addOptional(value, type = "recovery_run") {
    const workout = optionalWorkout(value, type);
    saveOptional(workout);

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
  function render(program) {
    activeProgram = program;
    workoutIndex.clear();
    restoreOptional(program);
    physiologicalRibbon(program.athlete_snapshot);
    renderOverview(program);

    calendar.innerHTML = `
      <div class="calendar-premium-banner">
        <div>
          <span>ATLAS COACH × ATLAS RESEARCH</span>
          <strong>Plan hebdomadaire adaptatif</strong>
          <small>
            Quatre séances principales et une séance
            facultative revalidée par Atlas le jour même.
          </small>
        </div>
        <i>Contour doré · difficulté progressive</i>
      </div>

      ${calendarZoneLegend()}

  ${program.weeks.map(
        week => renderWeek(week, program)
      ).join("")}
    `;

    planPanel.hidden = false;
    document.body.classList.add(
      "has-premium-training-calendar"
    );
  }

  calendar.addEventListener("click", event => {
    const workoutButton = event.target.closest(
      "[data-workout-key]"
    );
    const optional = event.target.closest(
      "[data-optional-date]"
    );

    if (workoutButton) {
      openWorkout(
        workoutIndex.get(workoutButton.dataset.workoutKey)
      );
      return;
    }

    if (optional) {
      openActivityPicker(optional.dataset.optionalDate);
    }
  });

  async function loadProgram() {
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
          render(program);
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
