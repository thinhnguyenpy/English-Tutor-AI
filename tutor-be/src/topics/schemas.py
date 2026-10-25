from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    level: str
    sort_order: int
    # prompt_seed is deliberately not exposed: it is tutor-facing instruction
    # text, and showing it would tell the student what the tutor is about to do.
