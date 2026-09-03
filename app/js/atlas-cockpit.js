"use strict";

(() => {
  const analysis = document.querySelector(".athlete-analysis-home");
  const analysisToggle = document.querySelector(".mobile-analysis-toggle");
  const athleteProfileLink = document.querySelector(".athlete-profile-link");
  if (analysis && analysisToggle) {
    analysis.classList.add("is-mobile-collapsed");
    const setAnalysisOpen = opening => {
      analysis.classList.toggle("is-mobile-open", opening);
      analysis.classList.toggle("is-mobile-collapsed", !opening);
      analysisToggle.setAttribute("aria-expanded", String(opening));
      analysisToggle.textContent = opening ? "Réduire l’analyse" : "Voir l’analyse complète";
    };
    analysisToggle.addEventListener("click", () => setAnalysisOpen(!analysis.classList.contains("is-mobile-open")));
    athleteProfileLink?.addEventListener("click", event => {
      event.preventDefault();
      setAnalysisOpen(true);
      analysis.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  document.querySelectorAll(".insight-lanes > article").forEach((lane, index) => {
    const content = lane.querySelector("ul, ol");
    const heading = lane.querySelector("h3");
    if (!content || !heading) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mobile-lane-toggle";
    button.setAttribute("aria-expanded", "false");
    button.textContent = "Afficher les repères";
    heading.insertAdjacentElement("afterend", button);
    lane.classList.add("is-mobile-lane-collapsed");
    button.addEventListener("click", () => {
      const opening = lane.classList.toggle("is-mobile-lane-open");
      lane.classList.toggle("is-mobile-lane-collapsed", !opening);
      button.setAttribute("aria-expanded", String(opening));
      button.textContent = opening ? "Masquer les repères" : "Afficher les repères";
    });
  });

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

  const physiologyStatusLabel = status => ({
    estimated: "Estimation Atlas",
    longitudinal: "Estimation longitudinale",
    longitudinal_estimate: "Estimation longitudinale",
    validated: "Référence validée",
    validated_threshold_reference: "Référence de seuil validée",
    measured: "Mesure validée",
    session_adjusted_estimate: "Ajustement issu de la dernière séance"
  }[status] || "Référence Atlas");

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
      setText("[data-physiology-sv1-hr]", physiology.sv1?.heart_rate_bpm != null ? `${physiology.sv1.heart_rate_bpm} bpm · ${physiologyStatusLabel(physiology.sv1.status)}` : "FC à confirmer");
      setText("[data-physiology-sv2]", physiology.sv2?.speed_kmh != null ? `${decimal(physiology.sv2.speed_kmh)} km/h` : "—");
      setText("[data-physiology-sv2-hr]", physiology.sv2?.heart_rate_bpm != null ? `${physiology.sv2.heart_rate_bpm} bpm · ${physiologyStatusLabel(physiology.sv2.status)}` : "FC à confirmer");
      setText("[data-physiology-hrmax]", physiology.maximum_heart_rate_bpm != null ? `${physiology.maximum_heart_rate_bpm} bpm` : "—");
    }
  };

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
      const energy = analysis.energy_signature;
      setText("[data-energy-headline]", energy?.headline || "Signature énergétique en construction");
      setText("[data-energy-summary]", energy?.summary || "Atlas attend des séances FIT exploitables.");
      setText("[data-energy-confidence]", energy?.confidence ?? "—");
      setText(
        "[data-energy-competition-title]",
        energy?.competition?.status === "available" ? "Compétitions retrouvées" : "Historique à identifier"
      );
      setText("[data-energy-competition]", energy?.competition?.message);
      setText("[data-energy-cellular]", energy?.cellular_interpretation);
      const energyRoot = document.querySelector("[data-energy-domains]");
      if (energyRoot) {
        energyRoot.replaceChildren();
        (energy?.domains || []).forEach(domain => {
          const article = document.createElement("article");
          const score = domain.score == null ? null : Math.max(0, Math.min(100, Number(domain.score)));
          const trendTone = domain.trend === "en progression"
            ? "up"
            : domain.trend === "stable"
              ? "stable"
              : domain.trend === "en retrait"
                ? "down"
                : "unknown";
          const trendLabel = domain.trend === "en progression"
            ? "Progression"
            : domain.trend === "stable"
              ? "Maintien"
              : domain.trend === "en retrait"
                ? "Baisse"
                : "À confirmer";
          article.className = `energy-domain energy-domain-${domain.key}`;
          article.dataset.trend = trendTone;
          if (domain.key === energy?.dominant_domain) article.classList.add("is-dominant");
          article.innerHTML = `
            <div><span>${domain.short}</span><b>${domain.label}</b>${domain.key === energy?.dominant_domain ? "<em>Point fort</em>" : ""}</div>
            <strong>${score == null ? "—" : Math.round(score)}<small>/100</small></strong>
            <i><span style="width:${score || 0}%"></span></i>
            <p>${domain.session_count ? `Niveau calculé à partir de ${domain.session_count} séance${domain.session_count > 1 ? "s" : ""} classée${domain.session_count > 1 ? "s" : ""} dans cette filière.` : "Données insuffisantes pour caractériser cette filière."}</p>
            <span class="energy-trend" data-trend="${trendTone}">${trendLabel}</span>
          `;
          energyRoot.appendChild(article);
        });
      }
      const family = energy?.family_progression;
      setText("[data-family-headline]", family?.headline || "Endurance Z1–Z2 en construction");
      setText("[data-family-summary]", family?.summary || "Atlas recherche des séances comparables.");
      setText("[data-family-hr]", family?.reference_heart_rate_bpm != null ? `${family.reference_heart_rate_bpm} bpm` : "—");
      setText("[data-family-sessions]", family ? `${family.session_count} séance${family.session_count > 1 ? "s" : ""} retenue${family.session_count > 1 ? "s" : ""}` : "");
      setText("[data-family-speed]", family?.recent?.speed_at_reference_hr_kmh != null ? `${String(family.recent.speed_at_reference_hr_kmh).replace(".", ",")} km/h` : "—");
      setText("[data-family-speed-before]", family?.early?.speed_at_reference_hr_kmh != null ? `contre ${String(family.early.speed_at_reference_hr_kmh).replace(".", ",")} km/h auparavant` : "Mesure en attente");
      setText("[data-family-drift]", family?.recent?.median_drift_percent != null ? `${String(family.recent.median_drift_percent).replace(".", ",")} %` : "Non mesurée");
      setText("[data-family-confidence]", family ? `Confiance ${family.confidence}/100` : "");
      setText("[data-family-method]", family?.method || "Atlas compare uniquement des sorties d’endurance de qualité suffisante.");
      setText("[data-family-exclusions]", family ? `${family.excluded} séance${family.excluded > 1 ? "s" : ""} écartée${family.excluded > 1 ? "s" : ""} car non comparable${family.excluded > 1 ? "s" : ""}.` : "");
      const familyTrend = document.querySelector("[data-family-trend]");
      if (familyTrend) {
        const labels = { up: "↗ Progression", stable: "→ Maintien", down: "↘ Régression", insufficient: "À confirmer" };
        familyTrend.dataset.trend = family?.trend || "insufficient";
        const trendPercent = Number(family?.trend_percent);
        const percentage = Number.isFinite(trendPercent)
          ? ` · ${trendPercent > 0 ? "+" : ""}${String(trendPercent).replace(".", ",")} %`
          : "";
        familyTrend.textContent = `${labels[family?.trend] || labels.insufficient}${percentage}`;
      }
      const familyChart = document.querySelector("[data-family-chart]");
      const familySvg = familyChart?.querySelector("svg");
      const familyMessage = document.querySelector("[data-family-chart-message]");
      const familyPoints = (family?.points || []).filter(point => Number.isFinite(Number(point.equivalent_speed_kmh)));
      if (familySvg) {
        familySvg.replaceChildren();
        if (familyPoints.length >= 2) {
          familyChart.classList.remove("is-empty");
          if (familyMessage) familyMessage.hidden = true;
          const ns = "http://www.w3.org/2000/svg";
          const values = familyPoints.map(point => Number(point.equivalent_speed_kmh));
          const min = Math.min(...values);
          const max = Math.max(...values);
          const spread = Math.max(.5, max - min);
          const plot = { left: 72, right: 928, top: 25, bottom: 220 };
          const yFor = value => plot.bottom - ((value - (min - spread * .2)) / (spread * 1.4)) * (plot.bottom - plot.top);
          [0, .5, 1].forEach(ratio => {
            const y = plot.top + ratio * (plot.bottom - plot.top);
            const line = document.createElementNS(ns, "line");
            line.setAttribute("x1", plot.left); line.setAttribute("x2", plot.right);
            line.setAttribute("y1", y); line.setAttribute("y2", y); line.setAttribute("class", "family-chart-grid");
            familySvg.appendChild(line);
          });
          const coords = familyPoints.map((point, index) => ({
            ...point,
            x: plot.left + index * ((plot.right - plot.left) / Math.max(1, familyPoints.length - 1)),
            y: yFor(Number(point.equivalent_speed_kmh)),
          }));
          const area = document.createElementNS(ns, "path");
          area.setAttribute("d", `M ${coords[0].x} ${plot.bottom} L ${coords.map(point => `${point.x} ${point.y}`).join(" L ")} L ${coords.at(-1).x} ${plot.bottom} Z`);
          area.setAttribute("class", "family-chart-area");
          familySvg.appendChild(area);
          const line = document.createElementNS(ns, "polyline");
          line.setAttribute("points", coords.map(point => `${point.x},${point.y}`).join(" "));
          line.setAttribute("class", "family-chart-line");
          familySvg.appendChild(line);
          coords.forEach(point => {
            const dot = document.createElementNS(ns, "circle");
            dot.setAttribute("cx", point.x); dot.setAttribute("cy", point.y); dot.setAttribute("r", 5);
            dot.setAttribute("class", "family-chart-point");
            const title = document.createElementNS(ns, "title");
            title.textContent = `${point.day} · ${point.equivalent_speed_kmh} km/h à FC comparable`;
            dot.appendChild(title); familySvg.appendChild(dot);
          });
          [[coords[0], familyPoints[0].day], [coords.at(-1), familyPoints.at(-1).day]].forEach(([point, label]) => {
            const text = document.createElementNS(ns, "text");
            text.setAttribute("x", point.x); text.setAttribute("y", 252);
            text.setAttribute("text-anchor", point === coords[0] ? "start" : "end");
            text.setAttribute("class", "family-chart-label"); text.textContent = label;
            familySvg.appendChild(text);
          });
        } else {
          familyChart?.classList.add("is-empty");
          if (familyMessage) { familyMessage.hidden = false; familyMessage.textContent = family?.summary || "Quatre séances comparables sont nécessaires."; }
        }
      }
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
          ? `${Math.round(physiology.sv1_heart_rate_bpm)} bpm · ${physiologyStatusLabel(physiology.sv1_status)}`
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
          ? `${Math.round(physiology.sv2_heart_rate_bpm)} bpm · ${physiologyStatusLabel(physiology.sv2_status)}`
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
          .filter(item => !cutoff || new Date(item.timestamp || item.day) >= cutoff)
          .map(item => ({
            day: item.day,
            timestamp: item.timestamp || item.day,
            value: Number(item[selectedPhysiologyMetric]),
            kind: item.kind,
            method: item.method,
            confidence: item.confidence,
            adjustedMetrics: item.adjusted_metrics || [],
          }))
          .filter(item => Number.isFinite(item.value) && item.value > 0)
          .sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)));
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
        const axisMin = min - spread * 0.22;
        const axisMax = max + spread * 0.22;
        const plot = { left: 82, right: 930, top: 32, bottom: 244 };
        const coords = points.map((point, index) => {
          const x = plot.left + index * ((plot.right - plot.left) / Math.max(1, points.length - 1));
          const y = plot.bottom - ((point.value - axisMin) / (axisMax - axisMin)) * (plot.bottom - plot.top);
          return { ...point, x, y };
        });
        const ns = "http://www.w3.org/2000/svg";
        const [, chartUnit] = metricMeta[selectedPhysiologyMetric];
        Array.from({ length: 5 }, (_, index) => index).forEach(index => {
          const y = plot.top + index * ((plot.bottom - plot.top) / 4);
          const value = axisMax - index * ((axisMax - axisMin) / 4);
          const line = document.createElementNS(ns, "line");
          line.setAttribute("x1", String(plot.left)); line.setAttribute("x2", String(plot.right));
          line.setAttribute("y1", String(y)); line.setAttribute("y2", String(y));
          line.setAttribute("class", "chart-grid"); chartSvg.appendChild(line);
          const tick = document.createElementNS(ns, "text");
          tick.setAttribute("x", String(plot.left - 12)); tick.setAttribute("y", String(y + 4));
          tick.setAttribute("text-anchor", "end"); tick.setAttribute("class", "chart-axis-label");
          tick.textContent = `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })}`;
          chartSvg.appendChild(tick);
        });
        const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
        const meanY = plot.bottom - ((mean - axisMin) / (axisMax - axisMin)) * (plot.bottom - plot.top);
        const meanLine = document.createElementNS(ns, "line");
        meanLine.setAttribute("x1", String(plot.left)); meanLine.setAttribute("x2", String(plot.right));
        meanLine.setAttribute("y1", String(meanY)); meanLine.setAttribute("y2", String(meanY));
        meanLine.setAttribute("class", "chart-mean"); chartSvg.appendChild(meanLine);
        const meanLabel = document.createElementNS(ns, "text");
        meanLabel.setAttribute("x", String(plot.right - 5)); meanLabel.setAttribute("y", String(meanY - 7));
        meanLabel.setAttribute("text-anchor", "end"); meanLabel.setAttribute("class", "chart-mean-label");
        meanLabel.textContent = `Moyenne ${mean.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} ${chartUnit}`;
        chartSvg.appendChild(meanLabel);
        const area = document.createElementNS(ns, "path");
        area.setAttribute("d", `M ${coords[0].x} ${plot.bottom} L ${coords.map(p => `${p.x} ${p.y}`).join(" L ")} L ${coords.at(-1).x} ${plot.bottom} Z`);
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
          const measuredAt = new Date(point.timestamp);
          const dateLabel = measuredAt.toLocaleDateString("fr-FR");
          const timeLabel = point.timestamp.includes("T")
            ? ` à ${measuredAt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`
            : "";
          title.textContent = `${dateLabel}${timeLabel} · ${label} ${point.value.toLocaleString("fr-FR")} ${unit}`;
          circle.appendChild(title);
          chartSvg.appendChild(circle);
        });
        const datePoints = [...new Set([0, Math.floor((coords.length - 1) / 2), coords.length - 1])].map(index => coords[index]);
        datePoints.forEach((point, index) => {
          const label = document.createElementNS(ns, "text");
          label.setAttribute("x", String(point.x));
          label.setAttribute("y", "274");
          label.setAttribute("text-anchor", index === 0 ? "start" : index === datePoints.length - 1 ? "end" : "middle");
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
        const adjustmentCount = points.filter(point => point.kind === "validated" && point.adjustedMetrics.length).length;
        if (chartNote) chartNote.textContent = adjustmentCount
          ? `${adjustmentCount} ajustement${adjustmentCount > 1 ? "s" : ""} issu${adjustmentCount > 1 ? "s" : ""} des séances · chaque modification validée est enregistrée automatiquement.`
          : estimatedCount
            ? `${estimatedCount} point${estimatedCount > 1 ? "s" : ""} rétrospectif${estimatedCount > 1 ? "s" : ""} Atlas, calculé${estimatedCount > 1 ? "s" : ""} depuis les séances disponibles.`
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
      const setTrend = (selector, value, unit, inverse = false) => {
        const target = document.querySelector(selector);
        if (!target) return;
        if (value == null) {
          target.textContent = "Tendance 7 jours indisponible";
          target.dataset.trend = "unknown";
          return;
        }
        const sign = value > 0 ? "+" : "";
        const favorable = (value > 0) !== inverse;
        const stable = Math.abs(Number(value)) < 0.25;
        const direction = stable ? "maintien" : favorable ? "progression" : "baisse";
        target.dataset.trend = stable ? "stable" : favorable ? "up" : "down";
        target.textContent = `7 j : ${sign}${String(value).replace(".", ",")}${unit} · ${direction}`;
      };
      setTrend("[data-analysis-hrv-trend]", analysis.benchmarks?.hrv_change_7d, " ms");
      setTrend("[data-analysis-sleep-trend]", analysis.benchmarks?.sleep_change_7d, " pt");
      setTrend("[data-analysis-resting-trend]", analysis.benchmarks?.resting_hr_change_7d, " bpm", true);
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
        const entries = values || [];
        const section = list.closest("article");
        if (section) section.dataset.itemCount = String(entries.length);
        entries.forEach((value, index) => {
          const item = document.createElement("li");
          item.style.setProperty("--item-index", String(index + 1));
          item.textContent = value;
          list.appendChild(item);
        });
      };
      renderList("[data-analysis-strengths]", analysis.strengths);
      renderList("[data-analysis-vigilance]", analysis.vigilance);
      renderList("[data-analysis-priorities]", analysis.priorities);

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
  const dashboardInputs = [...document.querySelectorAll("[data-dashboard-panel] input[type='checkbox']")];
  const themeInputs = [...document.querySelectorAll("input[name='atlas-theme']")];
  const canvasInputs = [...document.querySelectorAll("input[name='atlas-canvas']")];
  const sidebarInputs = [...document.querySelectorAll("input[name='atlas-sidebar']")];
  const themeKey = "atlasAppearanceTheme";
  const applyTheme = theme => {
    const supported = ["night", "ocean", "graphite", "aurora", "forest", "violet", "ember", "deepsea", "lagoon", "plum", "rose", "sand-card", "frost", "white"];
    const selected = supported.includes(theme) ? theme : "night";
    document.body.dataset.atlasTheme = selected;
    themeInputs.forEach(input => { input.checked = input.value === selected; });
  };
  applyTheme(localStorage.getItem(themeKey) || "night");
  themeInputs.forEach(input => input.addEventListener("change", () => {
    localStorage.setItem(themeKey, input.value);
    applyTheme(input.value);
  }));
  const canvasKey = "atlasAppearanceCanvas";
  const applyCanvas = canvas => {
    const supported = ["cosmos", "pearl", "mist", "sand", "ice", "sage", "white", "sky", "lavender", "blush", "slate"];
    const selected = supported.includes(canvas) ? canvas : "cosmos";
    document.body.dataset.atlasCanvas = selected;
    canvasInputs.forEach(input => { input.checked = input.value === selected; });
  };
  applyCanvas(localStorage.getItem(canvasKey) || "cosmos");
  canvasInputs.forEach(input => input.addEventListener("change", () => {
    localStorage.setItem(canvasKey, input.value);
    applyCanvas(input.value);
  }));
  const sidebarKey = "atlasAppearanceSidebar";
  const applySidebar = sidebar => {
    const supported = ["atlas", "ocean", "graphite", "forest", "violet", "copper", "ice", "pearl"];
    const selected = supported.includes(sidebar) ? sidebar : "atlas";
    document.body.dataset.atlasSidebar = selected;
    sidebarInputs.forEach(input => { input.checked = input.value === selected; });
  };
  applySidebar(localStorage.getItem(sidebarKey) || "atlas");
  sidebarInputs.forEach(input => input.addEventListener("change", () => {
    localStorage.setItem(sidebarKey, input.value);
    applySidebar(input.value);
  }));
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
