import asyncio
import logging

from .cleanup import perform_cleanup
from .database import SessionLocal

logger = logging.getLogger("adapt.scheduler")

CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours


async def run_cleanup_loop():
    """Runs perform_cleanup() once immediately, then every 24 hours,
    forever. Never raises -- a failed run is logged and the loop just
    waits for the next interval rather than killing the whole background
    task."""
    while True:
        db = SessionLocal()
        try:
            result = perform_cleanup(db)
            logger.info(
                "Automatic cleanup: expired %d experiment(s), deleted %d "
                "empty terms-agreement-only experiment(s).",
                result["expired_count"], result["deleted_count"],
            )
        except Exception:
            logger.exception("Automatic cleanup run failed.")
        finally:
            db.close()

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)