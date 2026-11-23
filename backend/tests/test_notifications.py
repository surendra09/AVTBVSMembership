from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import DeliveryStatus, Notification, NotificationChannel, NotificationDelivery
from app.services import notifications as notif
from tests.helpers import login, make_user, submitted_application


def run_worker():
    return notif.process_outbox(SessionLocal, batch_size=500)


def _deliveries(db, user_id, event):
    return db.scalars(select(NotificationDelivery).where(NotificationDelivery.user_id == user_id,
                                                         NotificationDelivery.event == event)).all()


def test_submission_creates_web_email_sms_and_admin_notifications(db):
    admin = make_user(role=__import__("app.models", fromlist=["Role"]).Role.ADMIN)
    _, app, user = submitted_application()
    web = db.scalars(select(Notification).where(Notification.user_id == user.id,
                                                Notification.event == "application_submitted")).all()
    assert len(web) == 1
    channels = {d.channel for d in _deliveries(db, user.id, "application_submitted")}
    assert channels == {NotificationChannel.EMAIL, NotificationChannel.SMS}
    assert db.scalar(select(Notification).where(Notification.user_id == admin.id,
                                                Notification.event == "admin_new_application"))


def test_worker_marks_deliveries_sent(db):
    _, _, user = submitted_application()
    stats = run_worker()
    assert stats["sent"] >= 2
    rows = _deliveries(db, user.id, "application_submitted")
    assert all(r.status == DeliveryStatus.SENT and r.sent_at for r in rows)


def test_failed_delivery_is_retried_then_marked_failed(db, monkeypatch):
    from app.core.config import settings
    _, _, user = submitted_application()

    def boom(_d):
        raise notif.DeliveryError("provider down")

    monkeypatch.setattr(notif, "deliver", boom)
    monkeypatch.setattr(settings, "NOTIFICATION_MAX_ATTEMPTS", 2)
    stats = run_worker()
    assert stats["retry"] >= 1
    db.expire_all()
    row = _deliveries(db, user.id, "application_submitted")[0]
    assert row.status == DeliveryStatus.PENDING and row.attempts == 1 and "provider down" in row.last_error
    # make it due again and fail permanently
    for d in db.scalars(select(NotificationDelivery)):
        d.next_attempt_at = d.created_at
    db.commit()
    run_worker()
    db.expire_all()
    assert _deliveries(db, user.id, "application_submitted")[0].status == DeliveryStatus.FAILED


def test_notification_failure_never_blocks_saving(monkeypatch):
    # Even if the provider is broken the application is saved and submitted.
    monkeypatch.setattr(notif, "deliver", lambda d: (_ for _ in ()).throw(notif.DeliveryError("down")))
    _, app, _ = submitted_application()
    assert app["status"] == "PENDING"


def test_user_notification_endpoints():
    _, _, user = submitted_application()
    c = login(user)
    r = c.get("/api/notifications")
    assert r.status_code == 200 and r.json()["total"] >= 1
    assert r.json()["items"][0]["event"] == "application_submitted"
    assert c.get("/api/notifications/unread-count").json()["count"] >= 1
    nid = r.json()["items"][0]["id"]
    assert c.patch(f"/api/notifications/{nid}/read").json()["is_read"] is True
    assert c.post("/api/notifications/read-all").status_code == 200
    assert c.get("/api/notifications/unread-count").json()["count"] == 0


def test_users_cannot_read_others_notifications():
    _, _, user = submitted_application()
    c = login(user)
    nid = c.get("/api/notifications").json()["items"][0]["id"]
    other = login(make_user())
    assert other.patch(f"/api/notifications/{nid}/read").status_code == 404


def test_admin_sees_delivery_records_with_sensitive_bodies_hidden():
    from app.models import Role
    admin = make_user(role=Role.ADMIN)
    c = login(admin)
    from tests.helpers import new_client, unique_phone, PASSWORD
    new_client().post("/api/auth/register", json={"full_name": "OTP Person", "email": "otpperson@example.org",
                                                  "phone": unique_phone(), "password": PASSWORD})
    run_worker()
    r = c.get("/api/admin/notification-deliveries", params={"q": "otpperson"})
    assert r.status_code == 200
    items = r.json()["items"]
    otp_rows = [i for i in items if i["event"] == "otp_email"]
    assert otp_rows and otp_rows[0]["body_preview"] == "[sensitive – hidden]"
    assert all(i["status"] == "SENT" for i in items)
