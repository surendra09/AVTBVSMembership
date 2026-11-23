"""Background worker for email/SMS delivery and edit-permission expiry.

Runs in-process (started by the FastAPI lifespan when NOTIFICATION_WORKER_ENABLED=true)
or as a dedicated process:  python -m app.workers.notifications
"""
import asyncio
import logging
import time

from app.core.config import settings
from app.database.session import SessionLocal
from app.services.notifications import process_expired_edit_permissions, process_outbox

logger = logging.getLogger("avtbvs.worker")


def run_once() -> dict:
    stats = process_outbox(SessionLocal)
    stats["expired_permissions"] = process_expired_edit_permissions(SessionLocal)
    return stats


async def worker_loop(stop: asyncio.Event) -> None:
    logger.info("Notification worker started (interval %ss)", settings.NOTIFICATION_WORKER_INTERVAL_SECONDS)
    while not stop.is_set():
        try:
            await asyncio.to_thread(run_once)
        except Exception:  # noqa: BLE001 – keep the loop alive; errors are logged
            logger.exception("Notification worker iteration failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.NOTIFICATION_WORKER_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger.info("Standalone notification worker running")
    while True:
        try:
            stats = run_once()
            if any(stats.values()):
                logger.info("Processed: %s", stats)
        except Exception:  # noqa: BLE001
            logger.exception("Worker iteration failed")
        time.sleep(settings.NOTIFICATION_WORKER_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
