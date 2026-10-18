(function () {
  const face = document.getElementById("timerFace");
  const duration = document.getElementById("duration");
  if (!face || !duration) return;
  function show(minutes) {
    face.textContent = String(minutes).padStart(2, "0") + ":00";
    duration.value = String(minutes);
  }
  document.querySelectorAll("[data-minutes]").forEach((button) => {
    button.addEventListener("click", () => show(Number(button.dataset.minutes)));
  });
  duration.addEventListener("change", () => show(Number(duration.value)));
})();