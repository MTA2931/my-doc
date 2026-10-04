"""Reusable access-control decorators.

``role_required`` blocks endpoints server-side (the sidebar only hides links —
the server is the authority). Unauthorized anonymous users are redirected to
the login page with a ``next`` parameter; authenticated users with an
insufficient role receive the styled 403 page (or JSON for API routes).
"""

from __future__ import annotations

from functools import wraps

from flask import abort, jsonify, request, redirect, url_for
from flask_login import current_user


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def _unauthorized_response():
    """Redirect anonymous users to login; 403 for insufficient roles."""
    if _wants_json():
        return jsonify(error="Authentication required."), 401
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


def _forbidden_response(required: tuple[str, ...]):
    if _wants_json():
        return jsonify(error="Insufficient permissions.",
                       required=list(required)), 403
    abort(403)


def role_required(*roles: str):
    """Allow the view only when ``current_user.role`` is in ``roles``.

    Usage::

        @admin_bp.route("/users")
        @role_required(ROLE_ADMIN, ROLE_SUPER)
        def users(): ...
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return _unauthorized_response()
            if current_user.role not in roles:
                return _forbidden_response(roles)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def capability_required(capability: str):
    """Allow the view only when the user's role grants ``capability``.

    Uses the same centralised matrix as ``User.can()`` so the backend and the
    UI can never disagree about what a role may access.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return _unauthorized_response()
            if not current_user.can(capability):
                return _forbidden_response((capability,))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def login_required(view):
    """Thin wrapper so blueprints don't need two imports for the common case."""
    from flask_login import login_required as flask_login_required

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return _unauthorized_response()
        return flask_login_required(view)(*args, **kwargs)
    return wrapped
