"""Top-level seed orchestrator, run on every boot from pre_start.

Every seeder must be idempotent — this runs unconditionally at startup.
"""

from loguru import logger

from src.core.database import SessionLocal
from src.topics.seed import seed_topics


async def seed_all() -> None:
    async with SessionLocal() as session:
        try:
            await seed_topics(session)
        except Exception as exc:  # noqa: BLE001 — a failed seed must not block boot
            logger.opt(exception=True).warning("Topic seed failed: {}", exc)
