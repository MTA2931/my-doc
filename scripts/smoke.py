"""Quick smoke test: renders every major page and hits key API routes.

Run manually:  python scripts/smoke.py
(Part of the development toolkit — pytest suite lives in /tests.)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import ROLE_ADMIN, ROLE_SUPER, ROLE_USER, Tag, User  # noqa: E402
from app.models.document import STATUS_PUBLISHED, Document  # noqa: E402
from app.services.markdown_service import render_markdown  # noqa: E402
from app.services.utils import reading_time_minutes  # noqa: E402

SAMPLE_MD = """# Hello world

This is **bold**, *italic* and `code`.

```python
print("hi")
```

| a | b |
|---|---|
| 1 | 2 |

- item one
- [x] done
"""


def main() -> int:
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        tag = Tag.get_or_create("python")
        alice = User(username="alice", email="alice@test.com",
                     role=ROLE_USER, display_name="Alice")
        alice.set_password("Passw0rd!x")
        db.session.add(alice)
        db.session.flush()
        alice.interests.append(tag)

        admin = User(username="boss", email="boss@test.com",
                     role=ROLE_SUPER, display_name="Boss")
        admin.set_password("Passw0rd!x")
        db.session.add(admin)
        db.session.flush()

        doc = Document(
            user_id=alice.id,
            title="Hello world",
            slug="hello-world",
            summary="A smoke-test document.",
            content_md=SAMPLE_MD,
            content_html=render_markdown(SAMPLE_MD),
            status=STATUS_PUBLISHED,
            reading_time=reading_time_minutes(SAMPLE_MD),
        )
        doc.tags.append(tag)
        db.session.add(doc)
        db.session.commit()
        doc_id, admin_id = doc.id, admin.id

    client = app.test_client()
    failures = []

    def check(path, expect=(200, 302), methods=("GET",)):
        for method in methods:
            resp = getattr(client, method.lower())(path)
            ok = resp.status_code in expect
            status = "OK  " if ok else "FAIL"
            print(f"{status} {method:4s} {path} -> {resp.status_code}")
            if not ok:
                failures.append((path, resp.status_code, resp.data[:600]))

    # Public pages
    check("/")
    check("/my-doc")
    check("/signup")
    check("/login")
    check("/forgot-password")
    check("/reset-password?token=bogus", expect=(302,))
    check("/verify-email?token=bogus", expect=(302,))
    check("/doc/hello-world")
    check("/doc/missing-doc", expect=(404,))
    check("/nope", expect=(404,))

    # Authenticated as regular user
    resp = client.post("/login", data={"email": "alice@test.com",
                                       "password": "Passw0rd!x"},
                       follow_redirects=False)
    print("login ->", resp.status_code)
    if resp.status_code != 302:
        failures.append(("login", resp.status_code, resp.data[:600]))

    check("/home")
    check("/interests")
    check("/doc/new")
    check(f"/doc/{doc_id}/edit")
    check("/dashboard/")
    check("/dashboard/documents")
    check("/dashboard/saves")
    check("/dashboard/settings")
    check("/dashboard/change-password")
    check("/dashboard/tickets")
    check("/dashboard/tickets/new")
    check("/dashboard/tickets/1", expect=(404,))  # none yet
    check("/admin/", expect=(403,))               # role gate
    check("/admin/users", expect=(403,))

    # API
    check("/api/feed?tab=latest")
    check("/api/feed?tab=foryou&q=hello")
    check("/api/tags?q=py")
    resp = client.post("/api/documents", json={
        "title": "API created doc",
        "content_md": "Body text for the API doc.",
        "tags": "python, api",
        "status": "draft",
    })
    print("POST /api/documents ->", resp.status_code)
    if resp.status_code != 201:
        failures.append(("api create", resp.status_code, resp.data[:600]))

    resp = client.post(f"/api/documents/{doc_id}/save", json={})
    print("POST save toggle ->", resp.status_code)
    if resp.status_code != 200:
        failures.append(("api save", resp.status_code, resp.data[:600]))

    # Admin as super admin
    client.post("/logout")
    resp = client.post("/login", data={"email": "boss@test.com",
                                       "password": "Passw0rd!x"})
    print("admin login ->", resp.status_code)

    # Boss reports alice's document (cannot report your own).
    resp = client.post(f"/api/documents/{doc_id}/report",
                       json={"reason": "spam", "details": "test"})
    print("POST report ->", resp.status_code)
    if resp.status_code != 201:
        failures.append(("api report", resp.status_code, resp.data[:600]))

    check("/admin/")
    check("/admin/users")
    check(f"/admin/users/{admin_id}")
    check("/admin/documents")
    check("/admin/tickets")
    check("/admin/reports")
    check("/admin/admins")
    check("/admin/settings")
    check("/api/admin/stats")

    print()
    if failures:
        print(f"{len(failures)} FAILURES:")
        for path, code, body in failures:
            print("-" * 60)
            print(path, code)
            print(body.decode("utf-8", "replace"))
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
