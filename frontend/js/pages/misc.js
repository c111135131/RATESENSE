function showResumeDialog({ onContinue, onRestart }) {
  const modal = el(`
    <div class="modal-backdrop">
      <div class="modal-box">
        <h3>Continue experiment?</h3>
        <p>We found an experiment already in progress on this device.</p>
        <div class="modal-actions">
          <button id="resumeYes" class="primary">Yes, Continue</button>
          <button id="resumeNo">No, Restart</button>
        </div>
      </div>
    </div>
  `);
  document.body.appendChild(modal);
  document.getElementById("resumeYes").addEventListener("click", () => { modal.remove(); onContinue(); });
  document.getElementById("resumeNo").addEventListener("click", () => { modal.remove(); onRestart(); });
}

function showRestartConfirmDialog(onConfirm) {
  const modal = el(`
    <div class="modal-backdrop">
      <div class="modal-box">
        <h3>Restart experiment?</h3>
        <p>This will discard your current progress and self-recorded video, and start a new session from the beginning. Your previously submitted answers are kept for research records.</p>
        <div class="modal-actions">
          <button id="restartConfirmYes" class="primary">Yes, Restart</button>
          <button id="restartConfirmNo">Cancel</button>
        </div>
      </div>
    </div>
  `);
  document.body.appendChild(modal);
  document.getElementById("restartConfirmYes").addEventListener("click", () => { modal.remove(); onConfirm(); });
  document.getElementById("restartConfirmNo").addEventListener("click", () => modal.remove());
}