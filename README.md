<div align="center">

# MyDoc

**A public platform for documents about programming, AI and the digital world.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-51%20passing-brightgreen.svg)](#running-tests)
[![Code style](https://img.shields.io/badge/style-PEP%208-lightgrey.svg)](https://peps.python.org/pep-0008/)

*Sign up for free, pick your interests, and start writing — or reading — in seconds.*

**[Report Bug](https://github.com/mta2931/my-doc/issues) · [Request Feature](https://github.com/mta2931/my-doc/issues) · [Contributing](CONTRIBUTING.md)**

</div>

---

## Table of Contents

- [Concept](#concept)
- [Features](#features)
- [Screenshots](#screenshots)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Installation & setup](#installation--setup)
- [Configuration](#configuration)
- [Running tests](#running-tests)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Concept

**MyDoc** (short for *MyDocument*) is a public platform where people create
accounts and write documents — articles, guides, notes and tutorials — with a
core focus on **programming, software development, computers, artificial
intelligence and the digital world**.

- Only logged-in users can create documents.
- Anyone can browse public documents.
- Readers can **save** (bookmark) and **report** documents.
- A full admin panel with three staff roles keeps the platform safe.

## Features

### For readers
- Personalised feed — **For You / Latest / Popular** tabs with skeleton loaders
- Debounced live search across titles, tags, content and authors
- Dark & light themes (animated sun/moon toggle, OS-aware, persisted)
- Save/bookmark documents into a personal library
- Report documents to the moderation team
- Responsive 3D landing page with mouse-parallax depth (pure CSS 3D)

### For writers
- Split-pane **Markdown editor** with toolbar and live preview
- Syntax-highlighted code blocks (local dependency-free highlighter)
- **Autosave** drafts, publish/unpublish, custom slugs, cover images
- Reading time, view counts, save counts per document
- Drafts are private until published; unlisted links supported

### For the team
- **Support tickets** with threaded replies and status workflow
- Admin panel with dashboard charts drawn on `<canvas>`
- User management: ban/unban, role changes, search & filters
- Document moderation: publish, feature, unpublish, delete
- Report queue: dismiss, unpublish, delete, ban author
- Site settings: registration toggle, maintenance mode, default theme
- Immutable **audit log** of every admin action

### Security
- Server-side Markdown sanitization (bleach, strict allowlist) — XSS-safe
- CSRF protection (Flask-WTF), rate limiting on auth endpoints (Flask-Limiter)
- Password hashing with werkzeug (scrypt) + strength meter
- Secure file uploads (extension + MIME + magic-byte checks, random names)
- Security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Role-based access control enforced **server-side** (`@role_required` / capability matrix)

## Screenshots

> Replace with your own captures after running the app locally.

| Landing (3D hero) | Feed | Editor |
|---|---|---|
| ![Landing](docs/screenshots/landing.png) | ![Feed](docs/screenshots/feed.png) | ![Editor](docs/screenshots/editor.png) |

| Dashboard | Admin panel | Dark theme |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Admin](docs/screenshots/admin.png) | ![Dark](docs/screenshots/dark.png) |

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | HTML5, CSS3 (design tokens, custom properties), Vanilla ES6+ JavaScript |
| Backend | Python 3.10+ · Flask 3 (Blueprints + application factory) |
| Database | SQLite by default via SQLAlchemy — swap to PostgreSQL with `DATABASE_URL` |
| Migrations | Flask-Migrate (Alembic) |
| Auth | Flask-Login · werkzeug password hashing · Flask-WTF CSRF · Flask-Limiter |
| Rendering | Jinja2 templates · server-side Markdown → sanitized HTML (bleach) |
| 3D landing | Pure CSS 3D transforms + JS parallax — no WebGL, degrades gracefully |
| Tests | pytest |

## Project structure

```
my-doc/
├── app/
│   ├── __init__.py              # application factory
│   ├── config.py                # env-driven configuration classes
│   ├── extensions.py            # db, migrate, login, csrf, limiter
│   ├── models/                  # User, Document, Save, Report, Ticket, …
│   ├── services/                # markdown, mailer, feeds, access, utils
│   ├── blueprints/              # main, auth, docs, dashboard, admin, api
│   ├── templates/               # Jinja2 (base, landing, auth, home, docs,
│   │                            #  dashboard, admin, errors, macros)
│   └── static/
│       ├── css/                 # tokens, themes, base, components, pages/
│       ├── js/                  # core, theme, components, api, pages/
│       ├── img/                 # logo, favicon
│       └── uploads/             # avatars & covers (git-ignored)
├── migrations/                  # Alembic migrations
├── tests/                       # pytest suite (51 tests)
├── scripts/                     # smoke.py, audit_deadcode.py dev tools
├── .github/                     # issue & PR templates
├── run.py                       # dev entry point
├── requirements.txt
├── .env.example
├── README.md  LICENSE  CONTRIBUTING.md  CODE_OF_CONDUCT.md
├── SECURITY.md  CHANGELOG.md
└── .gitignore
```

## Installation & setup

### 1. Clone & create a virtual environment

```bash
git clone https://github.com/mta2931/my-doc.git
cd my-doc

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

```bash
cp .env.example .env
# open .env and set at least SECRET_KEY for production
```

### 4. Initialise the database

```bash
flask --app run.py db upgrade      # apply migrations (creates instance/mydoc.db)
flask --app run.py seed-tags       # optional: seed the default topic tags
```

### 5. Create the first Super Admin

```bash
flask --app run.py create-superadmin
# prompts for username, e-mail and password
```

### 6. Run the development server

```bash
flask --app run.py run --debug
# or
python run.py
```

Open <http://127.0.0.1:5000> — the public landing page lives at `/my-doc`.

## Configuration

All configuration is read from environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `FLASK_ENV` | `development` | `development` \| `production` \| `testing` |
| `FLASK_DEBUG` | `1` | Enable the Werkzeug debugger in development |
| `SECRET_KEY` | dev fallback | Session/CSRF signing key — **required in production** |
| `DATABASE_URL` | `sqlite:///mydoc.db` | Any SQLAlchemy URL (SQLite, PostgreSQL, …) |
| `SESSION_COOKIE_SECURE` | `0` | `1` behind HTTPS in production |
| `REMEMBER_COOKIE_SECURE` | `0` | `1` behind HTTPS in production |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `Lax` \| `Strict` \| `None` |
| `RATELIMIT_STORAGE_URL` | `memory://` | Use `redis://…` for multi-process deployments |
| `RATELIMIT_ENABLED` | `1` | Global rate limiting switch |
| `MAX_UPLOAD_MB` | `4` | Max image upload size (avatars, covers) |
| `MAIL_PROVIDER` | `console` | `console` (prints to terminal) or `smtp` |
| `MAIL_SUPPRESS_SEND` | `1` | `0` to actually send e-mail |
| `MAIL_FROM` | `noreply@mydoc.local` | From address |
| `SMTP_HOST` / `SMTP_PORT` | `localhost` / `587` | SMTP server |
| `SMTP_USER` / `SMTP_PASSWORD` | empty | SMTP credentials |
| `SMTP_USE_TLS` | `1` | StartTLS |
| `SITE_URL` | `http://127.0.0.1:5000` | Base URL used in e-mail links |

**Switching to PostgreSQL**

```bash
pip install psycopg2-binary
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/mydoc"
flask --app run.py db upgrade
```

## Running tests

```bash
python -m pytest tests/ -q          # 51 tests
python scripts/smoke.py             # route/render smoke test
python scripts/audit_deadcode.py    # structural dead-code audit
```

The suite covers authentication flows, document CRUD + XSS sanitization,
role-based permissions (Support / Admin / Super Admin), key API endpoints,
security headers and the MTA Company credits.

## Deployment

### Gunicorn (Linux)

```bash
export FLASK_ENV=production
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost/mydoc"

gunicorn --workers 3 --bind 127.0.0.1:8000 "run:app"
```

### Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name mydoc.example.com;

    client_max_body_size 8M;

    location /static/ {
        alias /srv/my-doc/app/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Terminate TLS with Certbot and set `SESSION_COOKIE_SECURE=1`.

### Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN flask --app run.py db upgrade
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "run:app"]
```

```bash
docker build -t mydoc .
docker run -p 8000:8000 -e SECRET_KEY=change-me -e FLASK_ENV=production mydoc
```

## Roadmap

- [x] Markdown editor with live preview & autosave
- [x] Personalised feed with search and infinite loading
- [x] Roles: Support / Admin / Super Admin with audit log
- [ ] Email notifications for ticket replies
- [ ] User profile pages & following authors
- [ ] RSS feed and sitemap
- [ ] Two-factor authentication (TOTP)
- [ ] i18n (English + more languages)
- [ ] Embeddable charts/diagrams in documents

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and
our [Code of Conduct](CODE_OF_CONDUCT.md) before opening a pull request.

```bash
git checkout -b feature/awesome-change
python -m pytest tests/ -q
git commit -m "feat: add awesome change"
git push origin feature/awesome-change
```

## License

Distributed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Developed by MTA Company**

© 2026 MyDoc · MIT License · Built with Flask & vanilla JS

</div>

