from typing import Optional
from pydantic import BaseModel


class DemoCompleteRequest(BaseModel):
    experiment_id: str
    phase: int


class TrialSubmitRequest(BaseModel):
    experiment_id: str
    phase: int
    trial_index: int
    media_id: Optional[int] = None
    selected_speed: Optional[float] = None
    actual_speed: Optional[float] = None
    estimated_speed: Optional[float] = None
    hesitation_time_ms: Optional[int] = None
    delay_ms: Optional[int] = None
    direction: Optional[int] = None
    threshold_speed: Optional[float] = None
    tolerance_speed: Optional[float] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class MediaParamsOverride(BaseModel):
    phase3_actual_speed: Optional[float] = None
    phase4_direction: Optional[int] = None
    phase4_delay_ms: Optional[int] = None
    phase4_tick_ms: Optional[int] = None

class TesterInfo(BaseModel):
    experiment_id: str
    question_index: int
    field: str
    value: str
