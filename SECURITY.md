# Security Policy

## Supported Versions

Only the latest minor version receives security updates.

| Version | Supported |
|---------|-----------|
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x: |

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report privately via one of the following:

- GitHub's [Report a vulnerability](https://github.com/yusufkucukates/mcp-prompt-optimizer/security/advisories/new) flow (preferred)
- Email: `y.kucukates@gmail.com` with the subject line `[SECURITY] prompt-optimizer-mcp`

### What to include
- A description of the issue and its impact
- Steps to reproduce (minimal proof of concept if possible)
- The affected version(s)
- Your suggested mitigation, if any

### What to expect
- Acknowledgement within **72 hours**
- An initial assessment within **7 days**
- A fix and coordinated disclosure timeline agreed before any public release

Reporters who follow coordinated disclosure will be credited in the release notes unless they prefer to remain anonymous.

## Scope

In scope:
- Code in this repository (`src/`, `tests/`, `templates/`)
- Published PyPI package `prompt-optimizer-mcp`
- Official GitHub Actions workflows in `.github/workflows/`

Out of scope:
- Vulnerabilities in upstream dependencies (please report those upstream and let us know so we can bump versions)
- Issues that require the user to run a malicious prompt template from an untrusted source
