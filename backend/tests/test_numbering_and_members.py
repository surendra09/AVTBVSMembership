import threading

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models import Member, MemberSource, Role, User
from app.services import membership as svc
from app.services import numbering
from tests.helpers import form_payload, login, make_user, submitted_application


def _manual_payload(number: str, **kw) -> dict:
    data = {k: v for k, v in form_payload().items() if not k.startswith("declaration")}
    data.update({"membership_number": number, "aadhaar_number": None, **kw})
    return data


def test_numbers_are_sequential_and_skip_manual_numbers(db):
    admin = login(make_user(role=Role.ADMIN))
    # an existing paper member already holds number 2
    assert admin.post("/api/admin/members", json=_manual_payload("2", full_name="Old Member")).status_code == 201
    numbers = []
    for _ in range(3):
        _, app, _ = submitted_application()
        numbers.append(admin.post(f"/api/admin/applications/{app['id']}/approve", json={}).json()["membership_number"])
    assert numbers == ["1", "3", "4"]


def test_custom_template(monkeypatch, db):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MEMBERSHIP_NUMBER_TEMPLATE", "{prefix}{year}/{seq:04d}")
    monkeypatch.setattr(settings, "MEMBERSHIP_NUMBER_PREFIX", "AV/")
    assert numbering.format_membership_number(7).endswith("/0007")
    assert numbering.format_membership_number(7).startswith("AV/")


def test_concurrent_approvals_never_duplicate(db):
    admin_user = make_user(role=Role.ADMIN)
    apps = [submitted_application()[1]["id"] for _ in range(8)]
    errors = []

    def approve(app_id):
        try:
            with SessionLocal() as s:
                admin = s.get(User, admin_user.id)
                svc.approve_application(s, app_id, admin, {}, None, None)
                s.commit()
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=approve, args=(a,)) for a in apps]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    nums = db.scalars(select(Member.membership_number)).all()
    assert len(nums) == 8 and len(set(nums)) == 8
    assert sorted(int(n) for n in nums) == list(range(1, 9))


def test_no_number_for_pending_applications(db):
    submitted_application()
    assert db.scalar(select(func.count()).select_from(Member)) == 0


def test_manual_member_addition_requires_unique_number(db):
    admin = login(make_user(role=Role.ADMIN))
    r = admin.post("/api/admin/members", json=_manual_payload("AVT-0042"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ACTIVE" and body["source"] == "MANUAL_ENTRY" and body["linked_user_id"] is None
    r = admin.post("/api/admin/members", json=_manual_payload("AVT-0042", full_name="Someone Else"))
    assert r.status_code == 422 and "membership_number" in r.json()["detail"]["errors"]
    assert admin.get("/api/admin/members/check-number", params={"number": "AVT-0042"}).json()["exists"] is True
    m = db.scalar(select(Member).where(Member.membership_number == "AVT-0042"))
    assert m.source == MemberSource.MANUAL_ENTRY


def test_manual_member_does_not_need_introducer():
    admin = login(make_user(role=Role.ADMIN))
    r = admin.post("/api/admin/members", json=_manual_payload("77", introducer_name=None, introducer_phone=None,
                                                              introducer_reg_no=None))
    assert r.status_code == 201


def test_link_manual_member_to_account():
    admin = login(make_user(role=Role.ADMIN))
    member = admin.post("/api/admin/members", json=_manual_payload("500")).json()
    user = make_user()
    r = admin.post(f"/api/admin/members/{member['member_id']}/link-account", json={"email": user.email})
    assert r.status_code == 200 and r.json()["linked_user_email"] == user.email
    me = login(user).get("/api/auth/me").json()
    assert me["membership"]["is_member"] is True and me["membership"]["membership_number"] == "500"
    # cannot link twice
    assert admin.post(f"/api/admin/members/{member['member_id']}/link-account",
                      json={"email": make_user().email}).status_code == 409


def test_deactivate_member_removes_directory_access():
    c, app, user = submitted_application()
    admin = login(make_user(role=Role.ADMIN))
    member_id = admin.post(f"/api/admin/applications/{app['id']}/approve", json={}).json()["member_id"]
    assert c.get("/api/members").status_code == 200
    assert admin.patch(f"/api/admin/members/{member_id}/status", json={"status": "INACTIVE"}).status_code == 422
    r = admin.patch(f"/api/admin/members/{member_id}/status", json={"status": "INACTIVE", "reason": "Deceased"})
    assert r.status_code == 200 and r.json()["status"] == "INACTIVE"
    assert c.get("/api/members").status_code == 403
    assert login(make_user()).get("/api/members/public").json()["total"] == 0


def test_admin_edit_member_records_history():
    admin = login(make_user(role=Role.ADMIN))
    member = admin.post("/api/admin/members", json=_manual_payload("900")).json()
    r = admin.put(f"/api/admin/members/{member['member_id']}", json={"city": "Vellore", "receipt_number": "R-9"})
    assert r.status_code == 200
    fields = {h["field"] for h in r.json()["change_history"]}
    assert {"city", "office:receipt_number"} <= fields


def test_reports_and_csv_export():
    admin = login(make_user(role=Role.ADMIN))
    admin.post("/api/admin/members", json=_manual_payload("12"))
    r = admin.get("/api/admin/reports/summary")
    assert r.status_code == 200 and r.json()["members_by_source"]["MANUAL_ENTRY"] == 1
    csv = admin.get("/api/admin/reports/members.csv")
    assert csv.status_code == 200 and "Membership No." in csv.text
    assert form_payload()["aadhaar_number"] not in csv.text
