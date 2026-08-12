/* Thin wrapper around the ADAPT REST API (SRS section 8). */
const API_BASE = window.ADAPT_API_BASE || "http://127.0.0.1:8123/api/v1";

// The backend serves real video files from /media via FastAPI's StaticFiles
// mount (see backend/app/main.py). The frontend is usually a *different*
// origin/port than the backend (e.g. static server on :5173 vs API on
// :8123), so a bare "/media/video01.mp4" path from the API response would
// resolve against the FRONTEND's own origin and 404. API_ORIGIN strips the
// "/api/v1" suffix off API_BASE to get the backend's origin, so real
// <video src> tags can be built correctly.
const API_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, "");

async function apiRequest(path, { method = "GET", body, form } = {}) {
  const opts = { method, headers: {} };
  if (form) {
    opts.body = form; // multipart/form-data, browser sets boundary
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  const json = await res.json().catch(() => ({ success: false, message: "Invalid server response." }));
  if (!res.ok || json.success === false) {
    const err = new Error(json.message || `Request failed (${res.status})`);
    err.errorCode = json.error_code;
    err.status = res.status;
    throw err;
  }
  return json.data;
}

const Api = {
  createExperiment: () => apiRequest("/experiments", { method: "POST" }),
  resumeExperiment: (id) => apiRequest(`/experiments/${id}`),
  restartExperiment: (id) => apiRequest(`/experiments/${id}/restart`, { method: "POST" }),
  completeExperiment: (id) => apiRequest(`/experiments/${id}/complete`, { method: "POST" }),
  nextState: (id) => apiRequest(`/experiments/${id}/next`, { method: "POST" }),
  getMedia: (id) => apiRequest(`/experiments/${id}/media`),

  uploadPhase1: (experimentId, blob) => {
    const form = new FormData();
    form.append("experiment_id", experimentId);
    form.append("video_file", blob, "self_recording.webm");
    return apiRequest("/phase1/upload", { method: "POST", form });
  },
  completePhase1: (experimentId) => {
    const form = new FormData();
    form.append("experiment_id", experimentId);
    return apiRequest("/phase1/complete", { method: "POST", form });
  },

  // experimentId is optional (Demo can be viewed before an experiment
  // exists) but is passed whenever available so the backend can seed a
  // per-participant-but-still-deterministic set of demo parameters.
  getDemo: (phase, experimentId) =>
    apiRequest(`/demo?phase=${phase}${experimentId ? `&experiment_id=${encodeURIComponent(experimentId)}` : ""}`),
  completeDemo: (experimentId, phase) =>
    apiRequest("/demo/complete", { method: "POST", body: { experiment_id: experimentId, phase } }),

  getNextTrial: (experimentId, phase) =>
    apiRequest(`/trials/next?experiment_id=${experimentId}&phase=${phase}`),
  submitTrial: (payload) => apiRequest("/trials", { method: "POST", body: payload }),

  exportCsvUrl: () => `${API_BASE}/admin/export-csv`,

  // Resolve a backend-relative media path (e.g. "/media/video01.mp4") into
  // a fully-qualified URL against the backend's origin.
  mediaUrl: (path) => {
    if (!path) return "";
    if (/^https?:\/\//i.test(path)) return path;
    return `${API_ORIGIN}${path}`;
  },
};
