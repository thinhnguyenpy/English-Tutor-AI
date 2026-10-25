"""The agent boundaries, exercised without an Azure key.

`FunctionModel` stands in for the deployment, so these assert the contract we
control — that structured output matches the schema, that a refusal is returned
rather than a faked reply when no key is set, and that a cold-path failure
cannot take the conversation down with it.
"""

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from src.agents.memory_agent import ExtractedMemory, MemoryExtraction
from src.core.config import settings
from src.core.exceptions import TutorUnavailable
from src.memories import service as memory_service


def test_no_key_means_refusal_not_a_fake_reply():
    """The old Node server answered with canned encouragement when the key was
    missing, so a broken deployment looked like a working tutor. Building a
    model must fail loudly instead."""
    from src.agents.base import chat_model

    assert not settings.azure_configured, "test env must have no Azure key"
    chat_model.cache_clear()
    with pytest.raises(TutorUnavailable):
        chat_model()


async def test_memory_extraction_output_matches_the_table_taxonomy(session):
    """The agent's `kind` values have to be ones `memories` accepts, or every
    extracted fact is silently dropped by apply_extraction."""

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert info.output_tools, "structured output must be requested via a tool"
        args = MemoryExtraction(
            memories=[
                ExtractedMemory(
                    action="add",
                    kind="event",
                    content="Has an IELTS speaking test on 2026-09-14",
                    confidence=0.95,
                ),
                ExtractedMemory(action="skip", kind="profile", content="Lives somewhere"),
            ]
        ).model_dump(mode="json")
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)])

    agent = Agent(FunctionModel(respond), output_type=MemoryExtraction)
    result = await agent.run("student said things")

    changed = await memory_service.apply_extraction(session, result.output.memories)
    rows = await memory_service.list_memories(session)

    assert changed == 1, "the `skip` op must not create a row"
    assert rows[0].kind == "event"
    assert "2026-09-14" in rows[0].content


async def test_feedback_agent_returns_an_empty_list_cleanly():
    """Most utterances are fine. An agent that cannot express 'nothing to say'
    will invent corrections, which is worse than silence."""
    from src.agents.feedback_agent import TurnFeedbackResult

    agent = Agent(TestModel(custom_output_args={"items": []}), output_type=TurnFeedbackResult)
    result = await agent.run("I went to the market yesterday.")

    assert result.output.items == []


async def test_cold_pass_failure_does_not_propagate():
    """The rule the whole cold path rests on: a broken analysis step degrades
    the notes, never the conversation."""
    from src.conversations.cold import _guard

    async def boom():
        raise RuntimeError("analysis deployment is down")

    await _guard("memory", boom())  # must not raise


async def test_tutor_agent_streams_text():
    """The UI speaks each sentence as it arrives, so the reply has to come back
    as deltas rather than one final blob."""
    agent = Agent(TestModel(custom_output_text="Hello there. How was your day?"))

    chunks: list[str] = []
    async with agent.run_stream("hi") as result:
        async for delta in result.stream_text(delta=True):
            chunks.append(delta)

    assert "".join(chunks) == "Hello there. How was your day?"


def test_reasoning_effort_is_sent_only_when_configured():
    """Empty means "leave the parameter off" — a non-reasoning deployment
    rejects `reasoning_effort` outright, so it must be omittable."""
    from src.agents.base import reasoning_settings

    assert reasoning_settings("") is None
    assert reasoning_settings("minimal") == {"openai_reasoning_effort": "minimal"}


def test_titles_and_summaries_run_at_the_light_effort(monkeypatch):
    from src.agents import title_agent

    monkeypatch.setattr(title_agent, "analysis_model", lambda: TestModel())
    monkeypatch.setattr(settings, "AZURE_LLM_LIGHT_REASONING_EFFORT", "none")
    for build in (title_agent.build_title_agent, title_agent.build_summary_agent):
        assert build().model_settings == {"openai_reasoning_effort": "none"}
