"use strict";

(() => {
  const selectedAvatar =
    localStorage.getItem("atlasPreselectedAvatar") || "male";
  const avatar = document.getElementById("cockpitAvatar");

  if (avatar) {
    const female = selectedAvatar === "female";
    avatar.src = female
      ? "./assets/atlas-avatar-femme-clean-final.png?v=2"
      : "./assets/atlas-avatar-homme-clean-final.png?v=2";
    avatar.dataset.avatar = female ? "female" : "male";
    document.body.dataset.avatar = female ? "female" : "male";
  }

  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    if (element && value !== undefined && value !== null) {
      element.textContent = value;
    }
  };

  const localDayKey = date => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const todayKey = localDayKey(new Date());
  const todayLabel = new Date().toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long"
  });
  setText("[data-current-date]", todayLabel.toUpperCase());

  const formatDuration = minutes => {
    if (minutes === null || minutes === undefined || minutes === "") return null;
    if (!Number.isFinite(Number(minutes))) return null;
    const total = Math.round(Number(minutes));
    return `${Math.floor(total / 60)} h ${String(total % 60).padStart(2, "0")}`;
  };

  const recoveryLabel = score => {
    if (score >= 85) return "Très favorable";
    if (score >= 70) return "Favorable";
    if (score >= 55) return "Intermédiaire";
    if (score >= 40) return "Faible";
    return "Récupération nécessaire";
  };

  const loadLabel = value => {
    if (value === null || value === undefined || value === "") return "Aucune donnée";
    if (!Number.isFinite(Number(value))) return "À synchroniser";
    if (value < 50) return "Légère";
    if (value < 100) return "Modérée";
    if (value < 180) return "Soutenue";
    return "Élevée";
  };

  const renderIndexComponents = components => {
    const container = document.querySelector("[data-index-components]");
    if (!container) return;
    container.replaceChildren();
    (components || []).forEach(component => {
      const row = document.createElement("div");
      row.className = "index-component";
      row.innerHTML = `
        <span>${component.label}</span>
        <strong>${component.score}/100 · poids ${component.weight}%</strong>
        <div><i style="width:${Math.max(0, Math.min(100, component.score))}%"></i></div>
      `;
      container.appendChild(row);
    });
  };

  let currentRecoveryInsight = null;


  const updateRecoveryGauge = (value, interpretation = null) => {
    const gauge = document.querySelector("[data-recovery-gauge]");
    const zoneLabel = document.querySelector("[data-recovery-zone]");
    const score = Number(value);
    if (!gauge || !Number.isFinite(score)) return;

    const bounded = Math.max(0, Math.min(100, score));
    const zone = bounded < 40
      ? { key: "red", label: "Vigilance" }
      : bounded < 55
        ? { key: "orange", label: "Récupération fragile" }
        : bounded < 70
          ? { key: "yellow", label: "À surveiller" }
          : { key: "green", label: "Zone favorable" };

    gauge.style.setProperty("--recovery-position", `${bounded}%`);
    gauge.dataset.zone = zone.key;
    gauge.dataset.ready = "true";
    gauge.setAttribute("aria-busy", "false");
    gauge.setAttribute("aria-valuenow", String(Math.round(bounded)));
    const nuance = interpretation?.display_label;
    if (zoneLabel) {
      zoneLabel.textContent = nuance
        ? `${zone.label} · ${nuance}`
        : zone.label;
    }
  };

  const renderSyncInsights = payload => {
    const latest = payload?.recovery?.latest;
    currentRecoveryInsight = latest || currentRecoveryInsight;
    if (latest) {
      if (latest.day === todayKey) {
        setText("[data-atlas-index]", latest.atlas_recovery_index);
        setText(
          "[data-recovery-label]",
          latest.interpretation?.display_label
            || recoveryLabel(latest.atlas_recovery_index)
        );
        setText("[data-recovery-detail]", `${latest.atlas_recovery_index}/100 · confiance ${latest.confidence}/100`);
        updateRecoveryGauge(latest.atlas_recovery_index, latest.interpretation);
        if (latest.guidance) {
          setText("[data-readiness-summary]", latest.guidance);
        }
      }
      setText("[data-index-summary]", latest.explanation);
      renderIndexComponents(latest.components);
    }
    const physiology = payload?.physiology?.current;
    if (physiology) {
      const decimal = value => String(value).replace(".", ",");
      setText("[data-physiology-vo2]", physiology.vo2_max != null ? `${decimal(physiology.vo2_max)} ml/kg/min` : "—");
      setText("[data-physiology-vma]", physiology.vma_kmh != null ? `${decimal(physiology.vma_kmh)} km/h` : "—");
      setText("[data-physiology-sv1]", physiology.sv1?.speed_kmh != null ? `${decimal(physiology.sv1.speed_kmh)} km/h` : "—");
      setText("[data-physiology-sv1-hr]", physiology.sv1?.heart_rate_bpm != null ? `${physiology.sv1.heart_rate_bpm} bpm · estimation longitudinale` : "FC à confirmer");
      setText("[data-physiology-sv2]", physiology.sv2?.speed_kmh != null ? `${decimal(physiology.sv2.speed_kmh)} km/h` : "—");
      setText("[data-physiology-sv2-hr]", physiology.sv2?.heart_rate_bpm != null ? `${physiology.sv2.heart_rate_bpm} bpm · estimation longitudinale` : "FC à confirmer");
      setText("[data-physiology-hrmax]", physiology.maximum_heart_rate_bpm != null ? `${physiology.maximum_heart_rate_bpm} bpm` : "—");
    }
  };

  const nutritionModule = document.querySelector("[data-nutrition-module]");
  const nutritionSetting = document.querySelector("[data-nutrition-setting]");
  const nutritionNav = document.querySelector("[data-nutrition-nav]");
  const renderNutrition = payload => {
    if (!payload?.access?.enabled) return;
    if (nutritionModule) nutritionModule.hidden = false;
    if (nutritionSetting) nutritionSetting.hidden = false;
    if (nutritionNav) nutritionNav.hidden = false;
    if (location.hash === "#nutrition-hydratation" && nutritionModule) {
      requestAnimationFrame(() => nutritionModule.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
    const today = payload.today || {};
    const targets = payload.targets || {};
    setText("[data-hydration-value]", Math.round(today.hydration_ml || 0));
    setText("[data-energy-value]", today.record_count ? Math.round(today.energy_kcal || 0) : "—");
    setText("[data-protein-value]", today.record_count ? Math.round(today.protein_g || 0) : "—");
    setText("[data-carbs-value]", today.record_count ? Math.round(today.carbohydrate_g || 0) : "—");
    setText("[data-hydration-target]", targets.hydration_ml ? `Repère : ${targets.hydration_ml} ml` : "Ajoutez votre poids pour personnaliser le repère");
    setText("[data-protein-target]", targets.protein_g ? `repère ${targets.protein_g} g` : "repère à personnaliser");
    setText("[data-carbs-target]", targets.carbohydrate_g ? `repère ${targets.carbohydrate_g} g` : "repère à personnaliser");
    setText("[data-fuel-source]", today.sources?.length ? today.sources.join(" + ") : "Atlas + Santé Connect");
    setText("[data-fuel-guidance]", payload.recommendations?.[0] || "Apports enregistrés, analyse en cours.");
    const bar = document.querySelector("[data-hydration-progress]");
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, payload.progress?.hydration_percent || 0))}%`;
    if (!localStorage.getItem("atlasNutritionPilotAdded")) {
      let selected;
      try { selected = JSON.parse(localStorage.getItem("atlasCockpitVisibleMetrics") || "null"); } catch (_error) { selected = null; }
      if (Array.isArray(selected) && !selected.includes("nutrition")) {
        selected.push("nutrition");
        localStorage.setItem("atlasCockpitVisibleMetrics", JSON.stringify(selected));
      }
      localStorage.setItem("atlasNutritionPilotAdded", "1");
    }
    applyDashboard();
  };

  const loadNutrition = () => fetch("/api/atlas/nutrition-hydration", { cache: "no-store" })
    .then(response => response.ok ? response.json() : null).then(renderNutrition)
    .catch(error => console.warn("Atlas nutrition :", error));

  const saveNutrition = body => fetch("/api/atlas/nutrition-hydration", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  }).then(async response => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Enregistrement impossible");
    renderNutrition(payload.summary);
    return payload;
  });

  const updateCockpit = payload => {
    const latest = payload.latest;
    if (!latest) return;

    const latestComplete = payload.latest_complete || latest;
    const isCurrentDay = latest.day === todayKey;
    const latestDay = new Date(`${latest.day}T12:00:00`);
    const latestDayLabel = latestDay.toLocaleDateString("fr-FR");
    const completeDay = new Date(`${latestComplete.day}T12:00:00`);
    const completeDayLabel = completeDay.toLocaleDateString("fr-FR");
    const partial = Boolean(
      payload.latest_unavailable?.partial &&
      latest.sleep_duration_source === "health_connect"
    );
    const indexSource = latest.atlas_index != null ? latest : latestComplete;
    const indexDayLabel = new Date(
      `${indexSource.day}T12:00:00`
    ).toLocaleDateString("fr-FR");

    // Quand Santé Connect a produit un indice du jour, ne jamais le
    // remplacer ensuite par l'ancien score Garmin arrivé plus lentement.
    if (!partial) {
      setText("[data-atlas-index]", indexSource.atlas_index ?? "—");
      setText(
        "[data-recovery-label]",
        latest.atlas_index != null && isCurrentDay
          ? recoveryLabel(latest.atlas_index)
          : "Dernier indice connu"
      );
      setText(
        "[data-recovery-detail]",
        latest.atlas_index != null && isCurrentDay
          ? (latest.sleep_recovery_score != null
            ? `Sommeil récupérateur ${latest.sleep_recovery_score}/100`
            : "Indice Atlas du jour")
          : `${indexSource.atlas_index ?? "—"}/100 · données du ${indexDayLabel}`
      );
      updateRecoveryGauge(indexSource.atlas_index);
    }
    setText(
      "[data-readiness-title]",
      partial
        ? "Sommeil reçu · bilan physiologique partiel"
        : (isCurrentDay ? "Vous êtes prêt à vous entraîner" : "Données nocturnes indisponibles")
    );
    setText(
      "[data-readiness-summary]",
      partial
        ? (currentRecoveryInsight?.day === latest.day && currentRecoveryInsight?.guidance
          ? currentRecoveryInsight.guidance
          : `Santé Connect a transmis ${formatDuration(latest.sleep_duration_minutes)}. VFC et récupération complète restent datées du ${completeDayLabel}.`)
        : (isCurrentDay
          ? "Récupération élevée, sommeil satisfaisant et charge bien maîtrisée."
          : `Montre non portée ou aucune nouvelle mesure reçue. Dernier bilan complet : ${completeDayLabel}.`)
    );

    const duration = formatDuration(latest.sleep_duration_minutes);
    setText(
      "[data-sleep-value]",
      duration || (latest.sleep_score != null ? `${latest.sleep_score}/100` : "—")
    );
    setText(
      "[data-sleep-detail]",
      latest.sleep_duration_source === "health_connect"
        ? `Sommeil synchronisé par Santé Connect · ${latestDayLabel}`
        : (latest.sleep_quality_score != null
          ? (isCurrentDay
            ? `Qualité ${latest.sleep_quality_score} %`
            : `Dernière qualité mesurée ${latest.sleep_quality_score} % · ${latestDayLabel}`)
          : "Donnée Garmin la plus récente")
    );

    setText(
      "[data-hrv-value]",
      latestComplete.hrv_last_night_ms != null
        ? `${Math.round(latestComplete.hrv_last_night_ms)} ms`
        : "—"
    );
    setText(
      "[data-hrv-detail]",
      latestComplete.hrv_weekly_average_ms != null
        ? `Mesure du ${completeDayLabel} · moyenne 7 j : ${Math.round(latestComplete.hrv_weekly_average_ms)} ms`
        : (latestComplete.hrv_status || "Référence en construction")
    );

    setText("[data-load-value]", loadLabel(latest.training_load));
    setText(
      "[data-load-detail]",
      latest.training_load != null
        ? `Charge Garmin : ${Math.round(latest.training_load)}${isCurrentDay ? "" : ` · ${latestDayLabel}`}`
        : "Aucune activité chargée ce jour"
    );

    const progress = payload.program_progress;
    if (progress) {
      setText("[data-program-progress]", progress.percent);
      const bar = document.querySelector("[data-program-progress-bar]");
      if (bar) bar.style.width = `${progress.percent}%`;

      const workout = progress.next_workout;
      if (workout?.date) {
        const day = new Date(`${workout.date}T12:00:00`);
        const label = day.toLocaleDateString("fr-FR", {
          weekday: "long",
          day: "numeric",
          month: "long"
        });
        const sessionPrefix = workout.date === todayKey ? "SÉANCE DU JOUR" : "PROCHAINE SÉANCE";
        setText("[data-next-session-date]", `${sessionPrefix} · ${label.toUpperCase()}`);
        setText("[data-next-session-title]", workout.title);
        const duration = workout.duration_minutes
          ? `${Math.round(workout.duration_minutes)} min`
          : "Durée à confirmer";
        setText(
          "[data-next-session-detail]",
          [duration, workout.objective].filter(Boolean).join(" · ")
        );
      }
    }

    const analysis = payload.athlete_analysis;
    if (!analysis) {
      setText(
        "[data-analysis-summary]",
        "Le rapport n’a pas été transmis par le serveur. Redémarrez Atlas puis rechargez cette page."
      );
      setText("[data-analysis-confidence-text]", "Analyse momentanément indisponible.");
    }
    if (analysis) {
      setText("[data-analysis-summary]", analysis.summary);
      setText("[data-analysis-confidence]", analysis.confidence?.score ?? "—");
      setText(
        "[data-analysis-coverage]",
        analysis.confidence ? `${analysis.confidence.coverage_28d} %` : "—"
      );
      const physiology = analysis.physiology || {};
      const decimal = value => String(value).replace(".", ",");
      setText(
        "[data-physiology-vo2]",
        physiology.vo2_max != null
          ? `${decimal(physiology.vo2_max)} ml/kg/min`
          : "Non disponible"
      );
      setText(
        "[data-physiology-vma]",
        physiology.vma_kmh != null
          ? `${decimal(physiology.vma_kmh)} km/h`
          : "Non disponible"
      );
      setText(
        "[data-physiology-vma-reference]",
        physiology.vma_training_reference_kmh != null
          ? `Référence d’entraînement : ${decimal(physiology.vma_training_reference_kmh)} km/h`
          : "Référence à confirmer"
      );
      setText(
        "[data-physiology-sv1]",
        physiology.sv1_speed_kmh != null
          ? `${decimal(physiology.sv1_speed_kmh)} km/h`
          : "Non disponible"
      );
      setText(
        "[data-physiology-sv1-hr]",
        physiology.sv1_heart_rate_bpm != null
          ? `${Math.round(physiology.sv1_heart_rate_bpm)} bpm · ${physiology.sv1_status || "référence"}`
          : "FC à confirmer"
      );
      setText(
        "[data-physiology-sv2]",
        physiology.sv2_speed_kmh != null
          ? `${decimal(physiology.sv2_speed_kmh)} km/h`
          : "Non disponible"
      );
      setText(
        "[data-physiology-sv2-hr]",
        physiology.sv2_heart_rate_bpm != null
          ? `${Math.round(physiology.sv2_heart_rate_bpm)} bpm · ${physiology.sv2_status || "référence"}`
          : "FC à confirmer"
      );
      setText(
        "[data-physiology-hrmax]",
        physiology.maximum_heart_rate_bpm != null
          ? `${Math.round(physiology.maximum_heart_rate_bpm)} bpm`
          : "Non disponible"
      );
      const physiologyHistory = (analysis.physiology_history || []).filter(item => item?.day);
      const chartRoot = document.querySelector("[data-physiology-chart]");
      const chartSvg = chartRoot?.querySelector("svg");
      const chartMessage = document.querySelector("[data-physiology-chart-message]");
      const chartSummary = document.querySelector("[data-physiology-chart-summary]");
      let selectedPhysiologyMetric = "vo2_max";
      let selectedPhysiologyPeriod = 90;
      const metricMeta = {
        vo2_max: ["VO₂max", "ml/kg/min"],
        vma_kmh: ["VMA", "km/h"],
        sv1_speed_kmh: ["SV1", "km/h"],
        sv2_speed_kmh: ["SV2", "km/h"],
        maximum_heart_rate_bpm: ["FC maximale", "bpm"],
      };
      const renderPhysiologyChart = () => {
        if (!chartSvg) return;
        const now = new Date();
        const cutoff = selectedPhysiologyPeriod
          ? new Date(now.getTime() - selectedPhysiologyPeriod * 86400000)
          : null;
        const points = physiologyHistory
          .filter(item => !cutoff || new Date(item.day) >= cutoff)
          .map(item => ({
            day: item.day,
            value: Number(item[selectedPhysiologyMetric]),
            kind: item.kind,
            method: item.method,
            confidence: item.confidence,
          }))
          .filter(item => Number.isFinite(item.value) && item.value > 0)
          .sort((a, b) => String(a.day).localeCompare(String(b.day)));
        chartSvg.replaceChildren();
        if (points.length < 2) {
          chartRoot?.classList.add("is-empty");
          if (chartMessage) chartMessage.textContent = points.length
            ? "Une référence existe. Une deuxième mesure distincte fera apparaître la courbe."
            : "Aucune mesure disponible sur cette période.";
          if (chartSummary) chartSummary.textContent = "Historique physiologique en construction";
          return;
        }
        chartRoot?.classList.remove("is-empty");
        const values = points.map(point => point.value);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const spread = Math.max(max - min, Math.abs(max || 1) * 0.04);
        const coords = points.map((point, index) => {
          const x = 42 + index * (816 / Math.max(1, points.length - 1));
          const y = 190 - ((point.value - (min - spread * 0.25)) / (spread * 1.5)) * 145;
          return { ...point, x, y };
        });
        const ns = "http://www.w3.org/2000/svg";
        [55, 105, 155, 205].forEach(y => {
          const line = document.createElementNS(ns, "line");
          line.setAttribute("x1", "42"); line.setAttribute("x2", "858");
          line.setAttribute("y1", String(y)); line.setAttribute("y2", String(y));
          line.setAttribute("class", "chart-grid"); chartSvg.appendChild(line);
        });
        const area = document.createElementNS(ns, "path");
        area.setAttribute("d", `M ${coords[0].x} 205 L ${coords.map(p => `${p.x} ${p.y}`).join(" L ")} L ${coords.at(-1).x} 205 Z`);
        area.setAttribute("class", "chart-area"); chartSvg.appendChild(area);
        const path = document.createElementNS(ns, "path");
        path.setAttribute("d", `M ${coords.map(p => `${p.x} ${p.y}`).join(" L ")}`);
        path.setAttribute("class", "chart-line"); chartSvg.appendChild(path);
        coords.forEach(point => {
          const circle = document.createElementNS(ns, "circle");
          circle.setAttribute("cx", String(point.x)); circle.setAttribute("cy", String(point.y));
          circle.setAttribute("r", point.kind === "validated" ? "7" : "5");
          circle.setAttribute("class", `chart-point${point.kind === "validated" ? " is-validated" : ""}`);
          const title = document.createElementNS(ns, "title");
          const [label, unit] = metricMeta[selectedPhysiologyMetric];
          title.textContent = `${new Date(point.day).toLocaleDateString("fr-FR")} · ${label} ${point.value.toLocaleString("fr-FR")} ${unit}`;
          circle.appendChild(title);
          chartSvg.appendChild(circle);
        });
        [coords[0], coords.at(-1)].forEach((point, index) => {
          const label = document.createElementNS(ns, "text");
          label.setAttribute("x", String(point.x));
          label.setAttribute("y", "222");
          label.setAttribute("text-anchor", index ? "end" : "start");
          label.setAttribute("class", "chart-date");
          label.textContent = new Date(point.day).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "2-digit" });
          chartSvg.appendChild(label);
        });
        const delta = points.at(-1).value - points[0].value;
        const [label, unit] = metricMeta[selectedPhysiologyMetric];
        const deltaLabel = Math.abs(delta) < 0.05
          ? "stable sur la période"
          : `${delta >= 0 ? "+" : ""}${delta.toFixed(1).replace(".", ",")} sur la période`;
        if (chartSummary) chartSummary.textContent = `${label} : ${points.at(-1).value.toLocaleString("fr-FR")} ${unit} · ${deltaLabel}`;
        const chartNote = document.querySelector("[data-physiology-chart-note]");
        const estimatedCount = points.filter(point => point.kind === "atlas_estimate").length;
        if (chartNote) chartNote.textContent = estimatedCount
          ? `${estimatedCount} point${estimatedCount > 1 ? "s" : ""} hebdomadaire${estimatedCount > 1 ? "s" : ""} rétrospectif${estimatedCount > 1 ? "s" : ""} Atlas, calculé${estimatedCount > 1 ? "s" : ""} depuis les séances FIT et recalé${estimatedCount > 1 ? "s" : ""} sur votre référence actuelle.`
          : "Courbe fondée sur les références physiologiques validées.";
        if (chartMessage) chartMessage.textContent = "";
      };
      document.querySelectorAll("[data-physiology-metric]").forEach(button => button.addEventListener("click", () => {
        document.querySelectorAll("[data-physiology-metric]").forEach(item => item.classList.toggle("is-active", item === button));
        selectedPhysiologyMetric = button.dataset.physiologyMetric;
        renderPhysiologyChart();
      }));
      document.querySelectorAll("[data-physiology-period]").forEach(button => button.addEventListener("click", () => {
        document.querySelectorAll("[data-physiology-period]").forEach(item => item.classList.toggle("is-active", item === button));
        selectedPhysiologyPeriod = Number(button.dataset.physiologyPeriod);
        renderPhysiologyChart();
      }));
      renderPhysiologyChart();

      const fitCount = analysis.longitudinal_report?.activity_count || 0;
      const runningFitCount =
        analysis.longitudinal_report?.running_activity_count || 0;
      setText(
        "[data-fit-archive-count]",
        fitCount
          ? `${fitCount} séance${fitCount > 1 ? "s" : ""} FIT retrouvée${fitCount > 1 ? "s" : ""}, dont ${runningFitCount} en course`
          : "Aucune séance FIT structurée retrouvée dans les archives"
      );
      setText(
        "[data-analysis-hrv]",
        analysis.benchmarks?.hrv_28d != null
          ? `${String(analysis.benchmarks.hrv_28d).replace(".", ",")} ms`
          : "Donnée insuffisante"
      );
      setText(
        "[data-analysis-sleep]",
        analysis.benchmarks?.sleep_score_28d != null
          ? `${Math.round(analysis.benchmarks.sleep_score_28d)}/100`
          : "Donnée insuffisante"
      );
      setText(
        "[data-analysis-resting]",
        analysis.benchmarks?.resting_hr_28d != null
          ? `${Math.round(analysis.benchmarks.resting_hr_28d)} bpm`
          : "Donnée insuffisante"
      );
      const trendText = (value, unit, inverse = false) => {
        if (value == null) return "Tendance 7 jours indisponible";
        const sign = value > 0 ? "+" : "";
        const direction = value === 0 ? "stable" : ((value > 0) !== inverse ? "en hausse" : "en baisse");
        return `7 j : ${sign}${String(value).replace(".", ",")}${unit} · ${direction}`;
      };
      setText("[data-analysis-hrv-trend]", trendText(analysis.benchmarks?.hrv_change_7d, " ms"));
      setText("[data-analysis-sleep-trend]", trendText(analysis.benchmarks?.sleep_change_7d, " pt"));
      setText("[data-analysis-resting-trend]", trendText(analysis.benchmarks?.resting_hr_change_7d, " bpm", true));
      const freshness = analysis.confidence?.freshness_days;
      setText("[data-analysis-freshness]", freshness == null
        ? "Fraîcheur inconnue"
        : (freshness === 0 ? "Synchronisé aujourd’hui" : `Dernière donnée : il y a ${freshness} j`));
      setText("[data-analysis-confidence-text]", analysis.confidence?.explanation);
      setText("[data-analysis-notice]", analysis.medical_notice);

      const renderList = (selector, values) => {
        const list = document.querySelector(selector);
        if (!list) return;
        list.replaceChildren();
        (values || []).forEach(value => {
          const item = document.createElement("li");
          item.textContent = value;
          list.appendChild(item);
        });
      };
      renderList("[data-analysis-strengths]", analysis.strengths);
      renderList("[data-analysis-vigilance]", analysis.vigilance);
      renderList("[data-analysis-priorities]", analysis.priorities);

      const longitudinal = analysis.longitudinal_report;
      const conclusionsRoot = document.querySelector("[data-longitudinal-conclusions]");
      if (conclusionsRoot) {
        conclusionsRoot.replaceChildren();
        (longitudinal?.conclusions || []).forEach(conclusion => {
          const article = document.createElement("article");
          const statement = String(conclusion.conclusion || "").toLowerCase();
          article.dataset.tone = /retrait|défavor|surveill|variable|risque/.test(statement) ? "vigilance"
            : /stable|progress|favorable|régulier/.test(statement) ? "positive" : "neutral";
          article.innerHTML = `
            <div><span>${conclusion.topic}</span><b>${conclusion.confidence}/100 de confiance</b></div>
            <strong>${conclusion.conclusion}</strong>
            <small>${conclusion.evidence}</small>
          `;
          conclusionsRoot.appendChild(article);
        });
        if (!conclusionsRoot.children.length) {
          conclusionsRoot.textContent = "Historique encore insuffisant pour formuler une conclusion argumentée.";
        }
      }
      renderList("[data-longitudinal-missing]", longitudinal?.missing_data);

      const comparison = analysis.performance_comparison;
      setText(
        "[data-performance-message]",
        comparison?.message || "Comparaison indisponible."
      );
      const formatContext = group => {
        const rows = [
          ["Sommeil avant", group?.sleep_score_before, "/100"],
          ["VFC avant", group?.hrv_before_ms, " ms"],
          ["Récupération avant", group?.recovery_before, "/100"],
          ["Indice Atlas avant", group?.atlas_index_before, "/100"],
          ["Effort perçu après", group?.perceived_effort_after, "/10"],
          ["Sensation après", group?.sensation_after, "/10"],
          ["Fatigue après", group?.fatigue_after, "/10"],
          ["Douleur après", group?.pain_after, "/10"]
        ];
        return rows.filter(([_label, value]) => value != null);
      };
      const renderContext = (selector, group) => {
        const target = document.querySelector(selector);
        if (!target) return;
        target.replaceChildren();
        formatContext(group).forEach(([label, value, unit]) => {
          const term = document.createElement("dt");
          term.textContent = label;
          const detail = document.createElement("dd");
          detail.textContent = `${String(value).replace(".", ",")}${unit}`;
          target.append(term, detail);
        });
        if (!target.children.length) {
          const detail = document.createElement("dd");
          detail.textContent = "Contexte Wellness insuffisant";
          target.appendChild(detail);
        }
      };
      setText(
        "[data-best-score]",
        comparison?.best
          ? `${String(comparison.best.execution_score).replace(".", ",")}/100`
          : "—"
      );
      setText(
        "[data-difficult-score]",
        comparison?.difficult
          ? `${String(comparison.difficult.execution_score).replace(".", ",")}/100`
          : "—"
      );
      renderContext("[data-best-context]", comparison?.best);
      renderContext("[data-difficult-context]", comparison?.difficult);
    }

    setText(
      "[data-index-summary]",
      payload.index_explanation?.summary
    );
    if (!partial) renderIndexComponents(indexSource.atlas_index_components);

    const sync = document.querySelector(".sync-state");
    if (sync) {
      const ageDays = Math.floor((Date.now() - latestDay.getTime()) / 86400000);
      const unavailable = payload.latest_unavailable;
      if (unavailable?.partial) {
        sync.lastChild.textContent =
          ` Sommeil reçu le ${latestDay.toLocaleDateString("fr-FR")} · bilan physiologique partiel`;
        sync.classList.add("is-stale");
      } else if (unavailable?.day) {
        const missingDay = new Date(`${unavailable.day}T12:00:00`);
        sync.lastChild.textContent =
          ` Nuit du ${missingDay.toLocaleDateString("fr-FR")} non mesurée · ` +
          `dernières données fiables : ${completeDayLabel}`;
        sync.classList.add("is-stale");
      } else {
        sync.lastChild.textContent =
          isCurrentDay
            ? ` Données du ${latestDay.toLocaleDateString("fr-FR")}`
            : ` Dernières données : ${latestDay.toLocaleDateString("fr-FR")}`;
        sync.classList.toggle("is-stale", !isCurrentDay || ageDays > 1);
      }
    }
  };

  fetch("/api/atlas/wellness-history", { cache: "no-store" })
    .then(async response => {
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : null;
      if (!response.ok) {
        const message = response.status === 404
          ? "Redémarrez le serveur Atlas mis à jour"
          : (payload?.error || `Erreur Wellness ${response.status}`);
        throw new Error(message);
      }
      return payload;
    })
    .then(updateCockpit)
    .catch(error => {
      console.warn("Atlas Wellness :", error);
      document.querySelectorAll(".metrics small").forEach(element => {
        if (element.textContent === "Chargement…") {
          element.textContent = error.message;
        }
      });
      const sync = document.querySelector(".sync-state");
      if (sync) {
        sync.classList.add("is-stale");
        sync.lastChild.textContent = " API Wellness indisponible";
        sync.title = error.message;
      }
    });

  fetch("/api/atlas/sync-insights", { cache: "no-store" })
    .then(response => response.ok ? response.json() : null)
    .then(renderSyncInsights)
    .catch(error => console.warn("Atlas synchronisation :", error));

  const dashboardPanel = document.querySelector("[data-dashboard-panel]");
  const dashboardKey = "atlasCockpitVisibleMetrics";
  const dashboardInputs = [...document.querySelectorAll("[data-dashboard-panel] input")];
  const applyDashboard = () => {
    let selected;
    try { selected = JSON.parse(localStorage.getItem(dashboardKey) || "null"); } catch (_error) { selected = null; }
    if (!Array.isArray(selected)) selected = dashboardInputs.map(input => input.value);
    dashboardInputs.forEach(input => { input.checked = selected.includes(input.value); });
    document.querySelectorAll("[data-dashboard-metric]").forEach(element => {
      element.classList.toggle("is-dashboard-hidden", !selected.includes(element.dataset.dashboardMetric));
    });
  };
  applyDashboard();
  dashboardInputs.forEach(input => input.addEventListener("change", () => {
    const selected = dashboardInputs.filter(item => item.checked).map(item => item.value);
    localStorage.setItem(dashboardKey, JSON.stringify(selected));
    applyDashboard();
  }));
  document.querySelector("[data-dashboard-settings]")?.addEventListener("click", () => { if (dashboardPanel) dashboardPanel.hidden = false; });
  document.querySelector("[data-dashboard-close]")?.addEventListener("click", () => { if (dashboardPanel) dashboardPanel.hidden = true; });

  document.querySelectorAll("[data-water]").forEach(button => button.addEventListener("click", async () => {
    button.disabled = true;
    try { await saveNutrition({ type: "hydration", volume_ml: Number(button.dataset.water), name: "Eau" }); }
    catch (error) { setText("[data-nutrition-status]", error.message); }
    finally { button.disabled = false; }
  }));
  document.querySelector("[data-nutrition-form]")?.addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    Object.keys(values).forEach(key => { if (values[key] === "") delete values[key]; });
    setText("[data-nutrition-status]", "Enregistrement…");
    try { await saveNutrition({ type: "nutrition", ...values }); form.reset(); setText("[data-nutrition-status]", "Apport enregistré."); }
    catch (error) { setText("[data-nutrition-status]", error.message); }
  });
  loadNutrition();

  const popover = document.querySelector("[data-index-popover]");
  document.querySelector("[data-index-info]")?.addEventListener("click", () => {
    if (popover) popover.hidden = false;
  });
  document.querySelector("[data-index-close]")?.addEventListener("click", () => {
    if (popover) popover.hidden = true;
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && popover) popover.hidden = true;
  });

  document.querySelectorAll("[data-atlas-talk]").forEach(button => {
    button.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent(
        "atlas:conversation-open",
        { detail: { context: "cockpit" } }
      ));
    });
  });
})();
