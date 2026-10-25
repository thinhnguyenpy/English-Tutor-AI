"""Persistence for the durable facts the tutor remembers about the student."""

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_model import time_now
from src.core.exceptions import MemoryNotFound
from src.memories.models import ACTIVE, DISMISSED, MEMORY_KINDS, Memory


async def list_memories(session: AsyncSession, *, status: str | None = ACTIVE) -> list[Memory]:
    stmt = select(Memory)
    if status is not None:
        stmt = stmt.where(Memory.status == status)
    stmt = stmt.order_by(Memory.kind.asc(), Memory.last_seen_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def dismiss_memory(session: AsyncSession, memory_id: UUID) -> None:
    """Soft-delete. The row is kept so a future extraction pass can be told the
    student already rejected this fact, instead of cheerfully re-adding it."""
    memory = await session.get(Memory, memory_id)
    if memory is None:
        raise MemoryNotFound()
    memory.status = DISMISSED
    await session.commit()


async def apply_extraction(
    session: AsyncSession,
    items: list["ExtractedMemoryLike"],
    *,
    conversation_id: UUID | None = None,
) -> int:
    """Fold one extraction pass into the table. Returns rows added or updated.

    `add` / `update` / `skip` come from the agent, which is given the existing
    memories of each kind so it can decide. That keeps deduplication in the one
    place that can actually judge whether "works at Panasonic" and "is a
    Panasonic employee" are the same fact — no embeddings needed at this scale.
    """
    changed = 0
    now = time_now()

    for item in items:
        if item.action == "skip":
            continue
        if item.kind not in MEMORY_KINDS:
            logger.warning("Extraction returned unknown memory kind {!r}, ignoring", item.kind)
            continue

        if item.action == "update" and item.memory_id is not None:
            memory = await session.get(Memory, item.memory_id)
            if memory is None:
                logger.warning(
                    "Extraction referenced missing memory {}, adding instead", item.memory_id
                )
            elif memory.status == DISMISSED:
                # The student deleted this. Do not resurrect it.
                logger.info("Skipping update to dismissed memory {}", memory.id)
                continue
            else:
                memory.content = item.content
                memory.confidence = item.confidence
                memory.last_seen_at = now
                changed += 1
                continue

        session.add(
            Memory(
                kind=item.kind,
                content=item.content,
                confidence=item.confidence,
                status=ACTIVE,
                source_conversation_id=conversation_id,
                last_seen_at=now,
            )
        )
        changed += 1

    if changed:
        await session.commit()
    return changed


class ExtractedMemoryLike:
    """Structural type for what `apply_extraction` consumes.

    The real object is `src.agents.memory_agent.ExtractedMemory`; declaring the
    shape here keeps this module free of an agent import (and therefore of the
    Azure client) so it stays unit-testable without a key.
    """

    action: str
    memory_id: UUID | None
    kind: str
    content: str
    confidence: float
