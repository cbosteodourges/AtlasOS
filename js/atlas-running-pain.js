(() => {
  const groups = [
    ["Pied et cheville", [
      ["achilles", "Tendon d’Achille", "Charge tendineuse à réduire temporairement ; surveiller douleur matinale et raideur."],
      ["plantar", "Voûte plantaire", "Surveiller douleur au premier pas, chaussures et progression de charge."],
      ["metatarsal", "Têtes métatarsiennes", "Une douleur osseuse très localisée impose de suspendre les impacts et de faire évaluer rapidement."],
      ["ankle_medial", "Cheville · face interne", "Évaluer stabilité, gonflement et douleur à l’appui."],
      ["ankle_lateral", "Cheville · face externe", "Évaluer stabilité ligamentaire, gonflement et douleur à l’appui."]
    ]],
    ["Jambe", [
      ["shin", "Bord interne du tibia", "Compatible avec une surcharge tibiale ; réduire les impacts si la douleur progresse."],
      ["tibialis", "Jambier antérieur", "Surveiller la charge en côte, la chaussure et les releveurs du pied."],
      ["extensors", "Tendons releveurs des orteils", "Desserrer le laçage et contrôler la charge ne remplacent pas une évaluation si la douleur persiste."],
      ["tibial_tuberosity", "Tubérosité tibiale antérieure", "Chez l’adolescent, toute douleur persistante liée à la croissance mérite un avis professionnel."]
    ]],
    ["Genou", [
      ["patellar_mid", "Tendon rotulien", "Gérer la charge de saut et de course ; le renforcement progressif doit rester tolérable."],
      ["patellar_pole", "Pôle inférieur de la rotule", "Zone souvent sensible aux contraintes de saut et de freinage."],
      ["patellofemoral", "Autour de la rotule", "Contrôler tolérance aux escaliers, flexions et volume de course."],
      ["it_band", "Face externe du genou", "Examiner progression de charge, contrôle du bassin et force fessière."],
      ["quadriceps_tendon", "Tendon du quadriceps", "Réduire la charge irritante et réintroduire progressivement la force."],
      ["meniscus_medial", "Interligne interne du genou", "Douleur à l’appui, blocage ou perte d’extension nécessitent une évaluation."],
      ["meniscus_lateral", "Interligne externe du genou", "Douleur à l’appui, blocage ou gonflement nécessitent une évaluation."]
    ]],
    ["Bassin et région fessière", [
      ["adductors", "Adducteurs / pubis", "Surveiller douleur à l’appui unipodal, accélérations et changements de direction."],
      ["piriformis", "Piriforme", "Une douleur fessière irradiée ou accompagnée de signes neurologiques doit être évaluée."],
      ["glute_max", "Grand fessier", "Adapter la charge et vérifier force, mobilité et tolérance à l’effort."],
      ["glute_med", "Moyen fessier / grand trochanter", "Surveiller douleur en appui latéral et contrôle du bassin."]
    ]]
  ];

  const host = document.querySelector(".analysis-panel");
  if (!host) return;

  const section = document.createElement("section");
  section.className = "runner-pain-panel";
  section.innerHTML = `
    <header><span>REPÉRAGE RAPIDE</span><h2>Où avez-vous mal ?</h2>
    <p>Sélectionnez une zone directement, même sans manipuler le modèle 3D.</p></header>
    <div class="pain-groups"></div>
    <p class="pain-safety"><strong>Orientation, pas diagnostic.</strong> Arrêtez les impacts et demandez rapidement un avis en cas d’impossibilité d’appui, déformation, gonflement brutal, articulation rouge et chaude, fièvre, engourdissement, blocage, douleur nocturne ou douleur osseuse très localisée.</p>
  `;
  host.append(section);
  const list = section.querySelector(".pain-groups");

  groups.forEach(([title, points]) => {
    const group = document.createElement("details");
    group.open = title === "Pied et cheville";
    group.innerHTML = `<summary>${title}</summary><div></div>`;
    const body = group.querySelector("div");
    points.forEach(([id, label, advice]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.painId = id;
      button.textContent = label;
      button.addEventListener("click", () => openReport(id, label, advice));
      body.append(button);
    });
    list.append(group);
  });

  const dialog = document.createElement("dialog");
  dialog.className = "pain-dialog";
  dialog.innerHTML = `
    <form method="dialog">
      <button class="pain-close" value="cancel" aria-label="Fermer">×</button>
      <span>DOULEUR SIGNALÉE</span><h2 id="painTitle"></h2><p id="painAdvice"></p>
      <label>Côté<select id="painSide"><option>Gauche</option><option>Droite</option><option>Bilatéral</option><option>Central</option></select></label>
      <label>Intensité au repos <input id="painRest" type="range" min="0" max="10" value="0"><output id="painRestOut">0/10</output></label>
      <label>Intensité à l’effort <input id="painEffort" type="range" min="0" max="10" value="3"><output id="painEffortOut">3/10</output></label>
      <label>Depuis quand ?<select id="painOnset"><option>Aujourd’hui</option><option>2 à 7 jours</option><option>1 à 6 semaines</option><option>Plus de 6 semaines</option></select></label>
      <label class="pain-check"><input id="painWeight" type="checkbox"> Douleur ou difficulté à l’appui</label>
      <label>Précision<textarea id="painNote" placeholder="Début, geste déclencheur, évolution, gonflement…"></textarea></label>
      <p class="pain-warning" id="painWarning" hidden>Cette déclaration comporte un signal de vigilance. Mettez les impacts en pause et demandez un avis professionnel.</p>
      <button class="pain-save" value="default">Enregistrer dans mon historique</button>
    </form>
  `;
  document.body.append(dialog);

  let active = null;
  function openReport(id, label, advice) {
    active = { id, label };
    dialog.querySelector("#painTitle").textContent = label;
    dialog.querySelector("#painAdvice").textContent = advice;
    dialog.showModal();
  }
  ["painRest", "painEffort"].forEach(id => {
    const input = dialog.querySelector("#" + id);
    input.addEventListener("input", () => {
      dialog.querySelector("#" + id + "Out").textContent = input.value + "/10";
      updateWarning();
    });
  });
  dialog.querySelector("#painWeight").addEventListener("change", updateWarning);
  function updateWarning() {
    const alert = Number(dialog.querySelector("#painRest").value) >= 7 ||
      Number(dialog.querySelector("#painEffort").value) >= 8 ||
      dialog.querySelector("#painWeight").checked ||
      active?.id === "metatarsal";
    dialog.querySelector("#painWarning").hidden = !alert;
  }
  dialog.addEventListener("close", () => {
    if (dialog.returnValue !== "default" || !active) return;
    const report = {
      id: crypto.randomUUID?.() || String(Date.now()),
      zone_id: active.id, zone_label: active.label,
      side: dialog.querySelector("#painSide").value,
      rest_intensity: Number(dialog.querySelector("#painRest").value),
      effort_intensity: Number(dialog.querySelector("#painEffort").value),
      onset: dialog.querySelector("#painOnset").value,
      weight_bearing_problem: dialog.querySelector("#painWeight").checked,
      note: dialog.querySelector("#painNote").value.trim(),
      recorded_at: new Date().toISOString()
    };
    const key = "atlas.running_pain_reports.v1";
    const history = JSON.parse(localStorage.getItem(key) || "[]");
    history.push(report);
    localStorage.setItem(key, JSON.stringify(history));
    section.querySelector("header p").textContent = "Douleur enregistrée dans l’historique local Atlas.";
  });

  document.querySelector("#painButton")?.addEventListener("click", () => {
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  });
})();
