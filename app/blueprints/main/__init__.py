"""Main blueprint: landing page (/), home feed (/home) and root redirect."""

from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...services.feeds import FEED_TABS, build_feed_query, paginate_feed

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Root: logged in -> /home, otherwise the public landing page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return redirect(url_for("main.landing"))


@main_bp.route("/my-doc")
def landing():
    """Public 3D landing page explaining the platform."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("landing/index.html")


@main_bp.route("/home")
@login_required
def home():
    """Personalised feed of published documents matching the user's interests."""
    tab = request.args.get("tab", "foryou")
    if tab not in FEED_TABS:
        tab = "foryou"
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    feed = paginate_feed(
        build_feed_query(tab, current_user, query or None),
        page,
        current_app.config["DOCS_PER_PAGE"],
    )
    return render_template(
        "home/index.html",
        feed=feed,
        tab=tab,
        search=query,
    )
