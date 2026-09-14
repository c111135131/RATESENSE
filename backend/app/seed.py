"""Seed the Media table by scanning backend/app/media/ for video files.

Per SRS section 5 (Experiment Design):
scans backend/app/media/ for video files and creates one Media row
per file found, using the actual filename -- so adding/renaming/removing
files in that folder before first launch is all you need to do; nothing
in this file needs to change.

"""
import os

from sqlalchemy.orm import Session
from . import models

DEMO_VIDEO = ("demo_video.mp4", "/media/demo_video.mp4")

# Same directory backend/app/main.py mounts as /media, and the same
# extension whitelist backend/app/routers/admin.py's upload endpoint uses.
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}


def _scan_media_dir_for_videos(media_dir: str):
    """Returns a sorted list of (filename, media_path) tuples for every
    video file directly inside `media_dir` -- excludes subdirectories
    (e.g. media/recordings/, which holds self-recorded videos, not
    predefined experiment videos) and the demo video (seeded separately,
    always first)."""
    if not os.path.isdir(media_dir):
        return []

    found = []
    for entry in sorted(os.listdir(media_dir)):
        full_path = os.path.join(media_dir, entry)
        if not os.path.isfile(full_path):
            continue  # skip subdirectories like recordings/
        if entry == DEMO_VIDEO[0]:
            continue  # demo video is seeded separately, always first
        ext = os.path.splitext(entry)[1].lower()
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            continue  # skip .DS_Store, .gitkeep, etc.
        found.append((entry, f"/media/{entry}"))
    return found


def seed_media(db: Session):
    if db.query(models.Media).count() > 0:
        return

    # Demo video first, always -- gives it the lowest media_id so it
    # naturally sorts first even without relying on frontend sorting.
    db.add(models.Media(filename=DEMO_VIDEO[0], media_path=DEMO_VIDEO[1], is_active=True))

    for filename, path in _scan_media_dir_for_videos(MEDIA_DIR):
        db.add(models.Media(filename=filename, media_path=path, is_active=True))

    db.commit()


def get_demo_media(db: Session) -> models.Media:
    return db.query(models.Media).filter(models.Media.filename == DEMO_VIDEO[0]).first()


def get_predefined_media(db: Session):
    """The pool of videos eligible for random assignment to NEW
    experiments: every Media row EXCEPT the demo video, that hasn't been
    deactivated by an admin. This also naturally includes any video an
    admin uploads later via POST /admin/media/upload -- there's no fixed
    filename list to keep in sync."""
    return (
        db.query(models.Media)
        .filter(models.Media.filename != DEMO_VIDEO[0])
        .filter(models.Media.is_active.is_(True))
        .all()
    )