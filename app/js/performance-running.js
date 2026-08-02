"use strict";

(() => {
  // ████████████████████████████████████████████████████████████
  // 🟦 PARTIE A — A01 — CONFIGURATION
  // ████████████████████████████████████████████████████████████

  const ZONES = [
    { id: 1, hr: [50, 60], vma: [55, 65], name: "Récupération", color: "#5aa8ff" },
    { id: 2, hr: [60, 70], vma: [65, 75], name: "Endurance fondamentale", color: "#51d892" },
    { id: 3, hr: [70, 80], vma: [75, 85], name: "Endurance active", color: "#e7d353" },
    { id: 4, hr: [80, 90], vma: [85, 95], name: "Seuil", color: "#ff9a4f" },
    { id: 5, hr: [90, 100], vma: [95, 105], name: "VMA / intensité", color: "#ff5d68" }
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
    printButton: document.getElementById("printButton")
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
      renderPlan(profile, zones, plan);

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
    document.querySelector("#syncStatus");  syncProviderButtons.forEach((button) => {
    button.addEventListener("click", () => {
      syncProviderButtons.forEach((item) =>
        item.classList.remove("connected")
      );

      button.classList.add("connected");

      const providerName =
        button.querySelector("strong")?.textContent ||
        "Source de données";

      syncStatus.textContent =
        `${providerName} sélectionné. La connexion sécurisée sera activée à l’étape suivante.`;
    });
  });})();