(function () {
  const face = document.getElementById("timerFace");
  const duration = document.getElementById("duration");
  const ring = document.getElementById("timerRing");
  const status = document.getElementById("timerStatus");
  const startBtn = document.getElementById("timerStart");
  const pauseBtn = document.getElementById("timerPause");
  const resetBtn = document.getElementById("timerReset");
  const completeNote = document.getElementById("timerCompleteNote");
  if (!face || !duration || !startBtn || !pauseBtn || !resetBtn) return;

  let totalSeconds = Number(duration.value) * 60 || 15 * 60;
  let remaining = totalSeconds;
  let endAt = null;
  let timerId = null;
  let running = false;

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function render() {
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    face.textContent = pad(minutes) + ":" + pad(seconds);
    if (ring) {
      const used = totalSeconds ? ((totalSeconds - remaining) / totalSeconds) * 100 : 0;
      ring.style.strokeDashoffset = String(100 - used);
    }
  }

  function stopTicker() {
    if (timerId) {
      window.clearInterval(timerId);
      timerId = null;
    }
  }

  function setButtons() {
    startBtn.disabled = running;
    pauseBtn.disabled = !running;
    startBtn.textContent = remaining < totalSeconds && remaining > 0 && !running ? "Resume" : "Start";
  }

  function complete() {
    running = false;
    remaining = 0;
    stopTicker();
    render();
    if (status) status.textContent = "Session complete. That still counts.";
    if (completeNote) completeNote.hidden = false;
    setButtons();
  }

  function tick() {
    remaining = Math.max(0, Math.round((endAt - Date.now()) / 1000));
    if (remaining <= 0) {
      complete();
      return;
    }
    render();
  }

  function start() {
    if (remaining <= 0) remaining = totalSeconds;
    running = true;
    endAt = Date.now() + remaining * 1000;
    stopTicker();
    timerId = window.setInterval(tick, 250);
    if (status) status.textContent = "Stay with this one small pocket of time.";
    if (completeNote) completeNote.hidden = true;
    setButtons();
    tick();
  }

  function pause() {
    if (!running) return;
    remaining = Math.max(0, Math.round((endAt - Date.now()) / 1000));
    running = false;
    stopTicker();
    if (status) status.textContent = "Paused. Resume whenever you are ready.";
    setButtons();
    render();
  }

  function reset() {
    running = false;
    stopTicker();
    totalSeconds = Number(duration.value) * 60 || 15 * 60;
    remaining = totalSeconds;
    if (status) status.textContent = "Ready when you are.";
    if (completeNote) completeNote.hidden = true;
    setButtons();
    render();
  }

  function applyMinutes(minutes) {
    if (running) pause();
    duration.value = String(minutes);
    totalSeconds = minutes * 60;
    remaining = totalSeconds;
    if (completeNote) completeNote.hidden = true;
    if (status) status.textContent = minutes + "-minute cocoon ready.";
    setButtons();
    render();
  }

  document.querySelectorAll("[data-minutes]").forEach(function (button) {
    button.addEventListener("click", function () {
      applyMinutes(Number(button.dataset.minutes));
    });
  });
  duration.addEventListener("change", function () {
    applyMinutes(Number(duration.value));
  });
  startBtn.addEventListener("click", start);
  pauseBtn.addEventListener("click", pause);
  resetBtn.addEventListener("click", reset);
  window.addEventListener("pagehide", stopTicker);

  setButtons();
  render();
})();
