from itertools import groupby
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.database import SessionDep
from src.memories import service
from src.memories.models import ACTIVE
from src.memories.schemas import MemoryGroup, MemoryOut

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    session: SessionDep,
    status: str | None = Query(ACTIVE, description="active | dismissed | null for all"),
) -> list[MemoryOut]:
    rows = await service.list_memories(session, status=status)
    return [MemoryOut.model_validate(r) for r in rows]


@router.get("/grouped", response_model=list[MemoryGroup])
async def list_grouped(session: SessionDep) -> list[MemoryGroup]:
    """Bucketed by kind — how the Memory panel renders. `list_memories`
    already orders by kind, so a plain groupby is enough."""
    rows = await service.list_memories(session)
    return [
        MemoryGroup(kind=kind, items=[MemoryOut.model_validate(r) for r in items])
        for kind, items in groupby(rows, key=lambda r: r.kind)
    ]


@router.delete("/{memory_id}", status_code=204)
async def dismiss_memory(memory_id: UUID, session: SessionDep) -> None:
    """Soft-delete: the tutor stops using the fact, and a later extraction pass
    will not re-add it."""
    await service.dismiss_memory(session, memory_id)
