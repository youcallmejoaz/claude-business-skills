// Small helpers for Skills Studio. No build step.

// Drop zone: drag a spreadsheet in, or click to choose one.
document.addEventListener("dragover", (e) => {
  const zone = e.target.closest(".drop");
  if (zone) { e.preventDefault(); zone.classList.add("over"); }
});
document.addEventListener("dragleave", (e) => {
  const zone = e.target.closest(".drop");
  if (zone) zone.classList.remove("over");
});
document.addEventListener("drop", (e) => {
  const zone = e.target.closest(".drop");
  if (!zone) return;
  e.preventDefault();
  zone.classList.remove("over");
  const input = zone.querySelector("input[type=file]");
  input.files = e.dataTransfer.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
});
document.addEventListener("change", (e) => {
  if (e.target.matches(".drop input[type=file]")) {
    const zone = e.target.closest(".drop");
    const f = e.target.files[0];
    zone.classList.toggle("has-file", !!f);
    zone.querySelector(".chosen").textContent = f ? f.name + " ready" : "";
    const sample = document.querySelector("select[name=sample]");
    if (f && sample) sample.value = "";
  }
  if (e.target.matches("select[name=sample]") && e.target.value) {
    const input = document.querySelector(".drop input[type=file]");
    if (input) { input.value = ""; input.closest(".drop").classList.remove("has-file"); }
  }
});

// Load a sample email into the text box.
async function loadSample(kind, name, target) {
  if (!name) return;
  const res = await fetch(`/sample/${kind}/${encodeURIComponent(name)}`);
  document.getElementById(target).value = await res.text();
}

// Approve: nothing is sent; it only unlocks copy and export on this screen.
function approve(btn) {
  const bar = btn.closest(".approve-bar");
  bar.classList.add("approved");
  bar.querySelector(".note").innerHTML = '<span class="ok">Approved by you.</span> Still nothing sent: copy or export it yourself.';
  bar.querySelectorAll("[data-after-approve]").forEach((el) => { el.removeAttribute("disabled"); el.classList.remove("disabled"); });
  btn.remove();
}

async function copyText(btn, sourceId) {
  const el = document.getElementById(sourceId);
  const text = el.value !== undefined && el.tagName === "TEXTAREA" ? el.value : el.innerText;
  try { await navigator.clipboard.writeText(text); } catch (err) { /* clipboard may be blocked; text stays visible */ }
  const old = btn.textContent;
  btn.textContent = "Copied";
  setTimeout(() => { btn.textContent = old; }, 1600);
}

// Citation chips: highlight the sentence and its FAQ entry.
document.addEventListener("click", (e) => {
  const chip = e.target.closest(".cite");
  if (!chip) return;
  document.querySelectorAll(".cite.on, .faq-entry.on, .sent.hl").forEach((el) => el.classList.remove("on", "hl"));
  chip.classList.add("on");
  const sent = chip.closest(".sent");
  if (sent) sent.classList.add("hl");
  const entry = document.getElementById("src-" + chip.dataset.id);
  if (entry) { entry.classList.add("on"); entry.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
});

// Example chips on the connector page.
function ask(text) {
  const input = document.getElementById("question");
  input.value = text;
  input.form.requestSubmit();
}
