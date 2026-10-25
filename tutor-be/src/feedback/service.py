"""Persistence for per-turn review notes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.conversations.models import Message
from src.feedback.models import FEEDBACK_TYPES, TurnFeedback


async def save_feedback(session: AsyncSession, message_id: UUID, items: list) -> list[TurnFeedback]:
    rows = [
        TurnFeedback(
            message_id=message_id,
            type=item.type,
            original=item.original,
            corrected=item.corrected,
            explanation=item.explanation,
            severity=item.severity,
        )
        for item in items
        if item.type in FEEDBACK_TYPES
    ]
    if not rows:
        return []
    session.add_all(rows)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return rows


async def list_for_conversation(session: AsyncSession, conversation_id: UUID) -> list[TurnFeedback]:
    """Notes for one conversation, oldest first — the order they were said."""
    stmt = (
        select(TurnFeedback)
        .join(Message, Message.id == TurnFeedback.message_id)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), TurnFeedback.created_at.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_recent(session: AsyncSession, *, limit: int = 100) -> list[TurnFeedback]:
    stmt = select(TurnFeedback).order_by(TurnFeedback.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
