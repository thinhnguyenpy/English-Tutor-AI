"""Persistence for conversations and their messages."""

from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.conversations.models import ACTIVE, ARCHIVED, Conversation, Message
from src.conversations.schemas import ConversationCreate, ConversationUpdate
from src.core.base_model import time_now
from src.core.config import settings
from src.core.exceptions import ConversationNotFound


async def list_conversations(session: AsyncSession, *, status: str = ACTIVE) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.status == status)
        .order_by(Conversation.last_active_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_conversation(session: AsyncSession, conversation_id: UUID) -> Conversation:
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        raise ConversationNotFound()
    return conv


async def create_conversation(session: AsyncSession, data: ConversationCreate) -> Conversation:
    await _enforce_active_cap(session)
    conv = Conversation(
        title=data.title or "New conversation",
        topic_slug=data.topic_slug,
        status=ACTIVE,
        last_active_at=time_now(),
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def _enforce_active_cap(session: AsyncSession) -> None:
    """Keep at most MAX_ACTIVE_CONVERSATIONS in the sidebar by archiving the
    least-recently-active ones. Archiving, never deleting — the student's
    history and the memories extracted from it stay intact.
    """
    cap = settings.MAX_ACTIVE_CONVERSATIONS
    count = (
        await session.execute(
            select(func.count()).select_from(Conversation).where(Conversation.status == ACTIVE)
        )
    ).scalar_one()

    # Archive enough that this conversation plus the survivors still fit.
    overflow = count - cap + 1
    if overflow <= 0:
        return

    stale = (
        (
            await session.execute(
                select(Conversation)
                .where(Conversation.status == ACTIVE)
                .order_by(Conversation.last_active_at.asc())
                .limit(overflow)
            )
        )
        .scalars()
        .all()
    )

    for conv in stale:
        conv.status = ARCHIVED
        logger.info("Archived conversation {} ({}) to stay under the cap", conv.id, conv.title)
    await session.flush()


async def update_conversation(
    session: AsyncSession, conversation_id: UUID, data: ConversationUpdate
) -> Conversation:
    conv = await get_conversation(session, conversation_id)
    if data.title is not None:
        conv.title = data.title
    if data.status is not None:
        conv.status = data.status
    await session.commit()
    await session.refresh(conv)
    return conv


async def delete_conversation(session: AsyncSession, conversation_id: UUID) -> None:
    conv = await get_conversation(session, conversation_id)
    await session.delete(conv)
    await session.commit()


async def list_messages(
    session: AsyncSession, conversation_id: UUID, *, limit: int | None = None
) -> list[Message]:
    """Oldest first — the order they are rendered and replayed into the prompt.

    `limit` keeps the *newest* N, then flips them back to chronological order,
    which is what the prompt's verbatim tail needs.
    """
    if limit is None:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list((await session.execute(stmt)).scalars().all())

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    rows.reverse()
    return rows


async def append_message(
    session: AsyncSession,
    conversation_id: UUID,
    *,
    role: str,
    text: str,
    bump_turn: bool = False,
) -> Message:
    message = Message(conversation_id=conversation_id, role=role, text=text)
    session.add(message)

    conv = await get_conversation(session, conversation_id)
    conv.last_active_at = time_now()
    if bump_turn:
        conv.turn_count += 1

    await session.commit()
    await session.refresh(message)
    return message
