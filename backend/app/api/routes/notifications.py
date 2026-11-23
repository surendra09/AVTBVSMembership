from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.database.types import utcnow
from app.models import Notification, User
from app.schemas.common import Message, Page, paginate_meta

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationOut(BaseModel):
    id: int
    event: str
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(id=n.id, event=n.event, title=n.title, message=n.message, link=n.link, is_read=n.is_read,
                           created_at=n.created_at)


@router.get("", response_model=Page[NotificationOut])
def list_notifications(unread_only: bool = False, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Notification.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page[NotificationOut](items=[_out(n) for n in rows], **paginate_meta(total, page, page_size))


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"count": db.scalar(select(func.count()).select_from(Notification)
                               .where(Notification.user_id == user.id, Notification.is_read.is_(False))) or 0}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if not n.is_read:
        n.is_read, n.read_at = True, utcnow()
        db.commit()
    return _out(n)


@router.post("/read-all", response_model=Message)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
               .values(is_read=True, read_at=utcnow()))
    db.commit()
    return Message(message="All notifications marked as read")
