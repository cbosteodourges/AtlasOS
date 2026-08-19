"use strict";

(() => {
  const definitions = {
    recovery: {
      title: "Récupération",
      eyebrow: "INDICE ATLAS",
      field: "atlas_index",
      unit: "/100",
      label: "Indice Atlas de disponibilité",
      description: "Suivez la manière dont sommeil, VFC, stress nocturne et qualité des données influencent votre disponibilité.",
      understanding: "L’indice Atlas est recalculé chaque jour à partir des données disponibles. Il pondère la récupération du sommeil (30 %), le sommeil global (25 %), la VFC comparée à votre référence (30 %), le stress nocturne (10 %) et la qualité des données (5 %). Les poids absents sont redistribués."
    },
    sleep: {
      title: "Sommeil",
      eyebrow: "RÉCUPÉRATION NOCTURNE",
      field: "sleep_score",
      unit: "/100",
      label: "Score de sommeil Garmin",
      description: "Visualisez votre qualité de sommeil et ses variations au fil des cycles d’entraînement.",
      understanding: "Le score de sommeil synthétise notamment la durée, la continuité et la qualité physiologique de la nuit. Atlas l’interprète avec la VFC, le stress nocturne et votre charge récente."
    },
    hrv: {
      title: "Variabilité de fréquence cardiaque",
      eyebrow: "VFC NOCTURNE",
      field: "hrv_last_night_ms",
      unit: " ms",
      label: "VFC nocturne",
      description: "Comparez votre VFC à votre tendance personnelle plutôt qu’à une norme générale.",
      understanding: "La VFC reflète les variations entre deux battements. Son intérêt principal réside dans son évolution par rapport à votre propre référence. Une baisse isolée n’est pas nécessairement préoccupante ; la tendance et le contexte priment."
    },
    load: {
      title: "Charge d’entraînement",
      eyebrow: "CHARGE GARMIN",
      field: "training_load",
      unit: "",
      label: "Charge quotidienne",
      description: "Suivez la charge enregistrée dans les activités importées et son accumulation dans le temps.",
      understanding: "La charge représente le stress d’entraînement estimé pour les activités analysées. Atlas l’interprète avec la récupération, les douleurs et l’historique ; une charge élevée n’est adaptée que si elle reste progressive et bien tolérée."
    }
  };

  const params = new URLSearchParams(location.search);
  const metric = definitions[params.get("metric")] ? params.get("metric") : "recovery";
  const definition = definitions[metric];
  let history = [];
  let selectedRange = "90";

  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  };

  document.querySelectorAll("[data-metric-link]").forEach(link => {
    link.classList.toggle("active", link.dataset.metricLink === metric);
  });
  setText("[data-metric-title]", definition.title);
  setText("[data-metric-eyebrow]", definition.eyebrow);
  setText("[data-metric-description]", definition.description);
  setText("[data-chart-label]", definition.label);
  setText("[data-understanding-title]", definition.label);
  setText("[data-understanding-text]", definition.understanding);
  document.title = `Atlas OS — ${definition.title}`;

  const isAvailable = value =>
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value));

  const formatValue = value => {
    if (!isAvailable(value)) return "—";
    const rounded = Math.round(Number(value) * 10) / 10;
    return `${String(rounded).replace(".", ",")}${definition.unit}`;
  };

  const filteredHistory = () => {
    const valid = history.filter(item => isAvailable(item[definition.field]));
    if (selectedRange === "all" || !valid.length) return valid;
    const last = new Date(valid[valid.length - 1].day + "T12:00:00");
    const start = new Date(last);
    start.setDate(start.getDate() - Number(selectedRange) + 1);
    return valid.filter(item => new Date(item.day + "T12:00:00") >= start);
  };

  const renderComposition = latest => {
    const section = document.querySelector("[data-index-composition]");
    const grid = document.querySelector("[data-composition-grid]");
    if (metric !== "recovery" || !latest?.atlas_index_components?.length) {
      if (section) section.hidden = true;
      return;
    }
    section.hidden = false;
    grid.replaceChildren();
    latest.atlas_index_components.forEach(component => {
      const card = document.createElement("article");
      const label = document.createElement("span");
      const value = document.createElement("strong");
      label.textContent = component.label;
      value.textContent = `${component.score}/100 · poids ${component.weight}%`;
      card.append(label, value);
      grid.appendChild(card);
    });
  };

  const drawChart = points => {
    const canvas = document.getElementById("metricChart");
    const empty = document.querySelector("[data-empty]");
    const wrap = canvas.parentElement;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(300, wrap.clientWidth);
    const height = Math.max(280, wrap.clientHeight);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    empty.hidden = points.length > 0;
    if (!points.length) return;

    const values = points.map(item => Number(item[definition.field]));
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (metric === "recovery" || metric === "sleep") {
      min = Math.min(40, min);
      max = 100;
    } else {
      const pad = Math.max(3, (max - min) * .16);
      min -= pad;
      max += pad;
    }
    if (max === min) { max += 1; min -= 1; }

    const left = 52, right = 18, top = 18, bottom = 42;
    const chartW = width - left - right;
    const chartH = height - top - bottom;
    const x = index => left + (points.length === 1 ? chartW / 2 : index * chartW / (points.length - 1));
    const y = value => top + (max - value) * chartH / (max - min);

    ctx.font = "12px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (let step = 0; step <= 4; step += 1) {
      const value = min + (max - min) * step / 4;
      const yy = y(value);
      ctx.strokeStyle = "rgba(145,170,189,.13)";
      ctx.beginPath(); ctx.moveTo(left, yy); ctx.lineTo(width - right, yy); ctx.stroke();
      ctx.fillStyle = "#7895a8";
      ctx.fillText(String(Math.round(value)), left - 10, yy);
    }

    const gradient = ctx.createLinearGradient(0, top, 0, top + chartH);
    gradient.addColorStop(0, "rgba(56,209,255,.32)");
    gradient.addColorStop(1, "rgba(56,209,255,0)");
    ctx.beginPath();
    points.forEach((point, index) => {
      const xx = x(index), yy = y(Number(point[definition.field]));
      if (index === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    });
    ctx.lineTo(x(points.length - 1), top + chartH);
    ctx.lineTo(x(0), top + chartH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    points.forEach((point, index) => {
      const xx = x(index), yy = y(Number(point[definition.field]));
      if (index === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    });
    ctx.strokeStyle = "#38d1ff";
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.stroke();

    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    ctx.setLineDash([7, 6]);
    ctx.strokeStyle = "#51e7a6";
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(left, y(average)); ctx.lineTo(width - right, y(average)); ctx.stroke();
    ctx.setLineDash([]);

    const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#7895a8";
    labelIndexes.forEach(index => {
      const day = new Date(points[index].day + "T12:00:00");
      ctx.fillText(day.toLocaleDateString("fr-FR", {day:"2-digit", month:"short", year: points.length > 365 ? "2-digit" : undefined}), x(index), height - bottom + 13);
    });
  };

  const render = () => {
    const points = filteredHistory();
    setText("[data-data-count]", `${points.length} mesure${points.length > 1 ? "s" : ""}`);
    if (!points.length) {
      ["[data-average]","[data-minimum]","[data-maximum]","[data-trend]"].forEach(selector => setText(selector, "—"));
      drawChart(points);
      return;
    }
    const values = points.map(item => Number(item[definition.field]));
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    const section = Math.max(1, Math.floor(values.length / 3));
    const first = values.slice(0, section).reduce((a,b)=>a+b,0) / section;
    const lastValues = values.slice(-section);
    const last = lastValues.reduce((a,b)=>a+b,0) / lastValues.length;
    const difference = last - first;
    setText("[data-average]", formatValue(average));
    setText("[data-minimum]", formatValue(Math.min(...values)));
    setText("[data-maximum]", formatValue(Math.max(...values)));
    setText("[data-trend]", Math.abs(difference) < 1 ? "Stable" : difference > 0 ? `↗ +${formatValue(difference)}` : `↘ ${formatValue(difference)}`);
    const latest = points[points.length - 1];
    setText("[data-latest-value]", formatValue(latest[definition.field]));
    setText("[data-latest-date]", new Date(latest.day + "T12:00:00").toLocaleDateString("fr-FR", {dateStyle:"long"}));
    renderComposition(history[history.length - 1]);
    drawChart(points);
  };

  document.querySelectorAll("[data-range]").forEach(button => {
    button.addEventListener("click", () => {
      selectedRange = button.dataset.range;
      document.querySelectorAll("[data-range]").forEach(item => item.classList.toggle("active", item === button));
      render();
    });
  });

  fetch("/api/atlas/wellness-history", {cache:"no-store"})
    .then(async response => {
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : null;
      if (!response.ok) {
        throw new Error(
          response.status === 404
            ? "Le serveur en cours doit être redémarré après la mise à jour."
            : (payload?.error || `Erreur Wellness ${response.status}`)
        );
      }
      return payload;
    })
    .then(payload => {
      history = payload.history || [];
      render();
    })
    .catch(error => {
      console.warn("Atlas Wellness :", error);
      setText("[data-metric-description]", error.message);
      drawChart([]);
    });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(render, 120);
  });
})();
