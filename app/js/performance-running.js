"use strict";

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
    daysPerWeek: document.getElementById("daysPerWeek"),
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

  function getInputs() {
    const eventDate = elements.eventDate.value
      ? new Date(`${elements.eventDate.value}T12:00:00`)
      : null;

    return {
      eventType: elements.eventType.value,
      eventDate,
      vma: Number(elements.vma.value),
      hrMax: Number(elements.hrMax.value),
      hrRest: Number(elements.hrRest.value),
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
    if (profile.thresholdSource === "measured") {
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
        label: "Seuils mesurés — confiance élevée"
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
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (!profile.eventDate || profile.eventDate <= today) {
        throw new Error("Choisissez une date d’événement située dans le futur.");
      }

      if (!Number.isFinite(profile.vma) || profile.vma < 6) {
        throw new Error("Renseignez une VMA valide.");
      }

      if (!Number.isFinite(profile.hrMax) || profile.hrMax < 120) {
        throw new Error("Renseignez une fréquence cardiaque maximale valide.");
      }

      if (profile.hrRest >= profile.hrMax) {
        throw new Error("La fréquence cardiaque de repos doit être inférieure à la FC maximale.");
      }

      const zones = buildZones(profile);
      const thresholds = determineThresholds(profile, zones);
      const plan = generatePlan(profile, zones);

      renderZones(zones, thresholds);
      window.dispatchEvent(new CustomEvent(
        "atlas:zones-updated",
        {
          detail: {
            zones,
            thresholds,
            profile: {
              vma: profile.vma,
              hrMax: profile.hrMax,
              hrRest: profile.hrRest,
              displayMode: profile.displayMode
            }
          }
        }
      ));
      // Le programme privé Atlas Research est rendu par
// atlas-training-calendar.js. Ne pas réinjecter l’ancien plan.

      elements.durationSummary.textContent = `${plan.totalWeeks} semaines`;
      elements.eventSummary.textContent =
        `${EVENT_LABELS[profile.eventType]} · ${formatShortDate(profile.eventDate)}`;

      elements.physiologyPanel.hidden = false;
      elements.planPanel.hidden = false;

      localStorage.setItem("atlasRunningProfile", JSON.stringify({
        eventType: profile.eventType,
        eventDate: elements.eventDate.value,
        vma: profile.vma,
        hrMax: profile.hrMax,
        hrRest: profile.hrRest,
        daysPerWeek: profile.daysPerWeek,
        displayMode: profile.displayMode,
        thresholdSource: profile.thresholdSource,
        thresholds
      }));

      elements.physiologyPanel.scrollIntoView({ behavior: "smooth", block: "start" });
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
      elements.thresholdSource.value === "measured";

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

  elements.thresholdSource.addEventListener(
    "change",
    syncMeasuredThresholdFields
  );

  elements.calculateButton.addEventListener("click", calculate);
  elements.printButton.addEventListener("click", () => window.print());

  setDefaultDate();
  syncMeasuredThresholdFields();
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

  syncProviderButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const provider = button.dataset.provider;
      const providerName =
        button.querySelector("strong")?.textContent ||
        "Source de données";

      syncProviderButtons.forEach((item) =>
        item.classList.remove("connected")
      );

      if (provider !== "garmin") {
        button.classList.add("connected");
        syncStatus.textContent =
          `${providerName} sélectionné. Ce connecteur sera activé prochainement.`;
        return;
      }

      syncStatus.textContent =
        "Import des activités Garmin en cours…";

      try {
        const activities = await loadGarminActivities();

        if (activities.length === 0) {
          button.classList.add("connected");
          syncStatus.textContent =
            "Garmin est connecté, mais aucune activité n’a été trouvée.";
          return;
        }

        const latestActivity = [...activities].sort(
          (first, second) =>
            new Date(second.start_time) -
            new Date(first.start_time)
        )[0];
              displayGarminActivity(latestActivity);
        const distanceKm = (
          Number(latestActivity.distance_meters || 0) / 1000
        ).toFixed(2);

        const averageHeartRate =
          latestActivity.average_heart_rate_bpm
            ? `${Math.round(
                latestActivity.average_heart_rate_bpm
              )} bpm`
            : "FC indisponible";

        const sampleCount =
          Array.isArray(latestActivity.samples)
            ? latestActivity.samples.length
            : 0;

        button.classList.add("connected");
        syncStatus.textContent =
          `Garmin connecté · ${activities.length} activité(s) · ` +
          `Dernière séance : ${distanceKm} km en ` +
          `${formatActivityDuration(
            latestActivity.duration_seconds
          )} · ${averageHeartRate} · ` +
          `${sampleCount} mesures`;
      } catch (error) {
        console.error(error);
        syncStatus.textContent =
          "Import Garmin impossible. Lancez d’abord la commande " +
          "py scripts\\import_garmin.py puis ouvrez ATLAS " +
          "avec un serveur local.";
      }
    });
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

/* GESTION DES COMPÉTITIONS ATLAS COACH */
(() => {
  const fields = {
    name: document.getElementById("competitionName"),
    type: document.getElementById("competitionType"),
    date: document.getElementById("competitionDate"),
    targetTime: document.getElementById("competitionTargetTime"),
    priority: document.getElementById("competitionPriority"),
    courseProfile: document.getElementById("competitionCourseProfile")
  };

  const saveButton = document.getElementById("saveCompetitionButton");
  const saveStatus = document.getElementById("competitionSaveStatus");
  const trainingType = document.getElementById("eventType");
  const trainingDate = document.getElementById("eventDate");
  const storageKey = "atlasCoachCompetition";

  if (!saveButton || !saveStatus) {
    return;
  }

  function applyCompetition(competition) {
    Object.entries(fields).forEach(([key, field]) => {
      if (field && competition[key] != null) {
        field.value = competition[key];
      }
    });

    if (trainingType && competition.type) {
      trainingType.value = competition.type;
    }

    if (trainingDate && competition.date) {
      trainingDate.value = competition.date;
    }
  }

  try {
    const savedCompetition = JSON.parse(
      localStorage.getItem(storageKey) || "null"
    );

    if (savedCompetition) {
      applyCompetition(savedCompetition);
      saveStatus.textContent = "Compétition enregistrée et restaurée.";
    }
  } catch (error) {
    console.warn("Compétition Atlas Coach illisible.", error);
  }

  saveButton.addEventListener("click", () => {
    const competition = Object.fromEntries(
      Object.entries(fields).map(([key, field]) => [
        key,
        field ? field.value.trim() : ""
      ])
    );

    if (!competition.name || !competition.date) {
      saveStatus.textContent =
        "Indiquez le nom et la date de la compétition.";
      return;
    }

    localStorage.setItem(storageKey, JSON.stringify(competition));
    applyCompetition(competition);
    saveStatus.textContent =
      "Compétition enregistrée et transmise au plan d’entraînement.";
  });
})();
/* FIN GESTION DES COMPÉTITIONS ATLAS COACH */

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
      "../atlas-data/private/training-program.json",
      "/atlas-data/private/training-program.json"
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
