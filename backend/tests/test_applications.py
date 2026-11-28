from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from app.models import ApplicationStatus, Member, MemberApplication, MemberProfile, Role
from tests.helpers import (
    REQUIRED_DOCS, create_complete_application, form_payload, image_bytes, login, make_user, submitted_application,
    upload,
)


def _admin():
    return login(make_user(role=Role.ADMIN))


# --- Submission validation ---------------------------------------------------------
def test_complete_submission_goes_pending():
    _, app, _ = submitted_application()
    assert app["status"] == "PENDING"
    assert app["can_edit"] is False
    assert app["submitted_at"] is not None
    assert [h["action"] for h in app["history"]] == ["CREATED", "SUBMITTED"]


@pytest.mark.parametrize("field,label", [("introducer_name", "Introduced by Sri"),
                                         ("introducer_phone", "Introducer Phone No."),
                                         ("introducer_reg_no", "Introducer Registration No.")])
def test_missing_introducer_field_blocks_submission(field, label):
    c = login(make_user())
    app = create_complete_application(c, **{field: None})
    r = c.post(f"/api/applications/{app['id']}/submit")
    assert r.status_code == 422
    errors = r.json()["detail"]["errors"]
    assert errors[field] == f"{label} is mandatory"


def test_blank_introducer_strings_are_treated_as_missing():
    c = login(make_user())
    app = create_complete_application(c, introducer_name="   ", introducer_reg_no="")
    r = c.post(f"/api/applications/{app['id']}/submit")
    assert {"introducer_name", "introducer_reg_no"} <= set(r.json()["detail"]["errors"])


def test_missing_declaration_blocks_submission():
    c = login(make_user())
    app = create_complete_application(c, declaration_accepted=False, declaration_place=None)
    r = c.post(f"/api/applications/{app['id']}/submit")
    errors = r.json()["detail"]["errors"]
    assert "declaration_accepted" in errors and "declaration_place" in errors


def test_missing_photographs_block_submission():
    c = login(make_user())
    app = create_complete_application(c, docs=["ID_PROOF", "APPLICANT_SIGNATURE"])
    r = c.post(f"/api/applications/{app['id']}/submit")
    errors = r.json()["detail"]["errors"]
    assert {"document_PHOTO", "document_ADDITIONAL_PHOTO_1", "document_ADDITIONAL_PHOTO_2"} <= set(errors)


def test_under_18_is_rejected():
    c = login(make_user())
    dob = (date.today() - timedelta(days=365 * 17)).isoformat()
    app = create_complete_application(c, date_of_birth=dob)
    r = c.post(f"/api/applications/{app['id']}/submit")
    assert "18 years" in r.json()["detail"]["errors"]["date_of_birth"]


def test_invalid_aadhaar_and_pincode_rejected():
    c = login(make_user())
    r = c.post("/api/applications", json=form_payload(aadhaar_number="123412341234"))
    assert r.status_code == 422 and "aadhaar_number" in r.json()["detail"]["errors"]
    app = create_complete_application(c, pincode="12")
    r = c.post(f"/api/applications/{app['id']}/submit")
    assert "pincode" in r.json()["detail"]["errors"]


def test_unverified_account_cannot_submit():
    c = login(make_user(verified=False))
    app = create_complete_application(c)
    r = c.post(f"/api/applications/{app['id']}/submit")
    errors = r.json()["detail"]["errors"]
    assert "account_phone" in errors and "account_email" not in errors  # e-mail is not verified


def test_one_open_application_per_user():
    c = login(make_user())
    create_complete_application(c)
    assert c.post("/api/applications", json=form_payload()).status_code == 409


def test_aadhaar_encrypted_at_rest_and_masked_for_applicant(db):
    c = login(make_user())
    payload = form_payload()
    app = create_complete_application(c)
    raw = db.execute(text("SELECT aadhaar_number FROM member_applications WHERE id=:i"), {"i": app["id"]}).scalar()
    assert payload["aadhaar_number"] not in raw
    assert app["aadhaar_masked"].endswith(payload["aadhaar_number"][-4:])
    assert "aadhaar_number" not in app


# --- Uploads -------------------------------------------------------------------------
def test_invalid_uploaded_files_rejected():
    c = login(make_user())
    app = c.post("/api/applications", json=form_payload()).json()
    # wrong extension for a photo
    assert upload(c, app["id"], "PHOTO", b"%PDF-1.4" + b" " * 200, "photo.pdf").status_code == 422
    # spoofed: .jpg name but not an image
    assert upload(c, app["id"], "PHOTO", b"MZ" + b"\x00" * 500, "evil.jpg").status_code == 422
    # executable disguised as pdf
    assert upload(c, app["id"], "ID_PROOF", b"MZ" + b"\x00" * 500, "id.pdf").status_code == 422
    # PDF with JavaScript
    assert upload(c, app["id"], "ID_PROOF", b"%PDF-1.4 /JavaScript (alert(1))" + b" " * 200, "id.pdf").status_code == 422
    # too large
    big = image_bytes(size=(4000, 4000))
    from app.core.config import settings
    if len(big) > settings.MAX_PHOTO_BYTES:
        assert upload(c, app["id"], "PHOTO", big).status_code == 422
    # too small an image
    assert upload(c, app["id"], "PHOTO", image_bytes(size=(20, 20))).status_code == 422
    # valid PNG accepted
    assert upload(c, app["id"], "PHOTO", image_bytes("PNG"), "photo.png").status_code == 201


def test_documents_are_private():
    c, app, user = submitted_application()
    doc_url = app["documents"][0]["url"]
    assert c.get(doc_url).status_code == 200
    assert login(make_user()).get(doc_url).status_code == 404  # other user
    from tests.helpers import new_client
    assert new_client().get(doc_url).status_code == 401  # anonymous
    assert _admin().get(doc_url).status_code == 200


# --- Editing after submission ------------------------------------------------------
def test_user_cannot_edit_after_submission():
    c, app, _ = submitted_application()
    assert c.put(f"/api/applications/{app['id']}", json={"city": "Madurai"}).status_code == 409
    assert upload(c, app["id"], "PHOTO").status_code == 409


# --- Admin review ----------------------------------------------------------------------
def test_admin_approval_creates_member_and_number(db):
    c, app, user = submitted_application()
    admin = _admin()
    detail = admin.get(f"/api/admin/applications/{app['id']}").json()
    assert detail["aadhaar_number"]  # admins can verify the full Aadhaar
    assert len(detail["documents"]) == len(REQUIRED_DOCS)
    r = admin.post(f"/api/admin/applications/{app['id']}/approve",
                   json={"verified_by": "K. Ramanathan", "receipt_number": "R-55", "receipt_date": "2026-11-01",
                         "committee_chairman": "A", "committee_secretary": "B", "committee_president": "C"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "APPROVED"
    number = r.json()["membership_number"]
    assert number == "1"
    member = db.scalar(select(Member).where(Member.membership_number == number))
    assert member.status.value == "ACTIVE" and member.receipt_number == "R-55"
    me = c.get("/api/auth/me").json()
    assert me["membership"]["is_member"] is True and me["membership"]["membership_number"] == number
    assert c.get("/api/members/me").json()["membership_number"] == number


def test_admin_correction_request_and_resubmission():
    c, app, _ = submitted_application()
    admin = _admin()
    r = admin.post(f"/api/admin/applications/{app['id']}/corrections", json={"notes": "short"})
    assert r.status_code == 422  # must describe specific errors
    r = admin.post(f"/api/admin/applications/{app['id']}/corrections",
                   json={"notes": "Father's name does not match the ID proof. Please correct it."})
    assert r.json()["status"] == "CORRECTION_REQUIRED"
    mine = c.get("/api/applications/me").json()
    assert mine["can_edit"] is True and "Father's name" in mine["correction_notes"]
    assert c.put(f"/api/applications/{app['id']}", json={"father_name": "Sri Venkata Rao Garu"}).status_code == 200
    assert c.post(f"/api/applications/{app['id']}/submit").status_code == 409  # must use resubmit
    r = c.post(f"/api/applications/{app['id']}/resubmit")
    assert r.status_code == 200 and r.json()["status"] == "RESUBMITTED"
    queue = admin.get("/api/admin/applications", params={"status": ["PENDING", "RESUBMITTED"]}).json()
    assert any(i["id"] == app["id"] for i in queue["items"])


def test_admin_rejection_does_not_create_member(db):
    c, app, _ = submitted_application()
    admin = _admin()
    assert admin.post(f"/api/admin/applications/{app['id']}/reject", json={"reason": ""}).status_code == 422
    r = admin.post(f"/api/admin/applications/{app['id']}/reject",
                   json={"reason": "Applicant does not belong to the community."})
    assert r.json()["status"] == "REJECTED"
    assert db.scalar(select(Member)) is None
    # Rejected cannot be approved later
    assert admin.post(f"/api/admin/applications/{app['id']}/approve", json={}).status_code == 409
    assert c.get("/api/auth/me").json()["membership"]["is_member"] is False


def test_cannot_review_draft_or_double_approve():
    c = login(make_user())
    draft = create_complete_application(c)
    admin = _admin()
    assert admin.post(f"/api/admin/applications/{draft['id']}/approve", json={}).status_code == 409
    c.post(f"/api/applications/{draft['id']}/submit")
    assert admin.post(f"/api/admin/applications/{draft['id']}/approve", json={}).status_code == 200
    assert admin.post(f"/api/admin/applications/{draft['id']}/approve", json={}).status_code == 409


def test_application_history_is_complete():
    c, app, _ = submitted_application()
    admin = _admin()
    admin.post(f"/api/admin/applications/{app['id']}/corrections", json={"notes": "Please upload a clearer photo."})
    upload(c, app["id"], "PHOTO")
    c.post(f"/api/applications/{app['id']}/resubmit")
    admin.post(f"/api/admin/applications/{app['id']}/approve", json={})
    hist = admin.get(f"/api/admin/applications/{app['id']}").json()["history"]
    assert [h["action"] for h in hist] == ["CREATED", "SUBMITTED", "CORRECTION_REQUESTED", "RESUBMITTED", "APPROVED"]


def test_introducer_check_shows_matching_member():
    admin_user = make_user(role=Role.ADMIN)
    admin = login(admin_user)
    admin.post("/api/admin/members", json={**{k: v for k, v in form_payload().items() if not k.startswith("declaration")
                                              and not k.startswith("introducer")},
                                           "membership_number": "1001", "full_name": "Sri Subramanyam",
                                           "cell": "9840012345", "aadhaar_number": None})
    _, app, _ = submitted_application()
    check = admin.get(f"/api/admin/applications/{app['id']}").json()["introducer_check"]
    assert check == {"registration_number_found": True, "member_name": "Sri Subramanyam",
                     "member_status": "ACTIVE", "phone_matches": True}


def test_admin_list_search_filter_pagination():
    for i in range(3):
        submitted_application(full_name=f"Searchable Person {i}")
    admin = _admin()
    r = admin.get("/api/admin/applications", params={"q": "Searchable", "page_size": 2})
    body = r.json()
    assert body["total"] == 3 and len(body["items"]) == 2 and body["pages"] == 2
    r = admin.get("/api/admin/applications", params={"status": "APPROVED"})
    assert r.json()["total"] == 0


def test_approved_application_record_matches_member(db):
    _, app, _ = submitted_application()
    _admin().post(f"/api/admin/applications/{app['id']}/approve", json={})
    a = db.get(MemberApplication, app["id"])
    assert a.status == ApplicationStatus.APPROVED
    m = db.scalar(select(Member).where(Member.application_id == a.id))
    profile = db.get(MemberProfile, m.member_profile_id)
    assert profile.full_name == a.full_name and profile.aadhaar_number == a.aadhaar_number
