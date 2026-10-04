# Security Policy

**Developed by MTA Company**

## Supported versions

| Version | Supported |
|---|---|
| 1.x (main branch) | ✅ actively maintained |
| < 1.0 | ✅ security fixes only |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report them privately:

- **E-mail:** toutounchimani@gmail.com
- **Subject:** `[SECURITY] MyDoc — MyDoc Web and Cloud scerity team.`

Include as much of the following as you can:

1. Description of the vulnerability and its impact
2. Steps to reproduce (PoC, screenshots, requests)
3. Affected version / commit hash
4. Suggested fix, if you have one

### What to expect

| Stage | Target |
|---|---|
| Acknowledgement | within **48 hours** |
| Initial triage & severity | within **5 business days** |
| Fix or mitigation plan | within **14 days** for critical issues |
| Public disclosure | coordinated with you after a fix ships |

We ask that you give us a reasonable window to ship a patch before publishing
details, and that you avoid accessing other users' data, degrading the
service, or spamming users while testing.

## Scope

In scope:

- Authentication / session handling flaws
- Authorization & role bypass (Support / Admin / Super Admin)
- Injection: XSS, SQLi, SSTI, SSRF, command injection
- CSRF, open redirects, clickjacking
- File upload weaknesses (path traversal, type confusion)
- Secrets or credentials leaked in the repository

Out of scope:

- Denial-of-service fuzzing
- Attacks requiring physical access or social engineering
- Vulnerabilities in third-party dependencies with no impact on MyDoc
- Reports without a reproducible scenario

## Prefer encrypted disclosure?

Send your report via PGP key request to the address above and we will reply
with our public key.

Thank you for helping keep MyDoc and its community safe.
