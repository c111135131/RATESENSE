"""Deterministic per-trial parameter generation for Phase 2/3/4.

SRS spec (Phase 2 Noise):
    seed = hash(experimentID + phase + trialIndex)
    noise = Random(seed)
"""
import hashlib
import random

from . import params


def trial_seed(experiment_id: str, phase: int, trial_key) -> int:
    raw = f"{experiment_id}:{phase}:{trial_key}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:16], 16)


def _rng(experiment_id: str, phase: int, trial_key) -> random.Random:
    return random.Random(trial_seed(experiment_id, phase, trial_key))


def trial_noise(experiment_id: str, phase: int, trial_key) -> float:
    """Phase 2: additive noise for `speed = mouse_position*2 + noise`."""
    low, high = params.PHASE2_NOISE_RANGE
    return round(_rng(experiment_id, phase, trial_key).uniform(low, high), 4)


def trial_actual_speed(experiment_id: str, phase: int, trial_key) -> float:
    """Phase 3: the system-controlled actual playback speed for this trial."""
    return _rng(experiment_id, phase, trial_key).uniform(params.PHASE3_ACTUAL_SPEED_RANGE["low"], params.PHASE3_ACTUAL_SPEED_RANGE["high"])


def trial_direction(experiment_id: str, phase: int, trial_key) -> int:
    """Phase 4: acceleration (+1) or deceleration (-1) direction."""
    return 1 if _rng(experiment_id, phase, trial_key).random() < 0.5 else -1
