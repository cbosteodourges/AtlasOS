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
      sync.lastChild.textContent =
        ageDays <= 1
          ? ` Données du ${latestDay.toLocaleDateString("fr-FR")}`
          : ` Dernières données : ${latestDay.toLocaleDateString("fr-FR")}`;
      sync.classList.toggle("is-stale", ageDays > 1);
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
