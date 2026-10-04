"""Feed queries powering /home and the /api/feed endpoint."""

from __future__ import annotations

from flask import current_app
from sqlalchemy import or_

from ..extensions import db
from ..models import User
from ..models.document import (
    STATUS_PUBLISHED,
    VISIBILITY_PUBLIC,
    Document,
    document_tags,
)
from ..models.user import Tag

FEED_TABS = ("foryou", "latest", "popular")


def _base_query():
    """Published, public documents only."""
    return Document.query.filter(
        Document.status == STATUS_PUBLISHED,
        Document.visibility == VISIBILITY_PUBLIC,
    )


def _apply_search(query, term: str):
    """Match title, summary, content, tags or author name."""
    term = f"%{term.strip()}%"
    author_match = or_(
        User.username.ilike(term),
        User.display_name.ilike(term),
    )
    return (
        query.outerjoin(document_tags, document_tags.c.document_id == Document.id)
        .outerjoin(Tag, document_tags.c.tag_id == Tag.id)
        .outerjoin(Document.author)
        .filter(
            or_(
                Document.title.ilike(term),
                Document.summary.ilike(term),
                Document.content_md.ilike(term),
                Tag.name.ilike(term),
                author_match,
            )
        )
        .distinct()
    )


def build_feed_query(tab: str, user: User | None, search: str | None = None):
    """Build the ordered/filterd query for a feed tab."""
    query = _base_query()

    if search:
        query = _apply_search(query, search)

    if tab == "foryou" and user is not None and user.is_authenticated:
        interest_ids = [t.id for t in user.interests]
        if interest_ids:
            # EXISTS (not a JOIN) so it never collides with the search join.
            from sqlalchemy import select

            match = select(document_tags.c.document_id).where(
                document_tags.c.tag_id.in_(interest_ids),
                document_tags.c.document_id == Document.id,
            ).correlate(Document).exists()
            query = query.filter(match)
        # No interests chosen yet -> behave like "latest" (graceful fallback).

    if tab == "popular":
        query = query.order_by(
            Document.is_featured.desc(),
            Document.views_count.desc(),
            Document.published_at.desc().nullslast(),
        )
    else:  # foryou / latest -> recency
        query = query.order_by(
            Document.is_featured.desc(),
            Document.published_at.desc().nullslast(),
            Document.created_at.desc(),
        )
    return query


def paginate_feed(query, page: int, per_page: int) -> dict:
    """Paginate a feed query. Returns model objects under ``docs`` —
    API routes convert them with ``to_dict()`` before returning JSON."""
    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or current_app.config["DOCS_PER_PAGE"]), 24))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "docs": list(pagination.items),
        "page": pagination.page,
        "per_page": per_page,
        "total": pagination.total,
        "has_more": pagination.has_next,
    }
