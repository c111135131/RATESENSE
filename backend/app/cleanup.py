"""Shared expired-experiment cleanup logic.

Used by BOTH the manual POST /admin/cleanup endpoint (routers/admin.py)
and the automatic 24-hour background task (scheduler.py) -- keeping this
in one place means there's only ever one definition of "what counts as
expired" / "what's safe to delete" to maintain.
"""
import os

from sqlalchemy.orm import Session

from . import models
from .timeutils import now_toronto


def perform_cleanup(db: Session) -> dict:
    """Two separate things happen here, in order:

    1. Expire stale IN_PROGRESS experiments.
       Any experiment whose expired_at has passed gets marked EXPIRED,
       and its self-recording (if any) is deleted from disk -- exactly
       what the old cleanup endpoint always did. All trial/survey data is
       KEPT.

    2. Hard-delete empty EXPIRED/ABANDONED experiments.
       Any experiment that is now EXPIRED or ABANDONED, AND never
       progressed past terms-agreement, is deleted entirely -- not just
       marked. current_state == "terms-agreement" is the state every
       experiment starts in immediately after creation (see
       routers/experiments.py's create_experiment), so this precisely
       identifies "the participant never even got past the consent
       screen": there is no self-recording, no ExperimentTrial rows, and
       no SurveyResponse row attached yet -- just the empty Experiment
       row and the ExperimentMedia rows randomly assigned at creation.
       Keeping those forever is pure wasted space, so they're removed
       completely rather than just flagged.

       Note: an experiment expired in step 1 above that also happens to
       still be at terms-agreement is picked up by step 2 in the SAME
       call -- no need to wait for a second cleanup cycle.
    """
    now = now_toronto()

    # --- Step 1: expire stale IN_PROGRESS experiments (unchanged behavior) ---
    stale = (
        db.query(models.Experiment)
        .filter(models.Experiment.expired_at.isnot(None), models.Experiment.expired_at < now)
        .filter(models.Experiment.status == models.ExperimentStatus.IN_PROGRESS)
        .all()
    )
    expired_count = 0
    for exp in stale:
        for rec in exp.self_recordings:
            if not rec.deleted:
                if rec.video_path and os.path.exists(rec.video_path):
                    try:
                        os.remove(rec.video_path)
                    except OSError:
                        pass
                rec.deleted = True
        exp.status = models.ExperimentStatus.EXPIRED
        expired_count += 1
    db.commit()

    # --- Step 2: hard-delete empty terms-agreement-only experiments ---
    deletable = (
        db.query(models.Experiment)
        .filter(models.Experiment.current_state == "terms-agreement")
        .filter(models.Experiment.status.in_([
            models.ExperimentStatus.EXPIRED,
            models.ExperimentStatus.ABANDONED,
        ]))
        .all()
    )
    deleted_count = 0
    for exp in deletable:
        db.query(models.ExperimentMedia).filter(
            models.ExperimentMedia.experiment_id == exp.experiment_id
        ).delete(synchronize_session=False)

        # Defensive: a self-recording shouldn't exist yet at
        # terms-agreement, but clean up the file + row if one somehow does.
        for rec in list(exp.self_recordings):
            if rec.video_path and os.path.exists(rec.video_path):
                try:
                    os.remove(rec.video_path)
                except OSError:
                    pass
            db.delete(rec)

        db.query(models.ExperimentTrial).filter(
            models.ExperimentTrial.experiment_id == exp.experiment_id
        ).delete(synchronize_session=False)

        db.query(models.SurveyResponse).filter(
            models.SurveyResponse.experiment_id == exp.experiment_id
        ).delete(synchronize_session=False)

        db.delete(exp)
        deleted_count += 1
    db.commit()

    return {"expired_count": expired_count, "deleted_count": deleted_count}