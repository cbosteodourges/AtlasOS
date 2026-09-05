"use strict";

(() => {
  const stages = document.getElementById("profileCalibrationStages");
  if (!stages) return;

  const stageValue = document.getElementById("profileCalibrationStage");
  const sessions = document.getElementById("profileCalibrationSessions");
  const weeks = document.getElementById("profileCalibrationWeeks");
  const nextStep = document.getElementById("profileCalibrationNextStep");

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[character]));

  const render = payload => {
    stageValue.textContent = `${payload.active_stage}/5`;
    stageValue.nextElementSibling.textContent = payload.completed_stage_count >= 5
      ? "Profil établi"
      : "étape actuelle";
    sessions.textContent = String(payload.usable_session_count ?? 0);
    weeks.textContent = String(payload.covered_week_count ?? 0);
    nextStep.textContent = payload.next_step || "Atlas poursuit la calibration du profil.";
    stages.innerHTML = (payload.stages || []).map(stage => `
      <li class="is-${escapeHtml(stage.status)}">
        <span>${escapeHtml(stage.number)}</span>
        <div><strong>${escapeHtml(stage.title)}</strong><small>${escapeHtml(stage.description)}</small></div>
      </li>
    `).join("");
  };

  const load = async () => {
    try {
      const response = await fetch("/api/atlas-coach/profile-calibration", {
        cache: "no-store"
      });
      if (!response.ok) throw new Error("calibration indisponible");
      render(await response.json());
    } catch (error) {
      stages.innerHTML = "<li class=\"is-loading\"><strong>La calibration sera disponible après la prochaine synchronisation.</strong></li>";
      nextStep.textContent = "Synchronisez une première séance ou complétez votre profil de départ.";
    }
  };

  load();
  window.addEventListener("atlas:athlete-profile-loaded", load);
  window.addEventListener("atlas:training-program-loaded", load);
})();

(() => {
  const header = document.querySelector(".performance-header");
  if (!header) return;

  let previousY = Math.max(0, window.scrollY);
  let ticking = false;

  const updateHeader = () => {
    const currentY = Math.max(0, window.scrollY);
    const movement = currentY - previousY;

    if (currentY <= 24) {
      header.classList.remove("is-scroll-hidden");
    } else if (movement > 6) {
      header.classList.add("is-scroll-hidden");
    } else if (movement < -6) {
      header.classList.remove("is-scroll-hidden");
    }

    previousY = currentY;
    ticking = false;
  };

  window.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(updateHeader);
  }, { passive: true });

  header.addEventListener("focusin", () => {
    header.classList.remove("is-scroll-hidden");
  });
})();

(() => {
  // ████████████████████████████████████████████████████████████
  // 🟦 PARTIE A — A01 — CONFIGURATION
  // ████████████████████████████████████████████████████████████

  const ZONES = [
    { id: 1, hr: [50, 65], vma: [55, 65], name: "Récupération", color: "#5aa8ff" },
    { id: 2, hr: [65, 75], vma: [65, 75], name: "Endurance fondamentale", color: "#51d892" },
    { id: 3, hr: [75, 87], vma: [75, 92], name: "Endurance active", color: "#e7d353" },
    { id: 4, hr: [87, 95], vma: [92, 100], name: "VO₂max", color: "#ff9a4f" },
    { id: 5, hr: [95, 100], vma: [100, 110], name: "VMA courte / Anaérobie", color: "#ff5d68" }
  ];

  const EVENT_LABELS = {
    "5k": "5 km",
    "10k": "10 km",
    "half": "Semi-marathon",
    "marathon": "Marathon",
    "trail-short": "Trail court",
    "trail-long": "Trail long",
    "ultra": "Ultra-trail"
  };

  const MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
  ];

  const DAYS = [
    "dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"
  ];

  const elements = {
    eventType: document.getElementById("eventType"),
    eventDate: document.getElementById("eventDate"),
    vma: document.getElementById("vma"),
    hrMax: document.getElementById("hrMax"),
    hrRest: document.getElementById("hrRest"),
    vo2MaxProfile: document.getElementById("vo2MaxProfile"),
    daysPerWeek: document.getElementById("daysPerWeek"),
    runningExperience: document.getElementById("runningExperience"),
    weeklyVolume: document.getElementById("weeklyVolume"),
    recentLongRun: document.getElementById("recentLongRun"),
    recentRaceTime: document.getElementById("recentRaceTime"),
    intensityTolerance: document.getElementById("intensityTolerance"),
    trainingMotivation: document.getElementById("trainingMotivation"),
    initialAssessmentMethod: document.getElementById("initialAssessmentMethod"),
    halfCooperPanel: document.getElementById("halfCooperPanel"),
    halfCooperDistance: document.getElementById("halfCooperDistance"),
    halfCooperResult: document.getElementById("halfCooperResult"),
    availabilityDays: document.getElementById("availabilityDays"),
    specificDayOne: document.getElementById("specificDayOne"),
    specificDayTwo: document.getElementById("specificDayTwo"),
    longRunDay: document.getElementById("longRunDay"),
    weekdayDuration: document.getElementById("weekdayDuration"),
    weekendDuration: document.getElementById("weekendDuration"),
    preferredTime: document.getElementById("preferredTime"),
    trainingFlexibility: document.getElementById("trainingFlexibility"),
    profileSaveStatus: document.getElementById("profileSaveStatus"),
    displayMode: document.getElementById("displayMode"),
    thresholdSource: document.getElementById("thresholdSource"),
    measuredThresholds: document.getElementById("measuredThresholds"),
    sv1HrMeasured: document.getElementById("sv1HrMeasured"),
    sv1SpeedMeasured: document.getElementById("sv1SpeedMeasured"),
    sv2HrMeasured: document.getElementById("sv2HrMeasured"),
    sv2SpeedMeasured: document.getElementById("sv2SpeedMeasured"),
    calculateButton: document.getElementById("calculateButton"),
    physiologyPanel: document.getElementById("physiologyPanel"),
    planPanel: document.getElementById("planPanel"),
    zonesBody: document.getElementById("zonesBody"),
    thresholdScale: document.getElementById("thresholdScale"),
    thresholdConfidence: document.getElementById("thresholdConfidence"),
    sv1Summary: document.getElementById("sv1Summary"),
    sv2Summary: document.getElementById("sv2Summary"),
    durationSummary: document.getElementById("durationSummary"),
    eventSummary: document.getElementById("eventSummary"),
    planOverview: document.getElementById("planOverview"),
    trainingCalendar: document.getElementById("trainingCalendar"),
    validationMessage: document.getElementById("validationMessage"),
        printButton: document.getElementById("printButton"),
    garminActivityCard:
      document.getElementById("garminActivityCard"),
    garminActivityTitle:
      document.getElementById("garminActivityTitle"),
    garminActivityDate:
      document.getElementById("garminActivityDate"),
    garminDistance:
      document.getElementById("garminDistance"),
    garminDuration:
      document.getElementById("garminDuration"),
    garminPace:
      document.getElementById("garminPace"),
    garminAverageHeartRate:
      document.getElementById("garminAverageHeartRate"),
    garminMaximumHeartRate:
      document.getElementById("garminMaximumHeartRate"),
    garminElevationGain:
      document.getElementById("garminElevationGain"),
    garminCalories:
      document.getElementById("garminCalories"),
    garminDevice:
      document.getElementById("garminDevice")
  };

  // ████████████████████████████████████████████████████████████
  // 🟩 PARTIE B — B01 — UTILITAIRES
  // ████████████████████████████████████████████████████████████

  function addDays(value, days) {
    const result = new Date(value);
    result.setDate(result.getDate() + days);
    return result;
  }

  function startOfWeek(value) {
    const result = new Date(value);
    const day = result.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    result.setDate(result.getDate() + diff);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  function formatDate(value) {
    return `${DAYS[value.getDay()]} ${value.getDate()} ${MONTHS[value.getMonth()]} ${value.getFullYear()}`;
  }

  function formatShortDate(value) {
    return `${value.getDate()} ${MONTHS[value.getMonth()]} ${value.getFullYear()}`;
  }

  function paceFromSpeed(speed) {
    if (!speed || speed <= 0) return "—";
    const totalSeconds = Math.round(3600 / speed);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}'${String(seconds).padStart(2, "0")}/km`;
  }

  function round(value, digits = 0) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
  }

  function showValidation(message) {
    elements.validationMessage.textContent = message;
    elements.validationMessage.classList.add("visible");
    clearTimeout(window.atlasValidationTimer);
    window.atlasValidationTimer = setTimeout(() => {
      elements.validationMessage.classList.remove("visible");
    }, 3200);
  }

  function showAtlasProfileNotification(message) {
    let notification = document.getElementById(
      "atlasProfileNotification"
    );

    if (!notification) {
      notification = document.createElement("div");
      notification.id = "atlasProfileNotification";
      notification.setAttribute("role", "status");
      notification.setAttribute("aria-live", "polite");
      notification.style.cssText = [
        "position:fixed",
        "z-index:1000",
        "right:24px",
        "bottom:24px",
        "max-width:390px",
        "padding:14px 18px",
        "color:#eafff7",
        "font-size:.82rem",
        "font-weight:700",
        "line-height:1.4",
        "border:1px solid rgba(72,217,154,.7)",
        "border-radius:12px",
        "background:rgba(5,29,36,.97)",
        "box-shadow:0 12px 35px rgba(0,0,0,.38),0 0 18px rgba(72,217,154,.16)",
        "opacity:0",
        "transform:translateY(12px)",
        "transition:opacity .25s ease,transform .25s ease"
      ].join(";");
      document.body.appendChild(notification);
    }

    notification.textContent = `✓ ${message}`;
    notification.style.opacity = "1";
    notification.style.transform = "translateY(0)";

    clearTimeout(window.atlasProfileNotificationTimer);
    window.atlasProfileNotificationTimer = setTimeout(() => {
      notification.style.opacity = "0";
      notification.style.transform = "translateY(12px)";
    }, 5200);
  }
  function getInputs() {
    const eventDate = elements.eventDate.value
      ? new Date(`${elements.eventDate.value}T12:00:00`)
      : null;

    return {
      eventType: elements.eventType.value,
      eventDate,
      vma: Number(elements.vma.value),
      hrMax: Number(elements.hrMax.value),
      hrRest: elements.hrRest.value.trim() ? Number(elements.hrRest.value) : null,
      daysPerWeek: Number(elements.daysPerWeek.value),
      displayMode: elements.displayMode.value,
      thresholdSource: elements.thresholdSource.value
    };
  }

  // ████████████████████████████████████████████████████████████
  // 🟨 PARTIE C — C01 — CALCUL DES ZONES ET DES SEUILS
  // ████████████████████████████████████████████████████████████

  function buildZones(profile) {
    return ZONES.map(zone => {
      const hrLow = Math.round(profile.hrMax * zone.hr[0] / 100);
      const hrHigh = Math.round(profile.hrMax * zone.hr[1] / 100);
      const speedLow = round(profile.vma * zone.vma[0] / 100, 1);
      const speedHigh = round(profile.vma * zone.vma[1] / 100, 1);

      return {
        ...zone,
        hrLow,
        hrHigh,
        speedLow,
        speedHigh,
        paceLow: paceFromSpeed(speedHigh),
        paceHigh: paceFromSpeed(speedLow)
      };
    });
  }

  function determineThresholds(profile, zones) {
    if (["measured", "atlas_profile"].includes(profile.thresholdSource)) {
      const sv1Hr = Number(elements.sv1HrMeasured.value);
      const sv1Speed = Number(elements.sv1SpeedMeasured.value);
      const sv2Hr = Number(elements.sv2HrMeasured.value);
      const sv2Speed = Number(elements.sv2SpeedMeasured.value);

      if (![sv1Hr, sv1Speed, sv2Hr, sv2Speed].every(Number.isFinite) ||
          [sv1Hr, sv1Speed, sv2Hr, sv2Speed].some(value => value <= 0)) {
        throw new Error("Renseignez les quatre valeurs mesurées de SV1 et SV2.");
      }

      return {
        sv1Hr,
        sv1Speed,
        sv2Hr,
        sv2Speed,
        label: profile.thresholdSource === "measured" ? "Seuils mesurés — confiance élevée" : "Profil Atlas évolutif"
      };
    }

    // Placement demandé : SV1 après Z2, SV2 après Z3.
    return {
      sv1Hr: zones[1].hrHigh,
      sv1Speed: zones[1].speedHigh,
      sv2Hr: zones[2].hrHigh,
      sv2Speed: zones[2].speedHigh,
      label: "Seuils estimés par Atlas — à confirmer par un test"
    };
  }

  function renderZones(zones, thresholds) {
    elements.zonesBody.innerHTML = zones.map(zone => `
      <tr>
        <td>
          <span class="zone-name">
            <i class="zone-dot" style="background:${zone.color}"></i>
            Z${zone.id} · ${zone.name}
          </span>
        </td>
        <td>${zone.hr[0]}–${zone.hr[1]} %</td>
        <td>${zone.hrLow}–${zone.hrHigh} bpm</td>
        <td>${zone.vma[0]}–${zone.vma[1]} %</td>
        <td>${zone.speedLow}–${zone.speedHigh} km/h</td>
        <td>${zone.paceLow} à ${zone.paceHigh}</td>
      </tr>
    `).join("");

    zones.forEach(zone => {
      const summary = document.getElementById(`coachZone${zone.id}`);
      if (!summary) return;
      summary.innerHTML = `${zone.name}<small>${zone.speedLow}–${zone.speedHigh} km/h · ${zone.hrLow}–${zone.hrHigh} bpm</small>`;
    });

    elements.thresholdScale.innerHTML = zones.map(zone => {
      const marker = zone.id === 2
        ? `<i class="threshold-marker"><span>SV1</span></i>`
        : zone.id === 3
          ? `<i class="threshold-marker"><span>SV2</span></i>`
          : "";

      return `
        <div class="scale-zone" style="background:${zone.color}">
          <strong>Z${zone.id}</strong>
          <small>${zone.name}</small>
          ${marker}
        </div>
      `;
    }).join("");

    elements.sv1Summary.textContent =
      `${thresholds.sv1Hr} bpm · ${thresholds.sv1Speed} km/h · ${paceFromSpeed(thresholds.sv1Speed)}`;

    elements.sv2Summary.textContent =
      `${thresholds.sv2Hr} bpm · ${thresholds.sv2Speed} km/h · ${paceFromSpeed(thresholds.sv2Speed)}`;

    elements.thresholdConfidence.textContent = thresholds.label;
  }

  // ████████████████████████████████████████████████████████████
  // 🟧 PARTIE D — D01 — GÉNÉRATEUR DE PLAN
  // ████████████████████████████████████████████████████████████

  function getPhase(weekIndex, totalWeeks) {
    const ratio = weekIndex / Math.max(totalWeeks - 1, 1);

    if (ratio < 0.25) return "Développement général";
    if (ratio < 0.55) return "Développement spécifique";
    if (ratio < 0.82) return "Spécifique compétition";
    return "Affûtage";
  }

  function getTargetZone(zoneId, zones) {
    return zones.find(zone => zone.id === zoneId);
  }

  function zoneLine(zone, profile) {
    const hrText = `${zone.hr[0]}–${zone.hr[1]} % FCmax (${zone.hrLow}–${zone.hrHigh} bpm)`;
    const speedText = `${zone.vma[0]}–${zone.vma[1]} % VMA (${zone.speedLow}–${zone.speedHigh} km/h · ${zone.paceLow} à ${zone.paceHigh})`;

    if (profile.displayMode === "hr") return hrText;
    if (profile.displayMode === "speed") return speedText;
    return `${hrText} · ${speedText}`;
  }


  function progressiveLongRunMinutes(eventType, phase, weekIndex, totalWeeks) {
    const baseByEvent = {
      "5k": 55,
      "10k": 60,
      "half": 65,
      "marathon": 75,
      "trail-short": 70,
      "trail-long": 80,
      "ultra": 90
    };

    const ceilingByEvent = {
      "5k": 75,
      "10k": 95,
      "half": 125,
      "marathon": 180,
      "trail-short": 140,
      "trail-long": 210,
      "ultra": 300
    };

    const base = baseByEvent[eventType] || 60;
    const ceiling = ceilingByEvent[eventType] || 100;
    const ratio = weekIndex / Math.max(totalWeeks - 1, 1);

    let target = base + (ceiling - base) * Math.min(ratio, 0.82);

    // Semaine allégée toutes les 4 semaines.
    if ((weekIndex + 1) % 4 === 0) {
      target *= 0.82;
    }

    // Affûtage : réduction nette de la durée.
    if (phase === "Affûtage") {
      target *= 0.68;
    }

    return Math.max(base, Math.round(target / 5) * 5);
  }

  function sessionTemplates(profile, zones, phase, eventType, weekIndex, totalWeeks) {
    const z1 = getTargetZone(1, zones);
    const z2 = getTargetZone(2, zones);
    const z3 = getTargetZone(3, zones);
    const z4 = getTargetZone(4, zones);
    const z5 = getTargetZone(5, zones);

    const enduranceDuration = ["marathon", "trail-long", "ultra"].includes(eventType) ? 65 : 50;
    const longDuration = progressiveLongRunMinutes(
      eventType,
      phase,
      weekIndex,
      totalWeeks
    );

    const templates = {
      "Développement général": [
        {
          title: "Endurance fondamentale",
          objective: "Développer la base aérobie sous SV1.",
          blocks: [
            ["Échauffement", "10 min", z1],
            ["Corps de séance", `${enduranceDuration} min`, z2],
            ["Retour au calme", "10 min", z1]
          ]
        },
        {
          title: "Force et côtes",
          objective: "Développer la force spécifique et la tolérance musculo-tendineuse.",
          blocks: [
            ["Échauffement", "20 min", z2],
            ["Côtes", "8 × 45 s", z4],
            ["Récupération", "Descente lente", z1],
            ["Renforcement", "20 min jambes + tronc", z2]
          ]
        },
        {
          title: "Sortie longue progressive",
          objective: "Augmenter progressivement la durée d’effort.",
          blocks: [
            ["Début", `${Math.max(40, longDuration - Math.min(10, Math.round(longDuration * .12)))} min`, z2],
            ["Fin progressive", `${Math.min(10, Math.round(longDuration * .12))} min`, z3]
          ]
        }
      ],
      "Développement spécifique": [
        {
          title: "Intervalles au SV2",
          objective: "Élever la vitesse durable autour du deuxième seuil ventilatoire.",
          blocks: [
            ["Échauffement", "20 min", z2],
            ["Bloc principal", "4 × 6 min", z4],
            ["Récupération", "2 min", z1],
            ["Retour au calme", "12 min", z1]
          ]
        },
        {
          title: "Endurance et mobilité",
          objective: "Entretenir la base aérobie et la mobilité articulaire.",
          blocks: [
            ["Course", "50 min", z2],
            ["Mobilité", "15 min hanches, chevilles, rachis", z1]
          ]
        },
        {
          title: "Sortie longue spécifique",
          objective: "Développer l’endurance proche des contraintes de l’épreuve.",
          blocks: [
            ["Endurance", `${Math.round(longDuration * .82)} min`, z2],
            ["Spécifique", `${Math.round(longDuration * .18)} min`, z3]
          ]
        }
      ],
      "Spécifique compétition": [
        {
          title: "Séance allure compétition",
          objective: "Stabiliser l’allure cible et l’économie de course.",
          blocks: [
            ["Échauffement", "20 min", z2],
            ["Bloc principal", eventType === "5k" ? "6 × 1 000 m" : "3 × 12 min", z4],
            ["Récupération", "2 à 3 min", z1],
            ["Retour au calme", "15 min", z1]
          ]
        },
        {
          title: "VMA courte",
          objective: "Entretenir la puissance aérobie sans surcharge excessive.",
          blocks: [
            ["Échauffement", "20 min", z2],
            ["Bloc principal", "10 × 400 m", z5],
            ["Récupération", "1 min 15 s", z1],
            ["Retour au calme", "12 min", z1]
          ]
        },
        {
          title: "Sortie longue avec blocs",
          objective: "Maintenir l’endurance et répéter l’allure spécifique.",
          blocks: [
            ["Endurance", `${Math.max(45, longDuration - 30)} min`, z2],
            ["Blocs spécifiques", "2 × 10 min", z3],
            ["Récupération", "5 min", z2]
          ]
        }
      ],
      "Affûtage": [
        {
          title: "Rappel d’intensité",
          objective: "Conserver les adaptations en réduisant la fatigue.",
          blocks: [
            ["Échauffement", "18 min", z2],
            ["Bloc principal", "5 × 2 min", z4],
            ["Récupération", "2 min", z1],
            ["Retour au calme", "10 min", z1]
          ]
        },
        {
          title: "Footing facile",
          objective: "Favoriser la récupération et la fraîcheur.",
          blocks: [
            ["Course", "35 à 45 min", z2],
            ["Mobilité", "10 min", z1]
          ]
        },
        {
          title: "Activation pré-compétition",
          objective: "Préparer le système neuromusculaire sans générer de fatigue.",
          blocks: [
            ["Footing", "25 min", z2],
            ["Accélérations", "4 × 20 s", z4],
            ["Récupération", "1 min 30 s", z1]
          ]
        }
      ]
    };

    return templates[phase];
  }

  function chooseTrainingDays(daysPerWeek) {
    const patterns = {
      3: [2, 4, 0],       // mardi, jeudi, dimanche
      4: [2, 4, 6, 0],    // mardi, jeudi, samedi, dimanche
      5: [1, 2, 4, 6, 0],
      6: [1, 2, 3, 4, 6, 0]
    };

    return patterns[daysPerWeek] || patterns[4];
  }

  function generatePlan(profile, zones) {
    const today = new Date();
    today.setHours(12, 0, 0, 0);

    const eventDate = profile.eventDate;
    const totalDays = Math.ceil((eventDate - today) / 86400000);
    const totalWeeks = Math.max(1, Math.ceil(totalDays / 7));
    const trainingDays = chooseTrainingDays(profile.daysPerWeek);
    const firstWeek = startOfWeek(today);
    const weeks = [];

    for (let weekIndex = 0; weekIndex < totalWeeks; weekIndex += 1) {
      const weekStart = addDays(firstWeek, weekIndex * 7);
      const weekEnd = addDays(weekStart, 6);
      const phase = getPhase(weekIndex, totalWeeks);
      const templates = sessionTemplates(
        profile,
        zones,
        phase,
        profile.eventType,
        weekIndex,
        totalWeeks
      );
      const sessions = [];

      trainingDays.forEach((dayOfWeek, sessionIndex) => {
        const offset = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        const sessionDate = addDays(weekStart, offset);

        if (sessionDate < today || sessionDate >= eventDate) return;

        const template = templates[sessionIndex % templates.length];

        sessions.push({
          ...template,
          date: sessionDate,
          phase
        });
      });

      if (sessions.length) {
        weeks.push({
          index: weekIndex + 1,
          start: weekStart,
          end: weekEnd,
          phase,
          sessions
        });
      }
    }

    // Ajout explicite du jour de l’épreuve.
    weeks.push({
      index: totalWeeks,
      start: eventDate,
      end: eventDate,
      phase: "Compétition",
      sessions: [{
        date: eventDate,
        title: EVENT_LABELS[profile.eventType],
        objective: "Jour J — appliquer la stratégie d’allure, d’hydratation et de nutrition validée.",
        blocks: [
          ["Échauffement", "Adapté à l’épreuve", zones[1]],
          ["Compétition", "Gestion progressive", zones[profile.eventType === "5k" ? 4 : 3]],
          ["Retour au calme", "Marche et récupération", zones[0]]
        ]
      }]
    });

    return { weeks, totalWeeks, totalDays };
  }


  function parseTimeRangeMinutes(text) {
    if (!text) return 0;

    const normalized = text
      .toLowerCase()
      .replace(",", ".")
      .replace(/\s+/g, " ")
      .trim();

    const minuteRange = normalized.match(/(\d+(?:\.\d+)?)\s*(?:à|-)\s*(\d+(?:\.\d+)?)\s*min/);
    if (minuteRange) {
      return (Number(minuteRange[1]) + Number(minuteRange[2])) / 2;
    }

    const minutesSeconds = normalized.match(/(\d+(?:\.\d+)?)\s*min(?:ute)?s?\s*(\d+(?:\.\d+)?)?\s*s?/);
    if (minutesSeconds) {
      return Number(minutesSeconds[1]) +
        (minutesSeconds[2] ? Number(minutesSeconds[2]) / 60 : 0);
    }

    const secondsOnly = normalized.match(/(\d+(?:\.\d+)?)\s*s(?:ec(?:onde)?s?)?/);
    if (secondsOnly) {
      return Number(secondsOnly[1]) / 60;
    }

    const hours = normalized.match(/(\d+(?:\.\d+)?)\s*h/);
    const minutes = normalized.match(/(\d+(?:\.\d+)?)\s*min/);

    if (hours || minutes) {
      return (hours ? Number(hours[1]) * 60 : 0) +
        (minutes ? Number(minutes[1]) : 0);
    }

    return 0;
  }

  function parseRepeatedEffort(text, zone) {
    if (!text) return null;

    const normalized = text
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();

    const repeatedMinutes = normalized.match(/(\d+)\s*[×x]\s*(\d+(?:\.\d+)?)\s*min/);
    if (repeatedMinutes) {
      return {
        repetitions: Number(repeatedMinutes[1]),
        minutes: Number(repeatedMinutes[1]) * Number(repeatedMinutes[2])
      };
    }

    const repeatedSeconds = normalized.match(/(\d+)\s*[×x]\s*(\d+(?:\.\d+)?)\s*s/);
    if (repeatedSeconds) {
      return {
        repetitions: Number(repeatedSeconds[1]),
        minutes: Number(repeatedSeconds[1]) * Number(repeatedSeconds[2]) / 60
      };
    }

    const repeatedDistance = normalized.match(/(\d+)\s*[×x]\s*([\d\s]+)\s*m\b/);
    if (repeatedDistance && zone) {
      const repetitions = Number(repeatedDistance[1]);
      const metres = Number(repeatedDistance[2].replace(/\s/g, ""));
      const averageSpeed = (zone.speedLow + zone.speedHigh) / 2;

      return {
        repetitions,
        minutes: ((repetitions * metres) / 1000) / averageSpeed * 60
      };
    }

    return null;
  }

  function analyseSessionDurations(session) {
    const analysed = [];
    let previousRepetitions = 0;

    session.blocks.forEach(([label, duration, zone]) => {
      const repeated = parseRepeatedEffort(duration, zone);
      let minutes = 0;

      if (repeated) {
        minutes = repeated.minutes;
        previousRepetitions = repeated.repetitions;
      } else {
        minutes = parseTimeRangeMinutes(duration);

        if (
          /récupération/i.test(label) &&
          previousRepetitions > 1 &&
          minutes > 0
        ) {
          minutes *= previousRepetitions - 1;
          previousRepetitions = 0;
        }
      }

      analysed.push({
        label,
        duration,
        zone,
        minutes
      });
    });

    return analysed;
  }

  function sessionTotalMinutes(session) {
    return analyseSessionDurations(session)
      .reduce((sum, block) => sum + block.minutes, 0);
  }

  function formatDuration(totalMinutes) {
    if (!totalMinutes) return "Durée non calculable";

    const rounded = Math.round(totalMinutes);
    const hours = Math.floor(rounded / 60);
    const minutes = rounded % 60;

    if (!hours) return `${minutes} min`;
    if (!minutes) return `${hours} h`;
    return `${hours} h ${String(minutes).padStart(2, "0")}`;
  }

  function renderDistribution(session) {
    const timedBlocks = analyseSessionDurations(session)
      .filter(block => block.minutes > 0);

    const total = timedBlocks.reduce((sum, block) => sum + block.minutes, 0);
    if (!total) return "";

    return `
      <div class="session-distribution" aria-label="Répartition estimée des zones">
        ${timedBlocks.map(block => `
          <i
            title="${block.label} : ${Math.round(block.minutes)} min en Z${block.zone.id}"
            style="width:${(block.minutes / total) * 100}%;background:${block.zone.color}"
          ></i>
        `).join("")}
      </div>
    `;
  }

  function renderPlan(profile, zones, plan) {
    const totalSessions = plan.weeks.reduce((sum, week) => sum + week.sessions.length, 0);

    elements.planOverview.innerHTML = `
      <article><span>Épreuve</span><strong>${EVENT_LABELS[profile.eventType]}</strong></article>
      <article><span>Date</span><strong>${formatShortDate(profile.eventDate)}</strong></article>
      <article><span>Durée du plan</span><strong>${plan.totalWeeks} semaines</strong></article>
      <article><span>Séances programmées</span><strong>${totalSessions}</strong></article>
    `;

    elements.trainingCalendar.innerHTML = plan.weeks.map(week => `
      <section class="training-week">
        <header class="week-header">
          <strong>Semaine ${week.index} · ${week.phase}</strong>
          <span>${formatShortDate(week.start)}${week.end.getTime() !== week.start.getTime() ? ` → ${formatShortDate(week.end)}` : ""}</span>
        </header>

        <div class="session-list">
          ${week.sessions.map(session => `
            <article class="session-card">
              <div class="session-date">${formatDate(session.date)}</div>
              <h3>${session.title}</h3>
              <div class="session-objective">${session.objective}</div>
              <div class="session-total">
                ⏱ Durée totale calculée : ${formatDuration(sessionTotalMinutes(session))}
              </div>
              ${renderDistribution(session)}

              <div class="session-blocks">
                ${session.blocks.map(([label, duration, zone]) => `
                  <div class="session-block" style="--zone-color:${zone.color}">
                    <strong>${label} · Z${zone.id}</strong>
                    <span>${duration}</span>
                    <small>${zoneLine(zone, profile)}</small>
                  </div>
                `).join("")}
              </div>
            </article>
          `).join("")}
        </div>
      </section>
    `).join("");
  }

  // ████████████████████████████████████████████████████████████
  // 🟥 PARTIE F — F01 — VALIDATION ET ÉVÉNEMENTS
  // ████████████████████████████████████████████████████████████

  function calculate() {
    try {
      const profile = getInputs();

      if (!Number.isFinite(profile.vma) || profile.vma < 6) {
        throw new Error("Renseignez une VMA valide ou choisissez une méthode d’estimation.");
      }
      if (!Number.isFinite(profile.hrMax) || profile.hrMax < 120) {
        throw new Error("Renseignez une fréquence cardiaque maximale valide.");
      }
      if (Number.isFinite(profile.hrRest) && profile.hrRest >= profile.hrMax) {
        throw new Error("La fréquence cardiaque de repos doit être inférieure à la FC maximale.");
      }

      const zones = buildZones(profile);
      const thresholds = determineThresholds(profile, zones);
      renderZones(zones, thresholds);

      const availableDays = [
        ...elements.availabilityDays.querySelectorAll("input:checked")
      ].map(input => input.value);
      if (availableDays.length < profile.daysPerWeek) {
        throw new Error(
          "Sélectionnez au moins autant de jours disponibles que de séances prévues."
        );
      }

      const savedProfile = {
        eventType: profile.eventType,
        eventDate: elements.eventDate.value,
        vma: profile.vma,
        vo2Max: Number(elements.vo2MaxProfile.value) || null,
        hrMax: profile.hrMax,
        hrRest: profile.hrRest,
        daysPerWeek: profile.daysPerWeek,
        displayMode: profile.displayMode,
        thresholdSource: profile.thresholdSource,
        thresholds,
        experience: elements.runningExperience.value,
        weeklyVolumeKm: Number(elements.weeklyVolume.value) || null,
        recentLongRunKm: Number(elements.recentLongRun.value) || null,
        recentRaceTime: elements.recentRaceTime.value.trim(),
        intensityTolerance: elements.intensityTolerance.value,
        motivation: elements.trainingMotivation.value,
        assessmentMethod: elements.initialAssessmentMethod.value,
        availability: {
          days: availableDays,
          specificDayOne: elements.specificDayOne.value,
          specificDayTwo: elements.specificDayTwo.value,
          longRunDay: elements.longRunDay.value,
          weekdayDurationMinutes: Number(elements.weekdayDuration.value),
          weekendDurationMinutes: Number(elements.weekendDuration.value),
          preferredTime: elements.preferredTime.value,
          flexibility: elements.trainingFlexibility.value
        },
        updatedAt: new Date().toISOString()
      };

      localStorage.setItem(
        "atlasRunningProfile",
        JSON.stringify(savedProfile)
      );
      fetch("/api/atlas-user/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: savedProfile })
      }).catch(error => console.debug(
        "Profil Atlas conservé localement ; serveur indisponible.", error
      ));
      window.dispatchEvent(new CustomEvent(
        "atlas:zones-updated",
        { detail: { zones, thresholds, profile: savedProfile } }
      ));
      elements.profileSaveStatus.textContent =
        "Profil enregistré · zones recalculées automatiquement.";
      showAtlasProfileNotification(
        "Profil physiologique et disponibilités enregistrés."
      );
    } catch (error) {
      showValidation(error.message);
    }
  }

  function setDefaultDate() {
    const target = new Date();
    target.setDate(target.getDate() + 84);
    elements.eventDate.value = target.toISOString().slice(0, 10);
  }

  function syncMeasuredThresholdFields() {
    const showMeasuredFields =
      elements.thresholdSource.value !== "estimated";

    elements.measuredThresholds.hidden = !showMeasuredFields;

    [
      elements.sv1HrMeasured,
      elements.sv1SpeedMeasured,
      elements.sv2HrMeasured,
      elements.sv2SpeedMeasured
    ].forEach(input => {
      input.disabled = !showMeasuredFields;
      input.required = showMeasuredFields;
    });
  }

  function setAtlasNumberField(field, value) {
    if (value === null || value === undefined || value === "") return;
    const number = Number(value);
    if (field && Number.isFinite(number)) field.value = String(number);
  }

  function restoreAtlasRunningProfile() {
    try {
      const saved = JSON.parse(
        localStorage.getItem("atlasRunningProfile") || "null"
      );

      if (!saved) return null;

      setAtlasNumberField(elements.vma, saved.vma);
      setAtlasNumberField(elements.hrMax, saved.hrMax);
      setAtlasNumberField(elements.hrRest, saved.hrRest);
      setAtlasNumberField(elements.vo2MaxProfile, saved.vo2Max);
      setAtlasNumberField(elements.weeklyVolume, saved.weeklyVolumeKm);
      setAtlasNumberField(elements.recentLongRun, saved.recentLongRunKm);
      if (saved.recentRaceTime) elements.recentRaceTime.value = saved.recentRaceTime;
      if (saved.experience) elements.runningExperience.value = saved.experience;
      if (saved.intensityTolerance) elements.intensityTolerance.value = saved.intensityTolerance;
      if (saved.motivation) elements.trainingMotivation.value = saved.motivation;
      if (saved.assessmentMethod) elements.initialAssessmentMethod.value = saved.assessmentMethod;
      if (saved.availability) {
        const availability = saved.availability;
        elements.availabilityDays.querySelectorAll("input").forEach(input => {
          input.checked = (availability.days || []).includes(input.value);
        });
        if (availability.specificDayOne) elements.specificDayOne.value = availability.specificDayOne;
        if (availability.specificDayTwo) elements.specificDayTwo.value = availability.specificDayTwo;
        if (availability.longRunDay) elements.longRunDay.value = availability.longRunDay;
        setAtlasNumberField(elements.weekdayDuration, availability.weekdayDurationMinutes);
        setAtlasNumberField(elements.weekendDuration, availability.weekendDurationMinutes);
        if (availability.preferredTime) elements.preferredTime.value = availability.preferredTime;
        if (availability.flexibility) elements.trainingFlexibility.value = availability.flexibility;
      }

      if (saved.daysPerWeek) {
        elements.daysPerWeek.value = String(saved.daysPerWeek);
      }

      if (saved.displayMode) {
        elements.displayMode.value = saved.displayMode;
      }

      const validSource = [...elements.thresholdSource.options]
        .some(option => option.value === saved.thresholdSource);

      if (validSource) {
        elements.thresholdSource.value = saved.thresholdSource;
      }

      if (saved.thresholds) {
        setAtlasNumberField(
          elements.sv1HrMeasured,
          saved.thresholds.sv1Hr
        );
        setAtlasNumberField(
          elements.sv1SpeedMeasured,
          saved.thresholds.sv1Speed
        );
        setAtlasNumberField(
          elements.sv2HrMeasured,
          saved.thresholds.sv2Hr
        );
        setAtlasNumberField(
          elements.sv2SpeedMeasured,
          saved.thresholds.sv2Speed
        );
      }

      return saved;
    } catch (error) {
      console.debug("Profil local Atlas illisible.", error);
      return null;
    }
  }

  async function loadAtlasAthleteProfile() {
    try {
      const response = await fetch("/api/atlas-user/profile", {
        cache: "no-store"
      });
      if (response.ok) {
        const payload = await response.json();
        if (payload?.profile && Object.keys(payload.profile).length) {
          localStorage.setItem(
            "atlasRunningProfile",
            JSON.stringify(payload.profile)
          );
        } else {
          const local = JSON.parse(
            localStorage.getItem("atlasRunningProfile") || "null"
          );
          if (local) fetch("/api/atlas-user/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile: local })
          }).catch(() => {});
        }
      }
    } catch (error) {
      console.debug("Profil Atlas serveur indisponible.", error);
    }
    const saved = restoreAtlasRunningProfile();
    const preserveMeasured = saved?.thresholdSource === "measured";
    const sources = [
      "/api/atlas/sync-insights",
      window.ATLAS_ATHLETE_PROFILE_URL,
      "../atlas-data/private/athlete-profile.json",
      "/atlas-data/private/athlete-profile.json"
    ].filter(Boolean);

    for (const source of sources) {
      try {
        const response = await fetch(source, { cache: "no-store" });
        if (!response.ok) continue;

        const payload = await response.json();
        const physiology =
          payload?.physiology?.current || payload?.physiological || payload;

        if (!physiology) continue;

        setAtlasNumberField(
          elements.vma,
          physiology.vma_kmh
        );
        setAtlasNumberField(
          elements.vo2MaxProfile,
          physiology.vo2_max
        );
        setAtlasNumberField(
          elements.hrMax,
          physiology.maximum_heart_rate_bpm
        );
        setAtlasNumberField(
          elements.hrRest,
          physiology.resting_heart_rate_bpm
        );

        const sv1 = physiology.sv1 || {};
        const sv2 = physiology.sv2 || {};

        if (!preserveMeasured) {
          setAtlasNumberField(
            elements.sv1HrMeasured,
            sv1.heart_rate_bpm
          );
          setAtlasNumberField(
            elements.sv1SpeedMeasured,
            sv1.speed_kmh
          );
          setAtlasNumberField(
            elements.sv2HrMeasured,
            sv2.heart_rate_bpm
          );
          setAtlasNumberField(
            elements.sv2SpeedMeasured,
            sv2.speed_kmh
          );

          if (
            [sv1.heart_rate_bpm, sv1.speed_kmh,
             sv2.heart_rate_bpm, sv2.speed_kmh]
              .every(value => Number.isFinite(Number(value)))
          ) {
            elements.thresholdSource.value = "atlas_profile";
          }
        }

        syncMeasuredThresholdFields();

        window.dispatchEvent(new CustomEvent(
          "atlas:athlete-profile-loaded",
          { detail: { ...payload, physiological: physiology } }
        ));
        return;
      } catch (error) {
        console.debug(
          "Profil Atlas indisponible.",
          source,
          error
        );
      }
    }

    syncMeasuredThresholdFields();
  }

  async function loadLatestWellnessReferences() {
    try {
      const response = await fetch(
        `/api/atlas/wellness-history?v=${Date.now()}`,
        { cache: "no-store" }
      );
      if (!response.ok) return;
      const payload = await response.json();
      const observations = Array.isArray(payload.history)
        ? [...payload.history].reverse()
        : [];
      const restingHeartRate = observations.find(
        item => Number.isFinite(Number(item.resting_heart_rate_bpm))
      )?.resting_heart_rate_bpm;
      const wellnessVo2 = observations.find(
        item => Number.isFinite(Number(item.vo2_max))
      )?.vo2_max;

      setAtlasNumberField(elements.hrRest, restingHeartRate);
      setAtlasNumberField(elements.vo2MaxProfile, wellnessVo2);
    } catch (error) {
      console.debug("Références Wellness indisponibles.", error);
    }
  }
  elements.thresholdSource.addEventListener(
    "change",
    syncMeasuredThresholdFields
  );

  elements.initialAssessmentMethod.addEventListener("change", () => {
    elements.halfCooperPanel.hidden =
      elements.initialAssessmentMethod.value !== "half-cooper";
  });
  elements.halfCooperDistance.addEventListener("input", () => {
    const distance = Number(elements.halfCooperDistance.value);
    const vma = distance > 0 ? distance / 100 : null;
    elements.halfCooperResult.textContent = vma
      ? `VMA calculée : ${vma.toFixed(1).replace(".", ",")} km/h`
      : "VMA calculée : —";
    if (vma) elements.vma.value = vma.toFixed(1);
  });
  elements.calculateButton.addEventListener("click", calculate);
  elements.printButton.addEventListener("click", () => window.print());

  setDefaultDate();
  loadAtlasAthleteProfile();
  loadLatestWellnessReferences();
  const syncProviderButtons =
    document.querySelectorAll(".provider-button");

  const syncStatus =
    document.querySelector("#syncStatus");

  const GARMIN_ACTIVITIES_URL =
    "../atlas-data/private/garmin-normalized-activities.json";

  function formatActivityDuration(seconds) {
    const totalMinutes = Math.round(Number(seconds) / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours === 0) {
      return `${minutes} min`;
    }

    return `${hours} h ${String(minutes).padStart(2, "0")} min`;
  }

    function displayGarminActivity(activity) {
    const distanceKm =
      Number(activity.distance_meters || 0) / 1000;

    const speedKmh =
      Number(activity.average_speed_mps || 0) * 3.6;

    const activityDate =
      activity.start_time
        ? new Date(activity.start_time)
        : null;

    const activityLabels = {
      running: "Course à pied Garmin",
      trail_running: "Trail Garmin",
      cycling: "Cyclisme Garmin",
      swimming: "Natation Garmin"
    };

    elements.garminActivityTitle.textContent =
      activityLabels[activity.activity_type] ||
      "Activité Garmin";

    elements.garminActivityDate.textContent =
      activityDate
        ? activityDate.toLocaleString("fr-FR", {
            dateStyle: "long",
            timeStyle: "short"
          })
        : "Date indisponible";

    elements.garminDistance.textContent =
      `${distanceKm.toFixed(2).replace(".", ",")} km`;

    elements.garminDuration.textContent =
      formatActivityDuration(activity.duration_seconds);

    elements.garminPace.textContent =
      paceFromSpeed(speedKmh);

    elements.garminAverageHeartRate.textContent =
      activity.average_heart_rate_bpm
        ? `${Math.round(
            activity.average_heart_rate_bpm
          )} bpm`
        : "—";

    elements.garminMaximumHeartRate.textContent =
      activity.maximum_heart_rate_bpm
        ? `${Math.round(
            activity.maximum_heart_rate_bpm
          )} bpm`
        : "—";

    elements.garminElevationGain.textContent =
      activity.elevation_gain_m != null
        ? `${Math.round(
            activity.elevation_gain_m
          )} m`
        : "—";

    elements.garminCalories.textContent =
      activity.calories_kcal != null
        ? `${Math.round(
            activity.calories_kcal
          )} kcal`
        : "—";

    elements.garminDevice.textContent =
      activity.source_device || "Garmin";

    elements.garminActivityCard.hidden = false;
  }

  async function loadGarminActivities() {
    const response = await fetch(
      GARMIN_ACTIVITIES_URL,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(
        `Fichier Garmin indisponible (${response.status})`
      );
    }

    const activities = await response.json();

    if (!Array.isArray(activities)) {
      throw new Error(
        "Le fichier Garmin ne contient pas une liste valide."
      );
    }

    return activities;
  }

  const connectionWizard =
    document.getElementById("sensorConnectionWizard");
  const connectionSummary =
    document.getElementById("sensorConnectionSummary");
  const sensorOnboarding =
    document.getElementById("sensorOnboarding");
  const SENSOR_CONNECTION_KEY = "atlasCoachSensorConnection";
  const SENSOR_SETUP_KEY = "atlasCoachSensorSetupComplete";

  function setSensorOnboardingComplete(complete) {
    if (sensorOnboarding) sensorOnboarding.hidden = Boolean(complete);
  }

  function activityPeriod(activities) {
    const dated = activities
      .filter(activity => activity.start_time)
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    if (!dated.length) return "Période inconnue";
    const format = value => new Date(value).toLocaleDateString("fr-FR");
    return `${format(dated[0].start_time)} → ${format(
      dated[dated.length - 1].start_time
    )}`;
  }

  function filterActivitiesByHistory(activities, history) {
    if (history === "all") return activities;
    const months = Number(history);
    if (!Number.isFinite(months)) return activities;
    const limit = new Date();
    limit.setMonth(limit.getMonth() - months);
    return activities.filter(activity =>
      activity.start_time && new Date(activity.start_time) >= limit
    );
  }

  async function loadWellnessCount() {
    try {
      const response = await fetch(
        `/api/atlas/wellness-history?v=${Date.now()}`,
        { cache: "no-store" }
      );
      if (!response.ok) return 0;
      const payload = await response.json();
      return Number(payload.count) || 0;
    } catch {
      return 0;
    }
  }

  function renderConnectionSummary(config, activities, wellnessCount) {
    const latest = [...activities].sort(
      (a, b) => new Date(b.start_time) - new Date(a.start_time)
    )[0];
    connectionSummary.hidden = false;
    connectionSummary.innerHTML = `
      <header>
        <div><span>SOURCE PRINCIPALE</span><h3>Garmin connecté au prototype Atlas</h3></div>
        <strong>✓ Données détectées</strong>
      </header>
      <div class="sensor-summary-grid">
        <article><span>Activités trouvées</span><strong>${activities.length}</strong></article>
        <article><span>Journées Wellness</span><strong>${wellnessCount || "—"}</strong></article>
        <article><span>Période analysée</span><strong>${activityPeriod(activities)}</strong></article>
        <article><span>Dernière vérification</span><strong>${new Date().toLocaleString("fr-FR")}</strong></article>
      </div>
      <footer>
        <span>Mode actuel : données Garmin déjà importées sur cet appareil.</span>
        <button type="button" data-sensor-resync>Synchroniser maintenant</button>
        <button type="button" data-sensor-manage>Gérer la connexion</button>
      </footer>
    `;
    if (latest) displayGarminActivity(latest);
    syncStatus.textContent =
      `Garmin · ${activities.length} activité(s) exploitable(s) · ` +
      `${wellnessCount} journée(s) Wellness`;
    document.querySelector('[data-provider="garmin"]')?.classList.add("connected");
    localStorage.setItem(SENSOR_CONNECTION_KEY, JSON.stringify(config));
    localStorage.setItem(SENSOR_SETUP_KEY, "true");
    setSensorOnboardingComplete(true);
  }

  function renderManualConnectionSummary() {
    connectionWizard.hidden = true;
    connectionSummary.hidden = false;
    connectionSummary.innerHTML = `
      <header><div><span>MODE D’ENTRAÎNEMENT</span>
      <h3>Profil manuel sans montre connectée</h3></div>
      <strong>✓ Profil conservé</strong></header>
      <p>Vos informations et votre programme restent disponibles. Une montre pourra être ajoutée ultérieurement.</p>
    `;
    syncStatus.textContent = "Mode manuel actif · profil Atlas conservé.";
    setSensorOnboardingComplete(true);
  }

  async function synchronizeGarmin(config) {
    syncStatus.textContent = "Analyse des données Garmin disponibles…";
    try {
      const [allActivities, wellnessCount] = await Promise.all([
        loadGarminActivities(),
        config.wellness ? loadWellnessCount() : Promise.resolve(0)
      ]);
      const activities = filterActivitiesByHistory(
        allActivities,
        config.history
      );
      if (!activities.length) {
        connectionSummary.hidden = true;
        syncStatus.textContent =
          "Aucune activité Garmin trouvée sur la période choisie. " +
          "Un export Garmin doit d’abord être importé dans Atlas.";
        return;
      }
      renderConnectionSummary(config, activities, wellnessCount);
      connectionWizard.hidden = true;
    } catch (error) {
      console.error(error);
      connectionSummary.hidden = true;
      syncStatus.textContent =
        "Aucune donnée Garmin importée n’a été trouvée. " +
        "Le prototype local nécessite encore un export Garmin préalable.";
      connectionWizard.hidden = false;
      connectionWizard.innerHTML = `
        <div class="sensor-wizard-message is-warning">
          <span>GARMIN · DONNÉES ABSENTES</span>
          <h3>Préparer le premier import</h3>
          <p>La connexion en ligne Garmin n’est pas encore activée dans ce prototype.
          Exportez vos données Garmin, puis utilisez l’import Atlas avant de relancer cette vérification.</p>
          <button type="button" data-provider-retry="garmin">Réessayer la détection</button>
        </div>
      `;
    }
  }

  const PROVIDER_CONNECTORS = {
    "health-connect": {
      method: "Permissions natives Android",
      availability: "Application Android Atlas requise",
      wellness: true
    },
    polar: {
      method: "OAuth 2.0 · Polar AccessLink",
      availability: "Identifiants d’application à configurer",
      wellness: true
    },
    suunto: {
      method: "OAuth 2.0 · Suunto Cloud API",
      availability: "Accès partenaire à configurer",
      wellness: true
    },
    coros: {
      method: "OAuth 2.0 · COROS API",
      availability: "Validation COROS et identifiants requis",
      wellness: true
    },
    strava: {
      method: "OAuth 2.0 · Strava API v3",
      availability: "API réservée aux abonnés Strava",
      wellness: false
    }
  };

  async function renderStravaWizard(providerName = "Strava") {
    connectionWizard.hidden = false;
    connectionWizard.innerHTML = `
      <div class="sensor-wizard-message">
        <span>STRAVA · VÉRIFICATION</span>
        <h3>Connexion à Strava</h3>
        <p>Atlas vérifie la configuration du connecteur…</p>
      </div>
    `;

    try {
      const response = await fetch(
        `/api/atlas/strava/status?v=${Date.now()}`,
        { cache: "no-store" }
      );
      const status = await response.json();
      if (!response.ok || !status.ok) {
        throw new Error(status.error || "État Strava indisponible.");
      }

      if (!status.configured) {
        connectionWizard.innerHTML = `
          <div class="sensor-wizard-message">
            <span>STRAVA · API PAYANTE</span>
            <h3>Connexion non recommandée pour votre compte gratuit</h3>
            <p>Strava réserve actuellement la création d’une application API
            à ses abonnés. Atlas ne vous demande pas de souscrire un abonnement :
            Health Connect reste la source gratuite principale pour les
            activités et la récupération.</p>
            <small>Le connecteur Strava est conservé en sommeil si les
            conditions d’accès évoluent ultérieurement.</small>
          </div>
        `;
        syncStatus.textContent =
          "Strava · API réservée aux abonnés ; utilisez Health Connect.";
        return;
      }

      if (!status.connected) {
        connectionWizard.innerHTML = `
          <div class="sensor-wizard-message">
            <span>STRAVA · AUTORISATION</span>
            <h3>Autoriser Atlas à lire mes activités</h3>
            <p>Strava complétera Health Connect avec le GPS, le dénivelé,
            les tours, la pente, la cadence, la puissance et les flux
            chronologiques disponibles.</p>
            <button type="button" data-strava-connect>
              Connecter mon compte Strava
            </button>
          </div>
        `;
        syncStatus.textContent =
          "Strava configuré · autorisation personnelle nécessaire.";
        return;
      }

      const athleteName = [
        status.athlete?.firstname,
        status.athlete?.lastname
      ].filter(Boolean).join(" ");
      connectionWizard.innerHTML = `
        <div class="sensor-wizard-message">
          <span>STRAVA · CONNECTÉ</span>
          <h3>${athleteName || providerName} est prêt</h3>
          <p>Health Connect reste prioritaire. Strava complète les champs
          absents et les séries plus détaillées, sans créer de doublon.</p>
          <label class="sensor-history-choice">
            <span>Première synchronisation</span>
            <select data-strava-history>
              <option value="recent">Activités récentes</option>
              <option value="all">Importer aussi l’historique</option>
            </select>
          </label>
          <button type="button" data-strava-sync>
            Synchroniser Strava avec Atlas
          </button>
        </div>
      `;
      document.querySelector('[data-provider="strava"]')
        ?.classList.add("connected");
      syncStatus.textContent = "Strava connecté · prêt à synchroniser.";
    } catch (error) {
      connectionWizard.innerHTML = `
        <div class="sensor-wizard-message error">
          <h3>Connexion Strava indisponible</h3>
          <p>${error.message}</p>
        </div>
      `;
      syncStatus.textContent = "Strava · vérification impossible.";
    }
  }

  async function synchronizeStrava() {
    const button = connectionWizard.querySelector("[data-strava-sync]");
    const fullHistory = connectionWizard
      .querySelector("[data-strava-history]")?.value === "all";
    if (button) {
      button.disabled = true;
      button.textContent = "Synchronisation en cours…";
    }
    syncStatus.textContent =
      "Strava · récupération et fusion avec Health Connect…";
    try {
      const response = await fetch("/api/atlas/strava/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ full_history: fullHistory })
      });
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error || "Synchronisation Strava impossible.");
      }
      syncStatus.textContent =
        `Strava synchronisé · ${result.received} activité(s) reçue(s), ` +
        `${result.detailed} détaillée(s), ${result.total} activité(s) Atlas.`;
      if (button) button.textContent = "Synchronisation terminée";
    } catch (error) {
      syncStatus.textContent = `Strava · ${error.message}`;
      if (button) {
        button.disabled = false;
        button.textContent = "Réessayer la synchronisation";
      }
    }
  }

  function openProviderWizard(button) {
    const provider = button.dataset.provider;
    const providerName =
      button.querySelector("strong")?.textContent || "Source de données";
    syncProviderButtons.forEach(item => item.classList.remove("selected"));
    button.classList.add("selected");
    connectionWizard.hidden = false;

    if (provider === "manual") {
      connectionWizard.innerHTML = `
        <form class="sensor-consent-form" id="manualSensorForm">
          <header><span>SANS MONTRE CONNECTÉE</span><h3>Construire mon profil manuellement</h3></header>
          <p>Atlas peut créer un programme à partir de votre âge, de vos objectifs,
          de vos chronos et, si vous les connaissez, de votre FC maximale, VMA,
          VO₂max, SV1 et SV2. Une montre pourra être ajoutée plus tard.</p>
          <label><input type="checkbox" name="manualConsent" required>
            <span><strong>J’accepte la saisie de mes données sportives</strong>
            <small>Ces informations serviront uniquement à personnaliser Atlas.</small></span>
          </label>
          <button type="submit">Continuer vers mon profil</button>
        </form>
      `;
      syncStatus.textContent =
        "Mode sans montre sélectionné · profil et séances saisis manuellement.";
      return;
    }

    if (provider === "strava") {
      renderStravaWizard(providerName);
      return;
    }

    if (provider !== "garmin") {
      const connector = PROVIDER_CONNECTORS[provider];
      connectionWizard.innerHTML = `
        <form class="sensor-consent-form external-provider-form"
          id="externalProviderConsentForm" data-provider="${provider}"
          data-provider-name="${providerName}">
          <header><span>${providerName.toUpperCase()} · PARCOURS PRÉPARÉ</span>
            <h3>Autoriser les données à synchroniser</h3></header>
          <div class="connector-readiness">
            <span>Méthode prévue</span><strong>${connector.method}</strong>
            <small>${connector.availability}</small>
          </div>
          <label><input type="checkbox" name="activities" required>
            <span><strong>Activités sportives</strong>
            <small>Distance, durée, allure, fréquence cardiaque, dénivelé et tours.</small></span>
          </label>
          <label><input type="checkbox" name="wellness"
            ${connector.wellness ? "checked" : "disabled"}>
            <span><strong>Physiologie et récupération</strong>
            <small>${connector.wellness
              ? "Sommeil, VFC, stress et fréquence cardiaque de repos selon les données proposées."
              : "Cette source ne fournit pas ce niveau de données à Atlas."}</small></span>
          </label>
          <label class="sensor-history-choice"><span>Période souhaitée</span>
            <select name="history">
              <option value="3">3 derniers mois</option>
              <option value="12" selected>12 derniers mois</option>
              <option value="all">Tout l’historique autorisé</option>
            </select>
          </label>
          <p>Atlas enregistrera ces préférences. La connexion deviendra active
          dès que les identifiants développeur du fournisseur seront configurés.</p>
          <button type="submit">Enregistrer cette configuration</button>
        </form>
      `;
      syncStatus.textContent =
        `${providerName} sélectionné · ${connector.availability}.`;
      return;
    }

    connectionWizard.innerHTML = `
      <form class="sensor-consent-form" id="garminConsentForm">
        <header><span>GARMIN · ÉTAPE 2 SUR 3</span><h3>Autoriser l’analyse des données disponibles</h3></header>
        <label><input type="checkbox" name="activities" required>
          <span><strong>Activités sportives</strong><small>Distance, durée, allure, FC, dénivelé et appareil.</small></span>
        </label>
        <label><input type="checkbox" name="wellness" checked>
          <span><strong>Physiologie et récupération</strong><small>Sommeil, VFC, stress et fréquence cardiaque de repos.</small></span>
        </label>
        <label class="sensor-history-choice"><span>Période à prendre en compte</span>
          <select name="history">
            <option value="3">3 derniers mois</option>
            <option value="12" selected>12 derniers mois</option>
            <option value="all">Tout l’historique disponible</option>
          </select>
        </label>
        <p>Atlas utilise les fichiers Garmin FIT déjà importés et les archives
        Wellness disponibles. Atlas Connect complète automatiquement avec les
        mesures publiées par Garmin dans Santé Connect ; selon Garmin, la VFC
        peut ne pas y être transmise.</p>
        <button type="submit">Analyser les données disponibles</button>
      </form>
    `;
  }

  syncProviderButtons.forEach(button => {
    button.addEventListener("click", () => openProviderWizard(button));
  });

  connectionWizard.addEventListener("submit", event => {
    const formElement = event.target;
    if (![
      "garminConsentForm",
      "externalProviderConsentForm",
      "manualSensorForm"
    ].includes(formElement.id)) return;
    event.preventDefault();
    const form = new FormData(formElement);

    if (formElement.id === "manualSensorForm") {
      localStorage.setItem(SENSOR_CONNECTION_KEY, JSON.stringify({
        provider: "manual",
        updated_at: new Date().toISOString()
      }));
      localStorage.setItem(SENSOR_SETUP_KEY, "true");
      renderManualConnectionSummary();
      window.dispatchEvent(new CustomEvent(
        "atlas:coach-section-request",
        { detail: { section: "profile" } }
      ));
      return;
    }

    const config = {
      provider: formElement.dataset.provider || "garmin",
      provider_name: formElement.dataset.providerName || "Garmin",
      activities: form.get("activities") === "on",
      wellness: form.get("wellness") === "on",
      history: form.get("history") || "12",
      updated_at: new Date().toISOString()
    };

    if (config.provider === "garmin") {
      if (config.activities) synchronizeGarmin(config);
      return;
    }

    localStorage.setItem(
      "atlasCoachPendingSensorConnection",
      JSON.stringify(config)
    );
    const connector = PROVIDER_CONNECTORS[config.provider];
    connectionWizard.innerHTML = `
      <div class="sensor-wizard-message">
        <span>${config.provider_name.toUpperCase()} · CONFIGURATION ENREGISTRÉE</span>
        <h3>Connecteur prêt à recevoir ses identifiants</h3>
        <p>${connector.availability}. Atlas conservera le choix de la période et
        des catégories de données, mais aucune source ne sera marquée connectée
        avant une authentification réelle.</p>
      </div>
    `;
    syncStatus.textContent =
      `${config.provider_name} · configuration préparée, authentification en attente.`;
  });

  connectionWizard.addEventListener("click", event => {
    if (event.target.closest("[data-strava-connect]")) {
      window.location.href = "/api/atlas/strava/connect";
      return;
    }
    if (event.target.closest("[data-strava-sync]")) {
      synchronizeStrava();
      return;
    }
    if (event.target.closest('[data-provider-retry="garmin"]')) {
      openProviderWizard(
        document.querySelector('[data-provider="garmin"]')
      );
    }
  });

  connectionSummary.addEventListener("click", event => {
    const stored = JSON.parse(
      localStorage.getItem(SENSOR_CONNECTION_KEY) || "null"
    );
    if (event.target.closest("[data-sensor-resync]") && stored) {
      synchronizeGarmin(stored);
    }
    if (event.target.closest("[data-sensor-manage]")) {
      openProviderWizard(
        document.querySelector('[data-provider="garmin"]')
      );
    }
  });

  try {
    const storedConnection = JSON.parse(
      localStorage.getItem(SENSOR_CONNECTION_KEY) || "null"
    );
    setSensorOnboardingComplete(
      localStorage.getItem(SENSOR_SETUP_KEY) === "true" ||
      Boolean(storedConnection) ||
      Boolean(localStorage.getItem("atlasRunningProfile"))
    );
    if (storedConnection?.provider === "garmin") {
      synchronizeGarmin(storedConnection);
    } else if (storedConnection?.provider === "manual") {
      renderManualConnectionSummary();
    }
  } catch {
    localStorage.removeItem(SENSOR_CONNECTION_KEY);
    localStorage.removeItem(SENSOR_SETUP_KEY);
    setSensorOnboardingComplete(false);
  }

  if (new URLSearchParams(window.location.search).get("strava") === "connected") {
    const stravaButton = document.querySelector('[data-provider="strava"]');
    if (stravaButton) {
      stravaButton.classList.add("selected", "connected");
      renderStravaWizard("Strava");
    }
    window.history.replaceState(
      {},
      "",
      window.location.pathname + window.location.hash
    );
  }

  window.addEventListener("atlas:athlete-profile-loaded", () => {
    setSensorOnboardingComplete(true);
  });
})();

/* ████████████████████████████████████████████████████████████
   NAVIGATION ATLAS COACH
   ████████████████████████████████████████████████████████████ */

(() => {
  const navigation = document.querySelector(".coach-navigation");

  if (!navigation) {
    return;
  }

  const buttons = [
    ...navigation.querySelectorAll(".coach-navigation-button")
  ];

  const analysisPanel = document.getElementById("syncPanel");
  const trainingPanel = document.querySelector(".setup-panel");
  const physiologyPanel = document.getElementById("physiologyPanel");

  const status = document.createElement("p");
  status.className = "coach-navigation-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  navigation.insertAdjacentElement("afterend", status);

  function setActiveButton(activeButton) {
    buttons.forEach((button) => {
      const isActive = button === activeButton;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function scrollToPanel(panel) {
    if (!panel) {
      return;
    }

    const headerOffset = 92;
    const panelTop =
      panel.getBoundingClientRect().top +
      window.scrollY -
      headerOffset;

    window.scrollTo({
      top: panelTop,
      behavior: "smooth"
    });
  }

  function showStatus(message) {
    status.textContent = message;
    status.classList.add("visible");

    window.clearTimeout(showStatus.timeoutId);

    showStatus.timeoutId = window.setTimeout(() => {
      status.classList.remove("visible");
    }, 4200);
  }

  buttons.forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.classList.contains("active"))
    );

    button.addEventListener("click", () => {
      const space = button.dataset.coachSpace;

      setActiveButton(button);

        const sectionBySpace = {
          analysis: "sensors",
          training: "plan",
          competitions: "deadline",
          performance: "profile"
        };
        const statusBySpace = {
          analysis: "Espace Analyse : données, capteurs et activités.",
          training: "Espace Entraînement : plan personnalisé.",
          competitions: "Espace Compétitions : prochaine échéance et objectif.",
          performance: "Espace Performance : profil et zones personnelles."
        };
        const requestedSection = sectionBySpace[space];

        if (requestedSection) {
          window.dispatchEvent(
            new CustomEvent(
              "atlas:coach-section-request",
              { detail: { section: requestedSection } }
            )
          );
          showStatus(statusBySpace[space]);
          return;
        }

      if (space === "analysis") {
        scrollToPanel(analysisPanel);
        showStatus("Espace Analyse : données, capteurs et activités.");
        return;
      }

      if (space === "training") {
        scrollToPanel(trainingPanel);
        showStatus(
          "Espace Entraînement : profil, zones et plan personnalisé."
        );
        return;
      }

      if (space === "competitions") {
        scrollToPanel(document.getElementById("competitionPanel"));
        showStatus("Espace Compétitions : prochaine échéance et objectif.");
        return;
      }

      if (space === "performance") {
        if (physiologyPanel && !physiologyPanel.hidden) {
          scrollToPanel(physiologyPanel);
          showStatus(
            "Espace Performance : carte physiologique et zones personnelles."
          );
          return;
        }

        scrollToPanel(trainingPanel);
        showStatus(
          "Calculez d’abord vos zones pour afficher l’espace Performance."
        );
      }
    });
  });
})();

/* ████████████████████████████████████████████████████████████
   FIN NAVIGATION ATLAS COACH
   ████████████████████████████████████████████████████████████ */

/* GESTION MULTI-OBJECTIFS ATLAS COACH */
(() => {
  const fields = {
    id: document.getElementById("competitionId"),
    name: document.getElementById("competitionName"),
    type: document.getElementById("competitionType"),
    date: document.getElementById("competitionDate"),
    targetTime: document.getElementById("competitionTargetTime"),
    priority: document.getElementById("competitionPriority"),
    courseProfile: document.getElementById("competitionCourseProfile")
  };
  const cards = document.getElementById("competitionCards");
  const empty = document.getElementById("competitionEmpty");
  const editor = document.getElementById("competitionEditor");
  const editorTitle = document.getElementById("competitionEditorTitle");
  const addButton = document.getElementById("addCompetitionButton");
  const saveButton = document.getElementById("saveCompetitionButton");
  const cancelButtons = [
    document.getElementById("cancelCompetitionButton"),
    document.getElementById("cancelCompetitionAction")
  ].filter(Boolean);
  const saveStatus = document.getElementById("competitionSaveStatus");
  const trainingType = document.getElementById("eventType");
  const trainingDate = document.getElementById("eventDate");
  const storageKey = "atlasCoachCompetitions";
  const legacyKey = "atlasCoachCompetition";
  const priorityLabels = {
    a: "A · Objectif principal",
    b: "B · Objectif intermédiaire",
    c: "C · Course préparatoire"
  };
  const typeLabels = {
    "5k": "5 km", "10k": "10 km", half: "Semi-marathon",
    marathon: "Marathon", "trail-short": "Trail court",
    "trail-long": "Trail long", ultra: "Ultra-trail"
  };
  let competitions = [];

  if (!cards || !editor || !saveButton) return;

  const escapeHtml = value => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  function loadCompetitions() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
      if (Array.isArray(saved)) return saved;
      const legacy = JSON.parse(localStorage.getItem(legacyKey) || "null");
      if (legacy?.name && legacy?.date) {
        const migrated = [{
          ...legacy,
          id: `objective-${Date.now()}`,
          priority: legacy.priority || "a"
        }];
        localStorage.setItem(storageKey, JSON.stringify(migrated));
        return migrated;
      }
    } catch (error) {
      console.warn("Objectifs Atlas illisibles.", error);
    }
    return [];
  }

  function synchronizePrimaryObjective() {
    const primary = competitions.find(item => item.priority === "a")
      || competitions[0];
    if (!primary) return;
    if (trainingType) trainingType.value = primary.type || "10k";
    if (trainingDate) trainingDate.value = primary.date || "";
    try {
      const profile = JSON.parse(
        localStorage.getItem("atlasRunningProfile") || "{}"
      );
      profile.eventType = primary.type;
      profile.eventDate = primary.date;
      profile.primaryObjectiveId = primary.id;
      localStorage.setItem("atlasRunningProfile", JSON.stringify(profile));
    } catch (error) {
      console.warn("Profil Atlas non synchronisé avec l’objectif.", error);
    }
  }

  function persist() {
    localStorage.setItem(storageKey, JSON.stringify(competitions));
    fetch("/api/atlas-user/objectives", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objectives: competitions })
    }).catch(error => console.debug(
      "Objectifs conservés localement ; serveur indisponible.", error
    ));
    synchronizePrimaryObjective();
  }

  async function restoreServerObjectives() {
    const local = loadCompetitions();
    competitions = local;
    render();
    try {
      const response = await fetch("/api/atlas-user/objectives", {
        cache: "no-store"
      });
      if (!response.ok) return;
      const payload = await response.json();
      const server = Array.isArray(payload.objectives)
        ? payload.objectives : [];
      if (!payload.persisted && local.length) {
        competitions = local;
        persist();
      } else if (server.length) {
        competitions = server;
        localStorage.setItem(storageKey, JSON.stringify(competitions));
        render();
      } else if (local.length) {
        persist();
      }
    } catch (error) {
      console.debug("Objectifs Atlas serveur indisponibles.", error);
    }
  }

  function render() {
    const ordered = [...competitions].sort((a, b) => {
      if (a.priority !== b.priority) return a.priority.localeCompare(b.priority);
      return String(a.date).localeCompare(String(b.date));
    });
    empty.hidden = ordered.length > 0;
    cards.innerHTML = ordered.map(item => {
      const date = item.date
        ? new Date(`${item.date}T12:00:00`).toLocaleDateString(
            "fr-FR", { day: "numeric", month: "long", year: "numeric" }
          )
        : "Date à définir";
      return `
        <article class="competition-objective-card priority-${item.priority}">
          <header>
            <span>${priorityLabels[item.priority] || priorityLabels.c}</span>
            <strong>${escapeHtml(date)}</strong>
          </header>
          <h3>${escapeHtml(item.name)}</h3>
          <p>${escapeHtml(typeLabels[item.type] || item.type)}
            ${item.targetTime ? ` · objectif ${escapeHtml(item.targetTime)}` : ""}
          </p>
          <footer>
            <button type="button" data-objective-edit="${item.id}">Modifier</button>
            <button type="button" data-objective-delete="${item.id}">Supprimer</button>
          </footer>
        </article>
      `;
    }).join("");
    synchronizePrimaryObjective();
  }

  function resetForm() {
    fields.id.value = "";
    fields.name.value = "";
    fields.type.value = "half";
    fields.date.value = "";
    fields.targetTime.value = "";
    fields.priority.value = competitions.some(item => item.priority === "a")
      ? "b" : "a";
    fields.courseProfile.value = "flat";
    saveStatus.textContent = "";
  }

  function openEditor(objective = null) {
    editor.hidden = false;
    if (objective) {
      Object.entries(fields).forEach(([key, field]) => {
        if (field && objective[key] != null) field.value = objective[key];
      });
      editorTitle.textContent = "Modifier cet objectif";
    } else {
      resetForm();
      editorTitle.textContent = "Ajouter une échéance";
    }
    editor.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function closeEditor() {
    editor.hidden = true;
    saveStatus.textContent = "";
  }

  addButton?.addEventListener("click", () => openEditor());
  cancelButtons.forEach(button =>
    button.addEventListener("click", closeEditor)
  );

  saveButton.addEventListener("click", () => {
    const objective = Object.fromEntries(
      Object.entries(fields).map(([key, field]) => [
        key, field ? field.value.trim() : ""
      ])
    );
    if (!objective.name || !objective.date) {
      saveStatus.textContent = "Indiquez le nom et la date de l’objectif.";
      return;
    }
    if (new Date(`${objective.date}T12:00:00`) <= new Date()) {
      saveStatus.textContent = "Choisissez une échéance future.";
      return;
    }
    objective.id = objective.id || `objective-${Date.now()}`;
    if (objective.priority === "a") {
      competitions = competitions.map(item => (
        item.id !== objective.id && item.priority === "a"
          ? { ...item, priority: "b" }
          : item
      ));
    }
    const index = competitions.findIndex(item => item.id === objective.id);
    if (index >= 0) competitions[index] = objective;
    else competitions.push(objective);
    persist();
    render();
    closeEditor();
  });

  cards.addEventListener("click", event => {
    const edit = event.target.closest("[data-objective-edit]");
    const remove = event.target.closest("[data-objective-delete]");
    if (edit) {
      openEditor(
        competitions.find(item => item.id === edit.dataset.objectiveEdit)
      );
    }
    if (remove) {
      competitions = competitions.filter(
        item => item.id !== remove.dataset.objectiveDelete
      );
      if (
        competitions.length &&
        !competitions.some(item => item.priority === "a")
      ) {
        competitions[0].priority = "a";
      }
      persist();
      render();
    }
  });

  restoreServerObjectives();
})();
/* FIN GESTION MULTI-OBJECTIFS ATLAS COACH */

/* PROGRAMME RÉEL ATLAS RESEARCH */
(() => {
  const planPanel = document.getElementById("planPanel");
  const overview = document.getElementById("planOverview");
  const calendar = document.getElementById("trainingCalendar");

  if (!planPanel || !overview || !calendar) {
    return;
  }

  const PHASE_LABELS = {
    base: "Base aérobie",
    development: "Développement",
    specific: "Spécifique semi-marathon",
    taper: "Affûtage",
    race_week: "Semaine de course",
    recovery: "Récupération"
  };

  const WORKOUT_LABELS = {
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

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function parseLocalDate(value) {
    return new Date(`${value}T12:00:00`);
  }

  function formatDate(value, options = {}) {
    if (!value) return "—";

    return new Intl.DateTimeFormat("fr-FR", {
      day: "numeric",
      month: "short",
      year: options.year ? "numeric" : undefined
    }).format(parseLocalDate(value));
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

  function formatTargetTime(minutes) {
    const total = Number(minutes);

    if (!Number.isFinite(total)) return "Objectif libre";

    const hours = Math.floor(total / 60);
    const remaining = total % 60;

    return `${hours} h ${String(remaining).padStart(2, "0")}`;
  }

  function formatPace(secondsPerKm) {
    const total = Number(secondsPerKm);

    if (!Number.isFinite(total)) return "—";

    const minutes = Math.floor(total / 60);
    const seconds = Math.round(total % 60);

    return `${minutes}:${String(seconds).padStart(2, "0")}/km`;
  }

  function blockDuration(block) {
    const repetitions = Number(block.repetitions) || 1;
    const parts = [];

    if (block.duration_minutes != null) {
      parts.push(
        `${repetitions > 1 ? `${repetitions} × ` : ""}` +
        `${Number(block.duration_minutes).toLocaleString("fr-FR")} min`
      );
    } else if (block.distance_meters != null) {
      parts.push(
        `${repetitions > 1 ? `${repetitions} × ` : ""}` +
        `${Number(block.distance_meters).toLocaleString("fr-FR")} m`
      );
    }

    if (block.recovery_minutes != null) {
      parts.push(
        `récup. ${Number(block.recovery_minutes).toLocaleString("fr-FR")} min`
      );
    }

    return parts.join(" · ") || "Durée individualisée";
  }

  function blockTarget(block) {
    const target = block.target || {};
    const parts = [];

    if (target.zone) {
      parts.push(`Zone ${target.zone}`);
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

      parts.push(
        minimum === maximum
          ? `${minimum} km/h`
          : `${minimum}–${maximum} km/h`
      );
    }

    if (target.pace_min_per_km) {
      parts.push(`${target.pace_min_per_km}/km`);
    }

    if (target.heart_rate_min_bpm != null) {
      parts.push(
        `${target.heart_rate_min_bpm}–` +
        `${target.heart_rate_max_bpm} bpm`
      );
    }

    if (target.rpe_0_10 != null) {
      parts.push(`RPE ${target.rpe_0_10}/10`);
    }

    if (target.gradient_min_percent != null) {
      parts.push(
        `pente ${target.gradient_min_percent}–` +
        `${target.gradient_max_percent} %`
      );
    }

    if (
      target.intensity_pattern &&
      target.intensity_pattern !== "constant"
    ) {
      parts.push(
        `profil ${target.intensity_pattern.replaceAll("_", " ")}`
      );
    }

    return parts.join(" · ") || "Cible guidée par les sensations";
  }

  function evidenceValue(workout) {
    const note = (workout.coach_notes || []).find(
      item => item.startsWith("Confiance scientifique")
    );

    return note ? note.split(":").slice(1).join(":").trim() : null;
  }

  function suitabilityValue(workout) {
    const note = (workout.coach_notes || []).find(
      item => item.startsWith("Adéquation individuelle")
    );

    return note ? note.split(":").slice(1).join(":").trim() : null;
  }

  function renderLoad(workout) {
    const response = workout.expected_response;

    if (!response) return "";

    return `
      <div class="atlas-load-grid">
        <span>
          <small>Charge physiologique</small>
          <strong>${escapeHtml(response.physiological_load_0_100)}/100</strong>
        </span>
        <span>
          <small>Charge biomécanique</small>
          <strong>${escapeHtml(response.biomechanical_load_0_100)}/100</strong>
        </span>
        <span>
          <small>Récupération estimée</small>
          <strong>
            ${escapeHtml(response.recovery_min_hours)}–${escapeHtml(response.recovery_max_hours)} h
          </strong>
        </span>
      </div>
    `;
  }

  function renderWorkout(workout) {
    const isResearch = RESEARCH_TYPES.has(
      workout.workout_type
    );
    const evidence = evidenceValue(workout);
    const suitability = suitabilityValue(workout);

    return `
      <article class="session-card atlas-session ${isResearch ? "research-session" : ""}">
        <div class="atlas-session-head">
          <div>
            <div class="session-date">
              ${escapeHtml(formatDate(workout.workout_date, { year: true }))}
            </div>
            <h3>${escapeHtml(workout.title)}</h3>
          </div>

          <div class="atlas-session-badges">
            <span class="workout-type-badge">
              ${escapeHtml(
                WORKOUT_LABELS[workout.workout_type] ||
                workout.workout_type
              )}
            </span>
            ${isResearch ? `
              <span class="research-badge">Atlas Research</span>
            ` : ""}
          </div>
        </div>

        <div class="session-objective">
          ${escapeHtml(workout.objective)}
        </div>

        <div class="atlas-session-meta">
          <strong>${escapeHtml(formatMinutes(workout.planned_duration_minutes))}</strong>
          ${evidence ? `<span>Preuve ${escapeHtml(evidence)}</span>` : ""}
          ${suitability ? `<span>Adéquation ${escapeHtml(suitability)}</span>` : ""}
        </div>

        ${renderLoad(workout)}

        <div class="session-blocks">
          ${(workout.blocks || []).map(block => `
            <div class="session-block atlas-rich-block">
              <strong>${escapeHtml(block.name)}</strong>
              <span>${escapeHtml(blockDuration(block))}</span>
              <small>${escapeHtml(blockTarget(block))}</small>
              ${block.instructions ? `
                <p>${escapeHtml(block.instructions)}</p>
              ` : ""}
            </div>
          `).join("")}
        </div>

        ${(workout.expected_response?.sensitive_structures || []).length ? `
          <div class="sensitive-structures">
            <span>Vigilance biomécanique</span>
            ${workout.expected_response.sensitive_structures
              .map(item => `<i>${escapeHtml(item)}</i>`)
              .join("")}
          </div>
        ` : ""}
      </article>
    `;
  }

  function isCurrentWeek(week) {
    const today = new Date();
    today.setHours(12, 0, 0, 0);

    return (
      today >= parseLocalDate(week.start_date) &&
      today <= parseLocalDate(week.end_date)
    );
  }

  function setProgramNumberField(id, value) {
    const field = document.getElementById(id);
    const numericValue = Number(value);

    if (
      field &&
      value !== null &&
      value !== "" &&
      Number.isFinite(numericValue)
    ) {
      field.value = String(numericValue);
    }
  }

  function renderRealProgram(program) {
    const researchCount = program.weeks.reduce(
      (total, week) => total + week.workouts.filter(
        workout => RESEARCH_TYPES.has(workout.workout_type)
      ).length,
      0
    );
    const targetPace = program.goal.target_pace_seconds_per_km;

    overview.innerHTML = `
      <article>
        <span>Objectif</span>
        <strong>${escapeHtml(program.goal.name)}</strong>
      </article>
      <article>
        <span>Échéance</span>
        <strong>${escapeHtml(formatDate(program.goal.event_date, { year: true }))}</strong>
      </article>
      <article>
        <span>Temps cible</span>
        <strong>${escapeHtml(formatTargetTime(program.goal.target_time_minutes))}</strong>
        <small>${escapeHtml(formatPace(targetPace))}</small>
      </article>
      <article>
        <span>Programme</span>
        <strong>${escapeHtml(program.weeks.length)} semaines</strong>
        <small>${escapeHtml(program.total_running_workouts)} courses · ${researchCount} Research</small>
      </article>
    `;

      if (!document.body.classList.contains("has-premium-training-calendar")) {
    calendar.innerHTML = `
      <div class="atlas-program-banner">
        <div>
          <span>ATLAS COACH × ATLAS RESEARCH</span>
          <strong>Programme adaptatif personnel activé</strong>
          <small>
            Historique longitudinal, seuil individuel, VMA,
            tolérance biomécanique et niveau de preuve combinés.
          </small>
        </div>
        <i>${escapeHtml(program.athlete_id)}</i>
      </div>

      ${(program.warnings || []).length ? `
        <div class="atlas-program-warnings">
          ${program.warnings.map(
            warning => `<p>⚠ ${escapeHtml(warning)}</p>`
          ).join("")}
        </div>
      ` : ""}

      ${program.weeks.map(week => `
        <details
          class="training-week atlas-real-week phase-${escapeHtml(week.phase)}"
          ${isCurrentWeek(week) || week.week_number === 1 ? "open" : ""}
        >
          <summary class="week-header">
            <div>
              <strong>
                Semaine ${escapeHtml(week.week_number)}
                · ${escapeHtml(PHASE_LABELS[week.phase] || week.phase)}
              </strong>
              <small>${escapeHtml(week.objective)}</small>
            </div>
            <span>
              ${escapeHtml(formatDate(week.start_date))}
              →
              ${escapeHtml(formatDate(week.end_date))}
              · ${escapeHtml(formatMinutes(week.target_duration_minutes))}
            </span>
          </summary>

          <div class="session-list">
            ${(week.workouts || []).map(renderWorkout).join("")}
          </div>
        </details>
      `).join("")}
    `;
      }

    const heading = planPanel.querySelector(
      ".section-title h1"
    );

    if (heading) {
      heading.textContent =
        "Votre programme adaptatif jusqu’au semi-marathon";
    }

    planPanel.hidden = false;
    hydrateGoalFields(program);

    const snapshot = program.athlete_snapshot || {};
    setProgramNumberField("vo2MaxProfile", snapshot.vo2_max);
    setProgramNumberField(
      "hrRest",
      snapshot.resting_heart_rate_bpm
    );
  }

  function hydrateGoalFields(program) {
    const distance = Number(program.goal.distance_km);
    const type = (
      distance >= 20 && distance <= 22
        ? "half"
        : distance >= 41
          ? "marathon"
          : distance >= 9 && distance <= 11
            ? "10k"
            : "5k"
    );
    const targetMinutes = Number(
      program.goal.target_time_minutes
    );
    const targetHours = Math.floor(targetMinutes / 60);
    const targetRemainingMinutes = targetMinutes % 60;
    const targetTime = Number.isFinite(targetMinutes)
      ? `${String(targetHours).padStart(2, "0")}:` +
        `${String(targetRemainingMinutes).padStart(2, "0")}:00`
      : "";

    const values = {
      eventType: type,
      eventDate: program.goal.event_date,
      competitionName: program.goal.name,
      competitionType: type,
      competitionDate: program.goal.event_date,
      competitionTargetTime: targetTime,
      daysPerWeek: String(
        program.settings.running_sessions_per_week
      )
    };

    Object.entries(values).forEach(([id, value]) => {
      const field = document.getElementById(id);

      if (field && value) {
        field.value = value;
      }
    });
  }

  async function loadRealProgram() {
    const candidates = [
      window.ATLAS_TRAINING_PROGRAM_URL,
      "/api/atlas-coach/program"
    ].filter(Boolean);

    for (const source of candidates) {
      try {
        const response = await fetch(source, {
          cache: "no-store"
        });

        if (!response.ok) continue;

        const program = await response.json();

        if (
          !program ||
          !Array.isArray(program.weeks) ||
          !program.goal
        ) {
          continue;
        }

        renderRealProgram(program);
        window.ATLAS_ACTIVE_PROGRAM = program;
        window.dispatchEvent(new CustomEvent(
          "atlas:training-program-loaded",
          { detail: program }
        ));
        document.body.classList.add(
          "has-atlas-research-program"
        );
        return;
      } catch (error) {
        console.debug(
          "Programme Atlas Research indisponible.",
          source,
          error
        );
      }
    }
  }

  loadRealProgram();
})();
/* FIN PROGRAMME RÉEL ATLAS RESEARCH */
