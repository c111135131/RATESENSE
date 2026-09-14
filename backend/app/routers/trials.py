from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, state_machine, speed_utils, params
from ..database import get_db
from ..responses import ok, fail
from ..schemas import TrialSubmitRequest

router = APIRouter(prefix="/api/v1", tags=["trials"])


def _ordered_media_for_experiment(db: Session, experiment_id: str):
    """n predefined videos (randomized order at experiment creation) followed
    by the participant's own self-recorded video -- n+1 videos total, used
    identically across Phase 2/3/4 (SRS section 5).
    """
    rows = (
        db.query(models.ExperimentMedia)
        .filter(models.ExperimentMedia.experiment_id == experiment_id)
        .order_by(models.ExperimentMedia.display_order)
        .all()
    )
    media_list = [
        {
            "media_id": r.media.media_id,
            "media_path": r.media.media_path,
            "overrides": {
                "phase3_actual_speed": r.media.phase3_actual_speed_override,
                "phase4_direction": r.media.phase4_direction_override,
                "phase4_delay_ms": r.media.phase4_delay_ms_override,
                "phase4_tick_ms": r.media.phase4_tick_ms_override,
            },
        }
        for r in rows
    ]

    self_rec = (
        db.query(models.SelfRecording)
        .filter(models.SelfRecording.experiment_id == experiment_id, models.SelfRecording.deleted.is_(False))
        .order_by(models.SelfRecording.recording_id.desc())
        .first()
    )
    if self_rec:
        media_list.append({
            "media_id": None,
            "media_path": f"/media/recordings/{experiment_id}.webm",
            "overrides": {
                "phase3_actual_speed": self_rec.phase3_actual_speed_override,
                "phase4_direction": self_rec.phase4_direction_override,
                "phase4_delay_ms": self_rec.phase4_delay_ms_override,
                "phase4_tick_ms": self_rec.phase4_tick_ms_override,
            },
        })

    return media_list


@router.get("/trials/next")
def get_next_trial(experiment_id: str = Query(...), phase: int = Query(..., ge=2, le=4), db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    media_list = _ordered_media_for_experiment(db, experiment_id)
    trial_index = exp.current_trial + 1 if exp.current_phase == phase else 1

    if trial_index > len(media_list):
        return fail("No more trials for this phase.", "NO_MORE_TRIALS", 409)

    media_entry = media_list[trial_index - 1]
    overrides = media_entry["overrides"]
    media = {"media_id": media_entry["media_id"], "media_path": media_entry["media_path"]}

    data = {"trial_index": trial_index, "media": media}
    data["total_trials"] = len(media_list)
    
    if phase == 2:
        data["noise"] = speed_utils.trial_noise(experiment_id, phase, trial_index)
    elif phase == 3:
        override = overrides.get("phase3_actual_speed")
        data["actual_speed"] = (
            override if override is not None
            else speed_utils.trial_actual_speed(experiment_id, phase, trial_index)
        )
    elif phase == 4:
        delay_override = overrides.get("phase4_delay_ms")
        tick_override = overrides.get("phase4_tick_ms")
        direction_override = overrides.get("phase4_direction")
        data["delay_ms"] = delay_override if delay_override is not None else params.PHASE4_DELAY_MS
        data["tick_ms"] = tick_override if tick_override is not None else params.PHASE4_TICK_MS
        data["step"] = params.PHASE4_STEP
        data["direction"] = (
            direction_override if direction_override is not None
            else speed_utils.trial_direction(experiment_id, phase, trial_index)
        )

    # developer-mode console log (SRS section 8)
    print(f"Phase {phase} | Trial {trial_index} | Media Path {media['media_path']}")

    return ok(data)


@router.post("/trials")
def submit_trial(payload: TrialSubmitRequest, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).get(payload.experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    trial = models.ExperimentTrial(
        experiment_id=payload.experiment_id,
        phase=payload.phase,
        trial_index=payload.trial_index,
        media_id=payload.media_id,
        selected_speed=payload.selected_speed,
        actual_speed=payload.actual_speed,
        estimated_speed=payload.estimated_speed,
        hesitation_ms=payload.hesitation_time_ms,
        delay_ms=payload.delay_ms,
        direction=payload.direction,
        threshold_speed=payload.threshold_speed,
        tolerance_speed=payload.tolerance_speed,
    )
    db.add(trial)

    exp.current_phase = payload.phase
    exp.current_trial = payload.trial_index

    total_trials = len(_ordered_media_for_experiment(db, payload.experiment_id))
    next_state = exp.current_state
    if payload.trial_index >= total_trials:
        # all trials for this phase are done -> advance state machine
        realtest_state = f"phase{payload.phase}-realtest"
        next_state = state_machine.next_state(realtest_state)  # -> phaseN-complete
        exp.current_state = next_state
        exp.current_trial = 0

    db.commit()

    return ok({"next_state": next_state})
