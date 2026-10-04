"""User dashboard: stats, my documents, saves, settings, tickets."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from ...extensions import db
from ...models import Activity, Save, Tag, User
from ...models.document import STATUS_PUBLISHED, Document
from ...models.support import (
    TICKET_STATUSES,
    Ticket,
    TicketMessage,
    TICKET_CATEGORIES,
)
from ...services.utils import delete_uploaded, save_image_upload
from .forms import ChangePasswordForm, DeleteAccountForm, ProfileForm, TicketForm

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _parse_interests(raw: str) -> list[str]:
    return [p.strip().lower() for p in (raw or "").split(",") if p.strip()][:20]


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
@dashboard_bp.route("/")
@login_required
def index():
    total_docs = Document.query.filter(Document.user_id == current_user.id).count()
    published = Document.query.filter(
        Document.user_id == current_user.id, Document.status == STATUS_PUBLISHED
    ).count()
    views = (
        db.session.query(func.coalesce(func.sum(Document.views_count), 0))
        .filter(Document.user_id == current_user.id)
        .scalar()
    )
    saves_received = (
        db.session.query(func.coalesce(func.count(Save.id), 0))
        .join(Document, Save.document_id == Document.id)
        .filter(Document.user_id == current_user.id)
        .scalar()
    )
    open_tickets = Ticket.query.filter(
        Ticket.user_id == current_user.id,
        Ticket.status.in_(("open", "in_progress")),
    ).count()

    recent_docs = (
        Document.query.filter(Document.user_id == current_user.id)
        .order_by(Document.updated_at.desc())
        .limit(5)
        .all()
    )
    activities = (
        Activity.query.filter(Activity.user_id == current_user.id)
        .order_by(Activity.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "dashboard/index.html",
        stats={
            "total_docs": total_docs,
            "published": published,
            "views": int(views or 0),
            "saves": int(saves_received or 0),
            "open_tickets": open_tickets,
        },
        recent_docs=recent_docs,
        activities=activities,
    )



# ---------------------------------------------------------------------------
# My documents
# ---------------------------------------------------------------------------
@dashboard_bp.route("/documents")
@login_required
def documents():
    status = request.args.get("status", "all")
    q = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    query = Document.query.filter(Document.user_id == current_user.id)
    if status in ("draft", "published"):
        query = query.filter(Document.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(Document.title.ilike(like) | Document.summary.ilike(like))

    per_page = 10
    pagination = query.order_by(Document.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        "dashboard/documents.html",
        docs=pagination.items,
        pagination=pagination,
        status=status,
        q=q,
    )


# ---------------------------------------------------------------------------
# Saves (bookmarks)
# ---------------------------------------------------------------------------
@dashboard_bp.route("/saves")
@login_required
def saves():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    query = Save.query.filter(Save.user_id == current_user.id).order_by(Save.created_at.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    docs = [(s.document, s.created_at) for s in pagination.items if s.document is not None]
    return render_template(
        "dashboard/saves.html",
        entries=docs,
        pagination=pagination,
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    profile_form = ProfileForm(obj=current_user)
    delete_form = DeleteAccountForm()

    if profile_form.validate_on_submit():
        current_user.display_name = profile_form.display_name.data.strip()
        current_user.bio = (profile_form.bio.data or "").strip()
        current_user.theme = profile_form.theme.data or "auto"

        # Interests
        names = _parse_interests(profile_form.interests.data)
        if names:
            current_user.interests.clear()
            for name in names:
                try:
                    current_user.interests.append(Tag.get_or_create(name))
                except ValueError:
                    continue

        # Avatar upload
        avatar = profile_form.avatar.data
        if avatar and getattr(avatar, "filename", ""):
            try:
                relative = save_image_upload(avatar, "avatars")
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                if current_user.avatar:
                    delete_uploaded(current_user.avatar, "avatars")
                current_user.avatar = relative

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template(
        "dashboard/settings.html",
        profile_form=profile_form,
        delete_form=delete_form,
    )



# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------
@dashboard_bp.route("/tickets")
@login_required
def tickets():
    status = request.args.get("status", "all")
    query = Ticket.query.filter(Ticket.user_id == current_user.id)
    if status in TICKET_STATUSES:
        query = query.filter(Ticket.status == status)
    items = query.order_by(Ticket.updated_at.desc()).all()
    return render_template(
        "dashboard/tickets.html",
        tickets=items,
        status=status,
        statuses=TICKET_STATUSES,
    )


@dashboard_bp.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    form = TicketForm()
    if form.validate_on_submit():
        ticket = Ticket(
            user_id=current_user.id,
            subject=form.subject.data.strip(),
            category=form.category.data,
        )
        ticket.messages.append(
            TicketMessage(
                user_id=current_user.id,
                body=form.message.data.strip(),
                is_staff=False,
            )
        )
        db.session.add(ticket)
        db.session.flush()  # obtain ticket.id for the activity link
        Activity.log(
            current_user,
            "ticket",
            f"Opened support ticket: {ticket.subject}",
            url_for("dashboard.ticket_detail", ticket_id=ticket.id),
        )
        db.session.commit()
        flash("Your ticket has been opened. Our team will reply shortly.", "success")
        return redirect(url_for("dashboard.ticket_detail", ticket_id=ticket.id))

    return render_template("dashboard/ticket_new.html", form=form)


@dashboard_bp.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_detail(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    if ticket.user_id != current_user.id and not current_user.is_staff:
        abort(403)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Reply cannot be empty.", "error")
        elif len(body) > 5000:
            flash("Reply is too long (max 5000 characters).", "error")
        else:
            msg = TicketMessage(
                user_id=current_user.id,
                body=body,
                is_staff=current_user.is_staff,
            )
            ticket.messages.append(msg)
            if ticket.status == "closed" and current_user.is_staff:
                ticket.status = "in_progress"
            ticket.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash("Reply sent.", "success")
        return redirect(url_for("dashboard.ticket_detail", ticket_id=ticket.id))

    messages = ticket.messages.order_by(TicketMessage.created_at).all()
    return render_template(
        "dashboard/ticket_detail.html",
        ticket=ticket,
        messages=messages,
    )


@dashboard_bp.route("/change-password", methods=["GET", "POST"])

@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Your password has been changed.", "success")
        return redirect(url_for("dashboard.settings"))
    return render_template("dashboard/change_password.html", form=form)


@dashboard_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if not form.validate_on_submit() or not current_user.check_password(form.password.data):
        flash("Account deletion confirmation is invalid.", "error")
        return redirect(url_for("dashboard.settings"))

    # Remove stored avatar, then the account (cascades documents, saves, tickets).
    if current_user.avatar:
        delete_uploaded(current_user.avatar, "avatars")
    for doc in current_user.documents:
        if doc.cover_image:
            delete_uploaded(doc.cover_image, "covers")
    username = current_user.username
    db.session.delete(current_user)
    db.session.commit()
    flash(f"Account '{username}' and all of its content were deleted.", "success")
    return redirect(url_for("main.landing"))

