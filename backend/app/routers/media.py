from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..responses import ok, fail

router = APIRouter(prefix="/api/v1/experiments", tags=["media"])


@router.get("/{experiment_id}/media")
def get_experiment_media(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    rows = (
        db.query(models.ExperimentMedia)
        .filter(models.ExperimentMedia.experiment_id == experiment_id)
        .order_by(models.ExperimentMedia.display_order)
        .all()
    )
    data = [
        {"display_order": r.display_order, "media_id": r.media.media_id, "media_path": r.media.media_path}
        for r in rows
    ]
    return ok(data)
