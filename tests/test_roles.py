"""Role-based access control: Support / Admin / Super Admin boundaries."""

from app.models import ROLE_ADMIN, ROLE_SUPPORT, ROLE_SUPER, ROLE_USER, User

from .conftest import login, make_user, register

SUPPORT_PAGES = [
    "/admin/",
    "/admin/documents",
    "/admin/tickets",
    "/admin/reports",
]

ADMIN_PAGES = SUPPORT_PAGES + [
    "/admin/users",
    "/admin/settings",
]

SUPER_PAGES = ADMIN_PAGES + ["/admin/admins"]


def db_get_user(app, user_id):
    from app.extensions import db as _db

    return _db.session.get(User, user_id)


def test_regular_user_cannot_access_admin(client, app):
    register(client, username="plain", email="plain@test.dev")
    for path in SUPPORT_PAGES + ["/admin/admins"]:
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be 403 for members"


def test_anonymous_admin_access_redirects_to_login(client):
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_support_role_permissions(client, app):
    with app.app_context():
        make_user(username="sup", email="sup@test.dev", role=ROLE_SUPPORT)
    login(client, "sup@test.dev", "Str0ng!pass")

    for path in SUPPORT_PAGES:
        assert client.get(path).status_code == 200, f"{path} allowed for support"

    for path in ("/admin/users", "/admin/settings", "/admin/admins"):
        assert client.get(path).status_code == 403, f"{path} denied for support"


def test_admin_role_permissions(client, app):
    with app.app_context():
        make_user(username="adm", email="adm@test.dev", role=ROLE_ADMIN)
    login(client, "adm@test.dev", "Str0ng!pass")

    for path in ADMIN_PAGES:
        assert client.get(path).status_code == 200, f"{path} allowed for admin"

    assert client.get("/admin/admins").status_code == 403, "admins tab is super-only"


def test_super_admin_permissions(client, app):
    with app.app_context():
        make_user(username="boss", email="boss@test.dev", role=ROLE_SUPER)
    login(client, "boss@test.dev", "Str0ng!pass")

    for path in SUPER_PAGES:
        assert client.get(path).status_code == 200, f"{path} allowed for super admin"


def test_admin_stats_gate(client, app):
    """Support may view the dashboard stats; members may not."""
    with app.app_context():
        make_user(username="sup", email="sup@test.dev", role=ROLE_SUPPORT)
    login(client, "sup@test.dev", "Str0ng!pass")
    assert client.get("/api/admin/stats").status_code == 200
    client.post("/logout")

    register(client, username="plain2", email="plain2@test.dev")
    assert client.get("/api/admin/stats").status_code == 403


def test_admin_action_records_audit_log(client, app):
    with app.app_context():
        boss = make_user(username="boss", email="boss@test.dev", role=ROLE_SUPER)
        target = make_user(username="target", email="target@test.dev")
        boss_id, target_id = boss.id, target.id
    login(client, "boss@test.dev", "Str0ng!pass")

    resp = client.post(f"/admin/users/{target_id}/action",
                       data={"action": "ban"},
                       follow_redirects=False)
    assert resp.status_code == 302

    from app.models import AuditLog

    with app.app_context():
        entry = AuditLog.query.filter_by(action="user.ban").first()
        assert entry is not None
        assert entry.admin_id == boss_id
        assert entry.target_id == target_id



def test_only_super_admin_changes_super_role(client, app):
    with app.app_context():
        adm = make_user(username="adm", email="adm@test.dev", role=ROLE_ADMIN)
        adm_id = adm.id

    # Admin cannot grant the super role.
    login(client, "adm@test.dev", "Str0ng!pass")
    client.post(f"/admin/users/{adm_id}/action",
                data={"action": "role", "role": "super_admin"},
                follow_redirects=True)
    with app.app_context():
        assert db_get_user(app, adm_id).role == ROLE_ADMIN
    client.post("/logout")

    # Super admin CAN promote an admin.
    with app.app_context():
        make_user(username="boss", email="boss@test.dev", role=ROLE_SUPER)
    login(client, "boss@test.dev", "Str0ng!pass")
    client.post(f"/admin/users/{adm_id}/action",
                data={"action": "role", "role": "super_admin"})
    with app.app_context():
        assert db_get_user(app, adm_id).role == ROLE_SUPER


def test_last_super_admin_is_protected(client, app):
    with app.app_context():
        boss = make_user(username="boss", email="boss@test.dev", role=ROLE_SUPER)
        boss_id = boss.id

    login(client, "boss@test.dev", "Str0ng!pass")
    # Attempt to demote oneself — the last Super Admin must be preserved.
    resp = client.post(f"/admin/users/{boss_id}/action",
                       data={"action": "role", "role": "admin"},
                       follow_redirects=True)
    assert b"At least one Super Admin" in resp.data
    with app.app_context():
        assert db_get_user(app, boss_id).role == ROLE_SUPER


def test_super_admin_can_create_staff(client, app):
    with app.app_context():
        make_user(username="boss", email="boss@test.dev", role=ROLE_SUPER)
    login(client, "boss@test.dev", "Str0ng!pass")

    resp = client.post("/admin/admins", data={
        "username": "newstaff",
        "email": "newstaff@test.dev",
        "password": "Staff123!pw",
        "role": ROLE_SUPPORT,
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        staff = User.query.filter_by(username="newstaff").first()
        assert staff is not None
        assert staff.role == ROLE_SUPPORT


def test_support_cannot_ban_via_users_page(client, app):
    """Support never reaches the user action endpoint (capability gate)."""
    with app.app_context():
        victim = make_user(username="victim", email="victim@test.dev")
        victim_id = victim.id
    with app.app_context():
        make_user(username="sup", email="sup@test.dev", role=ROLE_SUPPORT)
    login(client, "sup@test.dev", "Str0ng!pass")

    resp = client.post(f"/admin/users/{victim_id}/action", data={"action": "ban"})
    assert resp.status_code == 403
    with app.app_context():
        assert db_get_user(app, victim_id).is_banned is False


def test_banned_user_cannot_login(client, app):
    with app.app_context():
        user = make_user(username="doomed", email="doomed@test.dev")
        doomed_id = user.id
        user.is_banned = True
        from app.extensions import db as _db

        _db.session.commit()

    resp = login(client, "doomed@test.dev", "Str0ng!pass")
    assert b"suspended" in resp.data
