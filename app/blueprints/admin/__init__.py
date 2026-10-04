"""Admin blueprint — role-gated panel.

``__init__`` creates the blueprint; routes live in ``routes.py`` so this
module stays import-light for decorators used elsewhere.
"""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import routes  # noqa: E402,F401  (registers routes on admin_bp)
