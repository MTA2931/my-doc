# Contributing to MyDoc

Thanks for your interest in making MyDoc better! This document explains how
to propose changes safely and consistently.

**Developed by MTA Company** — all contributions are subject to our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

```bash
git clone https://github.com/mta2931/my-doc.git
cd my-doc
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py db upgrade
flask --app run.py seed-tags
flask --app run.py create-superadmin
flask --app run.py run --debug
```

## Branch naming

| Prefix | Use for |
|---|---|
| `feature/<name>` | New functionality |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation only |
| `refactor/<name>` | Internal clean-ups without behaviour changes |
| `test/<name>` | Test additions/improvements |
| `chore/<name>` | Tooling, CI, dependencies |

## Commit messages

We follow a lightweight Conventional Commits style:

```
feat: add RSS feed endpoint
fix: prevent duplicate slug on document rename
docs: document the create-superadmin command
test: cover the report duplicate guard
refactor: extract feed query builder
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `style`.

## Coding style

- **Python**: PEP 8, target line length 100, type hints where they add clarity,
  docstrings for public functions/classes. Keep the application-factory and
  blueprint patterns intact.
- **JavaScript**: ES6+, no frameworks, no build step. Attach page modules to
  `window.MyDoc*` namespaces; no global leaks.
- **CSS**: use design tokens (custom properties) from `tokens.css`/`themes.css`
  — never hard-code colors or magic numbers.
- **Templates**: semantic HTML, ARIA where needed, labels on every input.

## Pull request checklist

- [ ] `python -m pytest tests/ -q` passes (all 51+ tests)
- [ ] `python scripts/smoke.py` passes
- [ ] New features come with tests
- [ ] UI changes work in **both** dark and light themes
- [ ] Keyboard navigation and visible focus states are preserved
- [ ] `prefers-reduced-motion` is respected for new animations
- [ ] Documentation (README/changelog) updated when behaviour changes
- [ ] No secrets, credentials or personal data committed

## Reporting bugs

Use the **Bug report** issue template and include:

1. Steps to reproduce
2. Expected vs. actual behaviour
3. Environment (OS, Python version, browser)
4. Logs/screenshots if available

Security issues must **not** be opened publicly — see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the
MIT License (see [LICENSE](LICENSE)).
