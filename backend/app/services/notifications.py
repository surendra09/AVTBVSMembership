"""Notification creation (website + email/SMS outbox) and delivery processing.

Creating notifications only inserts rows inside the caller's transaction, so a
provider outage can never block saving an application or membership. The worker
(`process_outbox`) delivers queued email/SMS with retries and failure logging.
"""
import json
import logging
import smtplib
import ssl
import uuid
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.types import utcnow
from app.models import (
    DeliveryStatus, EditPermission, EditRequest, Member, MemberProfile, Notification, NotificationChannel,
    NotificationDelivery, Role, User,
)
from app.services.notification_templates import render

logger = logging.getLogger("avtbvs.notifications")
_env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates" / "email"),
                   autoescape=select_autoescape(["html"]))

ALL = ("web", "email", "sms")


def _email_html(subject: str, body: str, action_url: str | None, action_label: str | None) -> str:
    return _env.get_template("base.html").render(
        subject=subject, paragraphs=[p for p in body.split("\n\n") if p.strip()],
        action_url=action_url, action_label=action_label or "Open AVTBVS Membership",
        logo_url=f"{settings.PUBLIC_APP_URL.rstrip('/')}/brand/emblem-192.png",
        org_abbreviation=settings.ORG_ABBREVIATION, org_full_name=settings.ORG_FULL_NAME,
        org_registration=settings.ORG_REGISTRATION, org_address=settings.ORG_ADDRESS,
        org_phone=settings.ORG_PHONE, org_email=settings.ORG_EMAIL,
    )


def _abs_link(link: str | None) -> str | None:
    if not link:
        return None
    return link if link.startswith("http") else f"{settings.PUBLIC_APP_URL.rstrip('/')}{link}"


def notify(db: Session, user: User, event: str, context: dict | None = None, channels=ALL,
           link: str | None = None, sensitive: bool = False, action_label: str | None = None) -> None:
    ctx = {"name": user.full_name, **(context or {})}
    t = render(event, ctx)
    notification = None
    if "web" in channels and t.message:
        notification = Notification(user_id=user.id, event=event, title=t.title, message=t.message, link=link)
        db.add(notification)
        db.flush()
    if "email" in channels and t.email_body and user.email:
        db.add(NotificationDelivery(
            notification_id=notification.id if notification else None, user_id=user.id, event=event,
            channel=NotificationChannel.EMAIL, recipient=user.email, subject=f"{t.email_subject}",
            body_text=t.email_body, body_html=_email_html(t.email_subject, t.email_body, _abs_link(link), action_label),
            is_sensitive=sensitive,
        ))
    if "sms" in channels and t.sms and user.phone:
        db.add(NotificationDelivery(
            notification_id=notification.id if notification else None, user_id=user.id, event=event,
            channel=NotificationChannel.SMS, recipient=user.phone, body_text=t.sms, is_sensitive=sensitive,
        ))


def notify_admins(db: Session, event: str, context: dict, link: str | None = None,
                  channels=("web", "email")) -> None:
    admins = db.scalars(select(User).where(User.role.in_([Role.ADMIN, Role.SUPER_ADMIN]), User.is_active.is_(True)))
    for admin in admins:
        notify(db, admin, event, {**context, "admin_name": admin.full_name}, channels=channels, link=link)


# --- Providers -----------------------------------------------------------------
class DeliveryError(Exception):
    pass


def _console(delivery: NotificationDelivery) -> str:
    """Development/testing provider: appends the message to a local outbox log."""
    path = Path(settings.CONSOLE_OUTBOX_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": utcnow().isoformat(), "channel": delivery.channel.value, "to": delivery.recipient,
              "subject": delivery.subject, "body": delivery.body_text}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("[console-%s] queued message #%s for delivery", delivery.channel.value.lower(), delivery.id)
    return f"console-{uuid.uuid4().hex[:12]}"


def _send_email(d: NotificationDelivery) -> str:
    if settings.EMAIL_PROVIDER == "console":
        return _console(d)
    msg = EmailMessage()
    msg["Subject"] = d.subject or "AVTBVS Membership"
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = d.recipient
    msg["Message-ID"] = f"<{uuid.uuid4().hex}@avtbvs>"
    msg.set_content(d.body_text)
    if d.body_html:
        msg.add_alternative(d.body_html, subtype="html")
    try:
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            if settings.SMTP_USE_TLS:
                server.starttls(context=ssl.create_default_context())
        with server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise DeliveryError(f"SMTP error: {exc.__class__.__name__}: {exc}") from exc
    return msg["Message-ID"]


def _e164(number: str) -> str:
    if number.startswith("+"):
        return number
    return f"{settings.SMS_DEFAULT_COUNTRY_CODE}{number.lstrip('0')}"


def _send_sms(d: NotificationDelivery) -> str:
    if settings.SMS_PROVIDER == "console":
        return _console(d)
    to = _e164(d.recipient)
    try:
        if settings.SMS_PROVIDER == "twilio":
            r = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
                data={"To": to, "From": settings.TWILIO_FROM_NUMBER, "Body": d.body_text},
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN), timeout=20,
            )
            if r.status_code >= 300:
                raise DeliveryError(f"Twilio HTTP {r.status_code}: {r.text[:300]}")
            return r.json().get("sid", "")
        if settings.SMS_PROVIDER == "msg91":
            # MSG91 Flow API (DLT-registered template required in India). The template
            # should contain a single variable "message" holding the text.
            r = httpx.post(
                "https://control.msg91.com/api/v5/flow/",
                headers={"authkey": settings.MSG91_AUTH_KEY, "content-type": "application/json"},
                json={"template_id": settings.MSG91_FLOW_ID, "sender": settings.MSG91_SENDER_ID,
                      "recipients": [{"mobiles": to.lstrip("+"), "message": d.body_text}]},
                timeout=20,
            )
            if r.status_code >= 300 or r.json().get("type") == "error":
                raise DeliveryError(f"MSG91 HTTP {r.status_code}: {r.text[:300]}")
            return str(r.json().get("message", ""))
    except httpx.HTTPError as exc:
        raise DeliveryError(f"SMS provider error: {exc}") from exc
    raise DeliveryError(f"Unknown SMS provider {settings.SMS_PROVIDER}")


def deliver(d: NotificationDelivery) -> str:
    return _send_email(d) if d.channel == NotificationChannel.EMAIL else _send_sms(d)


# --- Worker ----------------------------------------------------------------------
def _backoff(attempts: int) -> timedelta:
    return timedelta(minutes=min(2 ** (attempts - 1), 60))


def process_outbox(session_factory, batch_size: int = 25) -> dict:
    """Claim and deliver pending email/SMS rows. Safe to run from several workers."""
    stats = {"sent": 0, "failed": 0, "retry": 0}
    now = utcnow()
    with session_factory() as db:
        # Recover rows stuck in SENDING (e.g. worker crashed mid-send).
        db.execute(update(NotificationDelivery)
                   .where(NotificationDelivery.status == DeliveryStatus.SENDING,
                          NotificationDelivery.next_attempt_at < now - timedelta(minutes=10))
                   .values(status=DeliveryStatus.PENDING))
        stmt = (select(NotificationDelivery)
                .where(NotificationDelivery.status == DeliveryStatus.PENDING,
                       NotificationDelivery.next_attempt_at <= now)
                .order_by(NotificationDelivery.id).limit(batch_size))
        if db.bind.dialect.name == "mysql":
            stmt = stmt.with_for_update(skip_locked=True)
        rows = db.scalars(stmt).all()
        for row in rows:
            row.status = DeliveryStatus.SENDING
            row.next_attempt_at = now
        db.commit()
        ids = [r.id for r in rows]

    for delivery_id in ids:
        with session_factory() as db:
            d = db.get(NotificationDelivery, delivery_id)
            d.attempts += 1
            try:
                d.provider_message_id = deliver(d)
                d.status = DeliveryStatus.SENT
                d.sent_at = utcnow()
                d.last_error = None
                stats["sent"] += 1
            except Exception as exc:  # noqa: BLE001 – any provider failure is logged and retried
                d.last_error = str(exc)[:2000]
                if d.attempts >= settings.NOTIFICATION_MAX_ATTEMPTS:
                    d.status = DeliveryStatus.FAILED
                    stats["failed"] += 1
                    logger.error("Delivery #%s permanently failed after %s attempts", d.id, d.attempts)
                else:
                    d.status = DeliveryStatus.PENDING
                    d.next_attempt_at = utcnow() + _backoff(d.attempts)
                    stats["retry"] += 1
                    logger.warning("Delivery #%s failed (attempt %s); will retry", d.id, d.attempts)
            db.commit()
    return stats


def process_expired_edit_permissions(session_factory) -> int:
    """Notify members whose 24-hour editing window has ended (access itself is
    enforced on every request by comparing server time with expires_at)."""
    now = utcnow()
    count = 0
    with session_factory() as db:
        perms = db.scalars(
            select(EditPermission).where(EditPermission.expires_at <= now, EditPermission.expiry_notified_at.is_(None),
                                         EditPermission.revoked_at.is_(None)).limit(100)
        ).all()
        for p in perms:
            p.expiry_notified_at = now
            member = db.get(Member, p.member_id)
            profile = db.get(MemberProfile, member.member_profile_id) if member else None
            user = db.get(User, profile.user_id) if profile and profile.user_id else None
            if user:
                notify(db, user, "edit_permission_expired", link="/dashboard/membership")
            count += 1
        db.commit()
    return count


__all__ = ["notify", "notify_admins", "process_outbox", "process_expired_edit_permissions", "EditRequest",
           "and_", "or_"]
