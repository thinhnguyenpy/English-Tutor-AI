from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base_model import Base

LEVELS = ("beginner", "intermediate", "advanced")


class Topic(Base):
    """A pre-designed conversation starter, for when the student opens the app
    with nothing in particular to say. Seeded from data/topics.json."""

    __tablename__ = "topics"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="intermediate", nullable=False)
    # Injected into the tutor's system prompt to steer the opening turns.
    prompt_seed: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
