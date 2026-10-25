from uuid import UUID

from fastapi import APIRouter, Query

from src.conversations import service as conversation_service
from src.core.database import SessionDep
from src.feedback import service
from src.feedback.schemas import TurnFeedbackOut

router = APIRouter(tags=["feedback"])


@router.get("/conversations/{conversation_id}/feedback", response_model=list[TurnFeedbackOut])
async def list_conversation_feedback(
    conversation_id: UUID, session: SessionDep
) -> list[TurnFeedbackOut]:
    await conversation_service.get_conversation(session, conversation_id)  # 404 if missing
    rows = await service.list_for_conversation(session, conversation_id)
    return [TurnFeedbackOut.model_validate(r) for r in rows]


@router.get("/feedback", response_model=list[TurnFeedbackOut])
async def list_recent_feedback(
    session: SessionDep, limit: int = Query(100, ge=1, le=500)
) -> list[TurnFeedbackOut]:
    """Every note across all conversations, newest first — the review list."""
    rows = await service.list_recent(session, limit=limit)
    return [TurnFeedbackOut.model_validate(r) for r in rows]
