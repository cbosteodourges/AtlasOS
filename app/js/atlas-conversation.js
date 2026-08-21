"use strict";

(() => {
  const root = document.createElement("div");
  root.className = "atlas-conversation-backdrop";
  root.hidden = true;
  root.innerHTML = `
    <section class="atlas-conversation atlas-adaptation" role="dialog" aria-modal="true" aria-labelledby="atlasAdaptationTitle">
      <button class="atlas-conversation-close" type="button" aria-label="Fermer">×</button>
      <header>
        <span class="atlas-conversation-orb">↻</span>
        <div>
          <strong id="atlasAdaptationTitle">Adapter ma séance</strong>
          <small>Moteur local Atlas · aucune IA distante sollicitée</small>
        </div>
      </header>
      <p class="atlas-conversation-intro">Quatre réponses suffisent. Atlas les croise uniquement avec les données présentes sur votre ordinateur.</p>
      <form class="atlas-guided-form">
        <div class="atlas-guided-grid">
          <label><span><b>1</b> Quelle est votre énergie ?</span>
            <select data-feeling="energy" required>
              <option value="2">Très basse</option><option value="4">Basse</option><option value="6" selected>Moyenne</option><option value="8">Bonne</option><option value="10">Excellente</option>
            </select>
          </label>
          <label><span><b>2</b> Quelle fatigue ressentez-vous ?</span>
            <select data-feeling="fatigue" required>
              <option value="0">Aucune</option><option value="3" selected>Légère</option><option value="6">Modérée</option><option value="8">Forte</option><option value="10">Très forte</option>
            </select>
          </label>
          <label><span><b>3</b> Ressentez-vous une douleur ?</span>
            <select data-feeling="pain" required>
              <option value="0" selected>Aucune</option><option value="2">Légère</option><option value="5">Modérée</option><option value="8">Importante</option><option value="10">Très importante</option>
            </select>
          </label>
          <label><span><b>4</b> Que souhaitez-vous faire ?</span>
            <select name="preference" required>
              <option value="planned">Suivre le programme</option>
              <option value="endurance">Endurance facile</option>
              <option value="threshold">Seuil</option>
              <option value="vo2max">VO₂max</option>
              <option value="bike">Vélo endurance</option>
              <option value="rest">Repos ou mobilité</option>
            </select>
          </label>
        </div>
        <details class="atlas-guided-details">
          <summary>Ajouter une précision facultative</summary>
          <label class="atlas-guided-note">Votre précision
            <span class="atlas-note-input">
              <textarea name="note" maxlength="400" placeholder="Ex. jambes lourdes, douleur au tendon, nuit perturbée…"></textarea>
              <button class="atlas-voice-button" type="button" aria-label="Dicter cette précision" title="Dicter cette précision">🎙</button>
            </span>
            <small class="atlas-voice-status" aria-live="polite">Touchez le microphone puis acceptez l’autorisation affichée par le navigateur.</small>
          </label>
        </details>
        <aside class="atlas-microphone-help" hidden>
          <strong>Autoriser le microphone</strong>
          <p>Dans Chrome, touchez le cadenas ou l’icône à gauche de l’adresse, ouvrez « Autorisations », puis choisissez « Microphone : Autoriser ».</p>
        </aside>
        <button class="atlas-send-button" type="submit">Analyser mon état</button>
      </form>
      <section class="atlas-adaptation-result" hidden aria-live="polite">
        <div class="atlas-adaptation-summary"></div>
        <div class="atlas-adaptation-options"></div>
        <details class="atlas-knowledge"><summary>Ce qu’Atlas sait — et ne sait pas</summary><div></div></details>
        <small>Atlas propose et explique. Votre programme n’est jamais modifié sans votre choix.</small>
      </section>
    </section>
  `;
  document.body.appendChild(root);

  const form = root.querySelector(".atlas-guided-form");
  const submit = form.querySelector(".atlas-send-button");
  const result = root.querySelector(".atlas-adaptation-result");
  const summary = root.querySelector(".atlas-adaptation-summary");
  const optionsRoot = root.querySelector(".atlas-adaptation-options");
  const note = form.elements.note;
  const voice = root.querySelector(".atlas-voice-button");
  const voiceStatus = root.querySelector(".atlas-voice-status");
  const microphoneHelp = root.querySelector(".atlas-microphone-help");
  const knowledgeRoot = root.querySelector(".atlas-knowledge div");
  let lastPayload = null;

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition && window.isSecureContext) {
    const recognition = new SpeechRecognition();
    let listening = false;
    recognition.lang = "fr-FR";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.addEventListener("start", () => {
      listening = true;
      voice.classList.add("is-listening");
      voice.textContent = "●";
      voiceStatus.textContent = "Je vous écoute…";
    });
    recognition.addEventListener("result", event => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      note.value = [note.value.trim(), transcript].filter(Boolean).join(" ");
      voiceStatus.textContent = transcript
        ? "Dictée ajoutée. Vous pouvez la corriger avant l’envoi."
        : "Aucune parole reconnue.";
      note.focus();
    });
    recognition.addEventListener("error", event => {
      const messages = {
        "not-allowed": "Microphone refusé. Suivez les étapes affichées juste dessous.",
        "service-not-allowed": "Reconnaissance vocale indisponible dans Chrome.",
        "no-speech": "Aucune parole détectée. Réessayez en parlant après le signal.",
        "audio-capture": "Aucun microphone utilisable n’a été détecté."
      };
      voiceStatus.textContent =
        messages[event.error] || `Erreur du microphone : ${event.error}`;
      if (["not-allowed", "service-not-allowed"].includes(event.error)) {
        microphoneHelp.hidden = false;
      }
    });
    recognition.addEventListener("end", () => {
      listening = false;
      voice.classList.remove("is-listening");
      voice.textContent = "🎙";
    });
    voice.addEventListener("click", async () => {
      if (listening) {
        recognition.stop();
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});
        stream.getTracks().forEach(track => track.stop());
        microphoneHelp.hidden = true;
        recognition.start();
      } catch (_error) {
        voiceStatus.textContent = "Microphone bloqué. Autorisez-le dans les réglages du site, puis réessayez.";
        microphoneHelp.hidden = false;
      }
    });
    if (navigator.permissions?.query) {
      navigator.permissions.query({name: "microphone"}).then(permission => {
        microphoneHelp.hidden = permission.state !== "denied";
        if (permission.state === "denied") {
          voiceStatus.textContent = "Microphone actuellement bloqué pour ce site.";
        }
        permission.addEventListener?.("change", () => {
          microphoneHelp.hidden = permission.state !== "denied";
        });
      }).catch(() => {});
    }
  } else {
    voice.addEventListener("click", () => note.focus());
    voice.textContent = "⌨";
    voiceStatus.textContent = window.isSecureContext
      ? "Reconnaissance vocale indisponible : utilisez le microphone du clavier de votre téléphone."
      : "Sur cette adresse locale non sécurisée, utilisez le microphone du clavier du téléphone.";
  }

  const post = async payload => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    let response;
    try {
      response = await fetch("/api/atlas/conversation", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
        signal: controller.signal
      });
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Atlas met trop de temps à répondre. Réessayez dans quelques secondes.");
      throw new Error("Connexion au serveur Atlas impossible.");
    } finally {
      clearTimeout(timeout);
    }
    let data;
    try { data = await response.json(); }
    catch (_error) { throw new Error("Réponse Atlas illisible. Relancez le serveur local."); }
    if (!response.ok) throw new Error(data.error || "Atlas indisponible");
    if (!data.assessment || !Array.isArray(data.options)) {
      throw new Error("Le serveur Atlas utilise encore l’ancienne version. Arrêtez-le puis relancez tools\\atlas_web_server.py.");
    }
    return data;
  };

  const recordChoice = async option => {
    optionsRoot.querySelectorAll("button").forEach(button => { button.disabled = true; });
    try {
      const data = await post({...lastPayload, selected_option: option.id});
      localStorage.setItem("atlasAdaptationSelection", JSON.stringify({
        recordedAt: new Date().toISOString(),
        option,
        assessment: data.assessment
      }));
      summary.innerHTML = `<strong>Choix enregistré</strong><p>${data.response}</p>`;
      optionsRoot.replaceChildren();
      window.dispatchEvent(new CustomEvent("atlas:adaptation-selected", {detail: {option, assessment: data.assessment}}));
    } catch (error) {
      summary.innerHTML = `<strong>Enregistrement impossible</strong><p>${error.message}</p>`;
      optionsRoot.querySelectorAll("button").forEach(button => { button.disabled = false; });
    }
  };

  const render = data => {
    result.hidden = false;
    summary.innerHTML = `
      <div class="atlas-adaptation-score"><b>${data.assessment.score}</b><span>/100<br>disponibilité ajustée</span></div>
      <div><strong>${data.assessment.title}</strong><p>${data.response}</p><small>${data.assessment.evidence.join(" · ")}</small></div>
    `;
    optionsRoot.replaceChildren();
    knowledgeRoot.replaceChildren();
    const knowledge = data.knowledge || {};
    [
      ["Atlas sait", knowledge.knows || []],
      ["Atlas ne sait pas", knowledge.does_not_know || []]
    ].forEach(([title, values]) => {
      const section = document.createElement("section");
      const heading = document.createElement("strong");
      const list = document.createElement("ul");
      heading.textContent = title;
      values.forEach(value => {
        const item = document.createElement("li");
        item.textContent = value;
        list.appendChild(item);
      });
      section.append(heading, list);
      knowledgeRoot.appendChild(section);
    });
    data.options.forEach(option => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = option.recommended ? "is-recommended" : "";
      button.innerHTML = `<span>${option.recommended ? "Recommandé" : "Option"}</span><strong>${option.title}</strong><small>${option.description}</small>`;
      button.addEventListener("click", () => recordChoice(option));
      optionsRoot.appendChild(button);
    });
    result.scrollIntoView({behavior: "smooth", block: "nearest"});
  };

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const feeling = {};
    root.querySelectorAll("[data-feeling]").forEach(select => {
      feeling[select.dataset.feeling] = Number(select.value);
    });
    lastPayload = {
      mode: "guided_adaptation",
      feeling,
      preference: form.elements.preference.value,
      note: form.elements.note.value.trim()
    };
    submit.disabled = true;
    submit.textContent = "Calcul en cours…";
    try {
      render(await post(lastPayload));
    } catch (error) {
      result.hidden = false;
      summary.innerHTML = `<strong>Atlas n’est pas disponible</strong><p>${error.message}</p>`;
      optionsRoot.replaceChildren();
    } finally {
      submit.disabled = false;
      submit.textContent = "Analyser mon état";
    }
  });

  const open = () => {
    root.hidden = false;
    document.body.style.overflow = "hidden";
    result.hidden = true;
    knowledgeRoot.replaceChildren();
    setTimeout(() => form.querySelector("select")?.focus(), 0);
  };
  const close = () => {
    root.hidden = true;
    document.body.style.overflow = "";
  };

  document.addEventListener("click", event => {
    if (event.target.closest("[data-atlas-talk]")) {
      event.preventDefault();
      open();
    }
  });
  window.addEventListener("atlas:conversation-open", open);
  root.querySelector(".atlas-conversation-close").addEventListener("click", close);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !root.hidden) close(); });
})();
