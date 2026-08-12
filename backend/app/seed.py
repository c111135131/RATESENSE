"""Seed the Media table with the 5 predefined experiment videos.

Per SRS section 5 (Experiment Design):
  Every experiment uses 5 predefined videos + 1 self-recorded video = 6 videos.
  Future version: randomly select five videos from the Media table
  (implementation already supports this -- see experiments.py `assign_media`).
"""
from sqlalchemy.orm import Session
from . import models

# (filename, path)
PREDEFINED_VIDEOS = [
    ("walk.mp4", "/media/walk.mp4"),
    ("water.mp4", "/media/water.mp4"),
    ("ball.mp4", "/media/ball.mp4"),
    ("office1.mp4", "/media/office1.mp4"),
    ("office2.mp4", "/media/office2.mp4"),
]

DEMO_VIDEO = ("demo_video.mp4", "/media/demo_video.mp4")


def seed_media(db: Session):
    if db.query(models.Media).count() > 0:
        return
    for filename, path in PREDEFINED_VIDEOS + [DEMO_VIDEO]:
        db.add(models.Media(filename=filename, media_path=path))
    db.commit()


def get_demo_media(db: Session) -> models.Media:
    return db.query(models.Media).filter(models.Media.filename == DEMO_VIDEO[0]).first()


def get_predefined_media(db: Session):
    filenames = [f for f, _ in PREDEFINED_VIDEOS]
    return (
        db.query(models.Media)
        .filter(models.Media.filename.in_(filenames))
        .all()
    )
