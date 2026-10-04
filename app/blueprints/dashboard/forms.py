"""WTForms used by the user dashboard."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    Optional,
    Regexp,
)

from ...models import User
from ...services.utils import is_strong_password
from wtforms.validators import ValidationError

THEMES = [("auto", "System"), ("light", "Light"), ("dark", "Dark")]


def _current_password_check(form, field):  # noqa: ANN001
    from flask_login import current_user

    if not current_user.check_password(field.data):
        raise ValidationError("Your current password is incorrect.")


class ProfileForm(FlaskForm):
    display_name = StringField(
        "Display name",
        validators=[DataRequired(message="Enter a display name."), Length(min=2, max=80)],
    )
    bio = TextAreaField(
        "Bio",
        validators=[Optional(), Length(max=500, message="Bio must be 500 characters or fewer.")],
    )
    avatar = FileField(
        "Avatar",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Only PNG, JPG, GIF or WebP images."),
        ],
    )
    theme = SelectField("Theme", choices=THEMES)
    interests = StringField("Interests (comma separated)")
    submit = SubmitField("Save profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Enter your current password."), _current_password_check],
    )
    new_password = PasswordField(
        "New password",
        validators=[DataRequired(message="Choose a new password.")],
    )
    confirm = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Confirm your new password."),
            EqualTo("new_password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Update password")

    def validate_new_password(self, field):  # noqa: ANN001
        if not is_strong_password(field.data):
            raise ValidationError(
                "Password must be 8+ characters with upper/lower case, a number and a symbol."
            )


class DeleteAccountForm(FlaskForm):
    password = PasswordField(
        "Confirm with your password",
        validators=[DataRequired(message="Enter your password to confirm.")],
    )
    confirm = BooleanField(
        "I understand this permanently deletes my account and documents",
        validators=[DataRequired(message="You must acknowledge the consequences.")],
    )
    submit = SubmitField("Delete my account")


class TicketForm(FlaskForm):
    subject = StringField(
        "Subject",
        validators=[DataRequired(message="Give your ticket a subject."), Length(min=5, max=200)],
    )
    category = SelectField(
        "Category",
        choices=[
            ("account", "Account"),
            ("documents", "Documents"),
            ("billing", "Billing"),
            ("bug", "Bug report"),
            ("feature", "Feature request"),
            ("abuse", "Abuse report"),
            ("other", "Other"),
        ],
    )
    message = TextAreaField(
        "How can we help?",
        validators=[DataRequired(message="Describe your issue."), Length(min=10, max=5000)],
    )
    submit = SubmitField("Open ticket")
