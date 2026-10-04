"""Server-side Markdown rendering with strict HTML sanitization.

Every piece of user-authored content MUST pass through :func:`render_markdown`
before being stored in ``documents.content_html`` and before being rendered
into templates, so XSS can never reach a reader's browser.
"""

from __future__ import annotations

import re

import bleach
import markdown as md_lib

# Strict allowlist -----------------------------------------------------------
ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "ins", "mark", "sub", "sup",
    "code", "pre", "blockquote",
    "ul", "ol", "li",
    "a", "img",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "figure", "figcaption",
    "div", "span",
    "input",  # task-list checkboxes (disabled below)
}

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "code": ["class"],
    "pre": ["class"],
    "span": ["class"],
    "div": ["class"],
    "th": ["colspan", "rowspan", "align"],
    "td": ["colspan", "rowspan", "align"],
    "input": ["type", "checked", "disabled"],
    "*": ["class"],
}

ALLOWED_PROTOCOLS = {"http", "https", "mailto"}

# Markdown extensions
MD_EXTENSIONS = ["fenced_code", "tables", "sane_lists", "nl2br"]
MD_EXTENSION_CONFIGS = {}


def sanitize(html: str) -> str:
    """Clean untrusted HTML down to the allowlist."""
    if not html:
        return ""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


def render_markdown(text: str) -> str:
    """Convert Markdown to sanitized HTML. Safe to store and render."""
    if not text:
        return ""
    raw_html = md_lib.markdown(
        text,
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIGS,
        output_format="html5",
    )
    return sanitize(raw_html)


def plain_excerpt(text: str, limit: int = 180) -> str:
    """Flatten markdown to a plain-text excerpt for meta descriptions."""
    if not text:
        return ""
    # Drop fenced code blocks and inline markup markers.
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_~\-]+", " ", text)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text
