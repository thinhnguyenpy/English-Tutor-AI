"""Cold-path agent: decides what the tutor should remember about the student.

Structured output does the work that would otherwise be hand-rolled JSON
parsing with a regex — the agent must return operations that already match the
`memories` table's taxonomy, so a malformed answer fails at the boundary
instead of silently writing junk rows.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from src.agents.base import analysis_model
from src.agents.prompts.memory_prompts import MEMORY_EXTRACTION_PROMPT

MemoryKind = Literal["profile", "event", "goal", "preference", "language_issue"]


class ExtractedMemory(BaseModel):
    action: Literal["add", "update", "skip"]
    # Required for `update`; ignored otherwise.
    memory_id: UUID | None = None
    kind: MemoryKind
    content: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class MemoryExtraction(BaseModel):
    memories: list[ExtractedMemory] = Field(default_factory=list)


@dataclass
class MemoryDeps:
    # Existing facts rendered as "<id> (<kind>) <content>" so the agent can
    # reference them by id when it returns `update` or `skip`.
    existing: str
    conversation_date: str


def build_memory_agent() -> Agent[MemoryDeps, MemoryExtraction]:
    agent = Agent(
        analysis_model(),
        deps_type=MemoryDeps,
        output_type=MemoryExtraction,
    )

    @agent.instructions
    def _instructions(ctx: RunContext[MemoryDeps]) -> str:
        existing = ctx.deps.existing or "(nothing on file yet)"
        return (
            f"{MEMORY_EXTRACTION_PROMPT}\n\n"
            f"Today's date: {ctx.deps.conversation_date}\n\n"
            f"## Facts already on file\n{existing}"
        )

    return agent
