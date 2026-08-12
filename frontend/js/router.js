const STATE_HANDLERS = {
  "home": () => Pages.home(),
  "terms-agreement": () => Pages["terms-agreement"](),
  "procedure": () => Pages.procedure(),

  "phase1-start": () => Pages.phaseStart(1)(),
  "phase1-instruction": () => Pages["phase1-instruction"](),
  "phase1-recording": () => Pages["phase1-recording"](),
  "phase1-complete": () => Pages.phaseComplete(1)(),

  "phase2-start": () => Pages.phaseStart(2)(),
  "phase2-instruction": () => Pages.phaseInstruction(2)(),
  "phase2-demo": () => Pages.phaseDemo(2)(),
  "phase2-demo-complete": () => Pages.phaseDemoComplete(2)(),
  "phase2-realtest": () => Pages.phaseRealtest(2)(),
  "phase2-complete": () => Pages.phaseComplete(2)(),

  "phase3-start": () => Pages.phaseStart(3)(),
  "phase3-instruction": () => Pages.phaseInstruction(3)(),
  "phase3-demo": () => Pages.phaseDemo(3)(),
  "phase3-demo-complete": () => Pages.phaseDemoComplete(3)(),
  "phase3-realtest": () => Pages.phaseRealtest(3)(),
  "phase3-complete": () => Pages.phaseComplete(3)(),

  "phase4-start": () => Pages.phaseStart(4)(),
  "phase4-instruction": () => Pages.phaseInstruction(4)(),
  "phase4-demo": () => Pages.phaseDemo(4)(),
  "phase4-demo-complete": () => Pages.phaseDemoComplete(4)(),
  "phase4-realtest": () => Pages.phaseRealtest(4)(),
  "phase4-complete": () => Pages.phaseComplete(4)(),

  "completed": () => Pages.completed(),
};

const Router = {
  async go(state, { hardReset = false } = {}) {
    AppState.currentState = state;
    updateNavbar(state);
    window.location.hash = `#/${state}`;
    const handler = STATE_HANDLERS[state];
    if (!handler) {
      console.warn("No page handler registered for state:", state);
      return;
    }
    await handler();
  },

  // Ask backend for next_state and navigate there (frontend never decides).
  async advance() {
    try {
      const data = await Api.nextState(AppState.experimentId);
      await this.go(data.next_state);
    } catch (e) {
      showToast(e.message);
    }
  },
};
