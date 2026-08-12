"""Single source of truth for "current time" across the backend.

All timestamps (Experiment.created_at/updated_at/expired_at,
SelfRecording.upload_time, ExperimentTrial.created_at, and every
expiration/cleanup comparison) must use the SAME clock, or "expired"
checks and stored timestamps could silently drift out of sync with each
other. Every file that needs "now" should import and call now_toronto()
from here rather than calling datetime.utcnow()/datetime.now() directly.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

TORONTO_TZ = ZoneInfo("America/Toronto")


def now_toronto() -> datetime:
    """Current wall-clock time in Toronto (America/Toronto), correctly
    handling EST/EDT daylight-saving transitions.

    Returned as a NAIVE datetime (tzinfo stripped) rather than an
    aware one: SQLite has no native timezone type, and mixing naive and
    aware datetimes in comparisons (e.g. `expired_at < now_toronto()`)
    raises a TypeError. Every value produced by this function represents
    Toronto local time -- as long as nothing in this codebase calls
    datetime.utcnow() or datetime.now() directly, all stored/compared
    timestamps stay consistent.
    """
    return datetime.now(TORONTO_TZ).replace(tzinfo=None)
