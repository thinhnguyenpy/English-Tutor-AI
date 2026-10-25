"""The cold path — everything that happens after the student has their reply.

Grammar notes, memory extraction, rolling summaries and conversation titles all
run here, detached. The rule that governs this whole module: **a failure here
must never affect the conversation.** Every step is individually guarded, and
the worst outcome of a broken cold pass is that notes are missing from one turn.

SmartDocs runs this kind of work in a separate polling worker process claiming
rows `FOR UPDATE SKIP LOCKED`. That does not carry over here: SQLite has no
`SKIP LOCKED`, and with a single local user there is no queue to drain. Plain
`asyncio` tasks on the API process are the right size for the problem.
"""

import asyncio
from datetime import date
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocket, WebSocketState

from src.conversations import service as conversation_service
from src.conversations.models import ROLE_USER
from src.core.config import settings
from src.core.database import SessionLocal
from src.feedback import service as feedback_service
from src.memories import service as memory_service

# asyncio holds only weak references to tasks, so a fire-and-forget task can be
# garbage-collected mid-flight. Keeping a strong reference until it finishes is
# not optional.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


class SocketSender:
    """Serialises sends on one WebSocket.

    The cold path emits frames while the hot path may be streaming deltas for
    the next turn. Two coroutines awaiting `send_json` concurrently can
    interleave at the ASGI layer, so every send goes through one lock. Sends to
    an already-closed socket are dropped rather than raised — the student
    closing the tab is not an error.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket
        self._lock = asyncio.Lock()

    async def send(self, payload: dict) -> None:
        if self._websocket.client_state is not WebSocketState.CONNECTED:
            return
        async with self._lock:
            try:
                await self._websocket.send_json(payload)
            except RuntimeError:
                # Starlette raises RuntimeError when the socket closed between
                # the state check above and the send.
                logger.debug("Dropped frame {} — socket gone", payload.get("type"))


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


def schedule_cold_pass(
    *,
    sender: SocketSender,
    conversation_id: UUID,
    user_message_id: UUID,
    user_text: str,
    turn_number: int,
    final: bool = False,
) -> None:
    """`turn_number` is captured by the hot path when the turn is saved. The
    pass must not re-read `turn_count`: by the time feedback finishes the
    student may have spoken again, which used to skip titles and whole
    summary/memory cycles. `final` mines the tail at the turn cap."""
    _spawn(
        _run_cold_pass(
            sender=sender,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            user_text=user_text,
            turn_number=turn_number,
            final=final,
        )
    )


def schedule_final_pass(conversation_id: UUID) -> None:
    """On disconnect: memory for whatever the periodic passes have not seen
    yet, so a conversation that ends at turn 5 is still remembered."""
    _spawn(_run_final_pass(conversation_id))


async def _run_cold_pass(
    *,
    sender: SocketSender,
    conversation_id: UUID,
    user_message_id: UUID,
    user_text: str,
    turn_number: int,
    final: bool,
) -> None:
    if not settings.azure_configured:
        return

    # A session of its own: the request-scoped one closed when the turn ended.
    async with SessionLocal() as session:
        await _guard("feedback", _feedback_pass(sender, session, user_message_id, user_text))

        if turn_number == 1:
            await _guard("title", _title_pass(sender, session, conversation_id))

        if final or turn_number % settings.COLD_PASS_EVERY_N_TURNS == 0:
            await _memory_cycle(session, conversation_id, turn_number)


async def _run_final_pass(conversation_id: UUID) -> None:
    if not settings.azure_configured:
        return
    async with SessionLocal() as session:
        try:
            conversation = await conversation_service.get_conversation(session, conversation_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Final pass: conversation {} vanished ({})", conversation_id, exc)
            return
        if conversation.turn_count > conversation.memory_pass_turn:
            await _memory_cycle(session, conversation_id, conversation.turn_count)


# Conversations with a summary + memory cycle running. The turn-cap pass and
# the disconnect that follows it would otherwise extract the same tail twice.
_CYCLES_IN_FLIGHT: set[UUID] = set()


async def _memory_cycle(session: AsyncSession, conversation_id: UUID, turn_number: int) -> None:
    if conversation_id in _CYCLES_IN_FLIGHT:
        return
    _CYCLES_IN_FLIGHT.add(conversation_id)
    try:
        await _guard("summary", _summary_pass(session, conversation_id))
        if await _guard("memory", _memory_pass(session, conversation_id)):
            conversation = await conversation_service.get_conversation(session, conversation_id)
            conversation.memory_pass_turn = max(conversation.memory_pass_turn, turn_number)
            await session.commit()
    finally:
        _CYCLES_IN_FLIGHT.discard(conversation_id)


async def _guard(label: str, coro) -> bool:
    """Run one step; a failure is logged and reported as False, never raised."""
    try:
        await coro
    except Exception as exc:  # noqa: BLE001
        logger.opt(exception=True).warning("Cold pass step {!r} failed: {}", label, exc)
        return False
    return True


# --- individual passes -------------------------------------------------------


async def _feedback_pass(
    sender: SocketSender, session: AsyncSession, user_message_id: UUID, user_text: str
) -> None:
    from src.agents.feedback_agent import build_feedback_agent

    result = await build_feedback_agent().run(user_text)
    items = result.output.items
    if not items:
        return

    rows = await feedback_service.save_feedback(session, user_message_id, items)
    await sender.send(
        {
            "type": "feedback",
            "message_id": str(user_message_id),
            "items": [
                {
                    "id": str(r.id),
                    "type": r.type,
                    "original": r.original,
                    "corrected": r.corrected,
                    "explanation": r.explanation,
                    "severity": r.severity,
                }
                for r in rows
            ],
        }
    )


async def _title_pass(sender: SocketSender, session: AsyncSession, conversation_id: UUID) -> None:
    from src.agents.title_agent import build_title_agent

    transcript = await _transcript(session, conversation_id)
    if not transcript:
        return

    result = await build_title_agent().run(transcript)
    title = result.output.strip().strip('"')[:200]
    if not title:
        return

    conversation = await conversation_service.get_conversation(session, conversation_id)
    conversation.title = title
    await session.commit()
    await sender.send({"type": "title", "title": title})


async def _summary_pass(session: AsyncSession, conversation_id: UUID) -> None:
    from src.agents.title_agent import build_summary_agent

    transcript = await _transcript(session, conversation_id)
    if not transcript:
        return

    result = await build_summary_agent().run(transcript)
    conversation = await conversation_service.get_conversation(session, conversation_id)
    conversation.summary = result.output.strip()
    await session.commit()


async def _memory_pass(session: AsyncSession, conversation_id: UUID) -> None:
    from src.agents.memory_agent import MemoryDeps, build_memory_agent

    transcript = await _transcript(session, conversation_id, only_role=ROLE_USER)
    if not transcript:
        return

    existing = await memory_service.list_memories(session)
    rendered = "\n".join(f"{m.id} ({m.kind}) {m.content}" for m in existing)

    result = await build_memory_agent().run(
        transcript,
        deps=MemoryDeps(existing=rendered, conversation_date=date.today().isoformat()),
    )
    changed = await memory_service.apply_extraction(
        session, result.output.memories, conversation_id=conversation_id
    )
    if changed:
        logger.info("Memory pass: {} fact(s) added/updated", changed)


async def _transcript(
    session: AsyncSession, conversation_id: UUID, *, only_role: str | None = None
) -> str:
    messages = await conversation_service.list_messages(session, conversation_id)
    if only_role:
        messages = [m for m in messages if m.role == only_role]
    return "\n".join(f"{m.role}: {m.text}" for m in messages)
