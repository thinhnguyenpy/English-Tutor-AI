"""The hot path end to end through `_handle_turn`, with a FunctionModel in
place of the deployment.

`test_context.py` covers `build_context` on its own; these exist because the
bugs were in what `_handle_turn` *passed* to it — the topic seed never reached
the prompt even though `build_context` handled it correctly.
"""

from collections.abc import AsyncIterator

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.agents.prompts.tutor_prompts import PERSONA_PROMPTS, WRAP_UP_RULE
from src.agents.tutor_agent import TutorDeps
from src.conversations import service, ws_router
from src.conversations.models import Message
from src.conversations.schemas import ConversationCreate
from src.core.config import settings
from src.topics.models import Topic


class FakeSender:
    def __init__(self) -> None:
        self.frames: list[dict] = []

    async def send(self, payload: dict) -> None:
        self.frames.append(payload)


@pytest.fixture
def prompts(monkeypatch) -> list[str]:
    """Instructions the tutor agent was called with, one per model call."""
    seen: list[str] = []

    async def stream(messages: list[ModelMessage], _info: AgentInfo) -> AsyncIterator[str]:
        request = messages[-1]
        assert isinstance(request, ModelRequest)
        seen.append(request.instructions or "")
        yield "Nice. "
        yield "Tell me more?"

    def build() -> Agent[TutorDeps, str]:
        agent = Agent(FunctionModel(stream_function=stream), deps_type=TutorDeps)
        agent.instructions(lambda ctx: ctx.deps.system_prompt)
        return agent

    monkeypatch.setattr(ws_router, "build_tutor_agent", build)
    monkeypatch.setattr(ws_router, "schedule_cold_pass", lambda **_: None)
    return seen


async def _turn(session, conversation, text="Hello", **frame) -> FakeSender:
    sender = FakeSender()
    await ws_router._handle_turn(sender, session, conversation.id, text, frame)
    return sender


async def test_topic_seed_reaches_the_prompt(session, prompts):
    session.add(Topic(slug="commute", title="Commute", prompt_seed="Ask about their commute."))
    await session.commit()
    conv = await service.create_conversation(session, ConversationCreate(topic_slug="commute"))

    await _turn(session, conv)

    assert "Today's topic: Ask about their commute." in prompts[0]


async def test_missing_topic_does_not_break_the_turn(session, prompts):
    conv = await service.create_conversation(session, ConversationCreate(topic_slug="gone"))

    sender = await _turn(session, conv)

    assert "Today's topic" not in prompts[0]
    assert sender.frames[-1]["type"] == "reply_done"


async def test_persona_comes_from_the_conversation_not_the_frame(session, prompts):
    conv = await service.create_conversation(session, ConversationCreate(persona="grammar_tutor"))

    await _turn(session, conv, persona="fluency_coach")

    assert PERSONA_PROMPTS["grammar_tutor"] in prompts[0]
    assert PERSONA_PROMPTS["fluency_coach"] not in prompts[0]


def _msg(text: str) -> Message:
    return Message(role="user", text=text)


def test_history_keeps_the_newest_messages_that_fit():
    messages = [_msg("a" * 50), _msg("b" * 30), _msg("c" * 30)]

    kept = ws_router.trim_to_budget(messages, budget=70)

    assert [m.text[0] for m in kept] == ["b", "c"]


def test_history_tail_stays_contiguous_past_an_oversized_message():
    messages = [_msg("a" * 5), _msg("b" * 500), _msg("c" * 5)]

    assert [m.text[0] for m in ws_router.trim_to_budget(messages, budget=100)] == ["c"]


def test_overlong_and_empty_turns_are_refused_before_the_model():
    assert ws_router.turn_error("") == "Empty turn"
    assert ws_router.turn_error("x" * settings.MAX_TURN_CHARS) is None
    assert "too long" in ws_router.turn_error("x" * (settings.MAX_TURN_CHARS + 1))


async def test_last_turn_wraps_up_and_the_next_is_refused(session, prompts, monkeypatch):
    monkeypatch.setattr(settings, "MAX_TURNS_PER_CONVERSATION", 2)
    conv = await service.create_conversation(session, ConversationCreate())

    first = await _turn(session, conv)
    second = await _turn(session, conv)
    third = await _turn(session, conv)

    assert WRAP_UP_RULE.strip() not in prompts[0]
    assert WRAP_UP_RULE.strip() in prompts[1]
    assert first.frames[-1] | {"message_id": None, "user_message_id": None} == {
        "type": "reply_done",
        "message_id": None,
        "user_message_id": None,
        "turn_count": 1,
        "max_turns": 2,
    }
    assert second.frames[-1]["turn_count"] == 2
    assert third.frames == [{"type": "turn_limit", "turn_count": 2, "max_turns": 2}]
    assert len(prompts) == 2, "the refused turn must not reach the model"
    assert len(await service.list_messages(session, conv.id)) == 4, "nor be stored"
