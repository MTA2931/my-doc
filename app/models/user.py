"""User and tag models (accounts, roles, interests)."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
ROLE_USER = "user"
ROLE_SUPPORT = "support"
ROLE_ADMIN = "admin"
ROLE_SUPER = "super_admin"

# Ordered from least to most privileged.
ROLES = (ROLE_USER, ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER)

ROLE_LABELS = {
    ROLE_USER: "Member",
    ROLE_SUPPORT: "Support",
    ROLE_ADMIN: "Admin",
    ROLE_SUPER: "Super Admin",
}

# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------
user_interests = db.Table(
    "user_interests",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(db.Model):
    """A topic tag used for user interests and document categorisation."""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Tag {self.name}>"

    @classmethod
    def get_or_create(cls, name: str) -> "Tag":
        """Return the tag for ``name`` (case-insensitive), creating it if needed."""
        clean = (name or "").strip().lower()
        if not clean:
            raise ValueError("Tag name cannot be empty.")
        tag = db.session.scalar(db.select(cls).where(cls.name == clean))
        if tag is None:
            tag = cls(name=clean)
            db.session.add(tag)
        return tag


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    """A MyDoc account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default=ROLE_USER, index=True)
    is_banned = db.Column(db.Boolean, nullable=False, default=False)

    display_name = db.Column(db.String(80), nullable=False, default="")
    bio = db.Column(db.String(500), nullable=False, default="")
    avatar = db.Column(db.String(255), nullable=False, default="")
    theme = db.Column(db.String(10), nullable=False, default="auto")  # auto|light|dark

    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_expires = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime, nullable=True)

    # ------------------------------------------------------------------ rels
    interests = db.relationship(
        "Tag",
        secondary=user_interests,
        lazy="selectin",
        backref=db.backref("interested_users", lazy="dynamic"),
    )
    documents = db.relationship(
        "Document",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    saves = db.relationship(
        "Save",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    tickets = db.relationship(
        "Ticket",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Ticket.user_id",
        lazy="dynamic",
    )

    # -------------------------------------------------------------- helpers
    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.username}>"

    @property
    def effective_name(self) -> str:
        return self.display_name or self.username

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)

    @property
    def is_super_admin(self) -> bool:
        return self.role == ROLE_SUPER

    @property
    def is_admin(self) -> bool:
        """Admin or Super Admin."""
        return self.role in (ROLE_ADMIN, ROLE_SUPER)

    @property
    def is_staff(self) -> bool:
        """Any role that can enter the admin panel."""
        return self.role in (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def can(self, capability: str) -> bool:
        """Centralised capability check used by views, API and UI alike."""
        matrix = {
            "admin.access": (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER),
            "admin.dashboard": (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER),
            "admin.documents": (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER),
            "admin.tickets": (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER),
            "admin.reports": (ROLE_SUPPORT, ROLE_ADMIN, ROLE_SUPER),
            "admin.users": (ROLE_ADMIN, ROLE_SUPER),
            "admin.settings": (ROLE_ADMIN, ROLE_SUPER),
            "admin.admins": (ROLE_SUPER,),
            "admin.audit": (ROLE_ADMIN, ROLE_SUPER),
        }
        return self.role in matrix.get(capability, ())

    # ------------------------------------------------------------ passwords
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # --------------------------------------------------------------- to-dict
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.effective_name,
            "email": self.email,
            "role": self.role,
            "role_label": self.role_label,
            "is_banned": self.is_banned,
            "bio": self.bio,
            "avatar": self.avatar,
            "theme": self.theme,
            "interests": [t.name for t in self.interests],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login callback — banned users are treated as anonymous."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, uid)
    if user is None or user.is_banned:
        return None
    return user

