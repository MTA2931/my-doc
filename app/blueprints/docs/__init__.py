"""Document routes: public view plus the Markdown editor pages."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from ...extensions import db
from ...models.document import (
    STATUS_PUBLISHED,
    VISIBILITY_PUBLIC,
    Document,
    document_tags,
)

docs_bp = Blueprint("docs", __name__)


# ---------------------------------------------------------------------------
# Public document view
# ---------------------------------------------------------------------------
@docs_bp.route("/doc/<slug>")
def view(slug: str):
    doc = db.session.scalar(db.select(Document).where(Document.slug == slug))
    if doc is None:
        abort(404)

    # Drafts and unlisted docs are only visible to their owner (and staff).
    can_see = doc.is_published or (
        current_user.is_authenticated
        and (current_user.id == doc.user_id or current_user.is_staff)
    )
    if not can_see:
        abort(404)

    # Count a view once per session.
    viewed = session.get("viewed_docs", [])
    if doc.id not in viewed and doc.is_published:
        doc.views_count += 1
        viewed.append(doc.id)
        session["viewed_docs"] = viewed[-100:]
        db.session.commit()

    # Related documents sharing at least one tag (max 3).
    related = []
    tag_ids = [t.id for t in doc.tags]
    if tag_ids:
        related = (
            Document.query.join(
                document_tags, document_tags.c.document_id == Document.id
            )
            .filter(
                document_tags.c.tag_id.in_(tag_ids),
                Document.id != doc.id,
                Document.status == STATUS_PUBLISHED,
                Document.visibility == VISIBILITY_PUBLIC,
            )
            .distinct()
            .limit(3)
            .all()
        )
    if len(related) < 3:
        extra = (
            Document.query.filter(
                Document.id != doc.id,
                Document.status == STATUS_PUBLISHED,
                Document.visibility == VISIBILITY_PUBLIC,
                Document.id.notin_([r.id for r in related]),
            )
            .order_by(Document.views_count.desc())
            .limit(3 - len(related))
            .all()
        )
        related.extend(extra)

    is_owner = current_user.is_authenticated and current_user.id == doc.user_id
    is_saved = False
    if current_user.is_authenticated:
        from ...models import Save

        is_saved = Save.query.filter_by(
            user_id=current_user.id, document_id=doc.id
        ).first() is not None

    return render_template(
        "docs/view.html",
        doc=doc,
        related=related,
        is_owner=is_owner,
        is_saved=is_saved,
    )


# ---------------------------------------------------------------------------
# Editor pages (create / edit)
# ---------------------------------------------------------------------------
@docs_bp.route("/doc/new")
@login_required
def create():
    """Blank editor — the document is created via the API on first save."""
    return render_template("docs/editor.html", doc=None)


@docs_bp.route("/doc/<int:doc_id>/edit")
@login_required
def edit(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if doc is None:
        abort(404)
    if doc.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template("docs/editor.html", doc=doc)
