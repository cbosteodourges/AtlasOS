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
  }

  const routes = new Map([
    [".engine-coach", "./performance-running.html"],
    [".engine-physio", "./biomecanique.html"],
    [".engine-physiology", "./physiologie.html"],
    [".engine-memory", "./memoire.html"],
    [".engine-prevention", "./prevention.html"]
  ]);

  routes.forEach((href, selector) => {
    document.querySelector(selector)?.addEventListener(
      "click",
      () => {
        window.location.href = href;
      }
    );
  });

  document.querySelectorAll("[data-atlas-talk]").forEach(
    button => {
      button.addEventListener("click", () => {
        window.dispatchEvent(new CustomEvent(
          "atlas:conversation-open",
          { detail: { context: "cockpit" } }
        ));
      });
    }
  );
})();