from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..responses import ok, fail
from ..sanitize import sanitize_text
from ..schemas import TesterInfo

router = APIRouter(prefix="/api/v1/tester", tags=["tester"])

SURVEY_FIELDS = [
    "age", "gender", "occupation", "watch_hours", "platforms",
    "content_types", "preferred_speed", "adjust_behavior", "reasons", "satisfaction",
]


def _get_or_create(db: Session, experiment_id: str) -> models.TesterInfo:
    row = db.query(models.TesterInfo).get(experiment_id)
    if not row:
        row = models.TesterInfo(experiment_id=experiment_id, current_question=0, completed=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/{experiment_id}")
def get_survey_progress(experiment_id: str, db: Session = Depends(get_db)):
    """Resume support: tells the frontend which question to render next.
    Called on every page load of the survey -- if the participant closed
    the tab mid-survey, AppState.experimentId (LocalStorage, per SRS §6)
    is all the frontend needs to find its way back here and ask."""
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    row = _get_or_create(db, experiment_id)
    return ok({
        "current_question": row.current_question,
        "total_questions": len(SURVEY_FIELDS),
        "completed": row.completed,
    })


@router.post("/{experiment_id}/answer")
def submit_survey_answer(experiment_id: str, payload: TesterInfo, db: Session = Depends(get_db)):
    """Save exactly one question's answer and advance current_question.
    The frontend cannot move to question N+1 until this succeeds for
    question N (see survey.js's handleSurveyNext)."""
    if payload.experiment_id != experiment_id:
        return fail("experiment_id mismatch.", "BAD_REQUEST", 400)

    if payload.field not in SURVEY_FIELDS:
        return fail(f"Unknown survey field: {payload.field}", "INVALID_FIELD", 422)

    expected_field = (
        SURVEY_FIELDS[payload.question_index]
        if 0 <= payload.question_index < len(SURVEY_FIELDS) else None
    )
    if payload.field != expected_field:
        return fail("field does not match question_index.", "INVALID_FIELD", 422)

    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    row = _get_or_create(db, experiment_id)

    clean_value = sanitize_text(payload.value)
    setattr(row, payload.field, clean_value)

    row.current_question = max(row.current_question, payload.question_index + 1)
    if row.current_question >= len(SURVEY_FIELDS):
        row.completed = True

    db.commit()
    db.refresh(row)

    return ok({
        "current_question": row.current_question,
        "total_questions": len(SURVEY_FIELDS),
        "completed": row.completed,
    })