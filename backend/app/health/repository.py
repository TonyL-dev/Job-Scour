from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.models import User


def database_ready(session: Session) -> bool:
    try:
        # Query a migrated table: a reachable but unmigrated database is not ready.
        session.execute(select(User.id).limit(1))
    except SQLAlchemyError:
        session.rollback()
        return False
    return True
