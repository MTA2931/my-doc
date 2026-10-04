"""Audit log, activity feed and site settings models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from ..extensions import db


class AuditLog(db.Model):
    """Immutable record of privileged (admin) actions."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    target_type = db.Column(db.String(40), nullable=False, default="")
    target_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    admin = db.relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AuditLog {self.action}>"

    @classmethod
    def record(cls, admin, action: str, target_type: str = "", target_id=None, **detail) -> "AuditLog":
        entry = cls(
            admin_id=getattr(admin, "id", None),
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail, default=str),
        )
        db.session.add(entry)
        return entry

    @property
    def detail_parsed(self) -> dict:
        try:
            return json.loads(self.detail)
        except (TypeError, ValueError):
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "detail": self.detail_parsed,
            "admin": self.admin.effective_name if self.admin else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Activity(db.Model):
    """A user's recent activity entry (shown on their dashboard)."""

    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)  # doc_created | doc_published | saved | ...
    message = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship("User", backref=db.backref("activities", lazy="dynamic",
                                                      cascade="all, delete-orphan"))

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Activity {self.type}>"

    @classmethod
    def log(cls, user, type_: str, message: str, link: str = "") -> "Activity":
        entry = cls(user_id=user.id, type=type_, message=message[:300], link=link[:300])
        db.session.add(entry)
        return entry

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "message": self.message,
            "link": self.link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SiteSetting(db.Model):
    """Key/value store for site-wide settings editable by admins."""

    __tablename__ = "site_settings"

    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<SiteSetting {self.key}>"


# ---------------------------------------------------------------------------
# Settings helpers with defaults
# ---------------------------------------------------------------------------
SETTING_DEFAULTS = {
    "site_name": "MyDoc",
    "site_tagline": "Where knowledge gets documented.",
    "registration_enabled": "1",
    "maintenance_mode": "0",
    "default_theme": "auto",        # auto | light | dark
    "allow_image_uploads": "1",
    "footer_note": "Developed by MTA Company",
}


def get_setting(key: str, default: str | None = None) -> str:
    """Read a site setting, falling back to ``SETTING_DEFAULTS``."""
    if default is None:
        default = SETTING_DEFAULTS.get(key, "")
    row = db.session.get(SiteSetting, key)
    return row.value if row is not None else default


def set_setting(key: str, value: str) -> SiteSetting:
    """Write a site setting (creates the row when missing)."""
    row = db.session.get(SiteSetting, key)
    if row is None:
        row = SiteSetting(key=key, value=str(value))
        db.session.add(row)
    else:
        row.value = str(value)
    return row
