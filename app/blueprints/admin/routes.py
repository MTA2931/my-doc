"""Admin panel routes.

Every route is protected by ``capability_required`` (server-side) — the UI
additionally hides links the current role may not use. All mutating actions
are recorded in the audit log.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from ...extensions import db
from ...models import (
    ROLE_ADMIN,
    ROLE_SUPER,
    ROLE_SUPPORT,
    ROLE_USER,
    ROLES,
    AuditLog,
    User,
    get_setting,
    set_setting,
)
from ...models.document import STATUS_PUBLISHED, Document, Report
from ...models.support import (
    PRIORITY_LABELS,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
    TICKET_STATUS_LABELS,
    Ticket,
    TicketMessage,
)
from ...services.access import capability_required
from . import admin_bp
from .forms import AdminCreateForm, SiteSettingsForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _page_arg() -> int:
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def _range_days(days: int = 14):
    return datetime.now(timezone.utc) - timedelta(days=days)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route("/")
@capability_required("admin.dashboard")
def dashboard():
    stats = {
        "users": User.query.count(),
        "documents": Document.query.count(),
        "published": Document.query.filter(Document.status == STATUS_PUBLISHED).count(),
        "open_tickets": Ticket.query.filter(
            Ticket.status.in_(("open", "in_progress"))
        ).count(),
        "pending_reports": Report.query.filter(Report.status == "pending").count(),
        "banned_users": User.query.filter(User.is_banned.is_(True)).count(),
    }

    # 14-day series for the canvas charts
    since = _range_days(14)
    user_rows = (
        db.session.query(func.date(User.created_at), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .all()
    )
    doc_rows = (
        db.session.query(func.date(Document.created_at), func.count(Document.id))
        .filter(Document.created_at >= since)
        .group_by(func.date(Document.created_at))
        .all()
    )
    labels, u_series, d_series = [], [], []
    for i in range(14):
        day = (since + timedelta(days=i)).date()
        labels.append(day.isoformat())
        u_series.append(next((c for d, c in user_rows if str(d) == day.isoformat()), 0))
        d_series.append(next((c for d, c in doc_rows if str(d) == day.isoformat()), 0))

    audit = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    return render_template(
        "admin/index.html",
        stats=stats,
        chart=json.dumps({"labels": labels, "users": u_series, "docs": d_series}),
        audit=audit,
        section="dashboard",
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@admin_bp.route("/users")
@capability_required("admin.users")
def users_list():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "all")
    status = request.args.get("status", "all")

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            User.username.ilike(like) | User.email.ilike(like) |
            User.display_name.ilike(like)
        )
    if role in ROLES:
        query = query.filter(User.role == role)
    if status == "banned":
        query = query.filter(User.is_banned.is_(True))
    elif status == "active":
        query = query.filter(User.is_banned.is_(False))

    pagination = query.order_by(User.created_at.desc()).paginate(page=_page_arg(), per_page=15, error_out=False)
    return render_template(
        "admin/users.html",
        users=pagination.items,
        pagination=pagination,
        q=q,
        role=role,
        status=status,
        roles=ROLES,
        section="users",
    )


@admin_bp.route("/users/<int:user_id>")
@capability_required("admin.users")
def user_detail(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    docs = (
        Document.query.filter(Document.user_id == user.id)
        .order_by(Document.updated_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "admin/user_detail.html", profile=user, docs=docs, section="users"
    )


@admin_bp.route("/users/<int:user_id>/action", methods=["POST"])
@capability_required("admin.users")
def user_action(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    action = request.form.get("action", "")
    next_url = request.form.get("next") or url_for("admin.user_detail", user_id=user.id)

    if action == "ban":
        if user.id == current_user.id:
            flash("You cannot ban your own account.", "error")
            return redirect(next_url)
        if user.is_super_admin and not current_user.is_super_admin:
            flash("Only a Super Admin can ban a Super Admin.", "error")
            return redirect(next_url)
        user.is_banned = True
        AuditLog.record(current_user, "user.ban", "user", user.id, username=user.username)
        db.session.commit()
        flash(f"@{user.username} has been banned.", "success")

    elif action == "unban":
        user.is_banned = False
        AuditLog.record(current_user, "user.unban", "user", user.id, username=user.username)
        db.session.commit()
        flash(f"@{user.username} has been unbanned.", "success")

    elif action == "role":
        new_role = request.form.get("role", user.role)
        if new_role not in ROLES:
            flash("Unknown role.", "error")
            return redirect(next_url)
        # Only Super Admins may grant or revoke the Super Admin role.
        if (new_role == ROLE_SUPER or user.role == ROLE_SUPER) and not current_user.is_super_admin:
            flash("Only a Super Admin can change the Super Admin role.", "error")
            return redirect(next_url)
        if user.role == ROLE_SUPER and new_role != ROLE_SUPER:
            supers = User.query.filter(User.role == ROLE_SUPER, User.is_banned.is_(False)).count()
            if supers <= 1:
                flash("At least one Super Admin must always exist.", "error")
                return redirect(next_url)
        old_role = user.role
        user.role = new_role
        AuditLog.record(
            current_user, "user.role", "user", user.id,
            username=user.username, old_role=old_role, new_role=new_role,
        )
        db.session.commit()
        flash(f"@{user.username} is now {user.role_label}.", "success")

    else:
        flash("Unknown action.", "error")

    return redirect(next_url)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@admin_bp.route("/documents")
@capability_required("admin.documents")
def documents_list():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    featured = request.args.get("featured", "all")

    query = Document.query
    if q:
        like = f"%{q}%"
        query = query.join(Document.author).filter(
            Document.title.ilike(like) | Document.slug.ilike(like) |
            User.username.ilike(like)
        )
    if status in ("draft", "published"):
        query = query.filter(Document.status == status)
    if featured == "yes":
        query = query.filter(Document.is_featured.is_(True))
    elif featured == "no":
        query = query.filter(Document.is_featured.is_(False))

    pagination = query.order_by(Document.updated_at.desc()).paginate(page=_page_arg(), per_page=15, error_out=False)
    return render_template(
        "admin/documents.html",
        docs=pagination.items,
        pagination=pagination,
        q=q,
        status=status,
        featured=featured,
        section="documents",
    )


@admin_bp.route("/documents/<int:doc_id>/action", methods=["POST"])
@capability_required("admin.documents")
def document_action(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if doc is None:
        abort(404)
    action = request.form.get("action", "")
    next_url = request.form.get("next") or url_for("admin.documents_list")

    if action == "publish":
        doc.status = STATUS_PUBLISHED
        doc.published_at = doc.published_at or datetime.now(timezone.utc)
        AuditLog.record(current_user, "doc.publish", "document", doc.id, slug=doc.slug)
        message = f"Published '{doc.title}'."
    elif action == "unpublish":
        doc.status = "draft"
        AuditLog.record(current_user, "doc.unpublish", "document", doc.id, slug=doc.slug)
        message = f"Unpublished '{doc.title}'."
    elif action == "feature":
        doc.is_featured = True
        AuditLog.record(current_user, "doc.feature", "document", doc.id, slug=doc.slug)
        message = f"Featured '{doc.title}'."
    elif action == "unfeature":
        doc.is_featured = False
        AuditLog.record(current_user, "doc.unfeature", "document", doc.id, slug=doc.slug)
        message = f"Removed feature from '{doc.title}'."
    elif action == "delete":
        AuditLog.record(current_user, "doc.delete", "document", doc.id, slug=doc.slug)
        db.session.delete(doc)
        db.session.commit()
        flash("Document deleted.", "success")
        return redirect(next_url)
    else:
        flash("Unknown action.", "error")
        return redirect(next_url)

    db.session.commit()
    flash(message, "success")
    return redirect(next_url)


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------
@admin_bp.route("/tickets")
@capability_required("admin.tickets")
def tickets_list():
    status = request.args.get("status", "all")
    priority = request.args.get("priority", "all")
    q = request.args.get("q", "").strip()

    query = Ticket.query
    if status in TICKET_STATUSES:
        query = query.filter(Ticket.status == status)
    if priority in TICKET_PRIORITIES:
        query = query.filter(Ticket.priority == priority)
    if q:
        query = query.join(Ticket.user).filter(
            Ticket.subject.ilike(f"%{q}%") | User.username.ilike(f"%{q}%")
        )

    pagination = query.order_by(Ticket.updated_at.desc()).paginate(page=_page_arg(), per_page=15, error_out=False)
    return render_template(
        "admin/tickets.html",
        tickets=pagination.items,
        pagination=pagination,
        status=status,
        priority=priority,
        q=q,
        statuses=TICKET_STATUSES,
        priorities=TICKET_PRIORITIES,
        status_labels=TICKET_STATUS_LABELS,
        priority_labels=PRIORITY_LABELS,
        section="tickets",
    )


@admin_bp.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@capability_required("admin.tickets")
def ticket_detail(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if body:
            if len(body) > 5000:
                flash("Reply is too long (max 5000 characters).", "error")
            else:
                ticket.messages.append(
                    TicketMessage(user_id=current_user.id, body=body, is_staff=True)
                )
                if ticket.status in ("resolved", "closed"):
                    ticket.status = "in_progress"
                ticket.updated_at = datetime.now(timezone.utc)
                AuditLog.record(current_user, "ticket.reply", "ticket", ticket.id)
                db.session.commit()
                flash("Reply sent.", "success")
        else:
            flash("Reply cannot be empty.", "error")
        return redirect(url_for("admin.ticket_detail", ticket_id=ticket.id))

    messages = ticket.messages.order_by(TicketMessage.created_at).all()
    staff = User.query.filter(User.role.in_((ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER))).all()
    return render_template(
        "admin/ticket_detail.html",
        ticket=ticket,
        messages=messages,
        staff=staff,
        statuses=TICKET_STATUSES,
        priorities=TICKET_PRIORITIES,
        status_labels=TICKET_STATUS_LABELS,
        priority_labels=PRIORITY_LABELS,
        section="tickets",
    )


@admin_bp.route("/tickets/<int:ticket_id>/action", methods=["POST"])
@capability_required("admin.tickets")
def ticket_action(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)

    action = request.form.get("action", "")
    if action == "status":
        new_status = request.form.get("status", ticket.status)
        if new_status in TICKET_STATUSES:
            ticket.status = new_status
            AuditLog.record(current_user, "ticket.status", "ticket", ticket.id,
                            status=new_status)
    elif action == "priority":
        new_priority = request.form.get("priority", ticket.priority)
        if new_priority in TICKET_PRIORITIES:
            ticket.priority = new_priority
            AuditLog.record(current_user, "ticket.priority", "ticket", ticket.id,
                            priority=new_priority)
    elif action == "assign":
        assignee_id = request.form.get("assignee_id", "")
        if assignee_id == "":
            ticket.assignee_id = None
            AuditLog.record(current_user, "ticket.unassign", "ticket", ticket.id)
        else:
            assignee = db.session.get(User, int(assignee_id)) if assignee_id.isdigit() else None
            if assignee is None or not assignee.is_staff:
                flash("Choose a valid staff member.", "error")
                return redirect(url_for("admin.ticket_detail", ticket_id=ticket.id))
            ticket.assignee_id = assignee.id
            AuditLog.record(current_user, "ticket.assign", "ticket", ticket.id,
                            assignee=assignee.username)
    else:
        flash("Unknown action.", "error")
        return redirect(url_for("admin.ticket_detail", ticket_id=ticket.id))

    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Ticket updated.", "success")
    return redirect(url_for("admin.ticket_detail", ticket_id=ticket.id))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@admin_bp.route("/reports")
@capability_required("admin.reports")
def reports_list():
    status = request.args.get("status", "all")
    query = Report.query
    if status in ("pending", "reviewing", "dismissed", "actioned"):
        query = query.filter(Report.status == status)

    pagination = query.order_by(Report.created_at.desc()).paginate(page=_page_arg(), per_page=15, error_out=False)
    return render_template(
        "admin/reports.html",
        reports=pagination.items,
        pagination=pagination,
        status=status,
        section="reports",
    )


@admin_bp.route("/reports/<int:report_id>/action", methods=["POST"])
@capability_required("admin.reports")
def report_action(report_id: int):
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)

    action = request.form.get("action", "")
    note = (request.form.get("note") or "").strip()[:500]
    doc = report.document

    if action == "dismiss":
        report.status = "dismissed"
        report.resolution_note = note or "No violation found."
        message = "Report dismissed."
    elif action == "review":
        report.status = "reviewing"
        report.resolution_note = note
        message = "Report marked as reviewing."
    elif action == "unpublish":
        if doc is not None:
            doc.status = "draft"
            AuditLog.record(current_user, "doc.unpublish", "document", doc.id,
                            via="report", report_id=report.id)
        report.status = "actioned"
        report.resolution_note = note or "Document unpublished."
        message = "Document unpublished."
    elif action == "delete":
        if doc is not None:
            AuditLog.record(current_user, "doc.delete", "document", doc.id,
                            via="report", report_id=report.id)
            db.session.delete(doc)
        report.status = "actioned"
        report.resolution_note = note or "Document deleted."
        message = "Document deleted."
    elif action == "ban":
        if doc is not None and doc.author is not None:
            author = doc.author
            if author.is_super_admin and not current_user.is_super_admin:
                flash("Only a Super Admin can ban a Super Admin.", "error")
                return redirect(url_for("admin.reports_list"))
            author.is_banned = True
            AuditLog.record(current_user, "user.ban", "user", author.id,
                            via="report", report_id=report.id)
        report.status = "actioned"
        report.resolution_note = note or "Author banned."
        message = "Author banned and report actioned."
    else:
        flash("Unknown action.", "error")
        return redirect(url_for("admin.reports_list"))

    report.handled_by = current_user.id
    report.handled_at = datetime.now(timezone.utc)
    AuditLog.record(current_user, f"report.{action}", "report", report.id)
    db.session.commit()
    flash(message, "success")
    return redirect(url_for("admin.reports_list"))


# ---------------------------------------------------------------------------
# Admins (Super Admin only)
# ---------------------------------------------------------------------------
@admin_bp.route("/admins", methods=["GET", "POST"])
@capability_required("admin.admins")
def admins():
    form = AdminCreateForm()
    if form.validate_on_submit():
        staff = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            display_name=form.username.data.strip(),
            email_verified=True,
        )
        staff.set_password(form.password.data)
        db.session.add(staff)
        db.session.flush()
        AuditLog.record(current_user, "admin.create", "user", staff.id,
                        username=staff.username, role=staff.role)
        db.session.commit()
        flash(f"Staff account '{staff.username}' created.", "success")
        return redirect(url_for("admin.admins"))

    staff_users = (
        User.query.filter(User.role.in_((ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER)))
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template(
        "admin/admins.html",
        staff_users=staff_users,
        form=form,
        roles=ROLES,
        section="admins",
    )


@admin_bp.route("/admins/<int:user_id>/action", methods=["POST"])
@capability_required("admin.admins")
def admin_action(user_id: int):
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    action = request.form.get("action", "")

    if target.id == current_user.id:
        flash("You cannot modify your own staff account here.", "error")
        return redirect(url_for("admin.admins"))

    if action == "role":
        new_role = request.form.get("role", target.role)
        if new_role not in (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER):
            flash("Unknown role.", "error")
            return redirect(url_for("admin.admins"))
        if (new_role == ROLE_SUPER or target.role == ROLE_SUPER) and not current_user.is_super_admin:
            flash("Only a Super Admin can change the Super Admin role.", "error")
            return redirect(url_for("admin.admins"))
        if target.role == ROLE_SUPER and new_role != ROLE_SUPER:
            supers = User.query.filter(
                User.role == ROLE_SUPER, User.is_banned.is_(False)
            ).count()
            if supers <= 1:
                flash("At least one Super Admin must always exist.", "error")
                return redirect(url_for("admin.admins"))
        old_role = target.role
        target.role = new_role
        AuditLog.record(current_user, "admin.role", "user", target.id,
                        username=target.username, old_role=old_role, new_role=new_role)
        db.session.commit()
        flash(f"@{target.username} is now {target.role_label}.", "success")

    elif action == "remove":
        if target.role == ROLE_SUPER:
            supers = User.query.filter(
                User.role == ROLE_SUPER, User.is_banned.is_(False)
            ).count()
            if supers <= 1:
                flash("At least one Super Admin must always exist.", "error")
                return redirect(url_for("admin.admins"))
        target.role = ROLE_USER
        AuditLog.record(current_user, "admin.remove", "user", target.id,
                        username=target.username)
        db.session.commit()
        flash(f"@{target.username} is no longer a staff member.", "success")

    else:
        flash("Unknown action.", "error")

    return redirect(url_for("admin.admins"))


# ---------------------------------------------------------------------------
# Site settings
# ---------------------------------------------------------------------------
@admin_bp.route("/settings", methods=["GET", "POST"])
@capability_required("admin.settings")
def settings():
    form = SiteSettingsForm()
    if request.method == "GET":
        form.site_name.data = get_setting("site_name", "MyDoc")
        form.site_tagline.data = get_setting("site_tagline", "")
        form.footer_note.data = get_setting("footer_note", "Developed by MTA Company")
        form.default_theme.data = get_setting("default_theme", "auto")
        form.registration_enabled.data = get_setting("registration_enabled", "1") == "1"
        form.maintenance_mode.data = get_setting("maintenance_mode", "0") == "1"

    if form.validate_on_submit():
        set_setting("site_name", form.site_name.data.strip()[:60])
        set_setting("site_tagline", (form.site_tagline.data or "").strip()[:140])
        set_setting("footer_note", form.footer_note.data.strip()[:140])
        set_setting("default_theme", form.default_theme.data or "auto")
        set_setting("registration_enabled", "1" if form.registration_enabled.data else "0")
        set_setting("maintenance_mode", "1" if form.maintenance_mode.data else "0")
        AuditLog.record(current_user, "settings.update", "site")
        db.session.commit()
        flash("Site settings saved.", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", form=form, section="settings")





