from fastapi import APIRouter

from src.conversations.router import router as conversations_router
from src.conversations.ws_router import router as live_router
from src.core.config import settings
from src.feedback.router import router as feedback_router
from src.memories.router import router as memories_router
from src.topics.router import router as topics_router

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        # The frontend shows a "demo mode" banner off this flag. A missing key
        # must be visible, not silently degraded into generic replies.
        "tutor_configured": settings.azure_configured,
    }


api_router.include_router(conversations_router)
api_router.include_router(live_router)
api_router.include_router(memories_router)
api_router.include_router(feedback_router)
api_router.include_router(topics_router)
