from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User

LOCAL_OWNER = UUID("00000000-0000-4000-8000-000000000001")


def ensure_local_owner(session: Session) -> UUID:
    if session.get(User, LOCAL_OWNER) is None:
        session.add(
            User(id=LOCAL_OWNER, user_id=LOCAL_OWNER, display_name="Local user", mode="local")
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if session.get(User, LOCAL_OWNER) is None:
                raise
    return LOCAL_OWNER
