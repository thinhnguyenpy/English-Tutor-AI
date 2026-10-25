from uuid import UUID

from fastapi import APIRouter, Query

from src.conversations import service
from src.conversations.models import ACTIVE
from src.conversations.schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)
from src.core.database import SessionDep

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    session: SessionDep,
    status: str = Query(ACTIVE, description="active | archived"),
) -> list[ConversationOut]:
    rows = await service.list_conversations(session, status=status)
    return [ConversationOut.model_validate(r) for r in rows]


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(body: ConversationCreate, session: SessionDep) -> ConversationOut:
    conv = await service.create_conversation(session, body)
    return ConversationOut.model_validate(conv)


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, session: SessionDep) -> ConversationOut:
    conv = await service.get_conversation(session, conversation_id)
    return ConversationOut.model_validate(conv)


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: UUID, body: ConversationUpdate, session: SessionDep
) -> ConversationOut:
    conv = await service.update_conversation(session, conversation_id, body)
    return ConversationOut.model_validate(conv)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, session: SessionDep) -> None:
    await service.delete_conversation(session, conversation_id)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(conversation_id: UUID, session: SessionDep) -> list[MessageOut]:
    await service.get_conversation(session, conversation_id)  # 404 if missing
    rows = await service.list_messages(session, conversation_id)
    return [MessageOut.model_validate(r) for r in rows]
