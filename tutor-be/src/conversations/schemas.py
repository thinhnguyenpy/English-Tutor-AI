from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.agents.prompts.tutor_prompts import PERSONA_PROMPTS


def _known_persona(value: str | None) -> str | None:
    """Reject at the boundary: `build_system_prompt` would otherwise fall back
    to the default persona silently and the student would never know why."""
    if value is not None and value not in PERSONA_PROMPTS:
        raise ValueError(f"unknown persona {value!r}")
    return value


class ConversationCreate(BaseModel):
    title: str | None = None
    topic_slug: str | None = None
    persona: str | None = None

    _check_persona = field_validator("persona")(_known_persona)


class ConversationUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    persona: str | None = None

    _check_persona = field_validator("persona")(_known_persona)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    topic_slug: str | None
    status: str
    persona: str
    summary: str | None
    turn_count: int
    created_at: datetime
    last_active_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    text: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)
