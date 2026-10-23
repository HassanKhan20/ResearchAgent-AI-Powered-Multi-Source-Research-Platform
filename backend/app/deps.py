from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from .cache import get_cache
from .config import get_settings
from .db import get_db
from .models import User, UserSession


async def current_user(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None, description="Session token (for EventSource, which can't set headers)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw = token or (authorization or "").removeprefix("Bearer ").strip()
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing session token")

    cache = get_cache()
    user_id = await cache.get_json(f"session:{raw}")
    if user_id is None:
        session = await db.get(UserSession, raw)
        if session is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
        session.last_seen_at = datetime.now(timezone.utc)
        await db.commit()
        user_id = session.user_id
        await cache.set_json(f"session:{raw}", user_id, ttl=get_settings().session_ttl)

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user
