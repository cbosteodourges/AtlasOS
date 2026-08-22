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

  const formatDuration = minutes => {
    if (minutes === null || minutes === undefined || minutes === "") return null;
    if (!Number.isFinite(Number(minutes))) return null;
    const total = Math.round(Number(minutes));
    return `${Math.floor(total / 60)} h ${String(total % 60).padStart(2, "0")}`;
  };

  const recoveryLabel = score => {
    if (score >= 85) return "Excellente";
    if (score >= 70) return "Bonne";
    if (score >= 55) return "Modérée";
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

  const updateCockpit = payload => {
    const latest = payload.latest;
    if (!latest) return;

    setText("[data-atlas-index]", latest.atlas_index ?? "—");
    setText("[data-recovery-label]", recoveryLabel(latest.atlas_index));
    setText(
      "[data-recovery-detail]",
      latest.sleep_recovery_score != null
        ? `Sommeil récupérateur ${latest.sleep_recovery_score}/100`
        : "Indice Atlas du jour"
    );

    const duration = formatDuration(latest.sleep_duration_minutes);
    setText(
      "[data-sleep-value]",
      duration || (latest.sleep_score != null ? `${latest.sleep_score}/100` : "—")
    );
    setText(
      "[data-sleep-detail]",
      latest.sleep_quality_score != null
        ? `Qualité ${latest.sleep_quality_score} %`
        : "Donnée Garmin la plus récente"
    );

    setText(
      "[data-hrv-value]",
      latest.hrv_last_night_ms != null
        ? `${Math.round(latest.hrv_last_night_ms)} ms`
        : "—"
    );
    setText(
      "[data-hrv-detail]",
      latest.hrv_weekly_average_ms != null
        ? `Moyenne 7 j : ${Math.round(latest.hrv_weekly_average_ms)} ms`
        : (latest.hrv_status || "Référence en construction")
    );

    setText("[data-load-value]", loadLabel(latest.training_load));
    setText(
      "[data-load-detail]",
      latest.training_load != null
        ? `Charge Garmin : ${Math.round(latest.training_load)}`
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
        setText("[data-next-session-date]", `PROCHAINE SÉANCE · ${label.toUpperCase()}`);
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
    renderIndexComponents(latest.atlas_index_components);

    const sync = document.querySelector(".sync-state");
    if (sync) {
      const latestDay = new Date(`${latest.day}T12:00:00`);
      const ageDays = Math.floor((Date.now() - latestDay.getTime()) / 86400000);
      const unavailable = payload.latest_unavailable;
      if (unavailable?.day) {
        const missingDay = new Date(`${unavailable.day}T12:00:00`);
        sync.lastChild.textContent =
          ` Nuit du ${missingDay.toLocaleDateString("fr-FR")} non mesurée · ` +
          `dernières données fiables : ${latestDay.toLocaleDateString("fr-FR")}`;
        sync.classList.add("is-stale");
      } else {
        sync.lastChild.textContent =
          ageDays <= 1
            ? ` Données du ${latestDay.toLocaleDateString("fr-FR")}`
            : ` Dernières données : ${latestDay.toLocaleDateString("fr-FR")}`;
        sync.classList.toggle("is-stale", ageDays > 1);
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
