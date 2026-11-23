"""Private file storage with strict content validation.

Files live in PRIVATE_STORAGE_DIR, which is never served directly by Nginx or
FastAPI's static handler. Every download goes through an authorised endpoint.
Images are re-encoded (which strips EXIF/GPS metadata and any appended payload).
"""
import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.models.enums import DocumentType

Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
PDF_TYPE = "application/pdf"
IMAGE_EXT = {".jpg", ".jpeg", ".png"}

# Allowed formats per document type
ALLOWED: dict[DocumentType, set[str]] = {
    DocumentType.PHOTO: IMAGE_EXT,
    DocumentType.ADDITIONAL_PHOTO_1: IMAGE_EXT,
    DocumentType.ADDITIONAL_PHOTO_2: IMAGE_EXT,
    DocumentType.ID_PROOF: IMAGE_EXT | {".pdf"},
    DocumentType.APPLICANT_SIGNATURE: IMAGE_EXT,
    DocumentType.INTRODUCER_SIGNATURE: IMAGE_EXT,
}


@dataclass
class StoredFile:
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: str
    original_filename: str


def _root() -> Path:
    root = Path(settings.PRIVATE_STORAGE_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_name(name: str | None) -> str:
    base = os.path.basename(name or "upload")
    cleaned = "".join(c for c in base if c.isalnum() or c in "._- ")[:120]
    return cleaned or "upload"


def _max_bytes(doc_type: DocumentType) -> int:
    return settings.MAX_DOCUMENT_BYTES if doc_type == DocumentType.ID_PROOF else settings.MAX_PHOTO_BYTES


def _bad(msg: str) -> HTTPException:
    return HTTPException(422, msg)


async def validate_and_store(upload: UploadFile, doc_type: DocumentType) -> StoredFile:
    original = _safe_name(upload.filename)
    ext = Path(original).suffix.lower()
    allowed = ALLOWED[doc_type]
    if ext not in allowed:
        raise _bad(f"{doc_type.value}: allowed file types are {', '.join(sorted(e.upper()[1:] for e in allowed))}")

    limit = _max_bytes(doc_type)
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise _bad(f"File is too large. Maximum size is {limit // (1024 * 1024)} MB")
    if len(data) < 100:
        raise _bad("File is empty or corrupted")

    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise _bad("The file is not a valid PDF")
        lowered = data.lower()
        if b"/javascript" in lowered or b"/js " in lowered or b"/launch" in lowered:
            raise _bad("PDF files containing scripts are not accepted")
        content, content_type, out_ext = data, PDF_TYPE, ".pdf"
    else:
        try:
            with Image.open(io.BytesIO(data)) as probe:
                probe.verify()
            img = Image.open(io.BytesIO(data))
            fmt = (img.format or "").upper()
            if fmt not in ("JPEG", "PNG"):
                raise _bad("Only JPG, JPEG and PNG images are accepted")
            if img.width < 80 or img.height < 80:
                raise _bad("Image is too small; please upload a clearer image")
            img.load()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
            raise _bad("The file is not a valid image") from None
        buf = io.BytesIO()
        if fmt == "PNG":
            img.save(buf, format="PNG", optimize=True)
            content_type, out_ext = "image/png", ".png"
        else:
            img.convert("RGB").save(buf, format="JPEG", quality=90)
            content_type, out_ext = "image/jpeg", ".jpg"
        content = buf.getvalue()

    key = f"{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}{out_ext}"
    path = _root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content)
    os.chmod(path, 0o600)
    return StoredFile(key, content_type, len(content), hashlib.sha256(content).hexdigest(), original)


def resolve_path(storage_key: str) -> Path:
    root = _root()
    path = (root / storage_key).resolve()
    if root not in path.parents:  # path traversal guard
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return path


def delete_file(storage_key: str) -> None:
    try:
        resolve_path(storage_key).unlink(missing_ok=True)
    except HTTPException:
        pass
