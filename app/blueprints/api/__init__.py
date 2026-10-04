"""JSON REST API consumed by the frontend via fetch().

All mutating endpoints require:
  * an authenticated session (except where documented), and
  * a valid CSRF token (Flask-WTF accepts the ``X-CSRFToken`` header).

Errors are returned as ``{"error": "...", "errors": {field: [...]}}``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, current_app, jsonify, request, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...models import Activity, AuditLog, Report, Save, Tag
from ...models.document import (
    STATUS_PUBLISHED,
    VISIBILITY_PUBLIC,
    Document,
)
from ...models.support import Ticket, TicketMessage
from ...services.feeds import FEED_TABS, build_feed_query, paginate_feed
from ...services.markdown_service import render_markdown
from ...services.utils import (
    delete_uploaded,
    reading_time_minutes,
    save_image_upload,
    unique_slug,
)
from ...services.validators import (
    validate_document_payload,
    validate_message_body,
    validate_report_payload,
    validate_theme,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json() -> dict:
    return request.get_json(silent=True) or {}


def _bad_request(errors: dict, message: str = "Please fix the highlighted fields."):
    return jsonify(error=message, errors=errors), 400


def _owned_document(doc_id: int) -> Document:
    """Fetch a document the current user is allowed to modify."""
    doc = db.session.get(Document, doc_id)
    if doc is None:
        abort(404)
    if doc.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return doc


def _apply_tags(doc: Document, tag_names: list[str]) -> None:
    doc.tags.clear()
    for name in tag_names:
        doc.tags.append(Tag.get_or_create(name))


# ---------------------------------------------------------------------------
# Feed & search
# ---------------------------------------------------------------------------
@api_bp.route("/feed")
def feed():
    tab = request.args.get("tab", "foryou")
    if tab not in FEED_TABS:
        tab = "foryou"
    q = request.args.get("q", "").strip()[:120]
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", current_app.config["DOCS_PER_PAGE"])

    query = build_feed_query(tab, current_user, q or None)
    result = paginate_feed(query, page, per_page)
    result["docs"] = [doc.to_dict() for doc in result["docs"]]
    result["tab"] = tab
    result["q"] = q
    return jsonify(result)


@api_bp.route("/tags")
def tags():
    q = (request.args.get("q") or "").strip().lower()[:50]
    query = Tag.query
    if q:
        query = query.filter(Tag.name.ilike(f"%{q}%"))
    rows = query.order_by(Tag.name).limit(20).all()
    return jsonify(tags=[t.name for t in rows])


# ---------------------------------------------------------------------------
# Documents CRUD (editor)
# ---------------------------------------------------------------------------
@api_bp.route("/documents", methods=["POST"])
@login_required
def create_document():
    data = _json()
    clean, errors = validate_document_payload(data, partial=False)
    if errors:
        return _bad_request(errors)

    slug = clean.get("slug") or unique_slug(Document, clean["title"])
    if Document.query.filter(Document.slug == slug).first():
        return _bad_request({"slug": ["That slug is already in use."]})

    content_md = clean.get("content_md", "")
    status = clean.get("status", "draft")
    doc = Document(
        user_id=current_user.id,
        title=clean["title"],
        slug=slug,
        summary=clean.get("summary", ""),
        content_md=content_md,
        content_html=render_markdown(content_md),
        visibility=clean.get("visibility", VISIBILITY_PUBLIC),
        status=status,
        reading_time=reading_time_minutes(content_md),
    )
    if status == STATUS_PUBLISHED:
        doc.published_at = datetime.now(timezone.utc)

    db.session.add(doc)
    db.session.flush()
    _apply_tags(doc, clean.get("tags", []))
    Activity.log(current_user, "doc_created", f"Created document '{doc.title}'",
                 f"/doc/{doc.slug}")
    if status == STATUS_PUBLISHED:
        Activity.log(current_user, "doc_published", f"Published '{doc.title}'",
                     f"/doc/{doc.slug}")
    db.session.commit()
    return jsonify(doc=doc.to_dict(), redirect=url_for("docs.edit", doc_id=doc.id)), 201


@api_bp.route("/documents/<int:doc_id>", methods=["PUT"])
@login_required
def update_document(doc_id: int):
    doc = _owned_document(doc_id)
    data = _json()
    clean, errors = validate_document_payload(data, partial=False)
    if errors:
        return _bad_request(errors)

    if clean.get("slug") and clean["slug"] != doc.slug:
        if Document.query.filter(Document.slug == clean["slug"], Document.id != doc.id).first():
            return _bad_request({"slug": ["That slug is already in use."]})
        doc.slug = clean["slug"]
    elif "slug" not in clean and "title" in clean:
        doc.slug = unique_slug(Document, clean["title"], exclude_id=doc.id)

    doc.title = clean["title"]
    doc.summary = clean.get("summary", "")
    doc.content_md = clean.get("content_md", doc.content_md)
    doc.content_html = render_markdown(doc.content_md)
    doc.reading_time = reading_time_minutes(doc.content_md)
    doc.visibility = clean.get("visibility", doc.visibility)

    new_status = clean.get("status", doc.status)
    if new_status == STATUS_PUBLISHED and doc.status != STATUS_PUBLISHED:
        doc.published_at = datetime.now(timezone.utc)
        Activity.log(current_user, "doc_published", f"Published '{doc.title}'",
                     f"/doc/{doc.slug}")
    doc.status = new_status

    if "tags" in clean:
        _apply_tags(doc, clean["tags"])
    db.session.commit()
    return jsonify(doc=doc.to_dict(), saved_at=datetime.now(timezone.utc).isoformat())


@api_bp.route("/documents/<int:doc_id>/autosave", methods=["PUT"])
@login_required
def autosave_document(doc_id: int):
    """Partial save while typing — never changes publish status."""
    doc = _owned_document(doc_id)
    data = _json()
    clean, errors = validate_document_payload(data, partial=True)
    if errors:
        return _bad_request(errors)

    if "title" in clean and clean["title"]:
        doc.title = clean["title"]
    if "summary" in clean:
        doc.summary = clean["summary"]
    if "content_md" in clean:
        doc.content_md = clean["content_md"]
        doc.content_html = render_markdown(doc.content_md)
        doc.reading_time = reading_time_minutes(doc.content_md)
    if "tags" in clean:
        _apply_tags(doc, clean["tags"])
    if "slug" in clean and clean["slug"] and clean["slug"] != doc.slug:
        clash = Document.query.filter(
            Document.slug == clean["slug"], Document.id != doc.id
        ).first()
        if clash:
            return _bad_request({"slug": ["That slug is already in use."]})
        doc.slug = clean["slug"]
    db.session.commit()
    return jsonify(saved_at=datetime.now(timezone.utc).isoformat(),
                   reading_time=doc.reading_time)


@api_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id: int):
    doc = _owned_document(doc_id)
    Activity.log(current_user, "doc_deleted", f"Deleted document '{doc.title}'")
    db.session.delete(doc)
    db.session.commit()
    return jsonify(deleted=True, redirect=url_for("dashboard.documents"))


@api_bp.route("/documents/<int:doc_id>/status", methods=["POST"])
@login_required
def set_document_status(doc_id: int):
    """Toggle publish state without sending the whole document."""
    doc = _owned_document(doc_id)
    status = (_json().get("status") or "").strip().lower()
    if status not in ("draft", "published"):
        return _bad_request({"status": ["Status must be draft or published."]})
    if status == "published" and not doc.content_md.strip():
        return _bad_request({"content_md": ["Add some content before publishing."]})

    if status == "published" and doc.status != "published":
        doc.published_at = datetime.now(timezone.utc)
        Activity.log(current_user, "doc_published", f"Published '{doc.title}'",
                     f"/doc/{doc.slug}")
    doc.status = status
    db.session.commit()
    return jsonify(doc=doc.to_dict())


@api_bp.route("/documents/<int:doc_id>/cover", methods=["POST"])

@login_required
def upload_cover(doc_id: int):
    doc = _owned_document(doc_id)
    file = request.files.get("cover")
    if file is None:
        return _bad_request({"cover": ["No file uploaded."]})
    try:
        relative = save_image_upload(file, "covers")
    except ValueError as exc:
        return _bad_request({"cover": [str(exc)]})

    if doc.cover_image:
        delete_uploaded(doc.cover_image, "covers")
    doc.cover_image = relative
    db.session.commit()
    return jsonify(cover_image=doc.cover_image)


@api_bp.route("/documents/<int:doc_id>/save", methods=["POST"])
@login_required
def toggle_save(doc_id: int):
    """Bookmark / unbookmark a document."""
    doc = db.session.get(Document, doc_id)
    if doc is None:
        abort(404)
    if not doc.is_published:
        return jsonify(error="Only published documents can be saved."), 400

    existing = Save.query.filter_by(user_id=current_user.id, document_id=doc.id).first()
    if existing:
        db.session.delete(existing)
        saved = False
    else:
        db.session.add(Save(user_id=current_user.id, document_id=doc.id))
        Activity.log(current_user, "saved", f"Saved '{doc.title}'", f"/doc/{doc.slug}")
        saved = True
    db.session.commit()
    return jsonify(saved=saved, count=doc.save_count)


@api_bp.route("/documents/<int:doc_id>/report", methods=["POST"])
@login_required
def report_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if doc is None:
        abort(404)
    if doc.user_id == current_user.id:
        return jsonify(error="You cannot report your own document."), 400

    clean, errors = validate_report_payload(_json())
    if errors:
        return _bad_request(errors)

    duplicate = Report.query.filter_by(
        reporter_id=current_user.id, document_id=doc.id, status="pending"
    ).first()
    if duplicate:
        return jsonify(
            error="You already reported this document. Our team is reviewing it."
        ), 409

    report = Report(
        reporter_id=current_user.id,
        document_id=doc.id,
        reason=clean["reason"],
        details=clean.get("details", ""),
    )
    db.session.add(report)
    db.session.commit()
    return jsonify(reported=True,
                   message="Report submitted. Thank you for keeping MyDoc safe."), 201


# ---------------------------------------------------------------------------
# Ticket replies
# ---------------------------------------------------------------------------
@api_bp.route("/tickets/<int:ticket_id>/messages", methods=["GET"])
@login_required
def ticket_messages(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    if ticket.user_id != current_user.id and not current_user.is_staff:
        abort(403)
    rows = ticket.messages.order_by(TicketMessage.created_at).all()
    return jsonify(messages=[m.to_dict() for m in rows])


@api_bp.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
@login_required
def ticket_reply(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    if ticket.user_id != current_user.id and not current_user.is_staff:
        abort(403)

    clean, errors = validate_message_body(_json())
    if errors:
        return _bad_request(errors)

    msg = TicketMessage(
        user_id=current_user.id,
        body=clean["body"],
        is_staff=current_user.is_staff,
    )
    ticket.messages.append(msg)
    ticket.updated_at = datetime.now(timezone.utc)
    if current_user.is_staff and ticket.status in ("resolved", "closed"):
        ticket.status = "in_progress"
    db.session.commit()
    return jsonify(message=msg.to_dict()), 201


# ---------------------------------------------------------------------------
# Current user preferences
# ---------------------------------------------------------------------------
@api_bp.route("/me/theme", methods=["POST"])
@login_required
def set_theme():
    clean, errors = validate_theme(_json())
    if errors:
        return _bad_request(errors)
    current_user.theme = clean["theme"]
    db.session.commit()
    return jsonify(theme=current_user.theme)


# ---------------------------------------------------------------------------
# Admin stats (charts)
# ---------------------------------------------------------------------------
@api_bp.route("/admin/stats")
@login_required
def admin_stats():
    from sqlalchemy import func

    from ...models.document import Report as DocReport
    from ...models.support import Ticket as SupportTicket
    from ...models.user import User as UserModel

    if not current_user.can("admin.dashboard"):
        return jsonify(error="Insufficient permissions."), 403

    today = datetime.now(timezone.utc).date()

    def daily_series(model, column):
        """Counts per day for the last 14 days."""
        start = datetime.combine(today - timedelta(days=13), datetime.min.time(),
                                 tzinfo=timezone.utc)
        rows = (
            db.session.query(func.date(column), func.count(model.id))
            .filter(column >= start)
            .group_by(func.date(column))
            .all()
        )
        lookup = {str(d): int(c) for d, c in rows}
        labels, values = [], []
        for i in range(14):
            day = (today - timedelta(days=13 - i)).isoformat()
            labels.append(day)
            values.append(lookup.get(day, 0))
        return labels, values

    labels, users_series = daily_series(UserModel, UserModel.created_at)
    _, docs_series = daily_series(Document, Document.created_at)

    return jsonify(
        labels=labels,
        users=users_series,
        docs=docs_series,
        totals={
            "users": UserModel.query.count(),
            "documents": Document.query.count(),
            "published": Document.query.filter(
                Document.status == STATUS_PUBLISHED
            ).count(),
            "open_tickets": SupportTicket.query.filter(
                SupportTicket.status.in_(("open", "in_progress"))
            ).count(),
            "pending_reports": DocReport.query.filter(
                DocReport.status == "pending"
            ).count(),
            "audit_entries": AuditLog.query.count(),
        },
    )


