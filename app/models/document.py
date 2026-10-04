"""Document, save (bookmark) and report models."""

from __future__ import annotations

from datetime import datetime, timezone

from ..extensions import db

# ---------------------------------------------------------------------------
# Association table: documents <-> tags
# ---------------------------------------------------------------------------
document_tags = db.Table(
    "document_tags",
    db.Column("document_id", db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

# Status / visibility constants
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
VISIBILITY_PUBLIC = "public"
VISIBILITY_UNLISTED = "unlisted"

REPORT_PENDING = "pending"
REPORT_REVIEWING = "reviewing"
REPORT_DISMISSED = "dismissed"
REPORT_ACTIONED = "actioned"


class Document(db.Model):
    """A document (article, guide, note, tutorial) written by a user."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    summary = db.Column(db.String(400), nullable=False, default="")
    content_md = db.Column(db.Text, nullable=False, default="")
    content_html = db.Column(db.Text, nullable=False, default="")
    cover_image = db.Column(db.String(255), nullable=False, default="")

    status = db.Column(db.String(12), nullable=False, default=STATUS_DRAFT, index=True)
    visibility = db.Column(db.String(12), nullable=False, default=VISIBILITY_PUBLIC)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)

    views_count = db.Column(db.Integer, nullable=False, default=0)
    reading_time = db.Column(db.Integer, nullable=False, default=1)  # minutes

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    published_at = db.Column(db.DateTime, nullable=True)

    # ------------------------------------------------------------- relations
    author = db.relationship("User", back_populates="documents")
    tags = db.relationship("Tag", secondary=document_tags, lazy="selectin",
                           backref=db.backref("documents", lazy="dynamic"))
    saves = db.relationship("Save", back_populates="document", cascade="all, delete-orphan", lazy="dynamic")
    reports = db.relationship("Report", back_populates="document", cascade="all, delete-orphan", lazy="dynamic")

    # -------------------------------------------------------------- helpers
    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Document {self.slug}>"

    @property
    def is_published(self) -> bool:
        return self.status == STATUS_PUBLISHED

    @property
    def save_count(self) -> int:
        return self.saves.count()

    @property
    def url(self) -> str:
        return f"/doc/{self.slug}"

    @property
    def summary_or_excerpt(self) -> str:
        if self.summary:
            return self.summary
        # Fall back to the first ~180 characters of the markdown source.
        text = " ".join(self.content_md.split())
        return text[:180] + ("…" if len(text) > 180 else "")

    def to_dict(self, include_content: bool = False) -> dict:
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary_or_excerpt,
            "cover_image": self.cover_image,
            "status": self.status,
            "visibility": self.visibility,
            "is_featured": self.is_featured,
            "views_count": self.views_count,
            "save_count": self.save_count,
            "reading_time": self.reading_time,
            "tags": [t.name for t in self.tags],
            "author": {
                "id": self.author.id,
                "username": self.author.username,
                "display_name": self.author.effective_name,
                "avatar": self.author.avatar,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        if include_content:
            data["content_html"] = self.content_html
            data["content_md"] = self.content_md
        return data


class Save(db.Model):
    """A bookmark of a document by a user."""

    __tablename__ = "saves"
    __table_args__ = (db.UniqueConstraint("user_id", "document_id", name="uq_save_user_doc"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="saves")
    document = db.relationship("Document", back_populates="saves")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Save {self.user_id}:{self.document_id}>"


class Report(db.Model):
    """A user-submitted report against a document."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(1000), nullable=False, default="")
    status = db.Column(db.String(12), nullable=False, default=REPORT_PENDING, index=True)
    resolution_note = db.Column(db.String(500), nullable=False, default="")
    handled_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    handled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    reporter = db.relationship("User", foreign_keys=[reporter_id], backref="reports_made")
    document = db.relationship("Document", back_populates="reports")
    handler = db.relationship("User", foreign_keys=[handled_by])

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Report {self.id} {self.status}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reason": self.reason,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
