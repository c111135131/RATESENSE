Pages["phase1-instruction"] = async () => {
  renderInto(pageShell(`
    <h2 class="serif" style="font-size:1.6rem">What to do:</h2>
    <div class="two-col">
      <div class="col">
      <div class="demo-stage">
        <div class="demo-stage-overlay">
          <svg class="camera-illustration" viewBox="0 0 100 90" fill="none" stroke="white" stroke-width="3">
            <rect x="15" y="10" width="70" height="55" rx="6"/>
            <circle cx="50" cy="37" r="16"/>
            <circle cx="50" cy="37" r="2" fill="white"/>
            <rect x="35" y="70" width="30" height="6" rx="2"/>
            <rect x="42" y="76" width="16" height="8" rx="2"/>
          </svg>
        </div>
      </div>
        <p class="caption">Make sure your camera is connected and turned on.</p>
      </div>
      <div class="col">
        <div class="demo-stage">
          <div class="demo-stage-overlay"><img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExOXdhM3dpYnpmaXF4Ynlvb2Nra2FvZmVpenFpYXQwa3d1aHJoMXo2biZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/fX5cZemSfX1cMZYuUJ/giphy.gif" alt="helloworld"></div>
        </div>
        <p class="caption">Wave and say "Hello world!". Speak clearly and wave in a natural manner.</p>
      </div>
    </div>
    <div class="btn-row" style="margin-top:2rem;">${continueButton()}</div>
  `));

  document.getElementById("continueBtn").addEventListener("click", async () => {
    const hasCamera = await checkCamera();
    if (hasCamera) {
      Router.advance();
    } else {
      showCameraDeniedModal();
    }
  });
};

async function checkCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch (e) {
    return false;
  }
}

function showCameraDeniedModal() {
  const modal = el(`
    <div class="modal-backdrop">
      <div class="modal-box">
        <h3>No camera detected.</h3>
        <p>Please grant browser permission to proceed.</p>
        <div class="modal-actions"><button class="primary" id="modalYes">YES</button></div>
      </div>
    </div>
  `);
  document.body.appendChild(modal);
  document.getElementById("modalYes").addEventListener("click", () => modal.remove());
}

Pages["phase1-recording"] = async () => {
  renderInto(pageShell(`
    <div class="stage" id="stage">
      <video id="preview" autoplay muted playsinline></video>
      <div class="stage-overlay" id="overlay">
        <div class="serif" style="font-size:3rem; font-weight:800; margin-bottom:1rem; color:var(--red);" id="readyLabel">READY?</div>
        <button class="btn" id="startBtn" style="pointer-events:auto;">START</button>
        <div class="hint">Please <b style="color:var(--red);">CLICK</b> to start recording.</div>
      </div>
    </div>
  `, { noNavPadding: false }));

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    document.getElementById("preview").srcObject = stream;
  } catch (e) {
    showToast("Camera access is required to continue.");
    return;
  }

  document.getElementById("startBtn").addEventListener("click", () => startRecording(stream));
};

function startRecording(stream) {
  runPrepCountdown(3, () => runActualRecording(stream, 5));
}

/* Stage 1: a plain countdown (no MediaRecorder running yet) so the
   participant has a moment to get ready before anything is actually
   captured. */
function runPrepCountdown(seconds, onComplete) {
  const overlay = document.getElementById("overlay");
  overlay.innerHTML = `
    <div class="serif" style="font-size:2rem; font-weight:800; margin-bottom:1rem;">ready to recording...</div>
    <div class="countdown-ring" id="prepCountdown">${seconds}</div>
  `;

  let secondsLeft = seconds;
  const countdownEl = document.getElementById("prepCountdown");
  const timer = setInterval(() => {
    secondsLeft -= 1;
    if (secondsLeft > 0) {
      countdownEl.textContent = secondsLeft;
    } else {
      clearInterval(timer);
      onComplete();
    }
  }, 1000);
}

/* Stage 2: the actual capture -- MediaRecorder only starts here, once the
   prep countdown above has finished. */
function runActualRecording(stream, seconds) {
  const overlay = document.getElementById("overlay");
  overlay.innerHTML = `
    <div class="rec-badge">REC</div>
    <div class="serif" style="font-size:2rem; font-weight:800; margin: 0.75rem 0 0.5rem; color: var(--red)">You are recording now...</div>
    <div class="countdown-ring" style='color:var(--white); background-color:var(--red)' id="countdown">${seconds}</div>
  `;

  const chunks = [];
  const recorder = new MediaRecorder(stream, { mimeType: pickMimeType() });
  recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

  recorder.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop());
    const blob = new Blob(chunks, { type: recorder.mimeType });
    try {
      await Api.uploadPhase1(AppState.experimentId, blob);
      await Api.completePhase1(AppState.experimentId);
      Router.go("phase1-complete");
    } catch (e) {
      showToast("Upload failed: " + e.message);
    }
  };

  recorder.start();

  let secondsLeft = seconds;
  const countdownEl = document.getElementById("countdown");
  const timer = setInterval(() => {
    secondsLeft -= 1;
    countdownEl.textContent = Math.max(secondsLeft, 0);
    if (secondsLeft <= 0) {
      clearInterval(timer);
      recorder.stop();
    }
  }, 1000);
}

function pickMimeType() {
  const candidates = ["video/webm;codecs=vp8,opus", "video/webm", "video/mp4"];
  for (const c of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) return c;
  }
  return "";
}
