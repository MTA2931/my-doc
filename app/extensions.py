"""Flask extensions instantiated here and initialized inside the app factory.

Keeping extensions in their own module avoids circular imports between the
factory and the blueprints/models that use them.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)

# Login configuration (strings point at the auth blueprint's login view).
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


@login_manager.unauthorized_handler
def _unauthorized():
    """Redirect browsers to /login; return JSON 401 for API requests."""
    from flask import jsonify, redirect, request, url_for

    if request.path.startswith("/api/"):
        return jsonify(error="Authentication required."), 401
    target = request.full_path.rstrip("?") if request.query_string else request.path
    return redirect(url_for("auth.login", next=target))
