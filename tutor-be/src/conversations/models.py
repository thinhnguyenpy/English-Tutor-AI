import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.agents.prompts.tutor_prompts import DEFAULT_PERSONA
from src.core.base_model import Base, time_now

# Conversation.status
ACTIVE = "active"
ARCHIVED = "archived"

# Message.role
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class Conversation(Base):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    topic_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ACTIVE, nullable=False)
    # Per conversation, not global: one day is grammar drill, the next free
    # talk, and reopening an old conversation should keep its tutor.
    persona: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_PERSONA, server_default=DEFAULT_PERSONA, nullable=False
    )

    # Rolling summary of everything older than the verbatim tail replayed into
    # the prompt. Refreshed by the cold pass every COLD_PASS_EVERY_N_TURNS.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # The turn the last summary + memory pass covered. Anything after it is a
    # tail not yet mined for memories, which the final pass on disconnect or
    # at the turn cap picks up.
    memory_pass_turn: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=time_now, nullable=False
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_conversations_status_last_active", "status", "last_active_at"),)


class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)
