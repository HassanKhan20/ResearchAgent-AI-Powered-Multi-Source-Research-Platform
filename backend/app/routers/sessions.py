import secrets

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_cache
from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import User, UserSession
from ..schemas import SessionCreate, SessionOut, UserOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)) -> SessionOut:
    user = User(display_name=body.display_name or "Researcher")
    db.add(user)
    await db.flush()
    token = secrets.token_urlsafe(32)
    db.add(UserSession(token=token, user_id=user.id))
    await db.commit()
    await get_cache().set_json(f"session:{token}", user.id, ttl=get_settings().session_ttl)
    return SessionOut(token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user
