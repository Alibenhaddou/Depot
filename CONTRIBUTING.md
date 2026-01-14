# Contributing guidelines

This repository enforces strict quality gates on all pull requests. Please follow these rules:

- Every PR must include tests that provide **100% coverage** for added or modified code paths.
- All tests must pass and there must be **no new warnings from mypy**.
- Run `black .`, `flake8 .` locally and ensure zero reported errors before opening a PR.
- Security checks (Bandit and pip-audit) are run in CI; fix any reported issues or justify exceptions in the PR description.
- The CI pipeline will **reject** PRs that do not meet the above gates.

PR Checklist:
- [ ] Tests added/updated (100% coverage)
- [ ] Lint and formatting (Black, flake8)
- [ ] Type checks (mypy)
- [ ] Security scans (Bandit, pip-audit)
