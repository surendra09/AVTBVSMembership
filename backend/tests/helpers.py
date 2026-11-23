import io
import itertools
from datetime import date

from fastapi.testclient import TestClient
from PIL import Image

from app.core.security import CSRF_COOKIE, hash_password
from app.database.session import SessionLocal
from app.database.types import utcnow
from app.main import app
from app.models import Role, User
from app.utils.validators import _D, _P

PASSWORD = "Secret-pass-123"
_counter = itertools.count(1)
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


class Client(TestClient):
    """TestClient that echoes the CSRF cookie like the React app does."""

    def request(self, method, url, **kwargs):
        if method.upper() not in ("GET", "HEAD", "OPTIONS"):
            token = self.cookies.get(CSRF_COOKIE)
            if token:
                headers = dict(kwargs.pop("headers", None) or {})
                headers.setdefault("X-CSRF-Token", token)
                kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def new_client() -> Client:
    return Client(app, base_url="http://testserver")


def valid_aadhaar(seed: int = 0) -> str:
    base = f"{234567890 + seed:011d}"[-11:]
    base = "2" + base[1:]
    c = 0
    for i, ch in enumerate(reversed(base)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return base + str(_INV[c])


def unique_phone() -> str:
    return f"98{next(_counter):08d}"


def make_user(role: Role = Role.USER, verified: bool = True, name: str | None = None, active: bool = True) -> User:
    n = next(_counter)
    with SessionLocal() as db:
        u = User(full_name=name or f"Test User {n}", email=f"user{n}@example.org", phone=unique_phone(),
                 password_hash=hash_password(PASSWORD), role=role, is_active=active,
                 email_verified_at=utcnow() if verified else None, phone_verified_at=utcnow() if verified else None)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u


def login(user: User, client: Client | None = None) -> Client:
    c = client or new_client()
    r = c.post("/api/auth/login", json={"identifier": user.email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def image_bytes(fmt: str = "JPEG", size=(300, 380), color=(120, 140, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def pdf_bytes() -> bytes:
    return (b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [] "
            b"/Count 0 >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n" + b" " * 200)


def form_payload(**overrides) -> dict:
    data = {
        "full_name": "Ramesh Kumar", "father_name": "Sri Venkata Rao", "address_line1": "12, Kalappachari Street",
        "address_line2": "Park Town", "city": "Chennai", "state": "Tamil Nadu", "country": "India",
        "pincode": "600003", "aadhaar_number": valid_aadhaar(), "blood_group": "B+",
        "date_of_birth": "1985-04-12", "phone": "04425330821", "centre_x_no": "25", "cell": "9876543210",
        "email": "ramesh@example.org", "whatsapp_facebook": "9876543210", "family_surname": "Kottapalli",
        "gothram": "Kasyapa", "natchathiram": "Rohini", "occupation": "Merchant",
        "occupation_address": "45, Mint Street, Chennai", "native_place_address": "Nellore, Andhra Pradesh",
        "introducer_name": "Sri Subramanyam", "introducer_phone": "9840012345", "introducer_reg_no": "1001",
        "declaration_accepted": True, "declaration_place": "Chennai", "declaration_date": date.today().isoformat(),
    }
    data.update(overrides)
    return data


REQUIRED_DOCS = ["PHOTO", "ID_PROOF", "ADDITIONAL_PHOTO_1", "ADDITIONAL_PHOTO_2", "APPLICANT_SIGNATURE"]


def upload(c: Client, app_id: int, doc_type: str, content: bytes | None = None, filename: str | None = None):
    content = content if content is not None else (pdf_bytes() if doc_type == "ID_PROOF" else image_bytes())
    filename = filename or ("id.pdf" if doc_type == "ID_PROOF" else "photo.jpg")
    mime = "application/pdf" if filename.endswith(".pdf") else "image/jpeg"
    return c.post(f"/api/applications/{app_id}/documents", data={"doc_type": doc_type},
                  files={"file": (filename, content, mime)})


def create_complete_application(c: Client, docs=REQUIRED_DOCS, **overrides) -> dict:
    r = c.post("/api/applications", json=form_payload(**overrides))
    assert r.status_code == 201, r.text
    app = r.json()
    for d in docs:
        assert upload(c, app["id"], d).status_code == 201
    return app


def submitted_application(user: User | None = None, **overrides) -> tuple[Client, dict, User]:
    user = user or make_user()
    c = login(user)
    app = create_complete_application(c, **overrides)
    r = c.post(f"/api/applications/{app['id']}/submit")
    assert r.status_code == 200, r.text
    return c, r.json(), user
