"""Live conversational turn over a WebSocket.

Protocol (JSON frames):

    client → {"type": "user_turn", "text": "...",
              "difficulty": "...", "feedback_style": "..."}
    server → {"type": "reply_delta", "text": "..."}      streamed
    server → {"type": "reply_done", "message_id": "...", "user_message_id": "...",
              "turn_count": n, "max_turns": 30}
    server → {"type": "turn_limit", "turn_count": n, "max_turns": 30}   refused
    server → {"type": "feedback", "message_id": "...", "items": [...]}   cold
    server → {"type": "title", "title": "..."}                           cold
    server → {"type": "error", "detail": "..."}

Deltas are streamed so the browser's speech synthesiser can start reading the
first sentence while the rest is still being generated.
"""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.prompts.tutor_prompts import WRAP_UP_RULE
from src.agents.tutor_agent import TutorDeps, build_tutor_agent
from src.conversations import service
from src.conversations.cold import SocketSender, schedule_cold_pass, schedule_final_pass
from src.conversations.models import ROLE_ASSISTANT, ROLE_USER, Conversation, Message
from src.core.config import settings
from src.core.database import SessionLocal
from src.core.exceptions import TopicNotFound
from src.topics import service as topic_service

router = APIRouter(prefix="/conversations", tags=["live"])


def to_message_history(messages: list[Message]) -> list[ModelMessage]:
    """Replay stored turns as real request/response pairs rather than a
    flattened transcript, so the model sees who said what."""
    history: list[ModelMessage] = []
    for m in messages:
        if m.role == ROLE_USER:
            history.append(ModelRequest(parts=[UserPromptPart(content=m.text)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=m.text)]))
    return history


def trim_to_budget(messages: list[Message], budget: int) -> list[Message]:
    """Newest messages that fit in `budget` characters, oldest first. Stops at
    the first message that does not fit, so the kept tail stays contiguous."""
    kept: list[Message] = []
    used = 0
    for m in reversed(messages):
        used += len(m.text)
        if used > budget:
            break
        kept.append(m)
    kept.reverse()
    return kept


def turn_error(text: str) -> str | None:
    """Why a turn is refused before it reaches the model, or None."""
    if not text:
        return "Empty turn"
    if len(text) > settings.MAX_TURN_CHARS:
        return f"That turn is too long ({len(text)} characters, max {settings.MAX_TURN_CHARS})"
    return None


@router.websocket("/{conversation_id}/live")
async def live(websocket: WebSocket, conversation_id: UUID) -> None:
    await websocket.accept()
    logger.info("WS open for conversation {}", conversation_id)
    sender = SocketSender(websocket)

    try:
        while True:
            frame = await websocket.receive_json()

            if frame.get("type") != "user_turn":
                await sender.send(
                    {"type": "error", "detail": f"Unknown frame type {frame.get('type')!r}"}
                )
                continue

            text = (frame.get("text") or "").strip()
            if error := turn_error(text):
                await sender.send({"type": "error", "detail": error})
                continue

            if not settings.azure_configured:
                await sender.send(
                    {
                        "type": "error",
                        "detail": "Tutor is not configured — set AZURE_LLM_* in tutor-be/.env",
                    }
                )
                continue

            try:
                async with SessionLocal() as session:
                    await _handle_turn(sender, session, conversation_id, text, frame)
            except Exception as exc:  # noqa: BLE001 — one bad turn must not close the socket
                logger.opt(exception=True).error("Turn failed: {}", exc)
                await sender.send({"type": "error", "detail": str(exc)})

    except WebSocketDisconnect:
        logger.info("WS closed for conversation {}", conversation_id)
        schedule_final_pass(conversation_id)


async def _topic_seed(session: AsyncSession, conversation: Conversation) -> str | None:
    """The topic's tutor-facing seed, or None. A topic removed from
    data/topics.json after the conversation started just stops steering."""
    if not conversation.topic_slug:
        return None
    try:
        topic = await topic_service.get_by_slug(session, conversation.topic_slug)
    except TopicNotFound:
        return None
    return topic.prompt_seed


async def _handle_turn(
    sender: SocketSender,
    session: AsyncSession,
    conversation_id: UUID,
    text: str,
    frame: dict,
) -> None:
    from src.memories.context import build_context

    conversation = await service.get_conversation(session, conversation_id)
    max_turns = settings.MAX_TURNS_PER_CONVERSATION
    if conversation.turn_count >= max_turns:
        # Refused before anything is stored or any model is called.
        await sender.send(
            {"type": "turn_limit", "turn_count": conversation.turn_count, "max_turns": max_turns}
        )
        return

    # Persist the student's turn first: if the model call fails, what they said
    # is not lost.
    user_message = await service.append_message(
        session, conversation_id, role=ROLE_USER, text=text, bump_turn=True
    )

    # The tail still ends with the turn just saved — drop it, since it is the
    # prompt rather than history.
    tail = await service.list_messages(
        session, conversation_id, limit=settings.RECENT_TURNS_IN_CONTEXT + 1
    )
    tail = trim_to_budget(
        [m for m in tail if m.id != user_message.id], settings.HISTORY_CHAR_BUDGET
    )
    history = to_message_history(tail)

    # Persona belongs to the conversation; level and feedback style are the
    # student's own settings and ride along on every frame.
    system_prompt = await build_context(
        session,
        conversation,
        persona=conversation.persona,
        difficulty=frame.get("difficulty", "intermediate"),
        feedback_style=frame.get("feedback_style", "gentle"),
        topic_seed=await _topic_seed(session, conversation),
    )
    if conversation.turn_count == max_turns:
        system_prompt = f"{system_prompt}\n\n{WRAP_UP_RULE}"

    agent = build_tutor_agent()
    chunks: list[str] = []
    async with agent.run_stream(
        text, deps=TutorDeps(system_prompt=system_prompt), message_history=history
    ) as result:
        async for delta in result.stream_text(delta=True):
            chunks.append(delta)
            await sender.send({"type": "reply_delta", "text": delta})

    reply = "".join(chunks).strip()
    assistant_message = await service.append_message(
        session, conversation_id, role=ROLE_ASSISTANT, text=reply
    )

    await sender.send(
        {
            "type": "reply_done",
            "message_id": str(assistant_message.id),
            "user_message_id": str(user_message.id),
            "turn_count": conversation.turn_count,
            "max_turns": max_turns,
        }
    )

    # Everything past this point is detached: the student already has their
    # reply, so grammar notes and memory extraction can take as long as they
    # need without anyone waiting.
    schedule_cold_pass(
        sender=sender,
        conversation_id=conversation_id,
        user_message_id=user_message.id,
        user_text=text,
        turn_number=conversation.turn_count,
        final=conversation.turn_count == max_turns,
    )
