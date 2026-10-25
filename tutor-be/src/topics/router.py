from fastapi import APIRouter

from src.core.database import SessionDep
from src.topics import service
from src.topics.schemas import TopicOut

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
async def list_topics(session: SessionDep) -> list[TopicOut]:
    rows = await service.list_topics(session)
    return [TopicOut.model_validate(r) for r in rows]
