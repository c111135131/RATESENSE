import os
import random

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from .. import models, seed, state_machine
from ..database import get_db
from ..responses import ok, fail
from ..timeutils import now_toronto

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


def assign_media(db: Session, experiment_id: str):
    predefined = seed.get_predefined_media(db)

    num_to_select = len(predefined)
    print(num_to_select)
    order = random.sample(predefined, num_to_select)
    
    for idx, media in enumerate(order, start=1):
        db.add(models.ExperimentMedia(
            experiment_id=experiment_id, display_order=idx, media_id=media.media_id
        ))
    db.commit()


@router.post("")
def create_experiment(db: Session = Depends(get_db)):
    """Create a new experiment session (SRS 3. System Workflow)."""
    experiment = models.Experiment(current_state="terms-agreement", current_phase=0, current_trial=0)
    experiment.touch_expiration()
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    assign_media(db, experiment.experiment_id)

    return ok({
        "experiment_id": experiment.experiment_id,
        "current_state": experiment.current_state,
        "status": experiment.status.value,
    }, status_code=201)


@router.get("/{experiment_id}")
def resume_experiment(experiment_id: str = Path(...), db: Session = Depends(get_db)):
    """Retrieve experiment status after refresh or reconnect."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    if exp.expired_at and exp.expired_at < now_toronto() and exp.status == models.ExperimentStatus.IN_PROGRESS:
        exp.status = models.ExperimentStatus.EXPIRED
        db.commit()

    return ok({
        "experiment_id": exp.experiment_id,
        "current_state": exp.current_state,
        "current_phase": exp.current_phase,
        "current_trial": exp.current_trial,
        "status": exp.status.value,
    })


@router.post("/{experiment_id}/restart")
def restart_experiment(experiment_id: str, db: Session = Depends(get_db)):
    """Restart experiment while preserving previous experimental data."""
    old_exp = db.query(models.Experiment).get(experiment_id)
    if not old_exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    # Delete Phase 1 self-recording, keep historical experiment data.
    for rec in old_exp.self_recordings:
        if not rec.deleted:
            if rec.video_path and os.path.exists(rec.video_path):
                try:
                    os.remove(rec.video_path)
                except OSError:
                    pass
            rec.deleted = True
    old_exp.status = models.ExperimentStatus.ABANDONED
    db.commit()

    new_exp = models.Experiment(current_state="terms-agreement", current_phase=0, current_trial=0)
    new_exp.touch_expiration()
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    assign_media(db, new_exp.experiment_id)

    return ok({"new_experiment_id": new_exp.experiment_id})


@router.post("/{experiment_id}/complete")
def complete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    """Finish experiment: mark completed and delete self-recorded video."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    for rec in exp.self_recordings:
        if not rec.deleted:
            if rec.video_path and os.path.exists(rec.video_path):
                try:
                    os.remove(rec.video_path)
                except OSError:
                    pass
            rec.deleted = True

    exp.status = models.ExperimentStatus.COMPLETED
    exp.current_state = "completed"
    db.commit()

    return ok({"experiment_id": exp.experiment_id, "status": exp.status.value})


@router.post("/{experiment_id}/next")
def get_next_state(experiment_id: str, db: Session = Depends(get_db)):
    """The backend (not the frontend) controls experiment progression."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    nxt = state_machine.next_state(exp.current_state)
    exp.current_state = nxt
    if nxt in ("phase1-start",):
        exp.current_phase = 1
    for p in (2, 3, 4):
        if nxt == f"phase{p}-start":
            exp.current_phase = p
    db.commit()

    return ok({"next_state": nxt})
