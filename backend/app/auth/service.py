from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.repository import ensure_local_owner
from app.core.database import get_session


def local_owner(request: Request, session: Annotated[Session, Depends(get_session)]) -> UUID:
    if request.app.state.settings.mode != "local":
        raise HTTPException(
            403, "Career workspace requires local mode until authentication is implemented"
        )
    return ensure_local_owner(session)


Owner = Annotated[UUID, Depends(local_owner)]
Database = Annotated[Session, Depends(get_session)]
