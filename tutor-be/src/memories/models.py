import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base, time_now

# Memory.kind — the taxonomy the extraction agent must choose from. Keep this
# list and `ExtractedMemory.kind` in src/agents/memory_agent.py in sync.
KIND_PROFILE = "profile"
KIND_EVENT = "event"
KIND_GOAL = "goal"
KIND_PREFERENCE = "preference"
KIND_LANGUAGE_ISSUE = "language_issue"

MEMORY_KINDS = (
    KIND_PROFILE,
    KIND_EVENT,
    KIND_GOAL,
    KIND_PREFERENCE,
    KIND_LANGUAGE_ISSUE,
)

# Memory.status
ACTIVE = "active"
DISMISSED = "dismissed"


class Memory(Base):
    """One durable fact about the student, carried across every conversation.

    Dismissed rows are kept rather than deleted so the extraction agent can be
    told not to re-add something the student already rejected.
    """

    __tablename__ = "memories"

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=ACTIVE, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)

    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    # Bumped whenever the student says something that reconfirms this fact, so
    # stale facts can be aged out later without touching created_at.
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=time_now, nullable=False
    )

    __table_args__ = (Index("ix_memories_status_kind", "status", "kind"),)
