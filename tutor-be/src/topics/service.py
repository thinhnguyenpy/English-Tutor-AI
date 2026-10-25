from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import TopicNotFound
from src.topics.models import Topic


async def list_topics(session: AsyncSession) -> list[Topic]:
    stmt = select(Topic).order_by(Topic.sort_order.asc(), Topic.title.asc())
    return list((await session.execute(stmt)).scalars().all())


async def get_by_slug(session: AsyncSession, slug: str) -> Topic:
    stmt = select(Topic).where(Topic.slug == slug)
    topic = (await session.execute(stmt)).scalar_one_or_none()
    if topic is None:
        raise TopicNotFound()
    return topic
