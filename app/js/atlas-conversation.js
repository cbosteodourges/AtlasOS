"use strict";

(() => {
  const suggestions = [
    "Suis-je suffisamment récupéré pour ma prochaine séance ?",
    "Explique-moi l’objectif de la séance du jour.",
    "Pourquoi ma VFC a-t-elle évolué ?",
    "Je ressens une douleur : que dois-je renseigner ?",
    "Sur quoi dois-je travailler cette semaine ?"
  ];

  const root = document.createElement("div");
  root.className = "atlas-conversation-backdrop";
  root.hidden = true;
  root.innerHTML = `
    <section class="atlas-conversation" role="dialog" aria-modal="true" aria-labelledby="atlasConversationTitle">
      <button class="atlas-conversation-close" type="button" aria-label="Fermer">×</button>
      <header><span class="atlas-conversation-orb">✦</span><div><strong id="atlasConversationTitle">Parler à Atlas</strong><small>Assistant local explicable · vos données restent sur cet ordinateur</small></div></header>
      <p class="atlas-conversation-intro">Décrivez votre forme, votre sommeil, une douleur ou demandez une explication sur votre programme. Atlas propose et explique ; vous gardez toujours la décision finale.</p>
      <div class="atlas-conversation-suggestions" aria-label="Questions suggérées"></div>
      <div class="atlas-conversation-log" aria-live="polite"><div class="atlas-message atlas">Bonjour Christophe. Que souhaitez-vous comprendre ou signaler aujourd’hui ?</div></div>
      <div class="atlas-feeling">
        <label>Énergie<select data-feeling="energy"><option value="">Non renseignée</option><option value="2">Très basse</option><option value="4">Basse</option><option value="6">Moyenne</option><option value="8">Bonne</option><option value="10">Excellente</option></select></label>
        <label>Fatigue<select data-feeling="fatigue"><option value="">Non renseignée</option><option value="0">Aucune</option><option value="3">Légère</option><option value="6">Modérée</option><option value="8">Forte</option><option value="10">Très forte</option></select></label>
        <label>Douleur<select data-feeling="pain"><option value="">Non renseignée</option><option value="0">Aucune</option><option value="2">Légère</option><option value="5">Modérée</option><option value="8">Importante</option><option value="10">Très importante</option></select></label>
      </div>
      <form class="atlas-conversation-form">
        <textarea name="message" maxlength="1200" placeholder="Écrivez votre question ou votre ressenti…" required></textarea>
        <button type="submit">Envoyer</button>
        <small class="atlas-conversation-privacy">Journal enregistré localement dans la mémoire privée Atlas. Aucune adaptation du programme n’est appliquée sans validation.</small>
      </form>
    </section>
  `;
  document.body.appendChild(root);

  const log = root.querySelector(".atlas-conversation-log");
  const form = root.querySelector("form");
  const textarea = form.elements.message;
  const submit = form.querySelector("button");
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
  };

  const setSuggestions = values => {
    suggestionsRoot.replaceChildren();
    (values || suggestions).forEach(text => {
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

  const open = () => {
    root.hidden = false;
    document.body.style.overflow = "hidden";
    setTimeout(() => textarea.focus(), 0);
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
  root.addEventListener("click", event => {
    if (event.target === root) close();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !root.hidden) close();
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const message = textarea.value.trim();
    if (!message) return;
    const feeling = {};
    root.querySelectorAll("[data-feeling]").forEach(select => {
      if (select.value !== "") feeling[select.dataset.feeling] = Number(select.value);
    });
    addMessage(message, "user");
    textarea.value = "";
    submit.disabled = true;
    submit.textContent = "Analyse…";
    try {
      const response = await fetch("/api/atlas/conversation", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message, feeling})
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Atlas indisponible");
      addMessage(payload.response, "atlas", payload.mode);
      setSuggestions(payload.suggestions);
    } catch (error) {
      addMessage(
        "Le moteur de dialogue n’est pas encore joignable. Redémarrez le serveur Atlas puis réessayez.",
        "atlas",
        error.message
      );
    } finally {
      submit.disabled = false;
      submit.textContent = "Envoyer";
      textarea.focus();
    }
  });
})();
