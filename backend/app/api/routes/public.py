from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models import BLOOD_GROUPS, Member, MembershipStatus
from app.services.notification_templates import TEMPLATES

router = APIRouter(tags=["Public"])


@router.get("/health", summary="Liveness/readiness probe")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/public/config", summary="Organisation details and form options used by the website")
def public_config(db: Session = Depends(get_db)):
    return {
        "app_name": settings.APP_NAME,
        "organisation": {
            "full_name": settings.ORG_FULL_NAME, "abbreviation": settings.ORG_ABBREVIATION,
            "telugu_name": settings.ORG_TELUGU_NAME, "formerly_known_as": settings.ORG_FORMERLY_KNOWN_AS,
            "registration": settings.ORG_REGISTRATION, "address": settings.ORG_ADDRESS, "phone": settings.ORG_PHONE,
            "email": settings.ORG_EMAIL, "community_name": settings.ORG_COMMUNITY_NAME,
        },
        "form": {
            "blood_groups": list(BLOOD_GROUPS), "minimum_age_years": settings.MINIMUM_AGE_YEARS,
            "require_introducer_signature": settings.REQUIRE_INTRODUCER_SIGNATURE,
            "max_photo_mb": settings.MAX_PHOTO_BYTES // (1024 * 1024),
            "max_document_mb": settings.MAX_DOCUMENT_BYTES // (1024 * 1024),
            "edit_permission_hours": settings.EDIT_PERMISSION_HOURS,
        },
        "active_member_count": db.scalar(select(func.count()).select_from(Member)
                                         .where(Member.status == MembershipStatus.ACTIVE)) or 0,
        "notification_events": sorted(TEMPLATES),
    }
