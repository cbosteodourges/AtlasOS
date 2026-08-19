"use strict";

(() => {
  const selectedAvatar =
    localStorage.getItem("atlasPreselectedAvatar") || "male";
  const avatar = document.getElementById("cockpitAvatar");

  if (avatar) {
    const female = selectedAvatar === "female";
    avatar.src = female
      ? "./assets/avatar-female-hub.jpg"
      : "./assets/avatar-male-hub.jpg";
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
