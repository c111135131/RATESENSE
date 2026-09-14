"""Global, admin-editable experiment settings.

Currently just one setting: how many predefined videos get randomly
assigned to each NEW experiment (Video Library feature). Stored as a
single-row table (id=1) rather than a per-experiment value, so changing it
in the admin panel affects every experiment created from that point on --
Phase 2/3/4 all share the same ExperimentMedia rows (SRS: "All experiment
phases only use these six videos"), so this one setting cascades to all
three phases automatically.
"""
from sqlalchemy.orm import Session

from . import models

DEFAULT_TOTAL_TRIALS = 5
CONFIG_ROW_ID = 1


def get_or_create_config(db: Session) -> models.AppConfig:
    row = db.query(models.AppConfig).get(CONFIG_ROW_ID)
    if not row:
        row = models.AppConfig(id=CONFIG_ROW_ID, total_trials=DEFAULT_TOTAL_TRIALS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_total_trials(db: Session) -> int:
    """How many predefined videos to randomly assign to a NEW experiment
    (the participant's own self-recording is always added on top of this,
    per SRS -- this setting only controls the predefined-video count)."""
    return get_or_create_config(db).total_trials


def set_total_trials(db: Session, value: int) -> models.AppConfig:
    config = get_or_create_config(db)
    config.total_trials = value
    db.commit()
    db.refresh(config)
    return config