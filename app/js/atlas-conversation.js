"use strict";

(() => {
  const suggestions = [
    "Ma récupération aujourd’hui",
    "Ma prochaine séance",
    "Signaler une douleur"
  ];
  const root = document.createElement("div");
  root.className = "atlas-conversation-backdrop";
  root.hidden = true;
  root.innerHTML = `
    <section class="atlas-conversation" role="dialog" aria-modal="true" aria-labelledby="atlasConversationTitle">
      <button class="atlas-conversation-close" type="button" aria-label="Fermer">×</button>
      <header><span class="atlas-conversation-orb">✦</span><div><strong id="atlasConversationTitle">Parler à Atlas</strong><small>Posez une question ou dictez un ressenti</small></div></header>
      <p class="atlas-conversation-intro">Choisissez une proposition ou écrivez simplement ce que vous ressentez.</p>
      <div class="atlas-conversation-suggestions" aria-label="Propositions"></div>
      <div class="atlas-conversation-log" aria-live="polite"><div class="atlas-message atlas">Bonjour Christophe. Comment puis-je vous aider ?</div></div>
      <details class="atlas-feeling-details"><summary>Ajouter mon ressenti (facultatif)</summary>
        <div class="atlas-feeling">
          <label>Énergie<select data-feeling="energy"><option value="">—</option><option value="2">Très basse</option><option value="4">Basse</option><option value="6">Moyenne</option><option value="8">Bonne</option><option value="10">Excellente</option></select></label>
          <label>Fatigue<select data-feeling="fatigue"><option value="">—</option><option value="0">Aucune</option><option value="3">Légère</option><option value="6">Modérée</option><option value="8">Forte</option><option value="10">Très forte</option></select></label>
          <label>Douleur<select data-feeling="pain"><option value="">—</option><option value="0">Aucune</option><option value="2">Légère</option><option value="5">Modérée</option><option value="8">Importante</option><option value="10">Très importante</option></select></label>
        </div>
      </details>
      <form class="atlas-conversation-form">
        <div class="atlas-conversation-input">
          <textarea name="message" maxlength="1200" placeholder="Votre question ou votre ressenti…" required></textarea>
          <button class="atlas-voice-button" type="button" aria-label="Démarrer la dictée" title="Démarrer la dictée">🎙</button>
        </div>
        <button class="atlas-send-button" type="submit">Envoyer</button>
        <small class="atlas-conversation-privacy">Enregistré localement. Atlas n’adapte rien sans votre validation.</small>
      </form>
    </section>
  `;
  document.body.appendChild(root);

  const log = root.querySelector(".atlas-conversation-log");
  const form = root.querySelector("form");
  const textarea = form.elements.message;
  const submit = root.querySelector(".atlas-send-button");
  const voice = root.querySelector(".atlas-voice-button");
  const suggestionsRoot = root.querySelector(".atlas-conversation-suggestions");

  const addMessage = (text, role, meta) => {
    const bubble = document.createElement("div");
    bubble.className = `atlas-message ${role}`;
    bubble.textContent = text;
    if (meta) {
      const small = document.createElement("small");
      small.textContent = meta;
      bubble.appendChild(small);
    }
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  };

  const setSuggestions = values => {
    suggestionsRoot.replaceChildren();
    (values?.length ? values.slice(0, 3) : suggestions).forEach(text => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = text;
      button.addEventListener("click", () => {
        textarea.value = text;
        textarea.focus();
      });
      suggestionsRoot.appendChild(button);
    });
  };
  setSuggestions(suggestions);

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let dictating = false;
  let restartTimer = null;
  let initialText = "";
  let finalText = "";

  const updateVoiceButton = listening => {
    voice.classList.toggle("is-listening", listening);
    voice.textContent = listening ? "■ Stop" : "🎙";
    voice.setAttribute("aria-label", listening ? "Arrêter la dictée" : "Démarrer la dictée");
    voice.title = listening ? "Arrêter la dictée" : "Démarrer la dictée";
  };

  const stopDictation = () => {
    dictating = false;
    clearTimeout(restartTimer);
    updateVoiceButton(false);
    try { recognition?.stop(); } catch (_error) {}
  };

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "fr-FR";
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.addEventListener("start", () => updateVoiceButton(true));
    recognition.addEventListener("result", event => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const words = event.results[index][0].transcript.trim();
        if (event.results[index].isFinal) {
          finalText = [finalText, words].filter(Boolean).join(" ");
        } else {
          interim = [interim, words].filter(Boolean).join(" ");
        }
      }
      textarea.value = [initialText, finalText, interim].filter(Boolean).join(" ").trim();
    });
    recognition.addEventListener("end", () => {
      if (dictating) {
        restartTimer = setTimeout(() => {
          try { recognition.start(); } catch (_error) {}
        }, 250);
      } else {
        updateVoiceButton(false);
      }
    });
    recognition.addEventListener("error", event => {
      if (!["no-speech", "aborted"].includes(event.error)) {
        stopDictation();
        addMessage(
          "La dictée vocale a été interrompue. Vérifiez l’autorisation du microphone.",
          "atlas",
          event.error
        );
      }
    });

    voice.addEventListener("click", async () => {
      if (dictating) {
        stopDictation();
        textarea.focus();
        return;
      }
      try {
        if (!window.isSecureContext) {
          throw new Error("La dictée nécessite une connexion sécurisée ou localhost.");
        }
        if (navigator.mediaDevices?.getUserMedia) {
          const stream = await navigator.mediaDevices.getUserMedia({audio: true});
          stream.getTracks().forEach(track => track.stop());
        }
        initialText = textarea.value.trim();
        finalText = "";
        dictating = true;
        recognition.start();
      } catch (error) {
        stopDictation();
        addMessage(
          "Le microphone n’est pas accessible. Autorisez-le dans les paramètres du site.",
          "atlas",
          error.message
        );
      }
    });
  } else {
    voice.disabled = true;
    voice.title = "Dictée vocale non disponible dans ce navigateur";
  }

  const open = () => {
    root.hidden = false;
    document.body.style.overflow = "hidden";
    setTimeout(() => textarea.focus(), 0);
  };
  const close = () => {
    stopDictation();
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
  root.addEventListener("click", event => { if (event.target === root) close(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !root.hidden) close(); });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    stopDictation();
    const message = textarea.value.trim();
    if (!message || submit.disabled) return;
    const feeling = {};
    root.querySelectorAll("[data-feeling]").forEach(select => {
      if (select.value !== "") feeling[select.dataset.feeling] = Number(select.value);
    });
    addMessage(message, "user");
    textarea.value = "";
    submit.disabled = true;
    submit.textContent = "Analyse…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch("/api/atlas/conversation", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message, feeling}),
        signal: controller.signal
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Atlas indisponible");
      addMessage(payload.response, "atlas", payload.mode);
      setSuggestions(payload.suggestions);
    } catch (error) {
      const timeoutMessage = error.name === "AbortError"
        ? "Atlas a mis trop de temps à répondre. La requête a été arrêtée après 15 secondes."
        : "Atlas n’est pas joignable. Vérifiez que le serveur Atlas est démarré.";
      addMessage(timeoutMessage, "atlas", error.message);
    } finally {
      clearTimeout(timeout);
      submit.disabled = false;
      submit.textContent = "Envoyer";
      textarea.focus();
    }
  });
})();
