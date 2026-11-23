from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def audit(db: Session, actor: User | None, action: str, entity_type: str | None = None,
          entity_id: int | str | None = None, details: dict | None = None, request: Request | None = None) -> None:
    """Add an audit record to the current transaction. Never put secrets or Aadhaar in `details`."""
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or None,
        ip_address=(request.client.host if request and request.client else None),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
    ))
