"""Test fixtures.

Every test runs against a throwaway SQLite file, never the dev database. A
file rather than `:memory:` because the async engine hands out more than one
connection and an in-memory database is per-connection.

The Azure block is blanked before `src` is imported. Process env beats the
`.env` file in pydantic-settings, so a developer's real key in tutor-be/.env
never reaches a test — no test can bill the deployment, and the no-key
refusal contract stays testable on a configured machine.
"""

import os

for _var in ("AZURE_LLM_ENDPOINT", "AZURE_LLM_API_KEY", "AZURE_LLM_MODEL"):
    os.environ[_var] = ""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.base_model import Base
from src.models import *  # noqa: F401,F403 — populates Base.metadata


@pytest.fixture
async def session(tmp_path: Path) -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s

    await engine.dispose()
