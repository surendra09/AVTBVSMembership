"""FastAPI dependencies: authentication and role-based authorization."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ACCESS_COOKIE, decode_token
from app.database.session import get_db
from app.models import Member, MemberProfile, MembershipStatus, Role, User

bearer_scheme = HTTPBearer(auto_error=False, description="Access token (alternative to the HttpOnly cookie)")


def _token_from_request(request: Request, creds: HTTPAuthorizationCredentials | None) -> str | None:
    if creds and creds.scheme.lower() == "bearer":
        return creds.credentials
    return request.cookies.get(ACCESS_COOKIE)


def get_optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    token = _token_from_request(request, creds)
    if not token:
        return None
    payload = decode_token(token, "access")
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    # Tokens issued before a password change are no longer valid.
    if user.password_changed_at and payload.get("iat") and payload["iat"] < int(user.password_changed_at.timestamp()):
        return None
    request.state.user = user
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user

    return checker


require_admin = require_roles(Role.ADMIN, Role.SUPER_ADMIN)
require_super_admin = require_roles(Role.SUPER_ADMIN)


def get_active_member_for_user(db: Session, user: User) -> Member | None:
    return db.scalar(
        select(Member).join(MemberProfile, Member.member_profile_id == MemberProfile.id)
        .where(MemberProfile.user_id == user.id, Member.status == MembershipStatus.ACTIVE)
    )


def require_member_or_admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Full directory access: approved ACTIVE members, Admins and Super Admins only."""
    if user.is_admin or get_active_member_for_user(db, user):
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN,
                        "The full member directory is available to approved members only")


def require_active_member(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Member:
    member = get_active_member_for_user(db, user)
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only approved members can perform this action")
    return member
