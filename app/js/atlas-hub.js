if(location.hash==="#analysis"){location.replace("./atlas-cockpit.html#athlete-analysis");}
"use strict";const buttons=document.querySelectorAll("[data-tab]"),views=document.querySelectorAll("[data-view]");function activate(name){views.forEach(v=>v.classList.toggle("active",v.dataset.view===name));buttons.forEach(b=>b.classList.toggle("active",b.dataset.tab===name));}buttons.forEach(b=>b.addEventListener("click",()=>activate(b.dataset.tab)));


(() => {
  const selected = localStorage.getItem("atlasPreselectedAvatar") || "male";
  const image = document.querySelector("[data-atlas-avatar-image]");
  if (!image) return;
  image.src = selected === "female"
    ? "./assets/atlas-avatar-femme-clean-final.png?v=2"
    : "./assets/atlas-avatar-homme-clean-final.png?v=2";
  image.dataset.avatar = selected;
})();
