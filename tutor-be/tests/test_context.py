"""The prompt the tutor sees.

This is where "the tutor remembers me" is actually implemented: if the memory
block is missing, malformed, or leaks dismissed facts, the whole feature is
silently gone while the app still looks like it works.
"""

from src.conversations import service as conversation_service
from src.conversations.models import ROLE_ASSISTANT, ROLE_USER
from src.conversations.schemas import ConversationCreate
from src.core.config import settings
from src.memories.context import MEMORY_HEADER, SUMMARY_HEADER, build_context, recent_turns
from src.memories.models import ACTIVE, DISMISSED, Memory


async def _conversation(session, **kwargs):
    return await conversation_service.create_conversation(session, ConversationCreate(**kwargs))


def _memory(**kwargs) -> Memory:
    return Memory(
        kind=kwargs.get("kind", "profile"),
        content=kwargs["content"],
        status=kwargs.get("status", ACTIVE),
        confidence=kwargs.get("confidence", 0.9),
    )


async def test_active_memories_reach_the_prompt(session):
    conv = await _conversation(session)
    session.add(_memory(kind="profile", content="Works as a backend developer in Da Nang"))
    session.add(_memory(kind="event", content="Has an IELTS speaking test on 2026-09-14"))
    await session.commit()

    prompt = await build_context(session, conv)

    assert MEMORY_HEADER in prompt
    assert "- (profile) Works as a backend developer in Da Nang" in prompt
    assert "- (event) Has an IELTS speaking test on 2026-09-14" in prompt


async def test_dismissed_memories_never_reach_the_prompt(session):
    """Deleting a wrong fact in the UI has to actually stop the tutor using it."""
    conv = await _conversation(session)
    session.add(_memory(content="Lives in Hanoi", status=DISMISSED))
    session.add(_memory(content="Lives in Da Nang", status=ACTIVE))
    await session.commit()

    prompt = await build_context(session, conv)

    assert "Lives in Da Nang" in prompt
    assert "Hanoi" not in prompt


async def test_no_memory_header_when_nothing_remembered(session):
    """A first-run student should not be shown an empty "what you know" block —
    the model treats a header with nothing under it as a fact in itself."""
    conv = await _conversation(session)
    prompt = await build_context(session, conv)
    assert MEMORY_HEADER not in prompt


async def test_summary_included_only_when_present(session):
    conv = await _conversation(session)
    assert SUMMARY_HEADER not in await build_context(session, conv)

    conv.summary = "The student talked about their trip to Hoi An."
    await session.commit()

    prompt = await build_context(session, conv)
    assert SUMMARY_HEADER in prompt
    assert "Hoi An" in prompt


async def test_topic_seed_is_injected(session):
    conv = await _conversation(session)
    prompt = await build_context(session, conv, topic_seed="Ask about their commute.")
    assert "Ask about their commute." in prompt


async def test_persona_selects_the_right_prompt(session):
    conv = await _conversation(session)
    grammar = await build_context(session, conv, persona="grammar_tutor")
    fluency = await build_context(session, conv, persona="fluency_coach")

    assert "grammar tutor" in grammar.lower()
    assert "fluency coach" in fluency.lower()


async def test_unknown_persona_falls_back_rather_than_crashing(session):
    conv = await _conversation(session)
    prompt = await build_context(session, conv, persona="not_a_persona")
    assert "conversation partner" in prompt.lower()


async def test_recent_turns_are_chronological_and_capped(session):
    """The tail feeds message_history, so wrong order means the model sees the
    conversation running backwards."""
    conv = await _conversation(session)
    total = settings.RECENT_TURNS_IN_CONTEXT + 6
    for i in range(total):
        role = ROLE_USER if i % 2 == 0 else ROLE_ASSISTANT
        await conversation_service.append_message(session, conv.id, role=role, text=f"turn-{i}")

    tail = await recent_turns(session, conv)

    assert len(tail) == settings.RECENT_TURNS_IN_CONTEXT
    assert tail[0].text == f"turn-{total - settings.RECENT_TURNS_IN_CONTEXT}"
    assert tail[-1].text == f"turn-{total - 1}"
