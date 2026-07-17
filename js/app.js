// =========================
// Atlas OS
// Application principale
// =========================

window.addEventListener("load", () => {

    console.log("Atlas OS démarré");

});

// Animation bouton

const startButton = document.getElementById("startButton");

if(startButton){

    startButton.addEventListener("click", ()=>{

        alert("Bienvenue dans Atlas OS 🚀");

    });

}
