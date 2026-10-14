"""Revoke sessions started before lock/delete, including pending writes and SSE readers."""

from threading import RLock

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session


class WorkspaceBarrier:
    def __init__(self) -> None:
        self.epoch = 0
        self.lock = RLock()

    def invalidate(self) -> int:
        with self.lock:
            self.epoch += 1
            return self.epoch


def bind(session: Session, barrier: WorkspaceBarrier, epoch: int | None = None) -> None:
    session.info["workspace_barrier"] = barrier
    session.info["workspace_epoch"] = barrier.epoch if epoch is None else epoch


def validate_session(session: Session) -> None:
    barrier = session.info.get("workspace_barrier")
    if barrier and session.info["workspace_epoch"] != barrier.epoch:
        raise HTTPException(423, "Workspace access changed. Unlock or reload before continuing.")


@event.listens_for(Session, "do_orm_execute")
def before_execute(state: ORMExecuteState) -> None:
    validate_session(state.session)


@event.listens_for(Session, "before_flush")
def before_flush(session: Session, flush_context: object, instances: object) -> None:
    validate_session(session)


@event.listens_for(Session, "before_commit")
def before_commit(session: Session) -> None:
    barrier = session.info.get("workspace_barrier")
    if barrier:
        barrier.lock.acquire()
        try:
            validate_session(session)
        except BaseException:
            barrier.lock.release()
            raise
        session.info["workspace_commit_lock"] = barrier.lock


def release(session: Session) -> None:
    lock = session.info.pop("workspace_commit_lock", None)
    if lock:
        lock.release()


event.listen(Session, "after_commit", release)
event.listen(Session, "after_rollback", release)
