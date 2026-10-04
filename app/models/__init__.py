"""Database models for MyDoc.

Importing this package exposes every model so Alembic can autogenerate
migrations and blueprints can import from ``app.models`` directly.
"""

from .user import ROLE_ADMIN, ROLE_SUPPORT, ROLE_SUPER, ROLE_USER, ROLES, Tag, User
from .document import Document, Report, Save, document_tags
from .support import Ticket, TicketMessage
from .misc import Activity, AuditLog, SiteSetting, get_setting, set_setting

__all__ = [
    "User",
    "Tag",
    "Document",
    "Save",
    "Report",
    "Ticket",
    "TicketMessage",
    "AuditLog",
    "Activity",
    "SiteSetting",
    "get_setting",
    "set_setting",
    "ROLES",
    "ROLE_USER",
    "ROLE_SUPPORT",
    "ROLE_ADMIN",
    "ROLE_SUPER",
    "document_tags",
]
