from datetime import timedelta

from sqlalchemy import select

from app.database.session import SessionLocal
from app.database.types import utcnow
from app.models import EditPermission, MemberChangeHistory, Notification, Role
from app.services.notifications import process_expired_edit_permissions
from tests.helpers import login, make_user, submitted_application


def _approved_member():
    c, app, user = submitted_application()
    admin_user = make_user(role=Role.ADMIN)
    admin = login(admin_user)
    member_id = admin.post(f"/api/admin/applications/{app['id']}/approve", json={}).json()["member_id"]
    return c, admin, member_id, user, admin_user


def test_member_cannot_edit_without_permission():
    c, *_ = _approved_member()
    r = c.put("/api/members/profile", json={"city": "Hyderabad"})
    assert r.status_code == 403


def test_non_member_cannot_request_edit():
    c = login(make_user())
    assert c.post("/api/members/edit-requests", json={"reason": "Change of address after moving"}).status_code == 403


def test_full_edit_permission_flow(db):
    c, admin, member_id, user, admin_user = _approved_member()
    r = c.post("/api/members/edit-requests", json={"reason": "short"})
    assert r.status_code == 422
    r = c.post("/api/members/edit-requests", json={"reason": "I moved to a new address in Hyderabad."})
    assert r.status_code == 201
    req_id = r.json()["id"]
    # admin was notified (website)
    assert db.scalar(select(Notification).where(Notification.user_id == admin_user.id,
                                                Notification.event == "admin_edit_request"))
    assert c.post("/api/members/edit-requests", json={"reason": "Another request while pending"}).status_code == 409

    r = admin.post(f"/api/admin/edit-requests/{req_id}/approve", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["permission_active"] is True
    start, end = body["permission_starts_at"], body["permission_expires_at"]
    perm = db.scalar(select(EditPermission).where(EditPermission.edit_request_id == req_id))
    assert perm.expires_at - perm.starts_at == timedelta(hours=24)
    assert start and end

    r = c.put("/api/members/profile", json={"city": "Hyderabad", "state": "Telangana", "pincode": "500001"})
    assert r.status_code == 200, r.text
    assert r.json()["city"] == "Hyderabad" and r.json()["edit_permission_active"] is True
    hist = db.scalars(select(MemberChangeHistory).where(MemberChangeHistory.member_id == member_id)).all()
    assert {h.field_name for h in hist} == {"city", "state", "pincode"}
    assert db.scalar(select(Notification).where(Notification.user_id == admin_user.id,
                                                Notification.event == "admin_member_edited"))


def test_introducer_fields_not_member_editable():
    c, admin, member_id, *_ = _approved_member()
    req = c.post("/api/members/edit-requests", json={"reason": "Need to update my occupation"}).json()
    admin.post(f"/api/admin/edit-requests/{req['id']}/approve", json={})
    r = c.put("/api/members/profile", json={"introducer_reg_no": "9999"})
    assert r.status_code == 422


def test_editing_expires_after_24_hours(db):
    c, admin, member_id, user, _ = _approved_member()
    req = c.post("/api/members/edit-requests", json={"reason": "Update phone number please"}).json()
    admin.post(f"/api/admin/edit-requests/{req['id']}/approve", json={})
    assert c.put("/api/members/profile", json={"occupation": "Teacher"}).status_code == 200
    # Simulate the passage of time on the server side
    perm = db.scalar(select(EditPermission).where(EditPermission.edit_request_id == req["id"]))
    perm.starts_at = utcnow() - timedelta(hours=24, minutes=1)
    perm.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    r = c.put("/api/members/profile", json={"occupation": "Doctor"})
    assert r.status_code == 403
    assert c.get("/api/members/me").json()["edit_permission_active"] is False
    # expiry notification is sent once
    assert process_expired_edit_permissions(SessionLocal) == 1
    assert process_expired_edit_permissions(SessionLocal) == 0
    assert db.scalar(select(Notification).where(Notification.user_id == user.id,
                                                Notification.event == "edit_permission_expired"))
    # a new request is required again
    assert c.post("/api/members/edit-requests", json={"reason": "Need another change please"}).status_code == 201


def test_edit_rejection_and_revocation():
    c, admin, *_ = _approved_member()
    req = c.post("/api/members/edit-requests", json={"reason": "Correct my gothram spelling"}).json()
    assert admin.post(f"/api/admin/edit-requests/{req['id']}/reject", json={"note": ""}).status_code == 422
    r = admin.post(f"/api/admin/edit-requests/{req['id']}/reject", json={"note": "Please visit the office"})
    assert r.json()["status"] == "REJECTED"
    assert c.put("/api/members/profile", json={"gothram": "X"}).status_code == 403
    req2 = c.post("/api/members/edit-requests", json={"reason": "Correct my gothram spelling again"}).json()
    admin.post(f"/api/admin/edit-requests/{req2['id']}/approve", json={})
    admin.post(f"/api/admin/edit-requests/{req2['id']}/revoke")
    assert c.put("/api/members/profile", json={"gothram": "Y"}).status_code == 403


def test_member_photo_replacement_only_during_window():
    from tests.helpers import image_bytes
    c, admin, *_ = _approved_member()
    files = {"file": ("new.jpg", image_bytes(), "image/jpeg")}
    assert c.post("/api/members/profile/documents", data={"doc_type": "PHOTO"}, files=files).status_code == 403
    req = c.post("/api/members/edit-requests", json={"reason": "Update to a recent photograph"}).json()
    admin.post(f"/api/admin/edit-requests/{req['id']}/approve", json={})
    files = {"file": ("new.jpg", image_bytes(), "image/jpeg")}
    assert c.post("/api/members/profile/documents", data={"doc_type": "PHOTO"}, files=files).status_code == 201
