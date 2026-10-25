import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base

# TurnFeedback.type
TYPE_GRAMMAR = "grammar"
TYPE_VOCABULARY = "vocabulary"
TYPE_NATURALNESS = "naturalness"
# NB: no "pronunciation" yet. There is no audio on the server — speech-to-text
# happens in the browser — so any pronunciation verdict would be guesswork off
# the transcript. Added when Azure Speech pronunciation assessment lands.

FEEDBACK_TYPES = (TYPE_GRAMMAR, TYPE_VOCABULARY, TYPE_NATURALNESS)

# TurnFeedback.severity
SEVERITY_MINOR = "minor"
SEVERITY_MAJOR = "major"


class TurnFeedback(Base):
    """A correction attached to one user turn: what they said vs what they
    should have said. This is the source table for the review notes."""

    __tablename__ = "turn_feedback"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    original: Mapped[str] = mapped_column(Text, nullable=False)
    corrected: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default=SEVERITY_MINOR, nullable=False)

    __table_args__ = (Index("ix_turn_feedback_message", "message_id"),)
