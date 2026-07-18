/*=====================================================
 ATLAS OS V1.0
 app.js
=====================================================*/

document.addEventListener("DOMContentLoaded", () => {

const intro = document.getElementById("intro");
const sync = document.getElementById("sync");
const assistant = document.getElementById("assistant");
const dashboard = document.getElementById("dashboard");

const enterButton = document.getElementById("enterButton");
const continueButton = document.getElementById("continueButton");
const analyseBtn = document.getElementById("analyseBtn");


//========================================
// Apparition de l'intro
//========================================

intro.classList.add("fade-in");


//========================================
// Créer mon jumeau
//========================================

enterButton.addEventListener("click", () => {

intro.style.opacity="0";
intro.style.transform="scale(.95)";

setTimeout(()=>{

intro.classList.add("hidden");

sync.classList.remove("hidden");

sync.classList.add("fade-in");

window.scrollTo(0,0);

},700);

});


//========================================
// Continuer
//========================================

continueButton.addEventListener("click",()=>{

sync.style.opacity="0";

setTimeout(()=>{

sync.classList.add("hidden");

assistant.classList.remove("hidden");

assistant.classList.add("fade-in");

window.scrollTo(0,0);

},600);

});


//========================================
// Analyse
//========================================

analyseBtn.addEventListener("click",()=>{

const histoire=document.getElementById("story").value;

if(histoire.trim()===""){

alert("Commencez par raconter votre histoire 🙂");

return;

}

assistant.style.opacity="0";

setTimeout(()=>{

assistant.classList.add("hidden");

dashboard.classList.remove("hidden");

dashboard.classList.add("fade-in");

window.scrollTo(0,0);

},700);

});


//========================================
// Navigation basse
//========================================

const navButtons=document.querySelectorAll("#bottomNav button");

navButtons.forEach(button=>{

button.addEventListener("click",()=>{

navButtons.forEach(b=>b.classList.remove("active"));

button.classList.add("active");

});

});

});
