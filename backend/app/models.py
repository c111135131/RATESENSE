"""SQLAlchemy ORM models, matching SRS section 10 (Database Design)."""
import enum
import uuid
from datetime import timedelta

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Enum
)
from sqlalchemy.orm import relationship

from .database import Base
from .timeutils import now_toronto

EXPIRATION_HOURS = 24


class ExperimentStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    EXPIRED = "EXPIRED"


def new_experiment_id() -> str:
    return f"EXP_{uuid.uuid4().hex[:8].upper()}"


class Media(Base):
    """Stores experiment videos."""
    __tablename__ = "media"

    media_id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    media_path = Column(String, nullable=False)

    phase3_actual_speed_override = Column(Float, nullable=True)
    phase4_direction_override = Column(Integer, nullable=True)
    phase4_delay_ms_override = Column(Integer, nullable=True)
    phase4_tick_ms_override = Column(Integer, nullable=True)


class Experiment(Base):
    """Stores one experiment (one participant session)."""
    __tablename__ = "experiments"

    experiment_id = Column(String, primary_key=True, default=new_experiment_id)
    created_at = Column(DateTime, default=now_toronto)
    updated_at = Column(DateTime, default=now_toronto, onupdate=now_toronto)
    current_state = Column(String, default="home", nullable=False)
    current_phase = Column(Integer, default=0)
    current_trial = Column(Integer, default=0)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.IN_PROGRESS)
    expired_at = Column(DateTime, nullable=True)

    self_recordings = relationship("SelfRecording", back_populates="experiment")
    experiment_media = relationship("ExperimentMedia", back_populates="experiment")
    trials = relationship("ExperimentTrial", back_populates="experiment")

    def touch_expiration(self):
        self.expired_at = now_toronto() + timedelta(hours=EXPIRATION_HOURS)


class SelfRecording(Base):
    """Stores uploaded participant self-recorded video (Phase 1)."""
    __tablename__ = "self_recordings"

    recording_id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    video_path = Column(String, nullable=False)
    deleted = Column(Boolean, default=False)
    upload_time = Column(DateTime, default=now_toronto)

    phase3_actual_speed_override = Column(Float, nullable=True)
    phase4_direction_override = Column(Integer, nullable=True)
    phase4_delay_ms_override = Column(Integer, nullable=True)
    phase4_tick_ms_override = Column(Integer, nullable=True)

    experiment = relationship("Experiment", back_populates="self_recordings")


class ExperimentMedia(Base):
    """Stores which videos belong to one experiment, and their order."""
    __tablename__ = "experiment_media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    display_order = Column(Integer, nullable=False)
    media_id = Column(Integer, ForeignKey("media.media_id"))

    experiment = relationship("Experiment", back_populates="experiment_media")
    media = relationship("Media")


class ExperimentTrial(Base):
    """Stores every real (non-demo) trial. Unused fields per-phase stay NULL."""
    __tablename__ = "experiment_trials"

    trial_id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(String, ForeignKey("experiments.experiment_id"))
    phase = Column(Integer, nullable=False)
    trial_index = Column(Integer, nullable=False)
    media_id = Column(Integer, ForeignKey("media.media_id"))

    # Phase 2 (Direct Resolution)
    selected_speed = Column(Float, nullable=True)
    # Phase 3 (Speed Estimation)
    actual_speed = Column(Float, nullable=True)
    estimated_speed = Column(Float, nullable=True)
    # Phase 2 & 3 shared
    hesitation_ms = Column(Integer, nullable=True)
    # Phase 4 (Threshold and Tolerance)
    delay_ms = Column(Integer, nullable=True)
    direction = Column(Integer, nullable=True)
    threshold_speed = Column(Float, nullable=True)
    tolerance_speed = Column(Float, nullable=True)

    created_at = Column(DateTime, default=now_toronto)

    experiment = relationship("Experiment", back_populates="trials")
    media = relationship("Media")
