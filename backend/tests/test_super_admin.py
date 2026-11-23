from sqlalchemy import select

from app.models import AuditLog, Role, User
from tests.helpers import login, make_user, new_client


def _super():
    u = make_user(role=Role.SUPER_ADMIN)
    return login(u), u


def test_super_admin_creates_admin_with_temporary_password(db):
    c, sa = _super()
    r = c.post("/api/super-admin/admins", json={"full_name": "New Admin", "email": "newadmin@example.org",
                                                "phone": "9123456780", "temporary_password": "Strong-pass-123"})
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "ADMIN" and r.json()["created_by_name"] == sa.full_name
    new = new_client()
    assert new.post("/api/auth/login", json={"identifier": "newadmin@example.org",
                                             "password": "Strong-pass-123"}).status_code == 200
    assert new.get("/api/admin/dashboard").status_code == 200
    assert new.get("/api/super-admin/admins").status_code == 403
    assert db.scalar(select(AuditLog).where(AuditLog.action == "admin.create"))


def test_super_admin_creates_admin_with_invitation(db):
    c, _ = _super()
    r = c.post("/api/super-admin/admins", json={"full_name": "Invited", "email": "invited@example.org",
                                                "phone": "9123456781"})
    assert r.status_code == 201
    u = db.scalar(select(User).where(User.email == "invited@example.org"))
    assert u.password_hash is None  # cannot log in until invitation link is used


def test_convert_existing_member_into_admin():
    c, _ = _super()
    user = make_user()
    r = c.post("/api/super-admin/admins/promote", json={"email": user.email})
    assert r.status_code == 200 and r.json()["role"] == "ADMIN"
    assert login(user).get("/api/admin/dashboard").status_code == 200
    assert c.post("/api/super-admin/admins/promote", json={"email": user.email}).status_code == 409


def test_activate_deactivate_admin():
    c, _ = _super()
    admin = make_user(role=Role.ADMIN)
    r = c.patch(f"/api/super-admin/admins/{admin.id}/status", json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    from tests.helpers import PASSWORD
    assert new_client().post("/api/auth/login", json={"identifier": admin.email, "password": PASSWORD}).status_code == 403
    assert c.patch(f"/api/super-admin/admins/{admin.id}/status", json={"is_active": True}).json()["is_active"] is True


def test_last_super_admin_is_protected():
    c, sa = _super()
    assert c.patch(f"/api/super-admin/admins/{sa.id}/status", json={"is_active": False}).status_code == 409
    assert c.put(f"/api/super-admin/admins/{sa.id}", json={"role": "ADMIN"}).status_code == 409
    other = make_user(role=Role.SUPER_ADMIN)
    # with a second super admin, demotion becomes possible
    assert c.put(f"/api/super-admin/admins/{other.id}", json={"role": "ADMIN"}).status_code == 200
    assert c.put(f"/api/super-admin/admins/{sa.id}", json={"role": "ADMIN"}).status_code == 409


def test_super_admin_has_all_admin_permissions():
    c, _ = _super()
    for url in ("/api/admin/dashboard", "/api/admin/applications", "/api/admin/members", "/api/admin/edit-requests",
                "/api/admin/reports/summary", "/api/admin/notification-deliveries"):
        assert c.get(url).status_code == 200, url


def test_audit_logs_and_dashboard():
    c, _ = _super()
    c.post("/api/super-admin/admins", json={"full_name": "Audited", "email": "aud@example.org", "phone": "9123456782",
                                            "temporary_password": "Strong-pass-123"})
    logs = c.get("/api/super-admin/audit-logs", params={"admin_only": True}).json()
    assert any(i["action"] == "admin.create" for i in logs["items"])
    dash = c.get("/api/super-admin/dashboard").json()
    assert dash["total_admins"] == 2 and dash["recent_admin_activity"]


def test_settings_and_sequence():
    c, _ = _super()
    s = c.get("/api/super-admin/settings").json()
    assert s["membership_numbering"]["template"] == "{seq}"
    r = c.put("/api/super-admin/settings/membership-sequence", json={"next_value": 5000})
    assert r.json()["examples"][0] == "5000"


def test_cli_bootstrap_refuses_second_super_admin(monkeypatch, capsys):
    from app import cli
    monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "Bootstrap-pass-123")
    args = type("A", (), {"name": "Root", "email": "root@example.org", "phone": "9000000001",
                          "allow_additional": False})
    assert cli.create_super_admin(args) == 0
    args.email, args.phone = "root2@example.org", "9000000002"
    assert cli.create_super_admin(args) == 1
    assert new_client().post("/api/auth/login", json={"identifier": "root@example.org",
                                                      "password": "Bootstrap-pass-123"}).status_code == 200
