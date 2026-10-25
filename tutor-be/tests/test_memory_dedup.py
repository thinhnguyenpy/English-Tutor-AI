"""Folding an extraction pass into the memories table.

The agent is mocked out — what is under test is the write logic, which is
where a bad decision becomes a permanently wrong fact the tutor keeps
repeating.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.memories import service
from src.memories.models import ACTIVE, DISMISSED, Memory


@dataclass
class FakeExtraction:
    """Mirrors src.agents.memory_agent.ExtractedMemory without importing it,
    so these tests need no Azure client."""

    action: str
    kind: str = "profile"
    content: str = ""
    confidence: float = 0.9
    memory_id: UUID | None = None


async def _add(session, **kwargs) -> Memory:
    memory = Memory(
        kind=kwargs.get("kind", "profile"),
        content=kwargs["content"],
        status=kwargs.get("status", ACTIVE),
        confidence=kwargs.get("confidence", 0.9),
    )
    session.add(memory)
    await session.commit()
    await session.refresh(memory)
    return memory


async def test_add_creates_a_row(session):
    changed = await service.apply_extraction(
        session, [FakeExtraction(action="add", kind="goal", content="Wants IELTS 7.0")]
    )
    rows = await service.list_memories(session)

    assert changed == 1
    assert [(r.kind, r.content) for r in rows] == [("goal", "Wants IELTS 7.0")]


async def test_skip_writes_nothing(session):
    await _add(session, content="Works in Da Nang")
    changed = await service.apply_extraction(
        session, [FakeExtraction(action="skip", content="Works in Da Nang")]
    )

    assert changed == 0
    assert len(await service.list_memories(session)) == 1


async def test_update_replaces_content_in_place(session):
    existing = await _add(session, content="Works in Hanoi")

    changed = await service.apply_extraction(
        session,
        [FakeExtraction(action="update", memory_id=existing.id, content="Works in Da Nang")],
    )
    rows = await service.list_memories(session)

    assert changed == 1
    assert len(rows) == 1, "update must not leave the stale row behind"
    assert rows[0].content == "Works in Da Nang"
    assert rows[0].id == existing.id


async def test_dismissed_memories_are_not_resurrected(session):
    """The student deleted this fact. An extraction pass that sees it mentioned
    again must not quietly bring it back."""
    dismissed = await _add(session, content="Has a cat", status=DISMISSED)

    changed = await service.apply_extraction(
        session,
        [FakeExtraction(action="update", memory_id=dismissed.id, content="Has a cat named Mimi")],
    )

    await session.refresh(dismissed)
    assert changed == 0
    assert dismissed.status == DISMISSED
    assert dismissed.content == "Has a cat"
    assert await service.list_memories(session, status=ACTIVE) == []


async def test_update_of_missing_row_falls_back_to_add(session):
    """A hallucinated id must not silently drop the fact on the floor."""
    changed = await service.apply_extraction(
        session,
        [FakeExtraction(action="update", memory_id=uuid4(), content="Studies at night")],
    )
    rows = await service.list_memories(session)

    assert changed == 1
    assert rows[0].content == "Studies at night"


async def test_unknown_kind_is_rejected(session):
    """`kind` drives how facts are grouped and rendered; an unknown value would
    show up as a phantom category in the Memory panel."""
    changed = await service.apply_extraction(
        session, [FakeExtraction(action="add", kind="astrology", content="Is a Leo")]
    )

    assert changed == 0
    assert await service.list_memories(session) == []


async def test_dismiss_hides_the_row_but_keeps_it(session):
    memory = await _add(session, content="Lives with parents")

    await service.dismiss_memory(session, memory.id)

    assert await service.list_memories(session, status=ACTIVE) == []
    kept = await service.list_memories(session, status=DISMISSED)
    assert [r.content for r in kept] == ["Lives with parents"]
