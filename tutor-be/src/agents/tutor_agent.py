"""The hot-path agent: the reply the student is waiting to hear.

Deliberately has no tools. Every fact it needs — the memory notes, the rolling
summary, the recent turns — is composed into the instructions up front by
`src.memories.context.build_context`. A tool call here would add a full
round-trip to a path where latency is the whole product.
"""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from src.agents.base import chat_model


@dataclass
class TutorDeps:
    # Fully-composed instructions: persona + level + feedback style + memory
    # notes + conversation summary.
    system_prompt: str


def build_tutor_agent() -> Agent[TutorDeps, str]:
    agent = Agent(
        chat_model(),
        deps_type=TutorDeps,
        output_type=str,
    )

    @agent.instructions
    def _instructions(ctx: RunContext[TutorDeps]) -> str:
        return ctx.deps.system_prompt

    return agent
