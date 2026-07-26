
"use strict";

// ████████████████████████████████████████████████████████████
// 🟦 PARTIE A — ÉTAT ET SÉLECTEURS
// ████████████████████████████████████████████████████████████

(() => {
  const STORAGE_KEY = "atlasGarminImportV1";

  const elements = {
    files: document.getElementById("garminFiles"),
    chooseFilesButton: document.getElementById("chooseFilesButton"),
    dropZone: document.getElementById("dropZone"),
    loadDemoButton: document.getElementById("loadDemoButton"),
    exportAtlasButton: document.getElementById("exportAtlasButton"),
    clearDataButton: document.getElementById("clearDataButton"),
    importStatus: document.getElementById("importStatus"),
    fileResults: document.getElementById("fileResults"),
    engineStatus: document.getElementById("engineStatus"),

    summaryActivities: document.getElementById("summaryActivities"),
    summaryPeriod: document.getElementById("summaryPeriod"),
    summaryDistance: document.getElementById("summaryDistance"),
    summaryDuration: document.getElementById("summaryDuration"),
    summaryHeartRate: document.getElementById("summaryHeartRate"),

    metricVolume28: document.getElementById("metricVolume28"),
    metricVolumeTrend: document.getElementById("metricVolumeTrend"),
    metricLongest: document.getElementById("metricLongest"),
    metricLongestDate: document.getElementById("metricLongestDate"),
    metricMaxHeartRate: document.getElementById("metricMaxHeartRate"),
    metricAveragePace: document.getElementById("metricAveragePace"),
    metricPaceNote: document.getElementById("metricPaceNote"),

    volumeBar: document.getElementById("volumeBar"),
    longestBar: document.getElementById("longestBar"),
    heartRateBar: document.getElementById("heartRateBar"),
    paceBar: document.getElementById("paceBar"),

    weeksChart: document.getElementById("weeksChart"),
    activitiesTableBody: document.getElementById("activitiesTableBody"),
    activitiesCountLabel: document.getElementById("activitiesCountLabel"),
    analysisConfidence: document.getElementById("analysisConfidence"),
    brainImportText: document.getElementById("brainImportText"),
    recognitionList: document.getElementById("recognitionList")
  };

  let atlasData = loadStoredData() || createEmptyData();

  // ████████████████████████████████████████████████████████████
  // 🟩 PARTIE B — MODÈLE DE DONNÉES
  // ████████████████████████████████████████████████████████████

  function createEmptyData() {
    return {
      version: 1,
      source: "garmin-manual-export",
      importedAt: null,
      activities: [],
      wellness: [],
      files: []
    };
  }

  function loadStoredData() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      console.warn("Impossible de lire les données Atlas locales.", error);
      return null;
    }
  }

  function saveData() {
    atlasData.importedAt = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(atlasData));
  }

  // ████████████████████████████████████████████████████████████
  // 🟨 PARTIE C — UTILITAIRES DE PARSING
  // ████████████████████████████████████████████████████████████

  function normalizeHeader(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[()]/g, " ")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function detectDelimiter(text) {
    const firstLine = text.split(/\r?\n/, 1)[0] || "";
    const candidates = [",", ";", "\t"];
    let best = ",";
    let bestCount = -1;

    candidates.forEach(candidate => {
      const count = (firstLine.match(new RegExp(
        candidate === "\t" ? "\\t" : `\\${candidate}`,
        "g"
      )) || []).length;

      if (count > bestCount) {
        best = candidate;
        bestCount = count;
      }
    });

    return best;
  }

  function parseCSV(text) {
    const delimiter = detectDelimiter(text);
    const rows = [];
    let row = [];
    let value = "";
    let quoted = false;

    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      const next = text[index + 1];

      if (char === '"') {
        if (quoted && next === '"') {
          value += '"';
          index += 1;
        } else {
          quoted = !quoted;
        }
        continue;
      }

      if (char === delimiter && !quoted) {
        row.push(value.trim());
        value = "";
        continue;
      }

      if ((char === "\n" || char === "\r") && !quoted) {
        if (char === "\r" && next === "\n") {
          index += 1;
        }

        row.push(value.trim());
        value = "";

        if (row.some(cell => cell !== "")) {
          rows.push(row);
        }

        row = [];
        continue;
      }

      value += char;
    }

    row.push(value.trim());
    if (row.some(cell => cell !== "")) {
      rows.push(row);
    }

    return rows;
  }

  function toNumber(value) {
    if (value === null || value === undefined || value === "") {
      return null;
    }

    let cleaned = String(value)
      .replace(/\u00a0/g, " ")
      .replace(/[^\d,.\-]/g, "")
      .trim();

    if (!cleaned) return null;

    const lastComma = cleaned.lastIndexOf(",");
    const lastDot = cleaned.lastIndexOf(".");

    if (lastComma > lastDot) {
      cleaned = cleaned.replace(/\./g, "").replace(",", ".");
    } else if (lastDot > lastComma) {
      cleaned = cleaned.replace(/,/g, "");
    } else {
      cleaned = cleaned.replace(",", ".");
    }

    const result = Number(cleaned);
    return Number.isFinite(result) ? result : null;
  }

  function parseDurationSeconds(value) {
    if (!value) return null;

    const text = String(value).trim();

    if (/^\d+(?:[.,]\d+)?$/.test(text)) {
      const numeric = toNumber(text);
      return numeric !== null ? Math.round(numeric * 60) : null;
    }

    const parts = text.split(":").map(Number);
    if (parts.some(Number.isNaN)) return null;

    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }

    if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }

    return null;
  }

  function parseDate(value) {
    if (!value) return null;
    const text = String(value).trim();

    const direct = new Date(text);
    if (!Number.isNaN(direct.getTime())) {
      return direct.toISOString();
    }

    const french = text.match(
      /(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/
    );

    if (french) {
      const year = Number(french[3]) < 100
        ? 2000 + Number(french[3])
        : Number(french[3]);

      const date = new Date(
        year,
        Number(french[2]) - 1,
        Number(french[1]),
        Number(french[4] || 12),
        Number(french[5] || 0),
        Number(french[6] || 0)
      );

      return date.toISOString();
    }

    return null;
  }

  function findColumn(headers, aliases) {
    const normalizedAliases = aliases.map(normalizeHeader);

    for (let index = 0; index < headers.length; index += 1) {
      const header = normalizeHeader(headers[index]);

      if (normalizedAliases.includes(header)) {
        return index;
      }
    }

    for (let index = 0; index < headers.length; index += 1) {
      const header = normalizeHeader(headers[index]);

      if (normalizedAliases.some(alias =>
        header.includes(alias) || alias.includes(header)
      )) {
        return index;
      }
    }

    return -1;
  }

  const aliases = {
    date: [
      "date",
      "date de l activite",
      "activity date",
      "start time",
      "heure de debut"
    ],
    type: [
      "type d activite",
      "activity type",
      "type",
      "sport"
    ],
    title: [
      "titre",
      "activity name",
      "nom de l activite",
      "title"
    ],
    distance: [
      "distance",
      "distance km",
      "distance mi"
    ],
    duration: [
      "duree",
      "time",
      "temps",
      "elapsed time",
      "moving time"
    ],
    calories: [
      "calories",
      "calories brulees"
    ],
    avgHr: [
      "fc moyenne",
      "frequence cardiaque moyenne",
      "avg hr",
      "average heart rate",
      "avg heart rate"
    ],
    maxHr: [
      "fc max",
      "frequence cardiaque maximale",
      "max hr",
      "maximum heart rate",
      "max heart rate"
    ],
    avgPace: [
      "allure moyenne",
      "avg pace",
      "average pace"
    ],
    bestPace: [
      "meilleure allure",
      "best pace"
    ],
    elevationGain: [
      "denivele positif",
      "gain d altitude",
      "elevation gain",
      "total ascent"
    ],
    cadence: [
      "cadence moyenne",
      "avg cadence",
      "average cadence",
      "avg run cadence"
    ],
    trainingEffect: [
      "benefice principal",
      "aerobic te",
      "training effect"
    ]
  };

  function parseActivitiesCSV(text, fileName) {
    const rows = parseCSV(text);

    if (rows.length < 2) {
      throw new Error("Le CSV ne contient pas assez de lignes.");
    }

    const headers = rows[0];
    const indexes = {};

    Object.entries(aliases).forEach(([key, values]) => {
      indexes[key] = findColumn(headers, values);
    });

    if (indexes.date < 0 && indexes.type < 0 && indexes.distance < 0) {
      throw new Error(
        "Atlas ne reconnaît pas ce CSV comme une liste d’activités Garmin."
      );
    }

    const activities = rows.slice(1).map((row, rowIndex) => {
      const get = key => indexes[key] >= 0 ? row[indexes[key]] : null;
      const date = parseDate(get("date"));
      const durationSeconds = parseDurationSeconds(get("duration"));
      let distanceKm = toNumber(get("distance"));

      const distanceHeader = indexes.distance >= 0
        ? normalizeHeader(headers[indexes.distance])
        : "";

      if (distanceKm !== null && distanceHeader.includes("mi")) {
        distanceKm *= 1.609344;
      }

      return {
        id: `${fileName}-${rowIndex}-${date || rowIndex}`,
        sourceFile: fileName,
        date,
        type: get("type") || "Activité",
        title: get("title") || get("type") || "Activité Garmin",
        distanceKm,
        durationSeconds,
        calories: toNumber(get("calories")),
        averageHeartRate: toNumber(get("avgHr")),
        maxHeartRate: toNumber(get("maxHr")),
        averagePace: get("avgPace") || null,
        bestPace: get("bestPace") || null,
        elevationGainM: toNumber(get("elevationGain")),
        averageCadence: toNumber(get("cadence")),
        trainingEffect: get("trainingEffect") || null,
        raw: Object.fromEntries(
          headers.map((header, index) => [header, row[index] ?? ""])
        )
      };
    }).filter(activity =>
      activity.date ||
      activity.distanceKm !== null ||
      activity.durationSeconds !== null
    );

    if (!activities.length) {
      throw new Error("Aucune activité exploitable n’a été trouvée.");
    }

    const recognizedFields = Object.fromEntries(
      Object.entries(indexes).map(([key, index]) => [key, index >= 0])
    );

    return {
      activities,
      recognizedFields,
      rowCount: rows.length - 1
    };
  }

  // ████████████████████████████████████████████████████████████
  // 🟧 PARTIE D — GESTION DES FICHIERS
  // ████████████████████████████████████████████████████████████

  async function processFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    setImportStatus("warning", "Analyse en cours", `${files.length} fichier(s)`);

    const results = [];
    const newActivities = [];

    for (const file of files) {
      const extension = file.name.split(".").pop().toLowerCase();

      try {
        if (extension === "csv") {
          const text = await file.text();
          const parsed = parseActivitiesCSV(text, file.name);

          newActivities.push(...parsed.activities);
          results.push({
            name: file.name,
            status: "success",
            detail: `${parsed.activities.length} activité(s) reconnue(s)`,
            recognizedFields: parsed.recognizedFields
          });
        } else if (extension === "json") {
          const json = JSON.parse(await file.text());
          const importedActivities = Array.isArray(json.activities)
            ? json.activities
            : [];

          newActivities.push(...importedActivities);
          results.push({
            name: file.name,
            status: "success",
            detail: `${importedActivities.length} activité(s) Atlas importée(s)`
          });
        } else if (extension === "fit") {
          results.push({
            name: file.name,
            status: "warning",
            detail: "FIT détecté — décodage prévu dans la prochaine étape"
          });
        } else if (extension === "zip") {
          results.push({
            name: file.name,
            status: "warning",
            detail: "ZIP détecté — extraction prévue dans la prochaine étape"
          });
        } else {
          results.push({
            name: file.name,
            status: "error",
            detail: "Format non pris en charge"
          });
        }
      } catch (error) {
        results.push({
          name: file.name,
          status: "error",
          detail: error.message || "Erreur de lecture"
        });
      }
    }

    atlasData.activities = deduplicateActivities([
      ...atlasData.activities,
      ...newActivities
    ]);

    atlasData.files = [
      ...atlasData.files,
      ...results.map(result => ({
        name: result.name,
        status: result.status,
        detail: result.detail,
        importedAt: new Date().toISOString()
      }))
    ].slice(-20);

    saveData();
    renderFileResults(results);
    renderAll();

    const successful = results.filter(result => result.status === "success").length;
    const warnings = results.filter(result => result.status === "warning").length;

    if (successful > 0) {
      setImportStatus(
        warnings ? "warning" : "success",
        "Import terminé",
        `${newActivities.length} nouvelle(s) activité(s) ajoutée(s)`
      );
    } else {
      setImportStatus(
        "error",
        "Aucune donnée importée",
        "Vérifiez le format des fichiers."
      );
    }
  }

  function deduplicateActivities(activities) {
    const map = new Map();

    activities.forEach(activity => {
      const key = [
        activity.date || "",
        activity.type || "",
        Number(activity.distanceKm || 0).toFixed(3),
        activity.durationSeconds || 0
      ].join("|");

      map.set(key, activity);
    });

    return Array.from(map.values()).sort(
      (a, b) => new Date(b.date || 0) - new Date(a.date || 0)
    );
  }

  function setImportStatus(state, title, detail) {
    elements.importStatus.dataset.state = state;
    elements.importStatus.querySelector("strong").textContent = title;
    elements.importStatus.querySelector("span").textContent = detail;
  }

  function renderFileResults(results) {
    if (!results.length) return;

    elements.fileResults.innerHTML = results.map(result => `
      <article class="file-result is-${result.status}">
        <i>${result.status === "success" ? "✓" : result.status === "warning" ? "!" : "×"}</i>
        <div>
          <strong>${escapeHTML(result.name)}</strong>
          <small>${escapeHTML(result.detail)}</small>
        </div>
        <em>${result.status === "success" ? "Importé" : result.status === "warning" ? "En attente" : "Erreur"}</em>
      </article>
    `).join("");
  }

  // ████████████████████████████████████████████████████████████
  // 🟥 PARTIE E — CALCULS PHYSIOLOGIQUES INITIAUX
  // ████████████████████████████████████████████████████████████

  function calculateMetrics() {
    const activities = atlasData.activities.filter(activity => activity.date);
    const now = activities.length
      ? new Date(Math.max(...activities.map(activity => new Date(activity.date).getTime())))
      : new Date();

    const start28 = new Date(now);
    start28.setDate(start28.getDate() - 27);
    start28.setHours(0, 0, 0, 0);

    const recent28 = activities.filter(activity =>
      new Date(activity.date) >= start28
    );

    const totalDistance = sum(activities, "distanceKm");
    const totalSeconds = sum(activities, "durationSeconds");
    const heartRates = activities
      .map(activity => activity.averageHeartRate)
      .filter(Number.isFinite);
    const maxHeartRates = activities
      .map(activity => activity.maxHeartRate)
      .filter(Number.isFinite);

    const running = activities.filter(activity =>
      /run|running|course|trail|tapis/i.test(
        `${activity.type || ""} ${activity.title || ""}`
      )
    );

    const runningPaces = running
      .map(activity => {
        if (
          Number.isFinite(activity.distanceKm) &&
          activity.distanceKm > 0 &&
          Number.isFinite(activity.durationSeconds)
        ) {
          return activity.durationSeconds / activity.distanceKm;
        }

        return null;
      })
      .filter(Number.isFinite);

    const longest = recent28
      .filter(activity => Number.isFinite(activity.distanceKm))
      .sort((a, b) => b.distanceKm - a.distanceKm)[0] || null;

    const dates = activities
      .map(activity => new Date(activity.date))
      .filter(date => !Number.isNaN(date.getTime()))
      .sort((a, b) => a - b);

    return {
      activities,
      recent28,
      totalDistance,
      totalSeconds,
      averageHeartRate: average(heartRates),
      maxHeartRate: maxHeartRates.length ? Math.max(...maxHeartRates) : null,
      averageRunningPaceSeconds: average(runningPaces),
      longest,
      firstDate: dates[0] || null,
      lastDate: dates[dates.length - 1] || null,
      weeks: buildWeeklyVolumes(activities, now)
    };
  }

  function buildWeeklyVolumes(activities, endDate) {
    const weeks = [];

    for (let offset = 7; offset >= 0; offset -= 1) {
      const start = startOfWeek(new Date(endDate));
      start.setDate(start.getDate() - offset * 7);

      const end = new Date(start);
      end.setDate(end.getDate() + 7);

      const weekActivities = activities.filter(activity => {
        const date = new Date(activity.date);
        return date >= start && date < end;
      });

      weeks.push({
        start,
        distanceKm: sum(weekActivities, "distanceKm"),
        durationSeconds: sum(weekActivities, "durationSeconds"),
        count: weekActivities.length
      });
    }

    return weeks;
  }

  function startOfWeek(date) {
    const result = new Date(date);
    const day = (result.getDay() + 6) % 7;
    result.setDate(result.getDate() - day);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  function sum(items, key) {
    return items.reduce((total, item) => {
      const value = item[key];
      return total + (Number.isFinite(value) ? value : 0);
    }, 0);
  }

  function average(values) {
    if (!values.length) return null;
    return values.reduce((total, value) => total + value, 0) / values.length;
  }

  // ████████████████████████████████████████████████████████████
  // 🟪 PARTIE F — RENDU
  // ████████████████████████████████████████████████████████████

  function renderAll() {
    const metrics = calculateMetrics();
    renderSummary(metrics);
    renderAnalysis(metrics);
    renderWeeks(metrics.weeks);
    renderActivities(metrics.activities);
    renderRecognition(metrics.activities);
    renderBrain(metrics);

    elements.exportAtlasButton.disabled = !atlasData.activities.length;
    elements.engineStatus.textContent = atlasData.activities.length
      ? `${atlasData.activities.length} activité(s) active(s)`
      : "Moteur prêt";
  }

  function renderSummary(metrics) {
    elements.summaryActivities.textContent = metrics.activities.length;
    elements.summaryDistance.textContent = `${formatNumber(metrics.totalDistance, 1)} km`;
    elements.summaryDuration.textContent = formatHours(metrics.totalSeconds);
    elements.summaryHeartRate.textContent = metrics.averageHeartRate
      ? `${Math.round(metrics.averageHeartRate)} bpm`
      : "—";

    if (metrics.firstDate && metrics.lastDate) {
      elements.summaryPeriod.textContent =
        `${formatDate(metrics.firstDate)} → ${formatDate(metrics.lastDate)}`;
    } else {
      elements.summaryPeriod.textContent = "Aucune donnée";
    }
  }

  function renderAnalysis(metrics) {
    const volume28 = sum(metrics.recent28, "distanceKm");
    const previousFour = metrics.weeks.slice(0, 4);
    const recentFour = metrics.weeks.slice(4, 8);
    const previousVolume = previousFour.reduce((sumValue, week) => sumValue + week.distanceKm, 0);
    const recentVolume = recentFour.reduce((sumValue, week) => sumValue + week.distanceKm, 0);

    elements.metricVolume28.textContent = `${formatNumber(volume28, 1)} km`;

    if (previousVolume > 0) {
      const trend = ((recentVolume - previousVolume) / previousVolume) * 100;
      elements.metricVolumeTrend.textContent =
        `${trend >= 0 ? "+" : ""}${formatNumber(trend, 0)} % vs 4 semaines précédentes`;
    } else {
      elements.metricVolumeTrend.textContent = "Référence antérieure insuffisante";
    }

    elements.metricLongest.textContent = metrics.longest
      ? `${formatNumber(metrics.longest.distanceKm, 1)} km`
      : "0 km";

    elements.metricLongestDate.textContent = metrics.longest
      ? formatDate(new Date(metrics.longest.date))
      : "Aucune activité";

    elements.metricMaxHeartRate.textContent = metrics.maxHeartRate
      ? `${Math.round(metrics.maxHeartRate)} bpm`
      : "—";

    elements.metricAveragePace.textContent = metrics.averageRunningPaceSeconds
      ? formatPace(metrics.averageRunningPaceSeconds)
      : "—";

    setBar(elements.volumeBar, Math.min(100, volume28 / 80 * 100));
    setBar(
      elements.longestBar,
      metrics.longest ? Math.min(100, metrics.longest.distanceKm / 25 * 100) : 0
    );
    setBar(
      elements.heartRateBar,
      metrics.maxHeartRate ? Math.min(100, metrics.maxHeartRate / 210 * 100) : 0
    );
    setBar(
      elements.paceBar,
      metrics.averageRunningPaceSeconds
        ? Math.max(10, Math.min(100, (480 - metrics.averageRunningPaceSeconds) / 240 * 100))
        : 0
    );

    const confidence = calculateConfidence(metrics.activities);
    elements.analysisConfidence.textContent = `Confiance : ${confidence}%`;
  }

  function renderWeeks(weeks) {
    if (!weeks.some(week => week.count > 0)) {
      elements.weeksChart.innerHTML =
        '<div class="chart-empty">Importez un CSV pour afficher les semaines.</div>';
      return;
    }

    const maximum = Math.max(...weeks.map(week => week.distanceKm), 1);

    elements.weeksChart.innerHTML = weeks.map(week => {
      const height = Math.max(3, week.distanceKm / maximum * 130);
      return `
        <article class="week-column">
          <div class="bar-zone">
            <i style="height:${height}px" title="${formatNumber(week.distanceKm, 1)} km"></i>
          </div>
          <strong>${formatNumber(week.distanceKm, 1)} km</strong>
          <span>${formatShortDate(week.start)}</span>
        </article>
      `;
    }).join("");
  }

  function renderActivities(activities) {
    const visible = activities.slice(0, 12);

    elements.activitiesCountLabel.textContent =
      `${activities.length} activité${activities.length > 1 ? "s" : ""}`;

    if (!visible.length) {
      elements.activitiesTableBody.innerHTML =
        '<tr><td colspan="7" class="table-empty">Aucune activité importée.</td></tr>';
      return;
    }

    elements.activitiesTableBody.innerHTML = visible.map(activity => `
      <tr>
        <td>${activity.date ? formatDate(new Date(activity.date)) : "—"}</td>
        <td>${escapeHTML(activity.title || activity.type || "Activité")}</td>
        <td>${Number.isFinite(activity.distanceKm) ? `${formatNumber(activity.distanceKm, 2)} km` : "—"}</td>
        <td>${Number.isFinite(activity.durationSeconds) ? formatDuration(activity.durationSeconds) : "—"}</td>
        <td>${Number.isFinite(activity.averageHeartRate) ? `${Math.round(activity.averageHeartRate)} bpm` : "—"}</td>
        <td>${Number.isFinite(activity.maxHeartRate) ? `${Math.round(activity.maxHeartRate)} bpm` : "—"}</td>
        <td>${derivePace(activity)}</td>
      </tr>
    `).join("");
  }

  function renderRecognition(activities) {
    const checks = [
      activities.some(activity => activity.date || activity.type),
      activities.some(activity => Number.isFinite(activity.distanceKm) || Number.isFinite(activity.durationSeconds)),
      activities.some(activity => Number.isFinite(activity.averageHeartRate) || Number.isFinite(activity.maxHeartRate)),
      activities.some(activity => activity.averagePace || (
        Number.isFinite(activity.distanceKm) && Number.isFinite(activity.durationSeconds)
      )),
      activities.some(activity => Number.isFinite(activity.elevationGainM) || Number.isFinite(activity.averageCadence))
    ];

    Array.from(elements.recognitionList.children).forEach((item, index) => {
      item.className = checks[index] ? "recognized" : "pending";
    });
  }

  function renderBrain(metrics) {
    if (!metrics.activities.length) {
      elements.brainImportText.textContent =
        "Importez votre historique Garmin pour permettre à Atlas d’évaluer le volume récent, la fréquence d’entraînement et les réponses cardiaques.";
      return;
    }

    const volume28 = sum(metrics.recent28, "distanceKm");
    const longest = metrics.longest
      ? `${formatNumber(metrics.longest.distanceKm, 1)} km`
      : "non déterminée";

    elements.brainImportText.textContent =
      `Atlas a reconnu ${metrics.activities.length} activité(s). ` +
      `Le volume des 28 derniers jours est de ${formatNumber(volume28, 1)} km ` +
      `et la plus longue sortie récente est de ${longest}. ` +
      `Ces données peuvent maintenant servir de base au moteur Physiologie et au futur plan adaptatif.`;
  }

  function calculateConfidence(activities) {
    if (!activities.length) return 0;

    const total = activities.length;
    const ratios = [
      activities.filter(activity => activity.date).length / total,
      activities.filter(activity => Number.isFinite(activity.distanceKm)).length / total,
      activities.filter(activity => Number.isFinite(activity.durationSeconds)).length / total,
      activities.filter(activity => Number.isFinite(activity.averageHeartRate)).length / total,
      activities.filter(activity => Number.isFinite(activity.maxHeartRate)).length / total
    ];

    return Math.round(
      ratios.reduce((sumValue, ratio) => sumValue + ratio, 0) /
      ratios.length *
      100
    );
  }

  // ████████████████████████████████████████████████████████████
  // ⬜ PARTIE G — FORMATAGE ET ACTIONS
  // ████████████████████████████████████████████████████████████

  function derivePace(activity) {
    if (activity.averagePace) return escapeHTML(activity.averagePace);

    if (
      Number.isFinite(activity.distanceKm) &&
      activity.distanceKm > 0 &&
      Number.isFinite(activity.durationSeconds)
    ) {
      return formatPace(activity.durationSeconds / activity.distanceKm);
    }

    return "—";
  }

  function formatPace(secondsPerKm) {
    const rounded = Math.round(secondsPerKm);
    const minutes = Math.floor(rounded / 60);
    const seconds = rounded % 60;
    return `${minutes}'${String(seconds).padStart(2, "0")}/km`;
  }

  function formatDuration(seconds) {
    const totalMinutes = Math.round(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (!hours) return `${minutes} min`;
    return `${hours} h ${String(minutes).padStart(2, "0")}`;
  }

  function formatHours(seconds) {
    if (!seconds) return "0 h";
    return `${formatNumber(seconds / 3600, 1)} h`;
  }

  function formatNumber(value, decimals = 1) {
    return new Intl.NumberFormat("fr-FR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(Number(value || 0));
  }

  function formatDate(date) {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric"
    }).format(date);
  }

  function formatShortDate(date) {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short"
    }).format(date);
  }

  function setBar(element, percent) {
    element.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  }

  function escapeHTML(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function exportAtlasData() {
    const blob = new Blob(
      [JSON.stringify(atlasData, null, 2)],
      { type: "application/json" }
    );

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `atlas-garmin-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function clearData() {
    const confirmed = window.confirm(
      "Effacer toutes les données Garmin enregistrées localement dans Atlas ?"
    );

    if (!confirmed) return;

    atlasData = createEmptyData();
    localStorage.removeItem(STORAGE_KEY);
    elements.fileResults.innerHTML =
      '<div class="empty-state">Les fichiers analysés apparaîtront ici.</div>';
    setImportStatus("idle", "Aucun fichier analysé", "Atlas attend un export Garmin.");
    renderAll();
  }

  async function loadDemo() {
    try {
      const response = await fetch("./samples/garmin-activities-demo.csv");
      if (!response.ok) throw new Error("Impossible de charger la démonstration.");

      const text = await response.text();
      const file = new File(
        [text],
        "garmin-activities-demo.csv",
        { type: "text/csv" }
      );

      await processFiles([file]);
    } catch (error) {
      setImportStatus("error", "Démonstration indisponible", error.message);
    }
  }

  elements.chooseFilesButton.addEventListener("click", () => {
    elements.files.click();
  });

  elements.files.addEventListener("change", event => {
    processFiles(event.target.files);
    event.target.value = "";
  });

  elements.loadDemoButton.addEventListener("click", loadDemo);
  elements.exportAtlasButton.addEventListener("click", exportAtlasData);
  elements.clearDataButton.addEventListener("click", clearData);

  ["dragenter", "dragover"].forEach(eventName => {
    elements.dropZone.addEventListener(eventName, event => {
      event.preventDefault();
      elements.dropZone.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    elements.dropZone.addEventListener(eventName, event => {
      event.preventDefault();
      elements.dropZone.classList.remove("is-dragging");
    });
  });

  elements.dropZone.addEventListener("drop", event => {
    processFiles(event.dataTransfer.files);
  });

  if (atlasData.activities.length) {
    setImportStatus(
      "success",
      "Données locales restaurées",
      `${atlasData.activities.length} activité(s) disponible(s)`
    );
  }

  renderAll();
})();
