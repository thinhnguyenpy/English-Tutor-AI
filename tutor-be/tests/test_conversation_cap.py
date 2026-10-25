"""The sidebar holds a fixed number of conversations; the rest are archived.

Archiving must never lose data — the student's history and the memories
extracted from it have to survive falling off the list.
"""

from datetime import timedelta

import pytest

from src.conversations import service
from src.conversations.models import ACTIVE, ARCHIVED, Conversation
from src.conversations.schemas import ConversationCreate
from src.core.base_model import time_now
from src.core.config import settings


async def _create(session, title: str) -> Conversation:
    return await service.create_conversation(session, ConversationCreate(title=title))


async def test_stays_under_cap(session):
    cap = settings.MAX_ACTIVE_CONVERSATIONS
    for i in range(cap + 4):
        await _create(session, f"conv-{i}")

    active = await service.list_conversations(session, status=ACTIVE)
    archived = await service.list_conversations(session, status=ARCHIVED)

    assert len(active) == cap
    assert len(archived) == 4


async def test_archives_least_recently_active_not_oldest_created(session):
    """A conversation resumed today must outrank one created later but idle."""
    cap = settings.MAX_ACTIVE_CONVERSATIONS
    for i in range(cap):
        await _create(session, f"conv-{i}")

    revived, forgotten = (await service.list_conversations(session))[0], None
    all_active = await service.list_conversations(session)
    forgotten = all_active[-1]

    # `revived` was created first in wall-clock terms but is being used now;
    # `forgotten` is newer but has sat idle for a month.
    revived.last_active_at = time_now()
    forgotten.last_active_at = time_now() - timedelta(days=30)
    await session.commit()

    await _create(session, "the-new-one")

    active_ids = {c.id for c in await service.list_conversations(session, status=ACTIVE)}
    assert forgotten.id not in active_ids
    assert revived.id in active_ids


async def test_archived_conversation_keeps_its_messages(session):
    cap = settings.MAX_ACTIVE_CONVERSATIONS
    doomed = await _create(session, "doomed")
    await service.append_message(session, doomed.id, role="user", text="remember this")

    for i in range(cap):
        await _create(session, f"filler-{i}")

    await session.refresh(doomed)
    assert doomed.status == ARCHIVED

    messages = await service.list_messages(session, doomed.id)
    assert [m.text for m in messages] == ["remember this"]


@pytest.mark.parametrize("count", [1, 5])
async def test_under_cap_archives_nothing(session, count):
    for i in range(count):
        await _create(session, f"conv-{i}")
    assert len(await service.list_conversations(session, status=ARCHIVED)) == 0


async def test_persona_is_stored_per_conversation(session):
    from src.conversations.schemas import ConversationUpdate

    grammar = await service.create_conversation(
        session, ConversationCreate(persona="grammar_tutor")
    )
    default = await service.create_conversation(session, ConversationCreate())
    assert (grammar.persona, default.persona) == ("grammar_tutor", "conversation_partner")

    updated = await service.update_conversation(
        session, default.id, ConversationUpdate(persona="fluency_coach")
    )
    assert updated.persona == "fluency_coach"


def test_unknown_persona_is_rejected_not_silently_defaulted():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ConversationCreate(persona="pirate")
