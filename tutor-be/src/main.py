from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.pre_start import init_services
from src.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("English Tutor AI starting up")
    await init_services()
    try:
        yield
    finally:
        logger.info("Shutting down")


app = FastAPI(
    title="English Tutor AI",
    description="Local AI English tutor with persistent conversations and long-term memory",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)

app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Pass `exc` positionally, not interpolated into the format string —
    loguru parses `{`/`}` in the message as format placeholders, so an
    exception whose text contains JSON would make the handler itself raise
    and bury the original error."""
    logger.opt(exception=True).error("Unhandled exception: {}", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)},
    )
