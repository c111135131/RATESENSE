import os

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from .. import models, state_machine
from ..database import get_db
from ..responses import ok, fail
from ..timeutils import now_toronto

router = APIRouter(prefix="/api/v1/phase1", tags=["phase1"])

MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media", "recordings")
os.makedirs(MEDIA_DIR, exist_ok=True)


@router.post("/upload")
async def upload_self_recording(
    experiment_id: str = Form(...),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Record exactly 5 seconds, upload immediately, store video path."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    ext = os.path.splitext(video_file.filename or "recording.webm")[1] or ".webm"
    filename = f"{experiment_id}{ext}"
    dest_path = os.path.join(MEDIA_DIR, filename)

    contents = await video_file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    recording = models.SelfRecording(
        experiment_id=experiment_id,
        video_path=dest_path,
        deleted=False,
        upload_time=now_toronto(),
    )
    db.add(recording)
    db.commit()

    return ok({"success": True})



@router.post("/complete")
def complete_phase1(experiment_id: str = Form(...), db: Session = Depends(get_db)):
    """Update current_state and current_phase after Phase 1 finishes."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    exp.current_state = state_machine.next_state("phase1-recording")  # -> phase1-complete
    exp.current_phase = 1
    db.commit()

    return ok({"next_state": exp.current_state})
