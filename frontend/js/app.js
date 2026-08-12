async function bootstrap() {
  const id = AppState.loadId();

  if (!id) {
    Router.go("home");
    return;
  }

  try {
    const data = await Api.resumeExperiment(id);
    AppState.experimentId = id;

    if (data.status !== "IN_PROGRESS") {
      // COMPLETED / ABANDONED / EXPIRED -> start fresh
      AppState.clear();
      Router.go("home");
      return;
    }

    if (data.current_state === "home" || data.current_state === "terms-agreement") {
      Router.go(data.current_state);
      return;
    }

    showResumeDialog({
      onContinue: () => Router.go(data.current_state),
      onRestart: async () => {
        try {
          const restarted = await Api.restartExperiment(id);
          AppState.saveId(restarted.new_experiment_id);
          Router.go("home");
        } catch (e) {
          showToast(e.message);
        }
      },
    });

  } catch (e) {
    // experiment not found on server (e.g. fresh DB) -> start over
    AppState.clear();
    Router.go("home");
  }
}


function setupLogoRestart() {
  const logo = document.getElementById("logoLink");
  if (!logo) return;

  logo.addEventListener("click", (e) => {
    e.preventDefault();
    
    if (!AppState.experimentId) {
      Router.go("home");
      return;
    }

    showRestartConfirmDialog(async () => {
      try {
        const data = await Api.restartExperiment(AppState.experimentId);
        AppState.saveId(data.new_experiment_id);
        Router.go("home");
      } catch (err) {
        showToast(err.message);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupLogoRestart();
  bootstrap();
});