"""Server-side validation for JSON API payloads."""

from __future__ import annotations

import re

from .utils import is_strong_password, slugify

MAX_CONTENT_CHARS = 500_000
MAX_TAGS = 8
ALLOWED_VISIBILITY = ("public", "unlisted")
ALLOWED_STATUS = ("draft", "published")
REPORT_REASONS = ("spam", "plagiarism", "harassment", "misinformation", "other")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_document_payload(data: dict, partial: bool = False) -> tuple[dict, dict]:
    """Validate the create/update payload for a document.

    Returns ``(clean_data, errors)``. When ``partial`` is true only the keys
    that are present are validated (used by autosave).
    """
    clean: dict = {}
    errors: dict[str, list[str]] = {}

    def check_str(key: str, min_len: int, max_len: int, label: str, required: bool = True):
        if key not in data:
            if required and not partial:
                errors.setdefault(key, []).append(f"{label} is required.")
            return
        value = data.get(key)
        if value is None:
            value = ""
        if not isinstance(value, str):
            errors.setdefault(key, []).append(f"{label} must be text.")
            return
        value = value.strip()
        if required and len(value) < min_len:
            errors.setdefault(key, []).append(
                f"{label} must be at least {min_len} characters."
            )
            return
        if len(value) > max_len:
            errors.setdefault(key, []).append(
                f"{label} must be {max_len} characters or fewer."
            )
            return
        clean[key] = value

    # Title / summary / content
    check_str("title", 3, 200, "Title")
    check_str("summary", 0, 400, "Summary", required=False)
    if "content_md" in data:
        content = data.get("content_md") or ""
        if not isinstance(content, str):
            errors.setdefault("content_md", []).append("Content must be text.")
        elif len(content) > MAX_CONTENT_CHARS:
            errors.setdefault("content_md", []).append(
                f"Content is too long (max {MAX_CONTENT_CHARS:,} characters)."
            )
        else:
            clean["content_md"] = content

    # Visibility / status
    if "visibility" in data:
        vis = (data.get("visibility") or "").strip().lower()
        if vis not in ALLOWED_VISIBILITY:
            errors.setdefault("visibility", []).append("Invalid visibility value.")
        else:
            clean["visibility"] = vis
    if "status" in data and not partial:
        status = (data.get("status") or "").strip().lower()
        if status not in ALLOWED_STATUS:
            errors.setdefault("status", []).append("Invalid status value.")
        else:
            clean["status"] = status

    # Tags
    if "tags" in data:
        tags = data.get("tags")
        if isinstance(tags, str):
            tags = [t for t in tags.split(",")]
        if not isinstance(tags, list):
            errors.setdefault("tags", []).append("Tags must be a list.")
        else:
            clean_tags = []
            for tag in tags[:MAX_TAGS]:
                if not isinstance(tag, str):
                    continue
                name = tag.strip().lower()
                if not name:
                    continue
                if len(name) > 50:
                    errors.setdefault("tags", []).append("Tags must be 50 characters or fewer.")
                    break
                if name not in clean_tags:
                    clean_tags.append(name)
            clean["tags"] = clean_tags

    # Optional custom slug
    if "slug" in data and data.get("slug"):
        slug = slugify(str(data.get("slug")))
        if not SLUG_RE.match(slug):
            errors.setdefault("slug", []).append("Slug may only contain letters, numbers and dashes.")
        else:
            clean["slug"] = slug

    # Publishing requires meaningful content
    if clean.get("status") == "published":
        title = clean.get("title", "")
        content = clean.get("content_md", "")
        if len(title) < 3:
            errors.setdefault("title", []).append("A title of at least 3 characters is required to publish.")
        if not content.strip():
            errors.setdefault("content_md", []).append("Add some content before publishing.")

    return clean, errors


def validate_report_payload(data: dict) -> tuple[dict, dict]:
    """Validate a document report."""
    errors: dict[str, list[str]] = {}
    clean: dict = {}

    reason = (data.get("reason") or "").strip().lower()
    if reason not in REPORT_REASONS:
        errors.setdefault("reason", []).append("Choose a valid reason.")
    else:
        clean["reason"] = reason

    details = (data.get("details") or "").strip()
    if len(details) > 1000:
        errors.setdefault("details", []).append("Details must be 1000 characters or fewer.")
    clean["details"] = details
    return clean, errors


def validate_message_body(data: dict) -> tuple[dict, dict]:
    """Validate a ticket reply body."""
    errors: dict[str, list[str]] = {}
    body = (data.get("body") or "").strip()
    if not body:
        errors.setdefault("body", []).append("Reply cannot be empty.")
    elif len(body) > 5000:
        errors.setdefault("body", []).append("Reply must be 5000 characters or fewer.")
    return {"body": body}, errors


def validate_theme(data: dict) -> tuple[dict, dict]:
    """Validate a theme preference value."""
    theme = (data.get("theme") or "").strip().lower()
    if theme not in ("auto", "light", "dark"):
        return {}, {"theme": ["Theme must be auto, light or dark."]}
    return {"theme": theme}, {}
