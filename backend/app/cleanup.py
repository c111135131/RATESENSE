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