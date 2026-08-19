"use strict";const buttons=document.querySelectorAll("[data-tab]"),views=document.querySelectorAll("[data-view]");function activate(name){views.forEach(v=>v.classList.toggle("active",v.dataset.view===name));buttons.forEach(b=>b.classList.toggle("active",b.dataset.tab===name));}buttons.forEach(b=>b.addEventListener("click",()=>activate(b.dataset.tab)));


(() => {
  const selected = localStorage.getItem("atlasPreselectedAvatar") || "male";
  const image = document.querySelector("[data-atlas-avatar-image]");
  if (!image) return;
  image.src = selected === "female"
    ? "./assets/atlas-avatar-femme-sport-final.png?v=1"
    : "./assets/atlas-avatar-homme-sport-final.png?v=1";
  image.dataset.avatar = selected;
})();
