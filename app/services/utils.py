"""Shared utility helpers: slugs, reading time, uploads, password strength."""

from __future__ import annotations

import os
import re
import secrets
import unicodedata
from datetime import datetime, timezone

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_length: int = 200) -> str:
    """Turn arbitrary text into a URL-safe slug (ASCII, lowercase)."""
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = _SLUG_STRIP.sub("-", value.lower()).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return value[:max_length].strip("-") or "document"


def unique_slug(model, base: str, exclude_id: int | None = None) -> str:
    """Return a unique slug for ``model`` based on ``base`` text."""
    candidate = slugify(base)
    suffix = 1
    while True:
        query = model.query.filter(model.slug == candidate)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if query.first() is None:
            return candidate
        suffix += 1
        candidate = f"{slugify(base, max_length=210)}-{suffix}"


# ---------------------------------------------------------------------------
# Reading time / formatting
# ---------------------------------------------------------------------------
def reading_time_minutes(text: str) -> int:
    """Estimated reading time: 200 words per minute, minimum 1 minute."""
    words = len(re.findall(r"\b\w+\b", text or ""))
    return max(1, round(words / 200))


def time_ago(dt: datetime | None) -> str:
    """Human-friendly relative time ("3 hours ago")."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = months // 12
    return f"{years} year{'s' if years != 1 else ''} ago"


def format_number(n: int) -> str:
    """1234 -> 1.2k for compact display."""
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


# ---------------------------------------------------------------------------
# Secure image uploads
# ---------------------------------------------------------------------------
_MAGIC_SIGNATURES = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "gif": [b"GIF87a", b"GIF89a"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


def validate_image_upload(file: FileStorage) -> tuple[str | None, str | None]:
    """Validate an uploaded image.

    Returns ``(extension, None)`` on success or ``(None, error_message)``.
    Checks extension, MIME type, magic bytes and size.
    """
    if file is None or not file.filename:
        return None, "No file selected."
    allowed_ext = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    allowed_mime = current_app.config["ALLOWED_IMAGE_MIMES"]

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_ext:
        return None, f"Unsupported file type. Allowed: {', '.join(sorted(allowed_ext))}."

    mimetype = (file.mimetype or "").lower()
    if mimetype not in allowed_mime:
        return None, "File content type does not match an allowed image format."

    # Magic-byte sniffing so an .exe renamed to .png is rejected.
    file.seek(0)
    head = file.read(16)
    file.seek(0)
    signatures = _MAGIC_SIGNATURES.get(ext, [])
    if signatures and not any(head.startswith(sig) for sig in signatures):
        return None, "File content does not match its extension."

    max_bytes = current_app.config["MAX_CONTENT_LENGTH"]
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > max_bytes:
        return None, f"File too large (max {max_bytes // (1024 * 1024)} MB)."
    if size == 0:
        return None, "File is empty."
    return ext, None


def save_image_upload(file: FileStorage, subdir: str) -> str:
    """Save a validated upload under ``static/uploads/<subdir>`` with a random name.

    Returns the URL path relative to ``/static`` (served as ``/static/<path>``).
    """
    ext, error = validate_image_upload(file)
    if error:
        raise ValueError(error)
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    name = f"{secrets.token_hex(16)}.{ext}"
    file.save(os.path.join(folder, name))
    return f"uploads/{subdir}/{name}"


def delete_uploaded(relative_path: str, subdir: str) -> None:
    """Best-effort deletion of a previously stored upload."""
    if not relative_path:
        return
    base = os.path.abspath(os.path.join(current_app.config["UPLOAD_FOLDER"], subdir))
    target = os.path.abspath(os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path))
    if not target.startswith(base + os.sep):
        return
    try:
        if os.path.isfile(target):
            os.remove(target)
    except OSError:  # pragma: no cover - deletion is best effort
        current_app.logger.warning("Could not delete upload %s", target)


# ---------------------------------------------------------------------------
# Password strength
# ---------------------------------------------------------------------------
def password_strength(password: str) -> dict:
    """Score a password 0-4 with human-readable feedback."""
    password = password or ""
    checks = {
        "length": len(password) >= 8,
        "long": len(password) >= 12,
        "upper": bool(re.search(r"[A-Z]", password)),
        "digit": bool(re.search(r"\d", password)),
        "symbol": bool(re.search(r"[^\w\s]", password)),
    }
    score = sum(1 for key in ("length", "upper", "digit", "symbol") if checks[key])
    if checks["long"] and score >= 3:
        score = 4
    labels = ["Very weak", "Weak", "Fair", "Strong", "Very strong"]
    hints = []
    if not checks["length"]:
        hints.append("Use at least 8 characters.")
    if not checks["upper"]:
        hints.append("Add an uppercase letter.")
    if not checks["digit"]:
        hints.append("Add a number.")
    if not checks["symbol"]:
        hints.append("Add a symbol (!@#…).")
    return {"score": min(score, 4), "label": labels[min(score, 4)], "hints": hints}


def is_strong_password(password: str) -> bool:
    """Server-side policy: >=8 chars with at least 3 character classes."""
    if len(password or "") < 8:
        return False
    classes = sum(
        bool(re.search(pattern, password))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w\s]")
    )
    return classes >= 3


def random_token(bytes_len: int = 32) -> str:
    """Cryptographically strong hex token (e-mail verification / resets)."""
    return secrets.token_hex(bytes_len)
