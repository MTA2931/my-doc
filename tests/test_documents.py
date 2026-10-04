"""Document CRUD, privacy, sanitization, saves and status transitions."""

from app.models.document import STATUS_DRAFT, Document

from .conftest import register


def _create_doc(client, title="My First Doc", body="Hello **world**",
                status="draft", tags="python"):
    return client.post(
        "/api/documents",
        json={"title": title, "content_md": body, "summary": "Sum",
              "tags": tags, "status": status},
    )


def _get_document(app, doc_id):
    from app.extensions import db as _db

    return _db.session.get(Document, doc_id)


def test_create_document_requires_login(client):
    resp = client.post("/api/documents", json={"title": "Anonymous"})
    assert resp.status_code == 401


def test_create_and_edit_document(client, app):
    register(client)
    resp = _create_doc(client)
    assert resp.status_code == 201
    doc = resp.get_json()["doc"]
    assert doc["slug"].startswith("my-first-doc")

    resp = client.put(f"/api/documents/{doc['id']}",
                      json={"title": "Edited title", "content_md": "New body",
                            "status": "draft", "tags": "python"})
    assert resp.status_code == 200
    updated = resp.get_json()["doc"]
    assert updated["title"] == "Edited title"
    assert updated["slug"] != ""


def test_slug_is_unique(client, app):
    register(client)
    first = _create_doc(client, title="Same Title").get_json()["doc"]
    second = _create_doc(client, title="Same Title").get_json()["doc"]
    assert first["slug"] != second["slug"]


def test_publish_flow(client, app):
    register(client)
    doc = _create_doc(client, status="draft").get_json()["doc"]
    assert doc["status"] == "draft"

    resp = client.post(f"/api/documents/{doc['id']}/status",
                       json={"status": "published"})
    assert resp.status_code == 200
    assert resp.get_json()["doc"]["status"] == "published"

    page = client.get(f"/doc/{doc['slug']}")
    assert page.status_code == 200


def test_draft_is_private(client, app):
    register(client)
    doc = _create_doc(client, status="draft").get_json()["doc"]
    client.post("/logout")

    resp = client.get(f"/doc/{doc['slug']}")
    assert resp.status_code == 404


def test_owner_can_edit_others_cannot(client, app):
    register(client, username="owner", email="owner@test.dev")
    doc = _create_doc(client).get_json()["doc"]
    client.post("/logout")

    register(client, username="intruder", email="intruder@test.dev")
    resp = client.put(f"/api/documents/{doc['id']}",
                      json={"title": "Hacked", "content_md": "x", "status": "draft"})
    assert resp.status_code == 403


def test_delete_document(client, app):
    register(client)
    doc = _create_doc(client).get_json()["doc"]
    resp = client.delete(f"/api/documents/{doc['id']}")
    assert resp.status_code == 200
    with app.app_context():
        assert _get_document(app, doc["id"]) is None


def test_xss_is_sanitized(client, app):
    """Script tags must never survive into stored HTML."""
    register(client)
    evil = "<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>"
    resp = _create_doc(client, body=evil, status="published")
    assert resp.status_code == 201
    payload = resp.get_json()["doc"]

    with app.app_context():
        doc = _get_document(app, payload["id"])
        html = doc.content_html
        assert "<script" not in html
        assert "onerror" not in html

    page = client.get(f"/doc/{payload['slug']}")
    assert b"<script>alert(1)</script>" not in page.data


def test_markdown_renders_safely():
    from app.services.markdown_service import render_markdown

    html = render_markdown("# Title\n\n**bold** and `code`\n\n[ok](https://example.com)")
    assert "<h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert 'href="https://example.com"' in html

    # Dangerous inputs are neutralised.
    assert "<script" not in render_markdown("<script>bad()</script>")
    assert "javascript:" not in render_markdown("[click](javascript:alert(1))")


def test_save_toggle(client, app):
    register(client, username="saver", email="saver@test.dev")
    doc = _create_doc(client, status="published").get_json()["doc"]
    client.post("/logout")

    register(client, username="bookmarker", email="bm@test.dev")
    resp = client.post(f"/api/documents/{doc['id']}/save")
    assert resp.status_code == 200
    assert resp.get_json() == {"saved": True, "count": 1}

    resp = client.post(f"/api/documents/{doc['id']}/save")
    assert resp.get_json() == {"saved": False, "count": 0}


def test_autosave_does_not_publish(client, app):
    register(client)
    doc = _create_doc(client, status="draft").get_json()["doc"]
    resp = client.put(f"/api/documents/{doc['id']}/autosave",
                      json={"title": "Typed title", "content_md": "typed body"})
    assert resp.status_code == 200
    with app.app_context():
        stored = _get_document(app, doc["id"])
        assert stored.title == "Typed title"
        assert stored.status == STATUS_DRAFT


def test_publish_requires_content(client, app):
    register(client)
    resp = client.post("/api/documents",
                       json={"title": "Empty", "content_md": "", "status": "published"})
    assert resp.status_code == 400
    assert "content_md" in resp.get_json()["errors"]


def test_feed_excludes_drafts(client, app):
    register(client, username="pub", email="pub@test.dev")
    _create_doc(client, title="Visible", status="published")
    _create_doc(client, title="Hidden", status="draft")
    client.post("/logout")

    resp = client.get("/api/feed?tab=latest")
    titles = [d["title"] for d in resp.get_json()["docs"]]
    assert "Visible" in titles
    assert "Hidden" not in titles


def test_feed_search(client, app):
    register(client, username="searcher", email="searcher@test.dev")
    _create_doc(client, title="Kubernetes deep dive", tags="devops",
                status="published")
    client.post("/logout")

    resp = client.get("/api/feed?tab=latest&q=kubernetes")
    titles = [d["title"] for d in resp.get_json()["docs"]]
    assert "Kubernetes deep dive" in titles

    resp = client.get("/api/feed?tab=latest&q=zzz-no-match")
    assert resp.get_json()["docs"] == []

