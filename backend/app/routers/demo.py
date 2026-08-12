from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, seed, state_machine, speed_utils, params
from ..database import get_db
from ..responses import ok, fail
from ..schemas import DemoCompleteRequest

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.get("")
def get_demo_info(
    phase: int = Query(..., ge=2, le=4),
    experiment_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """All Demo pages (Phase 2-4) use the same predefined demo video.
    Demo interactions are never recorded (record_data: false), but the
    demo still gets real backend-generated parameters (same generator as
    real trials, just keyed on "demo" instead of a trial_index) so the
    practice run behaves identically to the real thing.
    """
    demo_media = seed.get_demo_media(db)
    data = {
        "phase": phase,
        "media_path": demo_media.media_path if demo_media else "/media/demo_video.mp4",
        "record_data": False,
    }


    seed_key = experiment_id or "anonymous-demo"

    if phase == 2:
        data["noise"] = speed_utils.trial_noise(seed_key, phase, "demo")
    elif phase == 3:
        data["actual_speed"] = speed_utils.trial_actual_speed(seed_key, phase, "demo")
    elif phase == 4:
        data["delay_ms"] = params.PHASE4_DELAY_MS
        data["tick_ms"] = params.PHASE4_TICK_MS
        data["step"] = params.PHASE4_STEP
        data["direction"] = speed_utils.trial_direction(seed_key, phase, "demo")

    return ok(data)


@router.post("/complete")
def complete_demo(payload: DemoCompleteRequest, db: Session = Depends(get_db)):

    exp = db.query(models.Experiment).get(payload.experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    expected_state = f"phase{payload.phase}-demo"
    if exp.current_state != expected_state:
        return fail(
            f"Experiment is not in the expected demo state (expected {expected_state}, got {exp.current_state}).",
            "INVALID_STATE", 409,
        )

    exp.current_state = state_machine.next_state(exp.current_state)  # -> phaseN-demo-complete
    db.commit()

    return ok({"next_state": exp.current_state})
