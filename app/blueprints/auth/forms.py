"""WTForms used by the auth blueprint."""

from __future__ import annotations

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from ...models import User
from ...services.utils import is_strong_password

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def _unique_username(form, field):  # noqa: ANN001 - WTForms validator signature
    if User.query.filter(User.username == field.data).first():
        raise ValidationError("That username is already taken.")


def _unique_email(form, field):  # noqa: ANN001
    if User.query.filter(User.email == (field.data or "").lower()).first():
        raise ValidationError("An account with that e-mail already exists.")


def _strong_password(form, field):  # noqa: ANN001
    if not is_strong_password(field.data):
        raise ValidationError(
            "Password must be at least 8 characters and include upper/lower "
            "case letters, a number and a symbol."
        )


class LoginForm(FlaskForm):
    email = StringField(
        "E-mail or username",
        validators=[DataRequired(message="Enter your e-mail or username.")],
    )
    password = PasswordField("Password", validators=[DataRequired(message="Enter your password.")])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class SignupForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Choose a username."),
            Length(min=3, max=30, message="Username must be 3–30 characters."),
            Regexp(USERNAME_RE, message="Use only letters, numbers and underscores."),
            _unique_username,
        ],
    )
    email = StringField(
        "E-mail",
        validators=[
            DataRequired(message="Enter your e-mail."),
            Email(message="Enter a valid e-mail address."),
            Length(max=255),
            _unique_email,
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Choose a password."), _strong_password],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Confirm your password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    interests = StringField("Interests")  # comma separated, filled by the JS step
    agree = BooleanField(
        "I agree to the terms and community guidelines",
        validators=[DataRequired(message="You must accept the terms to continue.")],
    )
    submit = SubmitField("Create account")


class ForgotPasswordForm(FlaskForm):
    email = StringField(
        "E-mail",
        validators=[DataRequired(message="Enter your e-mail."), Email(message="Enter a valid e-mail address.")],
    )
    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New password",
        validators=[DataRequired(message="Choose a new password."), _strong_password],
    )
    confirm = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Confirm your new password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Reset password")


class InterestsForm(FlaskForm):
    """Onboarding step: comma separated tag names from the hidden field."""

    interests = StringField("Interests", validators=[DataRequired(message="Pick at least one interest.")])
    submit = SubmitField("Save interests")
