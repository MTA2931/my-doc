"""Support ticket models."""

from __future__ import annotations

from datetime import datetime, timezone

from ..extensions import db

# Ticket lifecycle
TICKET_OPEN = "open"
TICKET_IN_PROGRESS = "in_progress"
TICKET_RESOLVED = "resolved"
TICKET_CLOSED = "closed"
TICKET_STATUSES = (TICKET_OPEN, TICKET_IN_PROGRESS, TICKET_RESOLVED, TICKET_CLOSED)

TICKET_STATUS_LABELS = {
    TICKET_OPEN: "Open",
    TICKET_IN_PROGRESS: "In Progress",
    TICKET_RESOLVED: "Resolved",
    TICKET_CLOSED: "Closed",
}

# Priorities
PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"
TICKET_PRIORITIES = (PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_URGENT)

PRIORITY_LABELS = {
    PRIORITY_LOW: "Low",
    PRIORITY_NORMAL: "Normal",
    PRIORITY_HIGH: "High",
    PRIORITY_URGENT: "Urgent",
}

# Categories
TICKET_CATEGORIES = ("account", "documents", "billing", "bug", "feature", "abuse", "other")
TICKET_CATEGORY_LABELS = {
    "account": "Account",
    "documents": "Documents",
    "billing": "Billing",
    "bug": "Bug report",
    "feature": "Feature request",
    "abuse": "Abuse report",
    "other": "Other",
}


class Ticket(db.Model):
    """A support ticket opened by a user."""

    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20), nullable=False, default="other", index=True)
    status = db.Column(db.String(15), nullable=False, default=TICKET_OPEN, index=True)
    priority = db.Column(db.String(10), nullable=False, default=PRIORITY_NORMAL, index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", foreign_keys=[user_id], back_populates="tickets")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    messages = db.relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Ticket {self.id} {self.status}>"

    @property
    def status_label(self) -> str:
        return TICKET_STATUS_LABELS.get(self.status, self.status)

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, self.priority)

    @property
    def category_label(self) -> str:
        return TICKET_CATEGORY_LABELS.get(self.category, self.category)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "category": self.category,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TicketMessage(db.Model):
    """A single message inside a ticket thread."""

    __tablename__ = "ticket_messages"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_staff = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    ticket = db.relationship("Ticket", back_populates="messages")
    user = db.relationship("User")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<TicketMessage {self.id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "body": self.body,
            "is_staff": self.is_staff,
            "author": self.user.effective_name if self.user else "Unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
