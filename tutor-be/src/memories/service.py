"""Persistence for the durable facts the tutor remembers about the student."""

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_model import time_now
from src.core.exceptions import MemoryNotFound
from src.memories.models import ACTIVE, DISMISSED, KIND_PROFILE, MEMORY_KINDS, Memory


async def list_memories(session: AsyncSession, *, status: str | None = ACTIVE) -> list[Memory]:
    stmt = select(Memory)
    if status is not None:
        stmt = stmt.where(Memory.status == status)
    stmt = stmt.order_by(Memory.kind.asc(), Memory.last_seen_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def list_for_context(session: AsyncSession, *, limit: int) -> list[Memory]:
    """The facts the tutor carries into a turn, at most `limit`.

    Profile facts (job, city, family) are kept first: they are few, stable and
    rarely re-mentioned, so ranking them by recency would drop exactly the
    things a tutor most needs to remember. The rest compete on `last_seen_at`.
    Returned in `list_memories` order (kind, then most recent) for rendering.
    """

    def ranked_ids(kind_filter, n: int):
        # Ranked in SQL: SQLite hands back naive datetimes while rows created
        # in this session hold aware ones, so sorting in Python can raise.
        return (
            select(Memory.id)
            .where(Memory.status == ACTIVE, kind_filter)
            .order_by(Memory.last_seen_at.desc())
            .limit(n)
        )

    profile_ids = list(await session.scalars(ranked_ids(Memory.kind == KIND_PROFILE, limit)))
    other_ids = list(
        await session.scalars(ranked_ids(Memory.kind != KIND_PROFILE, limit - len(profile_ids)))
    )
    chosen = set(profile_ids + other_ids)
    return [m for m in await list_memories(session) if m.id in chosen]


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
