"""Seed the preset conversation topics from data/topics.json.

Idempotent, and matches how smartdocs-be seeds policy knowledge: insert rows
that are missing, leave existing ones alone. Editing a topic in the DB is never
overwritten on the next boot.
"""

import json

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import BASE_DIR
from src.topics.models import Topic

TOPICS_PATH = BASE_DIR / "data" / "topics.json"


async def seed_topics(session: AsyncSession) -> int:
    if not TOPICS_PATH.exists():
        logger.warning("No topics file at {} — skipping topic seed", TOPICS_PATH)
        return 0

    payload = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    existing = set((await session.execute(select(Topic.slug))).scalars().all())

    added = 0
    for entry in payload:
        if entry["slug"] in existing:
            continue
        session.add(
            Topic(
                slug=entry["slug"],
                title=entry["title"],
                level=entry.get("level", "intermediate"),
                prompt_seed=entry["prompt_seed"],
                sort_order=entry.get("sort_order", 0),
            )
        )
        added += 1

    if added:
        await session.commit()
        logger.info("Seeded {} topic(s)", added)
    return added
