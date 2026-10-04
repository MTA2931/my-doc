"""Shared pytest fixtures for the MyDoc test suite."""

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.models import ROLE_ADMIN, ROLE_SUPPORT, ROLE_SUPER, ROLE_USER, Tag, User
from app.models.document import STATUS_PUBLISHED, Document
from app.services.markdown_service import render_markdown
from app.services.utils import reading_time_minutes


@pytest.fixture(scope="session")
def app():
    """Application instance backed by an in-memory database.

    IMPORTANT: never yield while an app context is open — Flask reuses an
    active app context for requests, which would share ``g`` (and thus
    flask-login's cached current_user) across every test.
    """
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
    yield application
    with application.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(app):
    """Truncate data between tests but keep the schema."""
    yield
    with app.app_context():
        _db.session.rollback()
        try:
            for table in reversed(_db.metadata.sorted_tables):
                _db.session.execute(table.delete())
            _db.session.commit()
        except Exception:  # pragma: no cover - recovery path
            _db.session.rollback()
            raise
        finally:
            _db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------
def make_user(username="reader", email=None, role=ROLE_USER, password="Str0ng!pass",
              interests=("python",)):
    user = User(
        username=username,
        email=email or f"{username}@test.dev",
        role=role,
        display_name=username.title(),
        email_verified=True,
    )
    user.set_password(password)
    _db.session.add(user)
    _db.session.flush()
    # Seed a default interest so login lands on /home, not onboarding.
    for name in interests:
        user.interests.append(Tag.get_or_create(name))
    _db.session.commit()
    return user


def make_document(author, title="Test document", body="# Hello\n\nSome **content**.",
                  status=STATUS_PUBLISHED, slug=None):
    doc = Document(
        user_id=author.id,
        title=title,
        slug=slug or slugify_title(title),
        summary="A test document.",
        content_md=body,
        content_html=render_markdown(body),
        status=status,
        reading_time=reading_time_minutes(body),
    )
    if status == STATUS_PUBLISHED:
        from datetime import datetime, timezone

        doc.published_at = datetime.now(timezone.utc)
    _db.session.add(doc)
    _db.session.commit()
    return doc


def slugify_title(title: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


@pytest.fixture()
def user(app):
    with app.app_context():
        return make_user()


@pytest.fixture()
def other_user(app):
    with app.app_context():
        return make_user(username="other", email="other@test.dev")


@pytest.fixture()
def support_user(app):
    with app.app_context():
        return make_user(username="helper", role=ROLE_SUPPORT)


@pytest.fixture()
def admin_user(app):
    with app.app_context():
        return make_user(username="admin", role=ROLE_ADMIN)


@pytest.fixture()
def super_admin(app):
    with app.app_context():
        return make_user(username="root", role=ROLE_SUPER)


@pytest.fixture()
def published_doc(app, user):
    with app.app_context():
        return make_document(user)



def login(client, email_or_username, password):
    """POST to the login endpoint."""
    return client.post(
        "/login",
        data={"email": email_or_username, "password": password},
        follow_redirects=False,
    )


def register(client, username="newbie", email="newbie@test.dev",
             password="Str0ng!pass", interests="python", agree="y", **overrides):
    """POST to the signup endpoint."""
    data = {
        "username": username,
        "email": email,
        "password": password,
        "confirm": password,
        "interests": interests,
        "agree": agree,
    }
    data.update(overrides)
    return client.post("/signup", data=data, follow_redirects=False)
