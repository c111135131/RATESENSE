from datetime import datetime
from zoneinfo import ZoneInfo

TORONTO_TZ = ZoneInfo("America/Toronto")


def now_toronto() -> datetime:
    return datetime.now(TORONTO_TZ).replace(tzinfo=None)
