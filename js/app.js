/* ==========================================================
   ATLAS OS v0.3
   Application principale
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    // ======================================
    // Splash Screen
    // ======================================

    const splash = document.getElementById("splash");
    const app = document.getElementById("app");

    setTimeout(() => {

        splash.style.display = "none";

        app.style.opacity = "1";

    }, 3500);


    // ======================================
    // Animation du texte
    // ======================================

    const typing = document.getElementById("typing");

    const message = "Racontez-moi votre histoire.";

    typing.textContent = "";

    let index = 0;

    function writeText() {

        if (index < message.length) {

            typing.textContent += message.charAt(index);

            index++;

            setTimeout(writeText, 40);

        }

    }

    writeText();


    // ======================================
    // Bouton principal
    // ======================================

    const startButton = document.getElementById("startButton");

    startButton.addEventListener("click", () => {

        startConversation();

    });

});


/* ==========================================================
   Première conversation Atlas
========================================================== */

function startConversation() {

    const hero = document.querySelector(".hero");

    hero.innerHTML = `

        <h1>Bonjour.</h1>

        <h2>Je suis Atlas.</h2>

        <p>

        Je vais apprendre à connaître votre corps.

        <br><br>

        Chaque douleur possède une histoire.

        <br><br>

        Commençons simplement.

        </p>

        <button id="nextQuestion">

            Commencer

        </button>

    `;

    document
        .getElementById("nextQuestion")
        .addEventListener("click", firstQuestion);

}


/* ==========================================================
   Première question
========================================================== */

function firstQuestion() {

    const hero = document.querySelector(".hero");

    hero.innerHTML = `

        <h1>Première étape</h1>

        <h2>Je vous écoute.</h2>

        <p>

        Racontez-moi votre histoire.

        <br><br>

        Depuis quand avez-vous mal ?

        </p>

        <textarea

            id="patientStory"

            placeholder="Expliquez librement ce qui vous amène aujourd'hui..."

        ></textarea>

        <button id="continueButton">

            Continuer

        </button>

    `;

    document
        .getElementById("continueButton")
        .addEventListener("click", saveStory);

}


/* ==========================================================
   Sauvegarde temporaire
========================================================== */

function saveStory() {

    const text = document
        .getElementById("patientStory")
        .value;

    localStorage.setItem("atlas_story", text);

    showSummary();

}


/* ==========================================================
   Résumé
========================================================== */

function showSummary() {

    const story = localStorage.getItem("atlas_story");

    const hero = document.querySelector(".hero");

    hero.innerHTML = `

        <h1>Merci.</h1>

        <h2>Votre histoire est enregistrée.</h2>

        <p>

        ${story}

        <br><br>

        Dans les prochaines versions,

        Atlas analysera automatiquement

        votre récit,

        vos douleurs,

        votre historique,

        vos données Garmin,

        votre sommeil,

        votre VFC,

        votre biomécanique

        et construira votre

        Jumeau Biomécanique Numérique.

        </p>

        <button onclick="location.reload()">

            Recommencer

        </button>

    `;

}
