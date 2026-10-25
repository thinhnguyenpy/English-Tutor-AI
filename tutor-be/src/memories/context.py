"""Builds the system prompt for one conversational turn.

Three tiers, cheapest first:

1. **Memory notes** — every active `Memory` row, verbatim. A few hundred facts
   is still only 1-2k tokens, so there is nothing to retrieve or rank yet. When
   this stops fitting, the next step is SQLite's built-in FTS5, and only after
   that embeddings.
2. **Rolling summary** — everything in this conversation older than the tail.
3. **Verbatim tail** — the last `RECENT_TURNS_IN_CONTEXT` messages.

Kept free of agent imports so it can be unit-tested without an Azure key.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.prompts.tutor_prompts import build_system_prompt
from src.conversations import service as conversation_service
from src.conversations.models import Conversation
from src.core.config import settings
from src.memories import service as memory_service
from src.memories.models import Memory

MEMORY_HEADER = "## What you know about this student"
SUMMARY_HEADER = "## Earlier in this conversation"


def render_memories(memories: list[Memory]) -> str:
    if not memories:
        return ""
    lines = [MEMORY_HEADER]
    lines += [f"- ({m.kind}) {m.content}" for m in memories]
    return "\n".join(lines)


def render_summary(conversation: Conversation) -> str:
    if not conversation.summary:
        return ""
    return f"{SUMMARY_HEADER}\n{conversation.summary}"


async def build_context(
    session: AsyncSession,
    conversation: Conversation,
    *,
    persona: str | None = None,
    difficulty: str = "intermediate",
    feedback_style: str = "gentle",
    topic_seed: str | None = None,
) -> str:
    """Compose the full instructions for the tutor agent.

    The verbatim tail is NOT included here — it is passed to the agent as
    `message_history` so the model sees real turn structure rather than a
    flattened transcript.
    """
    from src.agents.prompts.tutor_prompts import DEFAULT_PERSONA

    memories = await memory_service.list_memories(session)

    blocks = [
        build_system_prompt(
            persona=persona or DEFAULT_PERSONA,
            difficulty=difficulty,
            feedback_style=feedback_style,
            topic_seed=topic_seed,
        ),
        render_memories(memories),
        render_summary(conversation),
    ]
    return "\n\n".join(b for b in blocks if b)


async def recent_turns(session: AsyncSession, conversation: Conversation):
    """The verbatim tail, oldest first."""
    return await conversation_service.list_messages(
        session, conversation.id, limit=settings.RECENT_TURNS_IN_CONTEXT
    )
