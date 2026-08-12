const MODULE_COLOR_VAR = { 2: "var(--orange-2)", 3: "var(--yellow)", 4: "var(--tan)" };
const HOW_IT_WORKS_TEXT = {
  2: { left: "Move mouse, left to slow, right to speed up.<br/>Aim to find the <b style='color:var(--orange2)'>NATURAL</b> motion speed.", right: "CLICK to lock in your response."},
  3: { left: "Move mouse, left to slow, right to speed up.<br/>Aim to find the <b style='color:var(--yellow)'>CURRENT</b> playback rate.", right: "CLICK to lock in your response." },
  4: { left: "<b style='color:var(--tan)>CLICK</b> the moment the <b style='color:var(--tan)'>speed changes from 1x.</b>", right: "<b style='color:var(--tan)'>CLICK AGAIN</b> when it feels <b style='color:var(--tan)'>too fast or too slow.</b>" },
};

const DEMO_MEDIA_PATH = "../assets/demo_gif/";
const HOW_IT_WORKS_MEDIA = {
  2: { left: `${DEMO_MEDIA_PATH}demo-1.gif`, right: `${DEMO_MEDIA_PATH}demo-2.gif` },
  3: { left: `${DEMO_MEDIA_PATH}demo-3.gif`, right: `${DEMO_MEDIA_PATH}demo-4.gif` },
  4: { left: `${DEMO_MEDIA_PATH}demo-5.gif`, right: `${DEMO_MEDIA_PATH}demo-6.gif` },
};

/*  */
function isSilentPhase(phase) { return phase === 4; }

/* ---------- 9/15/21: phaseN-instruction (How it works) ----------*/
Pages.phaseInstruction = (phase) => async () => {
  const t = HOW_IT_WORKS_TEXT[phase];
  const m = HOW_IT_WORKS_MEDIA[phase];

  renderInto(pageShell(`
    <h2 class="serif" style="font-size:1.6rem; margin-bottom:1.5rem;">How it works?</h2>
    <div class="two-col">
      <div class="col">
        <div class="demo-stage">
          <div class="demo-stage-overlay"><img class="demo-gif" src="${m.left}"></div>
        </div>
        <p class="caption">${t.left}</p>
      </div>
      <div class="col">
        <div class="demo-stage">
          <div class="demo-stage-overlay"><img class="demo-gif" src="${m.right}"></div>
        </div>
        <p class="caption">${t.right}</p>
      </div>
    </div>
    <div class="btn-row" style="margin-top:2rem;">${continueButton()}</div>
  `));

  document.getElementById("continueBtn").addEventListener("click", () => Router.advance());
};

/* ---------- 10/16/22: phaseN-demo ---------- */
Pages.phaseDemo = (phase) => async () => {
  const demoInfo = await Api.getDemo(phase, AppState.experimentId);
  runInteractiveTrial({
    phase,
    mediaPath: demoInfo.media_path,
    isDemo: true,
    trialIndex: 0,
    totalTrials: 1,
    trialParams: demoInfo,
    onFinish: () => Router.go(`phase${phase}-demo-complete`),
  });
};

/* ---------- 11/17/23: phaseN-demo-complete ---------- */
Pages.phaseDemoComplete = (phase) => async () => {
  renderInto(pageShell(`
    <h1 class="serif" style="font-weight:800; font-size:clamp(1.6rem,5vw,2.3rem); color:${MODULE_COLOR_VAR[phase]};">Great job!<br/>Now onto the real test.</h1>
    <p class="subtitle" style="max-width:32rem;">${REALTEST_INTRO[phase]}</p>
    <div class="btn-row">
      ${continueButton()}
      <button class="btn btn-secondary" id="restartBtn">RESTART DEMO</button>
    </div>
  `));

  document.getElementById("continueBtn").addEventListener("click", async () => {
    try {
      await Api.completeDemo(AppState.experimentId, phase);
      await Router.advance();
    } catch (e) { showToast(e.message); }
  });
  document.getElementById("restartBtn").addEventListener("click", () => Router.go(`phase${phase}-demo`));
};

const REALTEST_INTRO = {
  2: "We'll show you a series of videos. Adjust the playback speed until it appears normal to you, then confirm by CLICKING.",
  3: "We'll show you a series of videos. Estimate the current playback rate, then confirm by CLICKING.",
  4: "We'll show you a series of videos. Set your threshold and tolerance for each.",
};

/* ---------- 12/18/24: phaseN-realtest ---------- */
Pages.phaseRealtest = (phase) => async () => {
  await runNextRealTrial(phase);
};

async function runNextRealTrial(phase) {
  let trialData;
  try {
    trialData = await Api.getNextTrial(AppState.experimentId, phase);
    console.log("trialData =", JSON.stringify(trialData, null, 2));

  } catch (e) {
    showToast(e.message);
    return;
  }

  runInteractiveTrial({
    phase,
    mediaPath: trialData.media.media_path,
    mediaId: trialData.media.media_id,
    isDemo: false,
    trialIndex: trialData.trial_index,
    totalTrials: 6,
    trialParams: trialData, // { noise } | { actual_speed } | { delay_ms, tick_ms, step, direction }
    onFinish: async (result) => {
      try {
        const payload = {
          experiment_id: AppState.experimentId,
          phase,
          trial_index: trialData.trial_index,
          media_id: trialData.media.media_id,
          ...result,
        };

        console.log("submit =", JSON.stringify(payload));

        const resp = await Api.submitTrial(payload);

        if (resp.next_state && resp.next_state !== `phase${phase}-realtest`) {
          Router.go(resp.next_state);
        } else {
          runNextRealTrial(phase);
        }
      } catch (e) {
        showToast(e.message);
      }
    },
  });
}

/* ---------- Shared interaction engine ----------*/
async function runInteractiveTrial({ phase, mediaPath, isDemo, trialIndex, totalTrials, trialParams, onFinish }) {
  const dots = Array.from({ length: totalTrials }, (_, i) =>
    `<span class="${i < trialIndex - 1 ? "done" : ""}"></span>`
  ).join("");

  const videoUrl = Api.mediaUrl(mediaPath);
  if (!videoUrl) {
    renderInto(pageShell(`
      <p class="subtitle">Could not load this trial's video (no media path returned by the server).</p>
      <p class="caption">Check that the backend is running and reachable, and that this page was opened via
        <code>http://</code> (e.g. <code>python3 -m http.server</code>) rather than double-clicking the file.</p>
    `));
    showToast("Missing video URL — see the on-screen message.");
    return;
  }

  const silent = isSilentPhase(phase);
  
  renderInto(pageShell(`
    ${!isDemo ? `<div class="progress-dots">${dots}</div>` : ""}
    <div class="stage${isDemo ? " demo-frame" : ""}" id="stage">
      <video id="trialVideo" src="${videoUrl}"${silent ? " muted" : ""} loop playsinline></video>
      <div class="stage-gate" id="stageGate">Loading video&hellip;</div>
      <div class="stage-overlay">
        <div class="result-readout" id="readout" style="visibility:hidden;">--</div>
      </div>
      ${phase !== 3 && phase !== 4 ? `<div class="side-label left">&laquo; Slower</div><div class="side-label right">Faster &raquo;</div>` : ""}
      <div class="hint" id="hint"></div>
    </div>
  `, { noNavPadding: true }));

  const video = document.getElementById("trialVideo");
  video.muted = silent;
  const gate = document.getElementById("stageGate");
  
  await playVideoWhenReady(video, gate);

  if (phase === 2) runPhase2(video, trialParams, isDemo, onFinish);
  else if (phase === 3) runPhase3(video, trialParams, isDemo, onFinish);
  else if (phase === 4) runPhase4(video, trialParams, isDemo, onFinish);
}

function playVideoWhenReady(video, gateEl) {
  return new Promise((resolve) => {
    function attemptPlay() {
      video.play().then(() => {
        gateEl.remove();
        resolve();
      }).catch(() => {
        gateEl.innerHTML = `<button class="btn" id="stageStartBtn">TAP TO START</button>`;
        document.getElementById("stageStartBtn").addEventListener("click", () => {
          video.play().then(() => { gateEl.remove(); resolve(); });
        }, { once: true });
      });
    }
    // readyState >= 2 (HAVE_CURRENT_DATA) means a frame is already available.
    if (video.readyState >= 2) attemptPlay();
    else video.addEventListener("loadeddata", attemptPlay, { once: true });
  });
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }


function revealResultAndContinue(html, onContinue, delayMs = 1500) {
  const readout = document.getElementById("readout");
  const hint = document.getElementById("hint");
  readout.style.visibility = "visible";
  readout.innerHTML = html;
  if (hint) hint.textContent = "";
  setTimeout(onContinue, delayMs);
}

/* Phase 2: Direct Resolution.  speed = mouse_position*2 + noise (noise is
   backend-provided, per SRS: seed = hash(experimentID+phase+trialIndex)). */
function runPhase2(video, trialParams, isDemo, onFinish) {
  const stage = document.getElementById("stage");
  document.getElementById("hint").textContent = "Move your mouse left/right, then CLICK when the speed feels natural.";
  const startTime = performance.now();
  const noise = trialParams.noise || 0;

  let speed = clamp(1.0 + noise, 0.1, 3);
  video.preservesPitch = false;
  video.playbackRate = speed;

  function onMove(e) {
    const rect = stage.getBoundingClientRect();
    const pos = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    speed = clamp(pos * 2 + noise, 0.1, 3);
    video.playbackRate = speed;
  }

  function onClick() {
    stage.removeEventListener("mousemove", onMove);
    stage.removeEventListener("click", onClick);
    video.pause();
    const hesitation = Math.round(performance.now() - startTime);
    const finalSpeed = speed;
    revealResultAndContinue(`${Math.round(finalSpeed * 100)}%`, () => {
      if (isDemo) onFinish();
      else onFinish({ selected_speed: Number(finalSpeed.toFixed(3)), hesitation_time_ms: hesitation });
    });
  }

  stage.addEventListener("mousemove", onMove);
  stage.addEventListener("click", onClick);
}

/* Phase 3: Speed Estimation. The video plays at a fixed, backend-chosen
   `actual_speed` for the whole trial; mouse movement changes the
   participant's on-screen ESTIMATE. */
function runPhase3(video, trialParams, isDemo, onFinish) {
  const stage = document.getElementById("stage");
  const readout = document.getElementById("readout");
  document.getElementById("hint").textContent = "Move your mouse to match the CURRENT playback rate, then CLICK to confirm.";
  readout.style.visibility = "visible";
  const startTime = performance.now();

  const actualSpeed = trialParams.actual_speed;
  video.playbackRate = clamp(actualSpeed, 0.1, 4);

  let estimate = 1.0;
  readout.textContent = "estimate: 100%";

  function onMove(e) {
    const rect = stage.getBoundingClientRect();
    const pos = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    estimate = pos * 2; // 0% - 200%
    readout.textContent = `estimate: ${Math.round(estimate * 100)}%`;
  }

  function onClick() {
    stage.removeEventListener("mousemove", onMove);
    stage.removeEventListener("click", onClick);
    video.pause();
    const hesitation = Math.round(performance.now() - startTime);
    const finalEstimate = estimate;
    revealResultAndContinue(
      `actual: ${Math.round(actualSpeed * 100)}% &nbsp;/&nbsp; your guess: ${Math.round(finalEstimate * 100)}%`,
      () => {
        if (isDemo) {
          onFinish();
        } else {
          onFinish({
            actual_speed: actualSpeed,
            estimated_speed: Number(finalEstimate.toFixed(3)),
            hesitation_time_ms: hesitation,
          });
        }
      }
    );
  }

  stage.addEventListener("mousemove", onMove);
  stage.addEventListener("click", onClick);
}

/* Phase 4: Threshold and Tolerance.
   Plays at 1.0x. After backend-provided delay_ms, speed drifts by `step`
   every `tick_ms` in the backend-provided `direction`.
   First click -> reveal Threshold immediately and KEEP it on screen.
   Second click -> reveal Tolerance BELOW the still-visible Threshold,
   then pause 1s before continuing. */
function runPhase4(video, trialParams, isDemo, onFinish) {
  const stage = document.getElementById("stage");
  const hint = document.getElementById("hint");
  const readout = document.getElementById("readout");
  hint.textContent = "CLICK the moment the speed changes from 1x.";
  video.playbackRate = 1.0;

  const { direction, delay_ms: delayMs, tick_ms: tickMs, step } = trialParams;

  let speed = 1.0;
  let clicks = 0;
  let thresholdSpeed = null;
  let tickTimer = null;

  const delayTimer = setTimeout(() => {
    tickTimer = setInterval(() => {
      speed = clamp(speed + direction * step, 0.05, 3);
      video.playbackRate = speed;
      
    }, tickMs);
  }, delayMs);

  function onClick() {
    clicks += 1;
    if (clicks === 1) {
      thresholdSpeed = speed;
     
      readout.style.visibility = "visible";
      readout.innerHTML = `Threshold: ${Math.round(thresholdSpeed * 100)}%`;
      hint.textContent = "CLICK AGAIN when it feels too fast or too slow.";
      return;
    }
    // second click
    clearTimeout(delayTimer);
    clearInterval(tickTimer);
    stage.removeEventListener("click", onClick);
    video.pause();
    const toleranceSpeed = speed;

    revealResultAndContinue(
      `Threshold: ${Math.round(thresholdSpeed * 100)}%<br/>Tolerance: ${Math.round(toleranceSpeed * 100)}%`,
      () => {
        if (isDemo) onFinish();
        else onFinish({
          delay_ms: delayMs,
          direction,
          threshold_speed: Number(thresholdSpeed.toFixed(3)),
          tolerance_speed: Number(toleranceSpeed.toFixed(3)),
        });
      }
    );
  }

  stage.addEventListener("click", onClick);
}
