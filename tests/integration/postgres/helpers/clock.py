from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def advance_postgres_clock(
    session: AsyncSession,
    *,
    seconds: float = 0.01,
) -> None:
    await session.execute(
        text("SELECT pg_sleep(:seconds)"),
        {"seconds": seconds},
    )
    await session.commit()
