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
    return get_or_create_config(db).total_trials


def set_total_trials(db: Session, value: int) -> models.AppConfig:
    config = get_or_create_config(db)
    config.total_trials = value
    db.commit()
    db.refresh(config)
    return config