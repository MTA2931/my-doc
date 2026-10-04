"""JSON API endpoints: feed, tags, reports, tickets, theme, status codes."""

from .conftest import login, register


def test_feed_returns_expected_shape(client, app):
    resp = client.get("/api/feed?tab=latest")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data) >= {"docs", "page", "per_page", "total", "has_more", "tab", "q"}
    assert isinstance(data["docs"], list)


def test_feed_tab_validation(client):
    resp = client.get("/api/feed?tab=whatever")
    assert resp.get_json()["tab"] == "foryou"  # falls back safely


def test_tags_autocomplete(client, app):
    from app.extensions import db as _db
    from app.models import Tag

    with app.app_context():
        _db.session.add(Tag.get_or_create("python"))
        _db.session.commit()

    resp = client.get("/api/tags?q=pyth")
    assert resp.get_json()["tags"] == ["python"]


def test_report_flow(client, app):
    register(client, username="writer", email="writer@test.dev")
    doc = client.post("/api/documents", json={
        "title": "Reportable", "content_md": "content here", "status": "published",
    }).get_json()["doc"]
    client.post("/logout")

    register(client, username="reporter", email="reporter@test.dev")

    resp = client.post(f"/api/documents/{doc['id']}/report",
                       json={"reason": "spam", "details": "spammy content"})
    assert resp.status_code == 201
    assert resp.get_json()["reported"] is True

    # Duplicate pending report -> 409
    resp = client.post(f"/api/documents/{doc['id']}/report",
                       json={"reason": "spam"})
    assert resp.status_code == 409

    # Invalid reason -> 400
    resp = client.post(f"/api/documents/{doc['id']}/report",
                       json={"reason": "not-a-reason"})
    assert resp.status_code == 400
    assert "reason" in resp.get_json()["errors"]


def test_report_own_document_rejected(client, app):
    register(client, username="solo", email="solo@test.dev")
    doc = client.post("/api/documents", json={
        "title": "Mine", "content_md": "body", "status": "published",
    }).get_json()["doc"]

    resp = client.post(f"/api/documents/{doc['id']}/report",
                       json={"reason": "spam"})
    assert resp.status_code == 400
    assert "own document" in resp.get_json()["error"]


def test_ticket_reply_permissions(client, app):
    from app.extensions import db as _db
    from app.models import ROLE_SUPPORT
    from app.models.support import Ticket

    from .conftest import make_user

    with app.app_context():
        owner = make_user(username="client", email="client@test.dev")
        ticket = Ticket(user_id=owner.id, subject="Help with login", category="account")
        _db.session.add(ticket)
        _db.session.flush()
        ticket_id = ticket.id
        make_user(username="helper", email="helper@test.dev", role=ROLE_SUPPORT)
        make_user(username="stranger", email="stranger@test.dev")
        _db.session.commit()

    # Owner can reply.
    login(client, "client@test.dev", "Str0ng!pass")
    resp = client.post(f"/api/tickets/{ticket_id}/messages",
                       json={"body": "Any update?"})
    assert resp.status_code == 201
    client.post("/logout")

    # Stranger cannot.
    login(client, "stranger@test.dev", "Str0ng!pass")
    resp = client.post(f"/api/tickets/{ticket_id}/messages",
                       json={"body": "let me in"})
    assert resp.status_code == 403
    client.post("/logout")

    # Support can.
    login(client, "helper@test.dev", "Str0ng!pass")
    resp = client.post(f"/api/tickets/{ticket_id}/messages",
                       json={"body": "We are on it."})
    assert resp.status_code == 201


def test_ticket_reply_validation(client, app):
    from app.extensions import db as _db
    from app.models.support import Ticket

    from .conftest import make_user

    with app.app_context():
        owner = make_user(username="client2", email="client2@test.dev")
        ticket = Ticket(user_id=owner.id, subject="Issue", category="bug")
        _db.session.add(ticket)
        _db.session.flush()
        ticket_id = ticket.id
        _db.session.commit()

    login(client, "client2@test.dev", "Str0ng!pass")
    resp = client.post(f"/api/tickets/{ticket_id}/messages", json={"body": ""})
    assert resp.status_code == 400
    assert "body" in resp.get_json()["errors"]


def test_theme_endpoint(client, app):
    register(client)
    resp = client.post("/api/me/theme", json={"theme": "light"})
    assert resp.status_code == 200
    assert resp.get_json()["theme"] == "light"

    resp = client.post("/api/me/theme", json={"theme": "neon"})
    assert resp.status_code == 400


def test_status_endpoint_validates(client, app):
    register(client)
    doc = client.post("/api/documents", json={
        "title": "Status test", "content_md": "body", "status": "draft",
    }).get_json()["doc"]

    resp = client.post(f"/api/documents/{doc['id']}/status",
                       json={"status": "sideways"})
    assert resp.status_code == 400


def test_security_headers_present(client):
    resp = client.get("/my-doc")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "Content-Security-Policy" in resp.headers
    assert "Referrer-Policy" in resp.headers


def test_meta_author_is_mta_company(client):
    resp = client.get("/my-doc")
    assert b'<meta name="author" content="MTA Company">' in resp.data


def test_footer_shows_mta_company(client):
    resp = client.get("/my-doc")
    assert b"Developed by MTA Company" in resp.data

