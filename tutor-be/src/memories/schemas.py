from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    content: str
    status: str
    confidence: float
    created_at: datetime
    last_seen_at: datetime


class MemoryGroup(BaseModel):
    """Memories bucketed by kind, which is how the Memory panel renders them."""

    kind: str
    items: list[MemoryOut]
