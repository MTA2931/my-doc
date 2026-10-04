"""WTForms used by the admin panel."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from ...models import ROLE_ADMIN, ROLE_SUPPORT, ROLE_SUPER, User
from ...services.utils import is_strong_password
from wtforms.validators import ValidationError

ROLE_CHOICES = [
    (ROLE_SUPPORT, "Support"),
    (ROLE_ADMIN, "Admin"),
    (ROLE_SUPER, "Super Admin"),
]


def _unique_username(form, field):  # noqa: ANN001
    if User.query.filter(User.username == field.data).first():
        raise ValidationError("That username is already taken.")


def _unique_email(form, field):  # noqa: ANN001
    if User.query.filter(User.email == (field.data or "").lower()).first():
        raise ValidationError("That e-mail is already registered.")


class AdminCreateForm(FlaskForm):
    """Create a new staff account (Super Admin only)."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=30),
            Regexp(r"^[A-Za-z0-9_]{3,30}", message="Letters, numbers and underscores only."),
            _unique_username,
        ],
    )
    email = StringField(
        "E-mail",
        validators=[DataRequired(), Email(), Length(max=255), _unique_email],
    )
    password = StringField(
        "Temporary password",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    role = SelectField("Role", choices=ROLE_CHOICES, default=ROLE_SUPPORT)
    submit = SubmitField("Create staff account")

    def validate_password(self, field):  # noqa: ANN001
        if not is_strong_password(field.data):
            raise ValidationError(
                "Password must be 8+ characters with upper/lower case, a number and a symbol."
            )


class ReportNoteForm(FlaskForm):
    """Optional resolution note when handling a report."""

    note = TextAreaField(
        "Resolution note",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Submit")


class SiteSettingsForm(FlaskForm):
    site_name = StringField("Site name", validators=[DataRequired(), Length(max=60)])
    site_tagline = StringField("Tagline", validators=[Optional(), Length(max=140)])
    footer_note = StringField(
        "Footer note", validators=[DataRequired(), Length(max=140)]
    )
    default_theme = SelectField(
        "Default theme",
        choices=[("auto", "Follow OS"), ("light", "Light"), ("dark", "Dark")],
    )
    registration_enabled = BooleanField("Allow new registrations")
    maintenance_mode = BooleanField("Maintenance mode")
    submit = SubmitField("Save settings")
