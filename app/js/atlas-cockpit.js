"use strict";

(() => {
  const selectedAvatar =
    localStorage.getItem("atlasPreselectedAvatar") || "male";
  const avatar = document.getElementById("cockpitAvatar");

  if (avatar) {
    const female = selectedAvatar === "female";
    avatar.src = female
      ? "./assets/atlas-avatar-female-transparent.png"
      : "./assets/atlas-avatar-male-transparent.png";
    avatar.dataset.avatar = female ? "female" : "male";
    document.body.dataset.avatar = female ? "female" : "male";
  }

  document.querySelectorAll("[data-atlas-talk]").forEach(button => {
    button.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent(
        "atlas:conversation-open",
        { detail: { context: "cockpit" } }
      ));
    });
  });
})();
