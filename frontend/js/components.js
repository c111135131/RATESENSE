/* Shared rendering helpers used across page modules. */

// Single shared page-registry object, attached to window. Declared once here;
// every js/pages/*.js file (loaded after this one) attaches its render
// functions to it directly via the bare `Pages` identifier -- do NOT
// redeclare `Pages` with const/let in those files.
window.Pages = {};

// define which state hides NAV
const HIDE_NAVBAR_STATES = [
  "phase1-recording",
  "phase2-demo", "phase2-realtest",
  "phase3-demo", "phase3-realtest",
  "phase4-demo", "phase4-realtest",
];

function updateNavbar(currentState) {
  const header = document.getElementById("siteHeader");
  const shouldShow = !HIDE_NAVBAR_STATES.includes(currentState);
  header.classList.toggle("hidden", !shouldShow);
}
//

// create container to put html element into app.root for rendering each state page
function el(html) {
  const div = document.createElement("div");
  div.innerHTML = html.trim();
  return div.firstElementChild;
}

function renderInto(html) {
  const app = document.getElementById("app");
  app.innerHTML = "";
  app.appendChild(el(html));
  return app;
}
//

function pageShell(innerHtml, { noNavPadding = false } = {}) {
  return `<div class="page${noNavPadding ? " no-nav-padding" : ""}">${innerHtml}</div>`;
}

function continueButton(label = "CONTINUE") {
  return `<button class="btn" id="continueBtn">${label}</button>`;
}

// show bug message
function showToast(message) {
  const existing = document.querySelector(".error-toast");
  if (existing) existing.remove();
  const toast = el(`<div class="error-toast">${message}</div>`);
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
//

// Page : Experiment Procedure, phaseN start 
const MODULE_META = {
  1: { key: "mod-red", title: "Self Record" },
  2: { key: "mod-orange2", title: "Direct Resolution" },
  3: { key: "mod-yellow", title: "Speed Estimation" },
  4: { key: "mod-tan", title: "Threshold and Tolerance" },
};

function moduleCircle(phase, { small = false } = {}) {
  const meta = MODULE_META[phase];
  return `<div class="module-circle ${meta.key}${small ? " small" : ""}" data-phase="${phase}" tabindex="0">${meta.title}</div>`;
}

function moduleRow() {
  const parts = [1, 2, 3, 4].map((p, i) => {
    const arrow = i < 3 ? `<span class="module-arrow">&rarr;</span>` : "";
    return `${moduleCircle(p, { small: true })}${arrow}`;
  });
  return `
    <div class="module-row" id="moduleRow">${parts.join("")}</div>
    <div class="module-tooltip" id="moduleTooltip" aria-live="polite"></div>
  `;
}
//

/* Wires up hover (mouse) + focus (keyboard/touch) on the circles rendered
   by moduleRow(), showing introTextByPhase[phase] in the tooltip beneath
   the row. Call this once, right after the markup containing moduleRow()'s
   output has actually been inserted into the DOM (renderInto() replaces
   #app's contents, so this can't run before that). */
function attachModuleRowTooltips(introTextByPhase) {
  const row = document.getElementById("moduleRow");
  const tooltip = document.getElementById("moduleTooltip");
  if (!row || !tooltip) return;

  row.querySelectorAll(".module-circle").forEach((circle) => {
    const phase = circle.getAttribute("data-phase");
    const text = introTextByPhase[phase] || "";

    const show = () => {
      tooltip.textContent = text;
      tooltip.classList.add("visible");
    };
    const hide = () => tooltip.classList.remove("visible");

    circle.addEventListener("mouseenter", show);
    circle.addEventListener("mouseleave", hide);
    circle.addEventListener("focus", show);
    circle.addEventListener("blur", hide);
  });
}


