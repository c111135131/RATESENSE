/* Client only ever persists the experimentId in LocalStorage (SRS 6).
   Everything else (phase, trial, status) lives on the server. */
const LS_KEY = "adapt_experiment_id";

const AppState = {
  experimentId: null,
  currentState: "home",
  currentPhase: 0,
  currentTrial: 0,
  mediaList: null,

  saveId(id) {
    this.experimentId = id;
    localStorage.setItem(LS_KEY, id);
  },
  loadId() {
    this.experimentId = localStorage.getItem(LS_KEY);
    return this.experimentId;
  },
  clear() {
    this.experimentId = null;
    this.mediaList = null;
    localStorage.removeItem(LS_KEY);
  },
};
