// Types the prompt at a steady pace, then reveals the result lines one by one.
function runTerminal(prompt, lines, cps = 26, gap = 420) {
  const typed = document.getElementById("typed");
  const out = document.getElementById("out");
  out.innerHTML = lines.map((l) => `<div class="line">${l || "&nbsp;"}</div>`).join("");
  let i = 0;
  const tick = () => {
    typed.textContent = prompt.slice(0, ++i);
    if (i < prompt.length) return setTimeout(tick, 1000 / cps);
    setTimeout(() => {
      document.querySelector(".cur").style.display = "none";
      [...out.children].forEach((el, k) => setTimeout(() => el.classList.add("show"), 500 + k * gap));
    }, 450);
  };
  setTimeout(tick, 400);
}
