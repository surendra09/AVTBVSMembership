import pytest

from app.models import Role
from tests.helpers import form_payload, login, make_user, new_client, submitted_application

PRIVATE_KEYS = {"photo_url", "cell", "phone", "email", "address_line1", "aadhaar_number", "aadhaar_masked",
                "date_of_birth", "blood_group", "introducer_name", "membership_number", "documents", "gothram"}


def _approved(name="Directory Person"):
    c, app, user = submitted_application(full_name=name)
    admin = login(make_user(role=Role.ADMIN))
    r = admin.post(f"/api/admin/applications/{app['id']}/approve", json={})
    return c, r.json()["member_id"]


def test_public_directory_exposes_only_name_and_father_name():
    _approved()
    r = new_client().get("/api/members/public")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert set(item) == {"id", "full_name", "father_name"}
    assert not PRIVATE_KEYS & set(item)


def test_public_directory_search_does_not_match_private_fields():
    _approved()
    # membership number search is a member-only feature
    assert new_client().get("/api/members/public", params={"q": "1"}).json()["total"] == 0
    assert new_client().get("/api/members/public", params={"q": "Directory"}).json()["total"] == 1


def test_visitor_and_non_member_cannot_access_full_directory():
    _, member_id = _approved()
    assert new_client().get("/api/members").status_code == 401
    assert new_client().get(f"/api/members/{member_id}").status_code == 401
    non_member = login(make_user())
    assert non_member.get("/api/members").status_code == 403
    assert non_member.get(f"/api/members/{member_id}").status_code == 403
    # applicant with a pending application is still not a member
    pending_client, _, _ = submitted_application()
    assert pending_client.get("/api/members").status_code == 403


def test_member_gets_full_directory_but_never_aadhaar_or_documents():
    c, member_id = _approved()
    r = c.get("/api/members")
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["membership_number"] == "1" and item["photo_url"] and item["cell"]
    for forbidden in ("aadhaar_number", "aadhaar_masked", "documents", "date_of_birth", "introducer_name",
                      "introducer_reg_no", "receipt_number"):
        assert forbidden not in item
    assert c.get(item["photo_url"]).status_code == 200


def test_member_consent_hides_contact_and_address():
    c, app, _ = submitted_application(show_contact_in_directory=False, show_address_in_directory=False)
    login(make_user(role=Role.ADMIN)).post(f"/api/admin/applications/{app['id']}/approve", json={})
    item = c.get("/api/members").json()["items"][0]
    assert item["cell"] is None and item["email"] is None and item["address_line1"] is None


def test_non_member_cannot_view_member_photos_or_id_documents():
    c, member_id = _approved()
    item = c.get("/api/members").json()["items"][0]
    me = c.get("/api/members/me").json()
    id_doc = next(d for d in me["documents"] if d["doc_type"] == "ID_PROOF")
    outsider = login(make_user())
    assert outsider.get(item["photo_url"]).status_code == 404
    # even another member cannot see someone else's ID proof
    c2, _ = _approved("Second Person")
    assert c2.get(id_doc["url"]).status_code == 404
    assert c2.get(item["photo_url"]).status_code == 200


@pytest.mark.parametrize("method,url", [
    ("get", "/api/admin/dashboard"), ("get", "/api/admin/applications"), ("get", "/api/admin/members"),
    ("post", "/api/admin/applications/1/approve"), ("get", "/api/admin/edit-requests"),
    ("get", "/api/super-admin/admins"), ("post", "/api/super-admin/admins"),
])
def test_member_cannot_access_admin_endpoints(method, url):
    c, _ = _approved()
    r = getattr(c, method)(url, **({"json": {}} if method == "post" else {}))
    assert r.status_code == 403


@pytest.mark.parametrize("url", ["/api/admin/dashboard", "/api/super-admin/admins", "/api/notifications",
                                 "/api/applications/me", "/api/members/me"])
def test_unauthenticated_calls_get_401(url):
    assert new_client().get(url).status_code == 401


def test_admin_cannot_create_admins():
    admin = login(make_user(role=Role.ADMIN))
    r = admin.post("/api/super-admin/admins", json={"full_name": "New Admin", "email": "na@example.org",
                                                    "phone": "9123456780", "temporary_password": "Strong-pass-123"})
    assert r.status_code == 403
    assert admin.post("/api/super-admin/admins/promote", json={"email": "x@example.org"}).status_code == 403


def test_admin_cannot_apply_for_membership():
    admin = login(make_user(role=Role.ADMIN))
    assert admin.post("/api/applications", json=form_payload()).status_code == 403


def test_applicant_cannot_see_others_applications():
    _, app, _ = submitted_application()
    other = login(make_user())
    assert other.get(f"/api/applications/{app['id']}").status_code == 404
    assert other.put(f"/api/applications/{app['id']}", json={"city": "X"}).status_code == 404


def test_user_cannot_set_office_use_fields():
    c = login(make_user())
    r = c.post("/api/applications", json={**form_payload(), "receipt_number": "R-1", "verified_by": "Me",
                                          "status": "APPROVED", "membership_number": "1"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "DRAFT" and body["membership_number"] is None
    assert "receipt_number" not in body
