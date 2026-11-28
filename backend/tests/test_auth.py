import json
import os

from sqlalchemy import select

from app.core.crypto import sha256_hex
from app.models import OtpCode, OtpPurpose, User
from app.utils.validators import is_valid_aadhaar
from tests.helpers import PASSWORD, make_user, new_client, unique_phone, valid_aadhaar


def _outbox():
    path = os.environ["CONSOLE_OUTBOX_FILE"]
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _register(c, **kw):
    body = {"full_name": "Lakshmi Devi", "email": "lakshmi@example.org", "phone": unique_phone(), "password": PASSWORD}
    body.update(kw)
    return c.post("/api/auth/register", json=body)


def test_verhoeff_helper():
    assert all(is_valid_aadhaar(valid_aadhaar(i)) for i in range(20))
    assert not is_valid_aadhaar("123456789012")


def test_register_creates_user_not_member_and_logs_in():
    c = new_client()
    r = _register(c)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["role"] == "USER"
    assert body["membership"]["is_member"] is False
    assert body["user"]["email_verified"] is False
    assert c.get("/api/auth/me").status_code == 200


def test_register_duplicate_email_and_phone(db):
    c = new_client()
    phone = unique_phone()
    assert _register(c, phone=phone).status_code == 201
    r = _register(new_client(), phone=phone)
    assert r.status_code == 422
    assert set(r.json()["detail"]["errors"]) == {"email", "phone"}


def test_register_rejects_weak_password():
    r = _register(new_client(), password="short")
    assert r.status_code == 422
    assert "password" in r.json()["detail"]["errors"]


def test_password_is_hashed_with_argon2(db):
    _register(new_client(), email="hash@example.org")
    user = db.scalar(select(User).where(User.email == "hash@example.org"))
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_login_with_email_and_phone_and_invalid_credentials():
    user = make_user()
    assert new_client().post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD}).status_code == 200
    assert new_client().post("/api/auth/login", json={"identifier": user.phone, "password": PASSWORD}).status_code == 200
    r = new_client().post("/api/auth/login", json={"identifier": user.email, "password": "wrong-password-1"})
    assert r.status_code == 401
    r = new_client().post("/api/auth/login", json={"identifier": "nobody@example.org", "password": PASSWORD})
    assert r.status_code == 401


def test_login_sets_httponly_cookies():
    user = make_user()
    c = new_client()
    r = c.post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    cookies = r.headers.get_list("set-cookie")
    access = next(h for h in cookies if h.startswith("avtbvs_access="))
    refresh = next(h for h in cookies if h.startswith("avtbvs_refresh="))
    assert "HttpOnly" in access and "HttpOnly" in refresh
    assert "samesite=lax" in access.lower()


def test_deactivated_user_cannot_login():
    user = make_user(active=False)
    r = new_client().post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    assert r.status_code == 403


def test_register_without_email():
    c = new_client()
    r = _register(c, email="")
    assert r.status_code == 201 and r.json()["user"]["email"] is None
    assert _register(new_client(), email=None).status_code == 201  # several accounts may omit e-mail
    c2 = new_client()
    phone = r.json()["user"]["phone"]
    assert c2.post("/api/auth/login", json={"identifier": phone, "password": PASSWORD}).status_code == 200


def test_phone_verification_with_otp_and_no_email_code(db):
    c = new_client()
    _register(c, email="otp@example.org")
    from tests.test_notifications import run_worker  # worker is not auto-running in tests
    run_worker()
    messages = _outbox()
    assert not any(m["channel"] == "EMAIL" and m["to"] == "otp@example.org" and "verification code" in m["body"]
                   for m in messages)
    sms_msg = next(m for m in messages if m["channel"] == "SMS" and "verification code" in m["body"])
    import re
    sms_code = re.search(r"(\d{6})", sms_msg["body"]).group(1)
    r = c.post("/api/auth/verify-phone", json={"code": sms_code})
    assert r.status_code == 200 and r.json()["user"]["phone_verified"] is True


def test_otp_locks_after_max_attempts(db):
    c = new_client()
    _register(c, email="lock@example.org")
    user = db.scalar(select(User).where(User.email == "lock@example.org"))
    otp = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == OtpPurpose.PHONE_VERIFY))
    for _ in range(5):
        assert c.post("/api/auth/verify-phone", json={"code": "999999"}).status_code == 400
    db.expire_all()
    otp = db.get(OtpCode, otp.id)
    assert otp.attempts >= 5


def test_password_reset_flow(db):
    user = make_user()
    c = new_client()
    r = c.post("/api/auth/forgot-password", json={"email": user.email})
    assert r.status_code == 200
    # unknown email gives the identical response (no enumeration)
    r2 = c.post("/api/auth/forgot-password", json={"email": "unknown@example.org"})
    assert r2.json() == r.json()
    from tests.test_notifications import run_worker
    run_worker()
    msg = next(m for m in _outbox() if m["to"] == user.email and "reset-password?token=" in m["body"])
    token = msg["body"].split("token=")[1].split()[0]
    assert db.scalar(select(OtpCode).where(OtpCode.code_hash == sha256_hex(token))) is not None
    r = c.post("/api/auth/reset-password", json={"token": token, "new_password": "Brand-new-pass-42"})
    assert r.status_code == 200
    # token is single-use
    assert c.post("/api/auth/reset-password", json={"token": token, "new_password": "Another-pass-42"}).status_code == 400
    assert new_client().post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD}).status_code == 401
    assert new_client().post("/api/auth/login",
                             json={"identifier": user.email, "password": "Brand-new-pass-42"}).status_code == 200


def test_refresh_rotation_and_reuse_detection():
    user = make_user()
    c = new_client()
    c.post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    old_refresh = c.cookies.get("avtbvs_refresh")
    r = c.post("/api/auth/refresh")
    assert r.status_code == 200
    assert c.cookies.get("avtbvs_refresh") != old_refresh
    # replaying the old refresh token is rejected and revokes the session family
    attacker = new_client()
    attacker.cookies.set("avtbvs_refresh", old_refresh, path="/api/auth")
    attacker.cookies.set("avtbvs_csrf", "x")
    r = attacker.post("/api/auth/refresh", headers={"X-CSRF-Token": "x"})
    assert r.status_code == 401
    assert c.post("/api/auth/refresh").status_code == 401


def test_logout_clears_session():
    user = make_user()
    c = new_client()
    c.post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_csrf_required_for_cookie_authenticated_writes():
    user = make_user()
    c = new_client()
    c.post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    # bypass the helper's automatic header
    from fastapi.testclient import TestClient
    r = TestClient.request(c, "POST", "/api/notifications/read-all")
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]


def test_bearer_token_works_for_api_clients():
    user = make_user()
    r = new_client().post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    token = r.json()["access_token"]
    bare = new_client()
    assert bare.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_login_rate_limit(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "3/60")
    c = new_client()
    codes = [c.post("/api/auth/login", json={"identifier": "x@example.org", "password": "bad-pass-123"}).status_code
             for _ in range(4)]
    assert codes[:3] == [401, 401, 401] and codes[3] == 429
