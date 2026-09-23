import csv
import io
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, params, speed_utils, seed, config_store
from ..sanitize import sanitize_filename
from ..auth import require_admin, verify_login
from ..database import get_db
from ..responses import ok, fail
from ..schemas import AdminLoginRequest, MediaParamsOverride, SettingsUpdateRequest
from ..cleanup import perform_cleanup

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

CSV_FIELDS = [
    "trial_id", "experiment_id", "phase", "trial_index", "media_name",
    "selected_speed", "actual_speed", "estimated_speed", "hesitation_ms",
    "delay_ms", "direction", "threshold_speed", "tolerance_speed", "created_at",

    "age", "gender", "occupation", "watch_hours", "platforms",
    "content_types", "preferred_speed", "adjust_behavior", "reasons", "satisfaction",
]

def _media_name_lookup(db: Session) -> dict:
    return {m.media_id: m.filename for m in db.query(models.Media).all()}

def _media_name_for(media_id, lookup: dict) -> str:
    if media_id is None:
        return "Self-Recording"
    return lookup.get(media_id, f"media_id={media_id}")

def _effective_phase34_params(experiment_id: str, trial_index: int, p3_override, p4_dir_override, p4_delay_override, p4_tick_override) -> dict:
    phase3_actual_speed = (
        p3_override if p3_override is not None
        else speed_utils.trial_actual_speed(experiment_id, 3, trial_index)
    )
    phase4_direction = (
        p4_dir_override if p4_dir_override is not None
        else speed_utils.trial_direction(experiment_id, 4, trial_index)
    )
    phase4_delay_ms = p4_delay_override if p4_delay_override is not None else params.PHASE4_DELAY_MS
    phase4_tick_ms = p4_tick_override if p4_tick_override is not None else params.PHASE4_TICK_MS

    return {
        "phase3_actual_speed": phase3_actual_speed,
        "phase3_actual_speed_is_override": p3_override is not None,
        "phase4_direction": phase4_direction,
        "phase4_direction_is_override": p4_dir_override is not None,
        "phase4_delay_ms": phase4_delay_ms,
        "phase4_delay_ms_is_override": p4_delay_override is not None,
        "phase4_tick_ms": phase4_tick_ms,
        "phase4_tick_ms_is_override": p4_tick_override is not None,
    }


# ---------------------------------------------------------------------------
# Auth (no Depends(require_admin) here -- this IS the endpoint that issues
# the token in the first place)
# ---------------------------------------------------------------------------
@router.post("/login")
def admin_login(payload: AdminLoginRequest):
    token = verify_login(payload.username, payload.password)
    if not token:
        return fail("Invalid username or password.", "INVALID_CREDENTIALS", 401)
    return ok({"token": token})

# ---------------------------------------------------------------------------
# Everything below requires a valid X-Admin-Token (see ../auth.py)
# ---------------------------------------------------------------------------
@router.get("/export-csv")
def export_csv(db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    """Generate experiment_data.csv and download it immediately (SRS 9).
    Each trial row is joined with that experiment's survey answers (if
    any), so every row also carries the participant's demographics --
    makes cross-referencing "did older participants judge speed
    differently" etc. possible directly in Excel/SPSS without a manual join."""
    trials = db.query(models.ExperimentTrial).all()
    media_lookup = _media_name_lookup(db)

    # experiment_id -> TesterInfo row, built once so we do a single query
    # instead of re-querying the DB inside the loop for every trial.
    survey_lookup = {s.experiment_id: s for s in db.query(models.TesterInfo).all()}

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()

    for t in trials:
        survey = survey_lookup.get(t.experiment_id)  # None if this experiment never did the survey
        row = {
            "trial_id": t.trial_id,
            "experiment_id": t.experiment_id,
            "phase": t.phase,
            "trial_index": t.trial_index,
            "media_name": _media_name_for(t.media_id, media_lookup),
            "selected_speed": t.selected_speed,
            "actual_speed": t.actual_speed,
            "estimated_speed": t.estimated_speed,
            "hesitation_ms": t.hesitation_ms,
            "delay_ms": t.delay_ms,
            "direction": t.direction,
            "threshold_speed": t.threshold_speed,
            "tolerance_speed": t.tolerance_speed,
            "created_at": t.created_at,
            "age": survey.age if survey else None,
            "gender": survey.gender if survey else None,
            "occupation": survey.occupation if survey else None,
            "watch_hours": survey.watch_hours if survey else None,
            "platforms": survey.platforms if survey else None,
            "content_types": survey.content_types if survey else None,
            "preferred_speed": survey.preferred_speed if survey else None,
            "adjust_behavior": survey.adjust_behavior if survey else None,
            "reasons": survey.reasons if survey else None,
            "satisfaction": survey.satisfaction if survey else None,
        }
        writer.writerow(row)

    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=experiment_data.csv"},
    )

@router.post("/cleanup")
def cleanup_expired(db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    """Manually trigger the same cleanup the 24-hour background task runs
    automatically (see scheduler.py) -- useful for an on-demand sweep
    without waiting for the next scheduled run."""
    result = perform_cleanup(db)
    return ok(result)

# ---------------------------------------------------------------------------
# DB browsing (so the admin doesn't need to open a separate DB tool)
# ---------------------------------------------------------------------------
@router.get("/experiments")
def list_experiments(page: int = Query(1, ge=1),
    size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db), 
    _admin: None = Depends(require_admin)):
    skip = (page - 1) * size
    rows = (
        db.query(models.Experiment)
        .order_by(models.Experiment.created_at.desc())
        .offset(skip)
        .limit(size)
        .all()
    )
    return ok([
        {
            "experiment_id": e.experiment_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            "current_state": e.current_state,
            "current_phase": e.current_phase,
            "current_trial": e.current_trial,
            "status": e.status.value,
            "expired_at": e.expired_at.isoformat() if e.expired_at else None,
        }
        for e in rows
    ])


@router.get("/experiments/{experiment_id}")
def get_experiment_detail(experiment_id: str, db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    exp = db.query(models.Experiment).get(experiment_id)
    if not exp:
        return fail("Experiment not found.", "EXPERIMENT_NOT_FOUND", 404)

    media_rows = (
        db.query(models.ExperimentMedia)
        .filter(models.ExperimentMedia.experiment_id == experiment_id)
        .order_by(models.ExperimentMedia.display_order)
        .all()
    )
    trial_rows = (
        db.query(models.ExperimentTrial)
        .filter(models.ExperimentTrial.experiment_id == experiment_id)
        .order_by(models.ExperimentTrial.phase, models.ExperimentTrial.trial_index)
        .all()
    )
    recording_rows = (
        db.query(models.SelfRecording)
        .filter(models.SelfRecording.experiment_id == experiment_id)
        .all()
    )
    media_lookup = _media_name_lookup(db)

    # --- the 5 predefined videos: read-only here (global override, edit
    # via PUT /admin/media/{media_id}/params in the Video Library screen) ---
    media_entries = []
    for m in media_rows:
        effective = _effective_phase34_params(
            experiment_id, m.display_order,
            m.media.phase3_actual_speed_override if m.media else None,
            m.media.phase4_direction_override if m.media else None,
            m.media.phase4_delay_ms_override if m.media else None,
            m.media.phase4_tick_ms_override if m.media else None,
        )
        media_entries.append({
            "media_id": m.media_id,
            "display_order": m.display_order,
            "filename": m.media.filename if m.media else None,
            "media_path": m.media.media_path if m.media else None,
            **effective,
        })


    active_recording = next((r for r in recording_rows if not r.deleted), None)
    self_recording_params = None
    if active_recording:
        trial_index = len(media_rows) + 1  # self-recording is always the last slot
        effective = _effective_phase34_params(
            experiment_id, trial_index,
            active_recording.phase3_actual_speed_override,
            active_recording.phase4_direction_override,
            active_recording.phase4_delay_ms_override,
            active_recording.phase4_tick_ms_override,
        )
        self_recording_params = {
            "recording_id": active_recording.recording_id,
            "phase3_actual_speed_override": active_recording.phase3_actual_speed_override,
            "phase4_direction_override": active_recording.phase4_direction_override,
            "phase4_delay_ms_override": active_recording.phase4_delay_ms_override,
            "phase4_tick_ms_override": active_recording.phase4_tick_ms_override,
            **effective,
        }

    return ok({
        "experiment": {
            "experiment_id": exp.experiment_id,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "updated_at": exp.updated_at.isoformat() if exp.updated_at else None,
            "current_state": exp.current_state,
            "current_phase": exp.current_phase,
            "current_trial": exp.current_trial,
            "status": exp.status.value,
            "expired_at": exp.expired_at.isoformat() if exp.expired_at else None,
        },
        "media": media_entries,
        "self_recording_params": self_recording_params,
        "self_recordings": [
            {
                "recording_id": r.recording_id,
                "video_path": r.video_path,
                "deleted": r.deleted,
                "upload_time": r.upload_time.isoformat() if r.upload_time else None,
            }
            for r in recording_rows
        ],
        "trials": [
            {
                "trial_id": t.trial_id,
                "phase": t.phase,
                "trial_index": t.trial_index,
                "media_id": t.media_id,
                "media_name": _media_name_for(t.media_id, media_lookup),
                "selected_speed": t.selected_speed,
                "actual_speed": t.actual_speed,
                "estimated_speed": t.estimated_speed,
                "hesitation_ms": t.hesitation_ms,
                "delay_ms": t.delay_ms,
                "direction": t.direction,
                "threshold_speed": t.threshold_speed,
                "tolerance_speed": t.tolerance_speed,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in trial_rows
        ],
    })


# ---------------------------------------------------------------------------
# Video parameter overrides (admin panel feature).
# These are GLOBAL -- keyed only on media_id, not on any one experiment --
# ---------------------------------------------------------------------------
@router.get("/media")
def list_media(db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    rows = db.query(models.Media).order_by(models.Media.media_id).all()
    return ok([
        {
            "media_id": m.media_id,
            "filename": m.filename,
            "media_path": m.media_path,
            "is_active": m.is_active,
            "phase3_actual_speed": m.phase3_actual_speed_override,
            "phase4_direction": m.phase4_direction_override,
            "phase4_delay_ms": m.phase4_delay_ms_override,
            "phase4_tick_ms": m.phase4_tick_ms_override,
        }
        for m in rows
    ])


@router.put("/media/{media_id}/params")
def update_media_params(
    media_id: int,
    payload: MediaParamsOverride,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    row = db.query(models.Media).get(media_id)
    if not row:
        return fail("Media not found.", "NOT_FOUND", 404)

    # exclude_unset (not exclude_none!) so a field the client didn't send
    # is left untouched, but a field explicitly sent as `null` DOES clear
    # that specific override.
    updates = payload.dict(exclude_unset=True)
    if "phase3_actual_speed" in updates:
        row.phase3_actual_speed_override = updates["phase3_actual_speed"]
    if "phase4_direction" in updates:
        row.phase4_direction_override = updates["phase4_direction"]
    if "phase4_delay_ms" in updates:
        row.phase4_delay_ms_override = updates["phase4_delay_ms"]
    if "phase4_tick_ms" in updates:
        row.phase4_tick_ms_override = updates["phase4_tick_ms"]

    db.commit()
    db.refresh(row)

    return ok({
        "media_id": row.media_id,
        "filename": row.filename,
        "phase3_actual_speed": row.phase3_actual_speed_override,
        "phase4_direction": row.phase4_direction_override,
        "phase4_delay_ms": row.phase4_delay_ms_override,
        "phase4_tick_ms": row.phase4_tick_ms_override,
    })

# ---------------------------------------------------------------------------
# Self-recording parameter overrides (admin panel feature).
# PER-EXPERIMENT -- unlike Media.*_override, a self-recorded video is
# unique to one experiment, so this only ever affects that one experiment.
# ---------------------------------------------------------------------------
@router.put("/experiments/{experiment_id}/self-recording/params")
def update_self_recording_params(
    experiment_id: str,
    payload: MediaParamsOverride,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    row = (
        db.query(models.SelfRecording)
        .filter(models.SelfRecording.experiment_id == experiment_id, models.SelfRecording.deleted.is_(False))
        .order_by(models.SelfRecording.recording_id.desc())
        .first()
    )
    if not row:
        return fail("No active self-recording found for this experiment.", "NOT_FOUND", 404)

    updates = payload.dict(exclude_unset=True)
    if "phase3_actual_speed" in updates:
        row.phase3_actual_speed_override = updates["phase3_actual_speed"]
    if "phase4_direction" in updates:
        row.phase4_direction_override = updates["phase4_direction"]
    if "phase4_delay_ms" in updates:
        row.phase4_delay_ms_override = updates["phase4_delay_ms"]
    if "phase4_tick_ms" in updates:
        row.phase4_tick_ms_override = updates["phase4_tick_ms"]

    db.commit()
    db.refresh(row)

    return ok({
        "recording_id": row.recording_id,
        "phase3_actual_speed": row.phase3_actual_speed_override,
        "phase4_direction": row.phase4_direction_override,
        "phase4_delay_ms": row.phase4_delay_ms_override,
        "phase4_tick_ms": row.phase4_tick_ms_override,
    })

# ---------------------------------------------------------------------------
# Global settings (admin panel feature): how many predefined videos get
# randomly assigned to each NEW experiment. Add these two endpoints into
# your existing admin.py. Make sure this import is present near the top:
# ---------------------------------------------------------------------------
@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    total_trials = config_store.get_total_trials(db)
    available = len(seed.get_predefined_media(db))
    return ok({
        "total_trials": total_trials,
        "available_media_count": available,
    })


@router.put("/settings")
def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    if payload.total_trials < 1:
        return fail("total_trials must be at least 1.", "INVALID_VALUE", 422)

    available = len(seed.get_predefined_media(db))
    config_store.set_total_trials(db, payload.total_trials)

    warning = None
    if payload.total_trials > available:
        warning = (
            f"Only {available} predefined videos exist in the Media table right now; "
            f"new experiments will use all {available} until more videos are added."
        )

    return ok({
        "total_trials": payload.total_trials,
        "available_media_count": available,
        "warning": warning,
    })

# ---------------------------------------------------------------------------
# Video upload / deactivate / activate / delete (admin panel feature).
# Paste these 4 endpoints into your existing admin.py. Make sure these
# (add whatever's missing to your existing import lines -- `os` is almost
# certainly already imported since export_csv/cleanup use it)
# ---------------------------------------------------------------------------

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB -- adjust to taste

# Same directory phase1.py's self-recordings live under (backend/app/media),
# just the top level rather than the recordings/ subfolder.
MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


@router.post("/media/upload")
async def upload_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    """Add a new predefined video to the pool. It becomes eligible for
    random assignment to NEW experiments immediately (existing
    experiments already in progress are unaffected, per SRS 5)."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return fail(
            f"Unsupported file type '{ext or '(none)'}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}",
            "INVALID_FILE_TYPE", 422,
        )

    # Never trust the client's filename directly (path traversal defense),
    # and prefix with a short random id so a same-named upload can never
    # silently overwrite an existing video file on disk.
    safe_name = sanitize_filename(file.filename)
    stored_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    dest_path = os.path.join(MEDIA_DIR, stored_filename)

    total_bytes = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    out.close()
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return fail("File too large (limit 200 MB).", "FILE_TOO_LARGE", 413)
                out.write(chunk)
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise

    media = models.Media(
        filename=stored_filename,
        media_path=f"/media/{stored_filename}",
        is_active=True,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return ok({
        "media_id": media.media_id,
        "filename": media.filename,
        "media_path": media.media_path,
        "is_active": media.is_active,
    }, status_code=201)


@router.post("/media/{media_id}/deactivate")
def deactivate_media(media_id: int, db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    """Soft delete: excludes this video from future experiments' random
    pool (see seed.get_predefined_media), but keeps the file and DB row
    intact -- past experiments that already reference it via
    ExperimentMedia / ExperimentTrial keep working exactly as before."""
    media = db.query(models.Media).get(media_id)
    if not media:
        return fail("Media not found.", "NOT_FOUND", 404)
    if media.filename == seed.DEMO_VIDEO[0]:
        return fail("The demo video can't be deactivated.", "PROTECTED_MEDIA", 400)

    media.is_active = False
    db.commit()
    return ok({"media_id": media.media_id, "is_active": media.is_active})


@router.post("/media/{media_id}/activate")
def activate_media(media_id: int, db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    """Undo a deactivation -- makes the video eligible for random
    assignment to new experiments again."""
    media = db.query(models.Media).get(media_id)
    if not media:
        return fail("Media not found.", "NOT_FOUND", 404)

    media.is_active = True
    db.commit()
    return ok({"media_id": media.media_id, "is_active": media.is_active})


@router.delete("/media/{media_id}")
def delete_media(media_id: int, db: Session = Depends(get_db), _admin: None = Depends(require_admin)):
    """Permanently delete -- ONLY allowed if this video was never actually
    used by any experiment (no ExperimentMedia / ExperimentTrial rows
    reference it). Use /deactivate instead for a video that's already in
    use, to avoid orphaning historical trial data or breaking an
    in-progress experiment's playback."""
    media = db.query(models.Media).get(media_id)
    if not media:
        return fail("Media not found.", "NOT_FOUND", 404)
    if media.filename == seed.DEMO_VIDEO[0]:
        return fail("The demo video can't be deleted.", "PROTECTED_MEDIA", 400)

    in_use = (
        db.query(models.ExperimentMedia).filter(models.ExperimentMedia.media_id == media_id).first()
        or db.query(models.ExperimentTrial).filter(models.ExperimentTrial.media_id == media_id).first()
    )
    if in_use:
        return fail(
            "This video has already been used by at least one experiment and can't be permanently "
            "deleted (it would orphan historical trial data). Use Deactivate instead to hide it from "
            "future experiments while keeping past data intact.",
            "MEDIA_IN_USE", 409,
        )

    if media.media_path:
        file_path = os.path.join(MEDIA_DIR, os.path.basename(media.media_path))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    db.delete(media)
    db.commit()
    return ok({"deleted": True, "media_id": media_id})