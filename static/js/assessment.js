(function () {
  const form = document.getElementById("assessmentForm");
  const bar = document.getElementById("assessProgressBar");
  const label = document.getElementById("assessProgressLabel");
  if (!form || !bar) return;

  const names = Array.from(new Set(
    Array.from(form.querySelectorAll('input[type="radio"]')).map(function (input) {
      return input.name;
    })
  ));

  function update() {
    const answered = names.filter(function (name) {
      return Boolean(form.querySelector('input[name="' + name + '"]:checked'));
    }).length;
    const percent = names.length ? (answered / names.length) * 100 : 0;
    bar.style.width = percent + "%";
    if (label) label.textContent = answered + " of " + names.length + " answered";
  }

  form.addEventListener("change", update);
  update();
})();
