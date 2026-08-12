/* Pages 1-3, 4/8/14/20 (phaseN-start), 7/13/19/25 (phaseN-complete), and Completed. */

Pages.home = async () => {
  renderInto(pageShell(`
    <div class="ribbon-wrap" aria-hidden="true">
    <img src="../assets/img/flow.png" alt="">
    </div>
    <h1 class="brand-title">RATESENSE</h1>
    <p class="subtitle">A Sense of Speed Media Playback User Study</p>
    <button class="btn" id="proceedBtn">PROCEED</button>
    <div style="margin-top:4rem; font-size:0.8rem; opacity:0.75; max-width: 32rem;">
      <p>Researcher: Finlay Braithwaite<br/>Supervised by Dr. Ali Mazalek, Synaesthetic Media Lab, Toronto Metropolitan University</p>
    </div>

  `));

  document.getElementById("proceedBtn").addEventListener("click", async () => {
    try {
      let id = AppState.loadId();
      if (!id) {
        const data = await Api.createExperiment();
        AppState.saveId(data.experiment_id);
        Router.go(data.current_state);
        return;
      }
      Router.go("terms-agreement");
    } catch (e) {
      showToast(e.message);
    }
  });
};

Pages["terms-agreement"] = async () => {
  renderInto(pageShell(`
    <h1 class="brand-title" style="font-size:2.5rem;">RATESENSE</h1>
    <p class="subtitle">This user study looks at participants' connection to the playback rate of media.</p>
    <div class="terms-box" id="termsBox" tabindex="0">
      <h2>Terms of Use &amp; Privacy Policy</h2>
      <p>By continuing, you acknowledge that you've read and understood the study details.</p>
      <p>You confirm that you agree to participate under the terms provided.</p>
      <p>Your use of our site constitutes acceptance of these Terms of Use and your agreement to be bound by them.</p>
      <p>Participation is voluntary. You may withdraw from the study at any time without penalty. Recorded clips captured during the Self Record module are used only for on-session playback-speed tasks and are permanently deleted at the end of your session.</p>
      <p>No personally identifying footage is retained or shared outside the research team once the session concludes.</p>
    </div>
    <label class="check-row" for="agreeCheckbox">
      <input type="checkbox" id="agreeCheckbox" />
      <span>I have read, understood, and agree to the Terms of Use and Privacy Policy.</span>
    </label>
    <p class="field-error" id="agreeError"></p>
    <div class="btn-row">${continueButton()}</div>
  `));

  document.getElementById("continueBtn").addEventListener("click", async () => {
    const checked = document.getElementById("agreeCheckbox").checked;
    if (!checked) {
      document.getElementById("agreeError").textContent = "You must agree to the Terms and Conditions before proceeding.";
      return;
    }
    await Router.advance();
  });
};

Pages.procedure = async () => {
  renderInto(pageShell(`
    <h1 class="brand-title" style="font-size:2.5rem;">RATESENSE</h1>
    <p class="subtitle">In this user study, you'll progress through the following modules.</p>
    ${moduleRow()}
    <div class="btn-row">${continueButton()}</div>
  `));

  attachModuleRowTooltips(PHASE_INTRO);
  document.getElementById("continueBtn").addEventListener("click", () => Router.advance());
};

const PHASE_INTRO = {
  1: "To begin, we will record a quick video clip of you. This clip will be used later in this session for tasks on playback speed perception. Don't worry, this clip will be <b style='color:var(--red)'>DELETED</b> at the end of this session.",
  2: "In this phase, you'll see video clips played at altered speeds. Your task is to adjust each clip back to what you believe is its original speed.",
  3: "In this phase, you'll see clips already sped up or slowed down. Your task is to gauge how fast or slow they are (e.g., 1.2x, 0.75x).",
  4: "This phase tests the point at which you first notice speed changes, and when it becomes \u201ctoo fast\u201d or \u201ctoo slow.\u201d For this phase, the clips are silent.",
};

Pages.phaseStart = (phase) => async () => {
  renderInto(pageShell(`
    ${moduleCircle(phase)}
    <p class="subtitle" style="max-width:32rem;">${PHASE_INTRO[phase]}</p>
    <div class="btn-row">${continueButton()}</div>
  `));
  document.getElementById("continueBtn").addEventListener("click", () => Router.advance());
};

const PHASE_COMPLETE_TEXT = {
  1: { title: "Recording Complete", body: "Your self-clip has been successfully recorded. This clip will be used later in this session for tasks on playback speed perception.", color: "" },
  2: { title: "Direct Resolution Complete", body: "You've finished adjusting speeds for this phase. Let's move on to the next phase, Speed Estimation.", color: "var(--orange-2)" },
  3: { title: "Speed Estimation Complete", body: "Thank you for providing your estimates. Next, we'll explore when you first notice and can no longer tolerate speed changes.", color: "var(--yellow)" },
  4: { title: "Threshold &amp; Tolerance Complete", body: "You've finished identifying your speed thresholds and tolerances. This concludes the interactive portion of the study.", color: "var(--tan)" },
};

Pages.phaseComplete = (phase) => async () => {
  const info = PHASE_COMPLETE_TEXT[phase];
  const isLast = phase === 4;
  renderInto(pageShell(`
    <h1 class="serif" style="font-weight:800; font-size:clamp(1.8rem,5vw,2.6rem); color:${info.color || "var(--red)"}; margin-bottom:0.75rem;">${info.title}</h1>
    <p class="subtitle" style="max-width:32rem;">${info.body}</p>
    <div class="btn-row">
      ${isLast ? `<button class="btn" id="homeBtn">BACK TO HOMEPAGE</button>` : continueButton()}
    </div>
  `));

  if (isLast) {
    document.getElementById("homeBtn").addEventListener("click", async () => {
      try {
        await Api.completeExperiment(AppState.experimentId);
      } catch (e) { /* non-fatal */ }
      AppState.clear();
      Router.go("home", { hardReset: true });
    });
  } else {
    document.getElementById("continueBtn").addEventListener("click", () => Router.advance());
  }
};

Pages.completed = Pages.phaseComplete(4);
