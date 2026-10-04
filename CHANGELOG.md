# Changelog

All notable changes to **MyDoc** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

**Developed by MTA Company**

## [Unreleased]

### Added
- (placeholder for work in progress)

## [1.0.0] - 2026-10-04

### Added
- Public 3D landing page (`/my-doc`) with pure-CSS floating document cards,
  mouse parallax, rotating scene, and graceful reduced-motion fallback
- Accounts: sign-up wizard with interests, login (e-mail or username),
  logout, remember me, password reset, e-mail verification (pluggable mailer)
- Personalised `/home` feed with **For You / Latest / Popular** tabs,
  debounced live search, skeleton loaders and "Load more" pagination
- Markdown editor with split-pane live preview, toolbar, word count,
  autosave, cover image uploads, custom slugs and publish workflow
- Public document pages with server-side sanitized HTML, reading time,
  view counts, saves (bookmarks) and report modal
- User panel: dashboard stats, my documents (search/filter/actions),
  saves, profile settings (avatar, bio, interests, theme), change password,
  account deletion, support tickets with threaded replies
- Admin panel with role-based access (**Support / Admin / Super Admin**),
  canvas growth charts, user & document moderation, report queue,
  ticket triage (status/priority/assignment), staff management
  (Super Admin only) and site settings (registration, maintenance mode)
- Audit log of every privileged action
- Complete dark & light theming with design tokens, animated theme toggle,
  OS-preference default, no-flash inline bootstrap, profile persistence
- Design system: spacing/type scales, buttons, inputs, cards, modals, toasts,
  dropdowns, tabs, tables, badges, pagination, skeletons, empty states
- Accessibility: semantic markup, ARIA, skip link, keyboard navigation,
  visible focus states, WCAG AA contrast, reduced-motion support
- Security hardening: bleach Markdown sanitization, CSRF, auth rate limits,
  secure uploads, CSP & security headers, capability matrix enforced
  server-side, safe redirect handling
- Flask-Migrate schema migrations; `flask create-superadmin` and
  `flask seed-tags` CLI commands
- pytest suite (51 tests) covering auth, roles, documents, API and security
- Full open-source scaffolding: README, LICENSE (MIT), CONTRIBUTING,
  CODE_OF_CONDUCT, SECURITY, CHANGELOG, GitHub issue/PR templates

[Unreleased]: https://github.com/mta2931/my-doc/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mta2931/my-doc/releases/tag/v1.0.0
