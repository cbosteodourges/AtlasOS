(() => {
  const regions = [
    { id: "foot", label: "Pied", hint: "Dessous, dessus, avant-pied ou talon", zones: [
      ["plantar", "Voûte plantaire / talon", "fascia ou surcharge plantaire"],
      ["metatarsal", "Têtes métatarsiennes", "douleur osseuse ou surcharge de l’avant-pied"],
      ["toe_extensors", "Dessus du pied / releveurs", "tendons extenseurs ou contrainte de chaussure"]
    ]},
    { id: "ankle", label: "Cheville", hint: "Arrière, face interne ou externe", zones: [
      ["achilles", "Tendon d’Achille", "raideur matinale ou douleur tendineuse"],
      ["ankle_medial", "Face interne", "complexe ligamentaire ou tendon tibial postérieur"],
      ["ankle_lateral", "Face externe", "complexe ligamentaire latéral ou tendons fibulaires"]
    ]},
    { id: "leg", label: "Jambe", hint: "Tibia, mollet ou face antérieure", zones: [
      ["shin", "Bord interne du tibia", "surcharge tibiale diffuse"],
      ["focal_tibia", "Point osseux très localisé", "atteinte osseuse à exclure"],
      ["tibialis", "Jambier antérieur", "muscle ou tendon antérieur"],
      ["calf", "Mollet", "soléaire ou gastrocnémiens"]
    ]},
    { id: "knee", label: "Genou", hint: "Rotule, tendons, côtés ou interligne", zones: [
      ["patellofemoral", "Autour / derrière la rotule", "douleur fémoro-patellaire"],
      ["patellar_mid", "Tendon rotulien", "douleur tendineuse sous la rotule"],
      ["patellar_pole", "Pôle inférieur de la rotule", "zone d’insertion du tendon"],
      ["tibial_tuberosity", "Tubérosité tibiale antérieure", "zone de croissance chez l’adolescent"],
      ["quadriceps_tendon", "Tendon du quadriceps", "douleur au-dessus de la rotule"],
      ["it_band", "Face externe", "bandelette ilio-tibiale"],
      ["meniscus_medial", "Interligne interne", "douleur articulaire interne"],
      ["meniscus_lateral", "Interligne externe", "douleur articulaire externe"]
    ]},
    { id: "thigh", label: "Cuisse", hint: "Avant, arrière, intérieur ou extérieur", zones: [
      ["quadriceps", "Quadriceps", "surcharge ou lésion musculaire antérieure"],
      ["hamstrings", "Ischio-jambiers", "muscle ou tendon postérieur"],
      ["adductors", "Adducteurs", "douleur médiale ou pubienne"]
    ]},
    { id: "hip", label: "Hanche et aine", hint: "Aine, côté ou bassin", zones: [
      ["groin", "Aine / pubis", "profil adducteur, ilio-psoas, inguinal ou pubien"],
      ["hip_joint", "Pli de hanche", "origine articulaire ou ilio-psoas à explorer"],
      ["greater_trochanter", "Côté du grand trochanter", "tendons fessiers ou douleur latérale"]
    ]},
    { id: "glute", label: "Région fessière", hint: "Centre, côté ou insertion", zones: [
      ["piriformis", "Fesse profonde", "piriforme ou origine neurologique à distinguer"],
      ["glute_max", "Grand fessier", "surcharge musculaire"],
      ["glute_med", "Moyen fessier", "corps musculaire ou tendon latéral"]
    ]},
    { id: "back", label: "Dos et bassin", hint: "Lombaires, sacrum ou articulation sacro-iliaque", zones: [
      ["lumbar", "Région lombaire", "douleur mécanique ou irradiée"],
      ["sacrum", "Sacrum / bassin", "douleur osseuse ou sacro-iliaque"]
    ]}
  ];

  const cockpit = document.querySelector(".cockpit");
  if (!cockpit) return;
  document.body.classList.add("health-guided-ready");

  const guided = document.createElement("main");
  guided.className = "health-pain-guide";
  guided.innerHTML = `
    <header class="pain-guide-head">
      <div><span>ATLAS SANTÉ · PARCOURS GUIDÉ</span><h1>Signaler une douleur</h1>
      <p>Localisez simplement la zone. Atlas décrit les observations, vérifie les signaux de vigilance et prépare une proposition pour Atlas Coach.</p></div>
      <button type="button" id="advancedAnatomy">Anatomie 3D avancée</button>
    </header>
    <nav class="pain-steps" aria-label="Étapes">
      <b class="active">1 · Région</b><b>2 · Zone</b><b>3 · Contexte</b><b>4 · Orientation</b>
    </nav>
    <section class="pain-layout">
      <aside class="pain-avatar-card">
        <div class="pain-avatar" aria-label="Carte corporelle simplifiée">
          <div class="avatar-head"></div><div class="avatar-trunk"></div>
          <div class="avatar-leg avatar-leg-left"></div><div class="avatar-leg avatar-leg-right"></div>
          <span class="avatar-side">FACE</span>
        </div>
        <p>Choisissez d’abord une région. Le modèle anatomique détaillé reste disponible en second niveau.</p>
      </aside>
      <div>
        <section id="painRegions" class="pain-stage active"><h2>Où se situe la douleur ?</h2><div class="region-grid"></div></section>
        <section id="painZones" class="pain-stage"><button class="pain-back" type="button">← Régions</button><h2 id="regionTitle"></h2><p id="regionHint"></p><div class="zone-grid"></div></section>
        <section id="painContext" class="pain-stage">
          <button class="pain-back" type="button">← Zones</button><h2 id="zoneTitle"></h2><p class="orientation-note" id="zoneNote"></p>
          <div class="pain-form-grid">
            <label>Côté<select id="painSide"><option>Gauche</option><option>Droite</option><option>Bilatéral</option><option>Central</option></select></label>
            <label>Depuis quand ?<select id="painOnset"><option>Aujourd’hui</option><option>2 à 7 jours</option><option>1 à 6 semaines</option><option>Plus de 6 semaines</option></select></label>
            <label>Douleur au repos <input id="painRest" type="range" min="0" max="10" value="0"><output>0/10</output></label>
            <label>Douleur à la course <input id="painEffort" type="range" min="0" max="10" value="3"><output>3/10</output></label>
          </div>
          <fieldset><legend>Ce qui accompagne la douleur</legend>
            <label><input type="checkbox" value="weight"> Appui ou marche difficile</label>
            <label><input type="checkbox" value="swelling"> Gonflement rapide ou important</label>
            <label><input type="checkbox" value="locking"> Blocage ou perte de mouvement</label>
            <label><input type="checkbox" value="neuro"> Engourdissement ou faiblesse</label>
            <label><input type="checkbox" value="redhot"> Zone rouge, chaude ou fièvre</label>
            <label><input type="checkbox" value="night"> Douleur nocturne ou au repos</label>
          </fieldset>
          <label class="pain-note">Précisions<textarea id="painNote" placeholder="Geste déclencheur, évolution, relief, chaussures, séance récente…"></textarea></label>
          <button class="pain-primary" id="analysePain" type="button">Analyser et préparer la proposition</button>
        </section>
        <section id="painResult" class="pain-stage" aria-live="polite"></section>
      </div>
    </section>
    <footer class="pain-disclaimer"><strong>Atlas oriente, il ne diagnostique pas.</strong> Une modification du programme n’est jamais appliquée silencieusement : la proposition doit être expliquée puis validée par l’utilisateur.</footer>
  `;
  cockpit.parentNode.insertBefore(guided, cockpit);

  let chosenRegion = null;
  let chosenZone = null;
  const stages = [...guided.querySelectorAll(".pain-stage")];
  const steps = [...guided.querySelectorAll(".pain-steps b")];
  const show = index => {
    stages.forEach((stage, i) => stage.classList.toggle("active", i === index));
    steps.forEach((step, i) => step.classList.toggle("active", i <= index));
    guided.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const regionGrid = guided.querySelector(".region-grid");
  regions.forEach(region => {
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `<strong>${region.label}</strong><small>${region.hint}</small>`;
    button.onclick = () => {
      chosenRegion = region;
      guided.querySelector("#regionTitle").textContent = region.label;
      guided.querySelector("#regionHint").textContent = region.hint;
      const zoneGrid = guided.querySelector(".zone-grid");
      zoneGrid.replaceChildren();
      region.zones.forEach(([id, label, note]) => {
        const zone = document.createElement("button");
        zone.type = "button";
        zone.innerHTML = `<strong>${label}</strong><small>${note}</small>`;
        zone.onclick = () => {
          chosenZone = { id, label, note };
          guided.querySelector("#zoneTitle").textContent = label;
          guided.querySelector("#zoneNote").textContent = "Profil possible à explorer : " + note + ". Cette indication ne constitue pas un diagnostic.";
          show(2);
        };
        zoneGrid.append(zone);
      });
      show(1);
    };
    regionGrid.append(button);
  });

  guided.querySelectorAll(".pain-back").forEach((button, index) => button.onclick = () => show(index));
  guided.querySelectorAll('input[type="range"]').forEach(input => input.oninput = () => input.nextElementSibling.textContent = input.value + "/10");

  guided.querySelector("#advancedAnatomy").onclick = () => {
    document.body.classList.toggle("atlas-anatomy-advanced");
    const advanced = document.body.classList.contains("atlas-anatomy-advanced");
    guided.querySelector("#advancedAnatomy").textContent = advanced ? "Revenir au parcours guidé" : "Anatomie 3D avancée";
    cockpit.hidden = !advanced;
    if (advanced) {
      cockpit.scrollIntoView({ behavior: "smooth" });
      setTimeout(() => window.dispatchEvent(new Event("resize")), 100);
    }
  };
  cockpit.hidden = true;

  guided.querySelector("#analysePain").onclick = () => {
    const checked = [...guided.querySelectorAll('#painContext input[type="checkbox"]:checked')].map(x => x.value);
    const rest = Number(guided.querySelector("#painRest").value);
    const effort = Number(guided.querySelector("#painEffort").value);
    const focalBone = ["metatarsal", "focal_tibia", "sacrum"].includes(chosenZone?.id);
    const red = checked.some(x => ["swelling", "locking", "neuro", "redhot"].includes(x)) || (focalBone && checked.includes("weight"));
    const amber = !red && (checked.length > 0 || rest >= 5 || effort >= 6 || focalBone);
    const level = red ? "vigilance" : amber ? "prudence" : "surveillance";
    const title = red ? "Suspendre les impacts et demander un avis professionnel" :
      amber ? "Réduire provisoirement la charge irritante" : "Surveiller sans modifier automatiquement le programme";
    const coach = red ? "Atlas Coach prépare le remplacement des séances avec impacts par du repos ou une activité sans impact, après validation." :
      amber ? "Atlas Coach peut proposer une baisse du volume, une séance facile ou du vélo, après validation." :
      "Le programme reste inchangé. Atlas suit l’évolution avant et après les prochaines séances.";
    const report = {
      id: crypto.randomUUID?.() || String(Date.now()), recorded_at: new Date().toISOString(),
      region_id: chosenRegion?.id, region_label: chosenRegion?.label,
      zone_id: chosenZone?.id, zone_label: chosenZone?.label,
      side: guided.querySelector("#painSide").value, onset: guided.querySelector("#painOnset").value,
      rest_intensity: rest, effort_intensity: effort, flags: checked,
      note: guided.querySelector("#painNote").value.trim(), triage_level: level
    };
    const canonicalKey = "atlas.health.pain_reports.v2";
    const anatomyLegacyKey = "atlas.running_pain_reports.v2";
    const readReports = key => {
      try {
        const stored = JSON.parse(localStorage.getItem(key) || "[]");
        return Array.isArray(stored) ? stored : [];
      } catch (_) {
        return [];
      }
    };
    const canonicalReports = readReports(canonicalKey);
    if (!canonicalReports.some(item => item?.id === report.id)) canonicalReports.unshift(report);
    localStorage.setItem(canonicalKey, JSON.stringify(canonicalReports));
    const anatomyReports = readReports(anatomyLegacyKey);
    if (!anatomyReports.some(item => item?.id === report.id)) anatomyReports.push(report);
    localStorage.setItem(anatomyLegacyKey, JSON.stringify(anatomyReports));
    window.dispatchEvent(new CustomEvent("atlas:pain-report-saved", { detail: report }));
    guided.querySelector("#painResult").innerHTML = `
      <span class="result-level ${level}">${level}</span><h2>${title}</h2>
      <p><strong>${chosenRegion.label} · ${chosenZone.label} · ${report.side}</strong><br>Repos ${rest}/10 · Course ${effort}/10 · ${report.onset.toLowerCase()}.</p>
      <div class="coach-impact"><span>IMPACT ATLAS COACH</span><p>${coach}</p></div>
      <p class="result-safety">${red ? "Ce signal ne doit pas attendre une adaptation automatique du plan." : "Réévaluez la douleur dans 24 heures et après la prochaine activité tolérée."}</p>
      <button class="pain-primary" id="newPain" type="button">Ajouter ou réévaluer une douleur</button>
    `;
    guided.querySelector("#newPain").onclick = () => show(0);
    show(3);
  };
})();