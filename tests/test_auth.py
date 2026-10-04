"""Authentication flows: signup, login, logout, password reset, verification."""

from app.models import User

from .conftest import login, make_user, register


def test_signup_creates_account(client, app):
    resp = register(client)
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.filter_by(username="newbie").first()
        assert user is not None
        assert user.check_password("Str0ng!pass")
        assert [t.name for t in user.interests] == ["python"]


def test_signup_rejects_duplicate_username(client, app):
    register(client)
    client.post("/logout")
    resp = register(client, email="other2@test.dev")
    assert resp.status_code == 200  # re-renders with errors
    assert b"That username is already taken." in resp.data


def test_signup_rejects_weak_password(client):
    resp = register(client, password="abc", confirm="abc")
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data or b"Password" in resp.data


def test_signup_requires_terms(client):
    resp = register(client, agree="")
    assert resp.status_code == 200
    assert b"must accept" in resp.data


def test_login_success_and_logout(client, app):
    with app.app_context():
        make_user(username="alice", email="alice@test.dev")
    resp = login(client, "alice@test.dev", "Str0ng!pass")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/home")

    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302


def test_login_with_username_works(client, app):
    with app.app_context():
        make_user(username="alice", email="alice@test.dev")
    resp = login(client, "alice", "Str0ng!pass")
    assert resp.status_code == 302


def test_login_wrong_password(client, app):
    with app.app_context():
        make_user(username="alice", email="alice@test.dev")
    resp = login(client, "alice@test.dev", "wrong-password")
    assert resp.status_code == 200
    assert b"Invalid credentials" in resp.data


def test_home_requires_login(client):
    resp = client.get("/home", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_next_redirect_is_safe(client, app):
    with app.app_context():
        make_user(username="alice", email="alice@test.dev")
    # Local next target is honoured.
    resp = client.post("/login?next=/dashboard/",
                       data={"email": "alice@test.dev", "password": "Str0ng!pass"})
    assert resp.headers["Location"].endswith("/dashboard/")
    client.post("/logout")

    # External next target is ignored (open-redirect protection).
    resp = client.post("/login?next=https://evil.example",
                       data={"email": "alice@test.dev", "password": "Str0ng!pass"})
    assert resp.headers["Location"].endswith("/home")


def test_banned_user_cannot_login(client, app):
    with app.app_context():
        user = make_user(username="bad", email="bad@test.dev")
        user.is_banned = True
        app.extensions  # noqa: B018 - touch to keep linters quiet
        from app.extensions import db as _db

        _db.session.commit()
    resp = login(client, "bad@test.dev", "Str0ng!pass")
    assert resp.status_code == 200
    assert b"suspended" in resp.data


def test_password_reset_flow(client, app):
    with app.app_context():
        user = make_user(username="resetme", email="resetme@test.dev")

    resp = client.post("/forgot-password", data={"email": "resetme@test.dev"})
    assert resp.status_code == 302

    with app.app_context():
        user = User.query.filter_by(email="resetme@test.dev").first()
        token = user.reset_token
        assert token

    resp = client.post(
        f"/reset-password?token={token}",
        data={"password": "N3w!Password", "confirm": "N3w!Password"},
    )
    assert resp.status_code == 302

    with app.app_context():
        user = User.query.filter_by(email="resetme@test.dev").first()
        assert user.reset_token is None
        assert user.check_password("N3w!Password")


def test_invalid_reset_token_redirects(client):
    resp = client.get("/reset-password?token=nope", follow_redirects=True)
    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.data


def test_email_verification(client, app):
    with app.app_context():
        user = make_user(username="verify", email="verify@test.dev",
                         password="Str0ng!pass")
        user.email_verified = False
        user.verification_token = "verify-token-123"
        from app.extensions import db as _db

        _db.session.commit()

    resp = client.get("/verify-email?token=verify-token-123", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="verify").first()
        assert user.email_verified is True
        assert user.verification_token is None
