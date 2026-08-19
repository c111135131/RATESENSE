// http://127.0.0.1:8123/api/v1
// https://ratesense-backend.onrender.com/api/v1
const ADMIN_API_BASE = window.ADAPT_API_BASE || "https://ratesense-backend.onrender.com/api/v1";
const TOKEN_KEY = "adapt_admin_token";

const AdminState = {
  token: sessionStorage.getItem(TOKEN_KEY) || null,
  view: "login", // "login" | "list" | "detail" | "media"
  experiments: [],
  detail: null,
  mediaLibrary: [],
};

/* ---------------------------------------------------------------------- */
/* API layer                                                              */
/* ---------------------------------------------------------------------- */
async function adminRequest(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (AdminState.token) headers["X-Admin-Token"] = AdminState.token;

  const res = await fetch(`${ADMIN_API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && path !== "/admin/login") {
    AdminState.token = null;
    sessionStorage.removeItem(TOKEN_KEY);
    renderLogin("Your session expired. Please log in again.");
    throw new Error("Unauthorized");
  }

  const json = await res.json().catch(() => ({ success: false, message: "Invalid server response." }));
  if (!res.ok || json.success === false) {
    throw new Error(json.message || `Request failed (${res.status})`);
  }
  return json.data;
}

const AdminApi = {
  login: (username, password) => adminRequest("/admin/login", { method: "POST", body: { username, password } }),
  listExperiments: () => adminRequest("/admin/experiments"),
  getExperiment: (id) => adminRequest(`/admin/experiments/${id}`),
  listMedia: () => adminRequest("/admin/media"),

  updateMediaParams: (mediaId, payload) =>
    adminRequest(`/admin/media/${mediaId}/params`, { method: "PUT", body: payload }),

  updateSelfRecordingParams: (experimentId, payload) =>
    adminRequest(`/admin/experiments/${experimentId}/self-recording/params`, { method: "PUT", body: payload }),
  cleanup: () => adminRequest("/admin/cleanup", { method: "POST" }),

  // CSV needs a custom header, so it can't be a plain <a href>: fetch it
  // as a blob ourselves and trigger the download via a throwaway link.
  downloadCsv: async () => {
    const headers = {};
    if (AdminState.token) headers["X-Admin-Token"] = AdminState.token;
    const res = await fetch(`${ADMIN_API_BASE}/admin/export-csv`, { headers });
    if (res.status === 401) {
      AdminState.token = null;
      sessionStorage.removeItem(TOKEN_KEY);
      renderLogin("Your session expired. Please log in again.");
      throw new Error("Unauthorized");
    }
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "experiment_data.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};

/* ---------------------------------------------------------------------- */
/* Small render helpers                                                   */
/* ---------------------------------------------------------------------- */
function root() { return document.getElementById("adminApp"); }
function el(html) { const d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstElementChild; }
function renderInto(html) {
  const r = root();
  r.innerHTML = html;
  return r;
}
function toast(message) {
  const existing = document.querySelector(".admin-toast");
  if (existing) existing.remove();
  const t = el(`<div class="admin-toast">${message}</div>`);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
function fmtDate(iso) {
  if (!iso) return "\u2014";
  return iso.replace("T", " ").split(".")[0]; // already Toronto local time from the backend
}

/* ---------------------------------------------------------------------- */
/* Login view                                                             */
/* ---------------------------------------------------------------------- */
function renderLogin(errorMessage = "") {
  renderInto(`
    <div class="admin-login">
      <h1 class="serif" style="font-family:'Playfair Display',serif;">ADAPT Admin</h1>
      <div class="admin-field">
        <label for="adminUsername">Username</label>
        <input id="adminUsername" type="text" autocomplete="username" />
      </div>
      <div class="admin-field">
        <label for="adminPassword">Password</label>
        <input id="adminPassword" type="password" autocomplete="current-password" />
      </div>
      <p class="admin-error" id="adminLoginError">${errorMessage}</p>
      <button class="admin-btn primary" id="adminLoginBtn" style="width:100%;">LOG IN</button>
    </div>
  `);

  const submit = async () => {
    const username = document.getElementById("adminUsername").value.trim();
    const password = document.getElementById("adminPassword").value;
    const errorEl = document.getElementById("adminLoginError");
    errorEl.textContent = "";
    try {
      const data = await AdminApi.login(username, password);
      AdminState.token = data.token;
      sessionStorage.setItem(TOKEN_KEY, data.token);
      await loadExperimentList();
    } catch (e) {
      errorEl.textContent = e.message;
    }
  };

  document.getElementById("adminLoginBtn").addEventListener("click", submit);
  document.getElementById("adminPassword").addEventListener("keydown", (e) => {
    if (e.key === "Enter") submit();
  });
}

/* ---------------------------------------------------------------------- */
/* Experiment list view                                                   */
/* ---------------------------------------------------------------------- */
async function loadExperimentList() {
  try {
    AdminState.experiments = await AdminApi.listExperiments();
    AdminState.view = "list";
    renderList();
  } catch (e) {
    toast(e.message);
  }
}

function renderList() {
  const rows = AdminState.experiments.map((e) => `
    <tr class="clickable" data-id="${e.experiment_id}">
      <td>${e.experiment_id}</td>
      <td>${fmtDate(e.created_at)}</td>
      <td><span class="admin-status-pill admin-status-${e.status}">${e.status}</span></td>
      <td>${e.current_state}</td>
      <td>${e.current_phase} / ${e.current_trial}</td>
    </tr>
  `).join("");

  renderInto(`
    <div class="admin-header">
      <h1 class="admin-title">ADAPT Admin</h1>
      <div class="admin-actions">
        <button class="admin-btn" id="btnVideoLibrary">Video Library</button>
        <button class="admin-btn" id="btnDownloadCsv">Export CSV</button>
        <button class="admin-btn danger" id="btnCleanup">Cleanup Expired</button>
        <button class="admin-btn" id="btnLogout">Log Out</button>
      </div>
    </div>

    <div class="admin-table-wrap">
      ${AdminState.experiments.length === 0
        ? `<div class="admin-empty">No experiments yet.</div>`
        : `<table class="admin-table">
            <thead><tr><th>Experiment ID</th><th>Created (Toronto)</th><th>Status</th><th>State</th><th>Phase / Trial</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>`}
    </div>
  `);

  root().querySelectorAll("tr.clickable").forEach((tr) => {
    tr.addEventListener("click", () => loadExperimentDetail(tr.getAttribute("data-id")));
  });
  document.getElementById("btnVideoLibrary").addEventListener("click", loadMediaLibrary);
  document.getElementById("btnDownloadCsv").addEventListener("click", async () => {
    try { await AdminApi.downloadCsv(); } catch (e) { toast(e.message); }
  });
  document.getElementById("btnCleanup").addEventListener("click", async () => {
    try {
      const data = await AdminApi.cleanup();
      toast(`Marked ${data.expired_count} experiment(s) as expired.`);
      loadExperimentList();
    } catch (e) { toast(e.message); }
  });
  document.getElementById("btnLogout").addEventListener("click", () => {
    AdminState.token = null;
    sessionStorage.removeItem(TOKEN_KEY);
    renderLogin();
  });
}

/* ---------------------------------------------------------------------- */
/* Experiment detail view                                                 */
/* ---------------------------------------------------------------------- */
async function loadExperimentDetail(experimentId) {
  try {
    AdminState.detail = await AdminApi.getExperiment(experimentId);
    AdminState.view = "detail";
    renderDetail();
  } catch (e) {
    toast(e.message);
  }
}

function renderDetail() {
  const { experiment, media, self_recording_params, self_recordings, trials } = AdminState.detail;

  const mediaRows = media.map((m) => `
    <tr>
      <td>${m.filename || "\u2014"}</td>
      <td>${m.phase3_actual_speed}${m.phase3_actual_speed_is_override ? "" : `<span class="system-auto-badge">auto</span>`}</td>
      <td>${m.phase4_direction}${m.phase4_direction_is_override ? "" : `<span class="system-auto-badge">auto</span>`}</td>
      <td>${m.phase4_delay_ms}${m.phase4_delay_ms_is_override ? "" : `<span class="system-auto-badge">auto</span>`}</td>
      <td>${m.phase4_tick_ms}${m.phase4_tick_ms_is_override ? "" : `<span class="system-auto-badge">auto</span>`}</td>
    </tr>
  `).join("");

  const trialRows = trials.map((t) => `
    <tr>
      <td>${t.phase}</td><td>${t.trial_index}</td><td>${t.media_name}</td>
      <td>${t.selected_speed ?? ""}</td><td>${t.actual_speed ?? ""}</td><td>${t.estimated_speed ?? ""}</td>
      <td>${t.hesitation_ms ?? ""}</td><td>${t.threshold_speed ?? ""}</td><td>${t.tolerance_speed ?? ""}</td>
      <td>${fmtDate(t.created_at)}</td>
    </tr>
  `).join("");

  const recordingRows = self_recordings.map((r) => `
    <tr><td>${r.recording_id}</td><td>${r.video_path}</td><td>${r.deleted ? "yes" : "no"}</td><td>${fmtDate(r.upload_time)}</td></tr>
  `).join("");

  renderInto(`
    <div class="admin-toolbar">
      <button class="admin-back" id="btnBack">&larr; Back to experiment list</button>
    </div>
    <div class="admin-header">
      <h1 class="admin-title">${experiment.experiment_id}</h1>
      <span class="admin-status-pill admin-status-${experiment.status}">${experiment.status}</span>
    </div>
    <p style="opacity:0.75; font-size:0.85rem;">
      Created: ${fmtDate(experiment.created_at)} (Toronto) &nbsp;|&nbsp;
      State: ${experiment.current_state} &nbsp;|&nbsp;
      Phase/Trial: ${experiment.current_phase} / ${experiment.current_trial} &nbsp;|&nbsp;
      Expires: ${fmtDate(experiment.expired_at)}
    </p>

    <h2 class="admin-section-title">Video Parameters (Phase 3 / Phase 4)</h2>
    <p style="opacity:0.7; font-size:0.8rem; margin-bottom:0.5rem;">
      The values shown are what this experiment actually uses right now
      (override if set, otherwise the auto-generated value). These 5 videos
      are GLOBAL settings -- edit them in
      <button class="admin-back" id="btnGoToLibraryFromDetail" style="display:inline;">Video Library</button>,
      which applies to every experiment using that video (past and future).
    </p>
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>Video</th><th>Phase3 actual_speed</th><th>Phase4 direction</th><th>Phase4 delay_ms</th><th>Phase4 tick_ms</th></tr></thead>
        <tbody>${mediaRows}</tbody>
      </table>
    </div>

    <h2 class="admin-section-title">Self-Recording</h2>
    <div class="admin-table-wrap">
      ${self_recordings.length === 0 ? `<div class="admin-empty">No self-recording uploaded yet.</div>` : `
        <table class="admin-table">
          <thead><tr><th>ID</th><th>Path</th><th>Deleted</th><th>Uploaded (Toronto)</th></tr></thead>
          <tbody>${recordingRows}</tbody>
        </table>`}
    </div>

    ${self_recording_params ? `
      <h2 class="admin-section-title">Self-Recording Parameters (Phase 3 / Phase 4)</h2>
      <p style="opacity:0.7; font-size:0.8rem; margin-bottom:0.5rem;">
        Unlike the 5 predefined videos above, the self-recorded video is
        unique to THIS experiment -- overrides here only ever affect this
        one experiment. Leave a field blank (or clear it and Save) to fall
        back to the auto-generated value.
      </p>
      <div class="admin-table-wrap">
        <table class="admin-table" id="selfRecordingParamsTable">
          <thead><tr><th>Phase3 actual_speed</th><th>Phase4 direction</th><th>Phase4 delay_ms</th><th>Phase4 tick_ms</th><th></th></tr></thead>
          <tbody>
            <tr>
              <td>
                <input type="number" step="0.01" class="p3-speed" value="${self_recording_params.phase3_actual_speed_override ?? ""}" placeholder="auto" />
                <div class="admin-hint">current: ${self_recording_params.phase3_actual_speed}</div>
              </td>
              <td>
                <select class="p4-direction">
                  <option value="" ${self_recording_params.phase4_direction_override === null ? "selected" : ""}>auto</option>
                  <option value="1" ${self_recording_params.phase4_direction_override === 1 ? "selected" : ""}>1 (accelerate)</option>
                  <option value="-1" ${self_recording_params.phase4_direction_override === -1 ? "selected" : ""}>-1 (decelerate)</option>
                </select>
                <div class="admin-hint">current: ${self_recording_params.phase4_direction}</div>
              </td>
              <td>
                <input type="number" class="p4-delay" value="${self_recording_params.phase4_delay_ms_override ?? ""}" placeholder="auto" />
                <div class="admin-hint">current: ${self_recording_params.phase4_delay_ms}</div>
              </td>
              <td>
                <input type="number" class="p4-tick" value="${self_recording_params.phase4_tick_ms_override ?? ""}" placeholder="auto" />
                <div class="admin-hint">current: ${self_recording_params.phase4_tick_ms}</div>
              </td>
              <td><button class="admin-btn small" id="btnSaveSelfRecording">Save</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    ` : ""}

    <h2 class="admin-section-title">Trials (${trials.length})</h2>
    <div class="admin-table-wrap">
      ${trials.length === 0 ? `<div class="admin-empty">No trials recorded yet.</div>` : `
        <table class="admin-table">
          <thead><tr>
            <th>Phase</th><th>Trial</th><th>Media</th><th>Selected</th><th>Actual</th><th>Estimated</th>
            <th>Hesitation(ms)</th><th>Threshold</th><th>Tolerance</th><th>Created (Toronto)</th>
          </tr></thead>
          <tbody>${trialRows}</tbody>
        </table>`}
    </div>
  `);

  document.getElementById("btnBack").addEventListener("click", loadExperimentList);
  document.getElementById("btnGoToLibraryFromDetail").addEventListener("click", loadMediaLibrary);

  const saveSelfRecordingBtn = document.getElementById("btnSaveSelfRecording");
  if (saveSelfRecordingBtn) {
    saveSelfRecordingBtn.addEventListener("click", async () => {
      const table = document.getElementById("selfRecordingParamsTable");
      const speedVal = table.querySelector(".p3-speed").value;
      const dirVal = table.querySelector(".p4-direction").value;
      const delayVal = table.querySelector(".p4-delay").value;
      const tickVal = table.querySelector(".p4-tick").value;

      const payload = {
        phase3_actual_speed: speedVal === "" ? null : Number(speedVal),
        phase4_direction: dirVal === "" ? null : Number(dirVal),
        phase4_delay_ms: delayVal === "" ? null : Number(delayVal),
        phase4_tick_ms: tickVal === "" ? null : Number(tickVal),
      };

      try {
        await AdminApi.updateSelfRecordingParams(experiment.experiment_id, payload);
        toast("Saved -- applies only to this experiment.");
        loadExperimentDetail(experiment.experiment_id);
      } catch (e) {
        toast(e.message);
      }
    });
  }
}

/* ---------------------------------------------------------------------- */
/* Video Library view -- GLOBAL parameter overrides, applied to every      */
/* experiment (past and future) that uses a given video.                  */
/* ---------------------------------------------------------------------- */
async function loadMediaLibrary() {
  try {
    AdminState.mediaLibrary = await AdminApi.listMedia();
    AdminState.view = "media";
    renderMediaLibrary();
  } catch (e) {
    toast(e.message);
  }
}

function renderMediaLibrary() {
  const rows = AdminState.mediaLibrary.map((m) => `
    <tr data-media-id="${m.media_id}">
      <td>${m.filename}</td>
      <td>
        <input type="number" step="0.01" class="p3-speed" value="${m.phase3_actual_speed ?? ""}" placeholder="auto" />
        ${m.phase3_actual_speed !== null ? `<span class="admin-override-badge">override</span>` : ""}
      </td>
      <td>
        <select class="p4-direction">
          <option value="" ${m.phase4_direction === null ? "selected" : ""}>auto</option>
          <option value="1" ${m.phase4_direction === 1 ? "selected" : ""}>1 (accelerate)</option>
          <option value="-1" ${m.phase4_direction === -1 ? "selected" : ""}>-1 (decelerate)</option>
        </select>
      </td>
      <td><input type="number" class="p4-delay" value="${m.phase4_delay_ms ?? ""}" placeholder="auto" /></td>
      <td><input type="number" class="p4-tick" value="${m.phase4_tick_ms ?? ""}" placeholder="auto" /></td>
      <td><button class="admin-btn small" data-save="${m.media_id}">Save</button></td>
    </tr>
  `).join("");

  renderInto(`
    <div class="admin-toolbar">
      <button class="admin-back" id="btnBackFromLibrary">&larr; Back to experiment list</button>
    </div>
    <div class="admin-header">
      <h1 class="admin-title">Video Library</h1>
    </div>
    <p style="opacity:0.75; font-size:0.85rem; max-width:40rem;">
      These parameters are GLOBAL: changing a video's Phase3 <code>actual_speed</code>
      or Phase4 <code>direction</code> / <code>delay_ms</code> / <code>tick_ms</code> here
      applies to <b>every experiment</b> that uses this video from now on
      &mdash; past experiments already run keep whatever value they actually used
      (see each experiment's Trials table). Leave a field blank (or clear it and Save)
      to fall back to the auto-generated (hash-based) value.
    </p>
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>Video</th><th>Phase3 actual_speed</th><th>Phase4 direction</th><th>Phase4 delay_ms</th><th>Phase4 tick_ms</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `);

  document.getElementById("btnBackFromLibrary").addEventListener("click", loadExperimentList);

  root().querySelectorAll("[data-save]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const mediaId = btn.getAttribute("data-save");
      const row = btn.closest("tr");
      const speedVal = row.querySelector(".p3-speed").value;
      const dirVal = row.querySelector(".p4-direction").value;
      const delayVal = row.querySelector(".p4-delay").value;
      const tickVal = row.querySelector(".p4-tick").value;

      const payload = {
        phase3_actual_speed: speedVal === "" ? null : Number(speedVal),
        phase4_direction: dirVal === "" ? null : Number(dirVal),
        phase4_delay_ms: delayVal === "" ? null : Number(delayVal),
        phase4_tick_ms: tickVal === "" ? null : Number(tickVal),
      };

      try {
        await AdminApi.updateMediaParams(mediaId, payload);
        toast(`Saved -- applies to every future use of ${row.querySelector("td").textContent}.`);
        loadMediaLibrary();
      } catch (e) {
        toast(e.message);
      }
    });
  });
}

/* ---------------------------------------------------------------------- */
/* Bootstrap                                                              */
/* ---------------------------------------------------------------------- */
(async function bootstrapAdmin() {
  if (AdminState.token) {
    try {
      await loadExperimentList();
      return;
    } catch (e) {
      // token was stale/invalid -- adminRequest() already redirected to login
      return;
    }
  }
  renderLogin();
})();