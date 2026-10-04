"""Authentication routes: signup, login, logout, password reset, verification."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ...extensions import db, limiter
from ...models import ROLES, ROLE_USER, Tag, User, get_setting
from ...models.misc import Activity
from ...services.mailer import send_password_reset_email, send_verification_email
from ...services.utils import random_token
from .forms import ForgotPasswordForm, InterestsForm, LoginForm, ResetPasswordForm, SignupForm

auth_bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    """Only allow local redirect targets (open-redirect protection)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("main.home")


def _split_interests(raw: str) -> list[str]:
    return [part.strip().lower() for part in (raw or "").split(",") if part.strip()][:20]


# ---------------------------------------------------------------------------
# Sign up
# ---------------------------------------------------------------------------
@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if get_setting("registration_enabled", "1") != "1":
        abort(403)

    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=ROLE_USER,
            display_name=form.username.data.strip(),
            verification_token=random_token(),
        )
        user.set_password(form.password.data)
        for name in _split_interests(form.interests.data):
            try:
                user.interests.append(Tag.get_or_create(name))
            except ValueError:
                continue
        db.session.add(user)
        db.session.flush()
        Activity.log(user, "welcome", "Welcome to MyDoc! Your account was created.")
        db.session.commit()

        send_verification_email(user)
        login_user(user)
        flash("Welcome to MyDoc! Check your inbox to verify your e-mail.", "success")
        if not user.interests:
            return redirect(url_for("auth.interests"))
        return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/signup.html", form=form)


# ---------------------------------------------------------------------------
# Log in / out
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        ident = (form.email.data or "").strip()
        user = User.query.filter(
            (User.email == ident.lower()) | (User.username == ident)
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid credentials. Please check your e-mail/username and password.", "error")
        elif user.is_banned:
            flash("This account has been suspended. Contact support for help.", "error")
        else:
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.effective_name}!", "success")
            if not user.interests:
                return redirect(url_for("auth.interests"))
            return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.landing"))



# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter(User.email == form.email.data.strip().lower()).first()
        if user is not None:
            from datetime import timedelta

            user.reset_token = random_token()
            user.reset_expires = datetime.now(timezone.utc) + timedelta(
                seconds=current_app.config["TOKEN_MAX_AGE_SECONDS"]
            )
            db.session.commit()
            send_password_reset_email(user)

        # Same message either way — never leak which addresses exist.
        flash("If that address has an account, a reset link is on its way.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    token = request.args.get("token", "") or request.form.get("token", "")
    user = None
    if token:
        user = User.query.filter(User.reset_token == token).first()
        if user is not None and user.reset_expires is not None:
            now = datetime.now(timezone.utc)
            expires = user.reset_expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                user.reset_token = None
                user.reset_expires = None
                db.session.commit()
                user = None

    if user is None:
        flash("This password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_expires = None
        db.session.commit()
        flash("Your password has been updated. Log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


# ---------------------------------------------------------------------------
# E-mail verification
# ---------------------------------------------------------------------------
@auth_bp.route("/verify-email")
def verify_email():
    token = request.args.get("token", "")
    user = User.query.filter(User.verification_token == token).first() if token else None
    if user is None:
        flash("This verification link is invalid or has already been used.", "error")
        return redirect(url_for("main.landing"))
    user.email_verified = True
    user.verification_token = None
    db.session.commit()
    flash("Your e-mail address has been verified. Thank you!", "success")
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Interests onboarding (first login / empty profile)
# ---------------------------------------------------------------------------
@auth_bp.route("/interests", methods=["GET", "POST"])
@login_required
def interests():
    form = InterestsForm()
    if form.validate_on_submit():
        names = _split_interests(form.interests.data)
        if not names:
            flash("Pick at least one interest.", "error")
        else:
            current_user.interests.clear()
            for name in names:
                try:
                    current_user.interests.append(Tag.get_or_create(name))
                except ValueError:
                    continue
            db.session.commit()
            flash("Your interests were saved — your feed is ready.", "success")
            return redirect(url_for("main.home"))

    selected = {t.name for t in current_user.interests}
    return render_template(
        "auth/interests.html",
        form=form,
        selected=selected,
    )

