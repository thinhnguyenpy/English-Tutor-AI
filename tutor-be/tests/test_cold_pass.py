"""When the cold path runs its steps — not what the agents say.

The agent-backed steps are replaced with recorders, so these pin down the
scheduling: which turn triggers a title, which triggers summary + memory, and
that memory for the tail of a short conversation is not lost.
"""

from contextlib import asynccontextmanager

import pytest

from src.conversations import cold, service
from src.conversations.schemas import ConversationCreate
from src.core.config import Settings


@pytest.fixture
def steps(session, monkeypatch) -> list[str]:
    ran: list[str] = []

    def recorder(label):
        async def step(*_args):
            ran.append(label)

        return step

    @asynccontextmanager
    async def same_session():
        yield session

    monkeypatch.setattr(Settings, "azure_configured", property(lambda _: True))
    monkeypatch.setattr(cold, "SessionLocal", same_session)
    for label in ("feedback", "title", "summary", "memory"):
        monkeypatch.setattr(cold, f"_{label}_pass", recorder(label))
    return ran


async def _conversation(session, turn_count: int, memory_pass_turn: int = 0):
    conv = await service.create_conversation(session, ConversationCreate())
    conv.turn_count, conv.memory_pass_turn = turn_count, memory_pass_turn
    await session.commit()
    return conv


async def _pass(conv, turn_number: int, final: bool = False) -> None:
    await cold._run_cold_pass(
        sender=None,
        conversation_id=conv.id,
        user_message_id=None,
        user_text="hi",
        turn_number=turn_number,
        final=final,
    )


async def test_uses_the_captured_turn_even_after_the_student_spoke_again(session, steps):
    conv = await _conversation(session, turn_count=7)  # turn 7 landed during turn 6's pass

    await _pass(conv, turn_number=6)

    assert steps == ["feedback", "summary", "memory"]
    assert conv.memory_pass_turn == 6


async def test_first_turn_gets_a_title_even_if_turn_two_already_landed(session, steps):
    conv = await _conversation(session, turn_count=2)

    await _pass(conv, turn_number=1)

    assert steps == ["feedback", "title"]


async def test_the_capped_last_turn_mines_the_tail(session, steps):
    conv = await _conversation(session, turn_count=29, memory_pass_turn=24)

    await _pass(conv, turn_number=29, final=True)

    assert steps == ["feedback", "summary", "memory"]
    assert conv.memory_pass_turn == 29


async def test_disconnect_remembers_a_conversation_shorter_than_one_cycle(session, steps):
    conv = await _conversation(session, turn_count=4)

    await cold._run_final_pass(conv.id)
    await cold._run_final_pass(conv.id)

    assert steps == ["summary", "memory"], "second disconnect has nothing new"
    assert conv.memory_pass_turn == 4


async def test_failed_memory_pass_leaves_the_tail_for_next_time(session, steps, monkeypatch):
    async def boom(*_args):
        raise RuntimeError("model down")

    monkeypatch.setattr(cold, "_memory_pass", boom)
    conv = await _conversation(session, turn_count=4)

    await cold._run_final_pass(conv.id)

    assert conv.memory_pass_turn == 0
