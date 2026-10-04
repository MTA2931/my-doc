"""MyDoc application factory.

Creates and configures the Flask application: extensions, blueprints,
error handlers, security headers, template helpers and CLI commands.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, render_template, request
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import get_config
from .extensions import csrf, db, limiter, login_manager, migrate

_engine_pragma_registered = False


# ---------------------------------------------------------------------------
# SQLite hardening (foreign keys ON)
# ---------------------------------------------------------------------------
def _register_sqlite_pragma() -> None:
    global _engine_pragma_registered
    if _engine_pragma_registered:
        return

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _engine_pragma_registered = True


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_app(config_object=None) -> Flask:
    """Application factory — build and return a configured Flask app."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or get_config())

    # Ensure instance folder exists (SQLite DB + local config live here).
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "app/static/uploads"), exist_ok=True)

    _register_sqlite_pragma()
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_request_hooks(app)
    _register_template_helpers(app)
    _register_cli(app)
    _configure_logging(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(reason):  # pragma: no cover - exercised via invalid token
        if request.path.startswith("/api/"):
            return jsonify(error="CSRF token missing or invalid."), 400
        from flask import flash

        flash("Your session expired. Please try again.", "error")
        return render_template("errors/400.html", reason=getattr(reason, "description", "")), 400


def _register_blueprints(app: Flask) -> None:
    from .blueprints.admin import admin_bp
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.docs import docs_bp
    from .blueprints.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)



# ---------------------------------------------------------------------------
# Error handlers (styled pages for browsers, JSON for the API)
# ---------------------------------------------------------------------------
def _register_error_handlers(app: Flask) -> None:
    def wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(400)
    def bad_request(err):  # pragma: no cover - CSRF / malformed input
        if wants_json():
            return jsonify(error=getattr(err, "description", "Bad request.")), 400
        return render_template("errors/400.html", reason=getattr(err, "description", "")), 400

    @app.errorhandler(403)
    def forbidden(err):
        if wants_json():
            return jsonify(error="Insufficient permissions."), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(err):
        if wants_json():
            return jsonify(error="Resource not found."), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        if wants_json():
            return jsonify(error="Method not allowed."), 405
        return render_template("errors/404.html"), 405

    @app.errorhandler(413)
    def payload_too_large(err):
        if wants_json():
            return jsonify(error="Upload too large."), 413
        from flask import flash

        flash("That file is too large.", "error")
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(err):  # pragma: no cover - defensive
        app.logger.exception("Unhandled server error")
        if wants_json():
            return jsonify(error="Internal server error."), 500
        return render_template("errors/500.html"), 500


# ---------------------------------------------------------------------------
# Request hooks: security headers + maintenance mode
# ---------------------------------------------------------------------------
def _register_request_hooks(app: Flask) -> None:
    from .models.misc import get_setting

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", app.config.get("REFERRER_POLICY", "strict-origin-when-cross-origin"))
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if app.config.get("CONTENT_SECURITY_POLICY"):
            response.headers.setdefault("Content-Security-Policy", app.config["CONTENT_SECURITY_POLICY"])
        if request.is_secure or app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.before_request
    def enforce_maintenance():
        """Block ordinary traffic while maintenance mode is enabled."""
        if not app.config.get("TESTING") and get_setting("maintenance_mode", "0") == "1":
            path = request.path
            if (
                path.startswith("/static/")
                or path.startswith("/api/")
                or path.startswith("/admin/")
                or path in ("/login", "/logout")
            ):
                return None
            from flask import abort

            abort(503)
        return None

    @app.errorhandler(503)
    def maintenance(err):  # pragma: no cover - toggled by admins
        if request.path.startswith("/api/"):
            return jsonify(error="Maintenance mode is enabled."), 503
        return render_template("errors/503.html"), 503



# ---------------------------------------------------------------------------
# Template helpers & filters
# ---------------------------------------------------------------------------
def _register_template_helpers(app: Flask) -> None:
    from datetime import datetime, timezone

    from .models.misc import get_setting
    from .models.user import Tag
    from .services.utils import format_number, time_ago

    @app.template_filter("time_ago")
    def _time_ago(dt):
        return time_ago(dt)

    @app.template_filter("numfmt")
    def _numfmt(n):
        return format_number(n)

    @app.template_filter("strftime")
    def _strftime(dt, fmt: str = "%b %d, %Y"):
        if dt is None:
            return ""
        return dt.strftime(fmt)

    @app.context_processor
    def inject_globals():
        """Values available to every template."""
        return {
            "site_name": get_setting("site_name", "MyDoc"),
            "site_tagline": get_setting("site_tagline", ""),
            "footer_note": get_setting("footer_note", "Developed by MTA Company"),
            "registration_enabled": get_setting("registration_enabled", "1") == "1",
            "current_year": datetime.now(timezone.utc).year,
            "all_tags": Tag.query.order_by(Tag.name).all(),
        }


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------
def _register_cli(app: Flask) -> None:
    import click
    from flask.cli import with_appcontext

    from .models import ROLE_SUPER, User
    from .services.utils import is_strong_password

    @app.cli.command("create-superadmin")
    @with_appcontext
    @click.option("--username", prompt=True, help="Username for the Super Admin.")
    @click.option("--email", prompt=True, help="E-mail for the Super Admin.")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
                  help="Password for the Super Admin.")
    def create_superadmin(username, email, password):
        """Bootstrap the first Super Admin account."""
        if not is_strong_password(password):
            raise click.ClickException(
                "Password must be 8+ characters and mix upper, lower, digits, symbols."
            )
        if User.query.filter(
            (User.username == username) | (User.email == email.lower())
        ).first():
            raise click.ClickException("A user with that username or e-mail already exists.")
        user = User(
            username=username,
            email=email.lower(),
            role=ROLE_SUPER,
            display_name=username,
            email_verified=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Super Admin '{user.username}' created successfully.")

    @app.cli.command("seed-tags")
    @with_appcontext
    def seed_tags():
        """Create the default set of topic tags."""
        from .models import Tag as TagModel
        from .services.tag_seed import DEFAULT_TAGS

        created = 0
        for name in DEFAULT_TAGS:
            tag = TagModel.query.filter(TagModel.name == name).first()
            if tag is None:
                db.session.add(TagModel(name=name))
                created += 1
        db.session.commit()
        click.echo(f"Seeded {created} new tags ({len(DEFAULT_TAGS)} total).")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _configure_logging(app: Flask) -> None:
    if app.debug or app.testing:
        app.logger.setLevel(logging.INFO)
        return
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(log_dir, "mydoc.log"), maxBytes=1_000_000, backupCount=5
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    except OSError:  # pragma: no cover - log directory not writable
        app.logger.warning("Could not create log file; logging to console only.")

