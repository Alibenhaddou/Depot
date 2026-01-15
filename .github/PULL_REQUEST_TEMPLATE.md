## Description

Describe the change and why it's needed.

## Checklist
- [ ] Tests added and passing (100% coverage required)
- [ ] Linting (black, flake8) OK
- [ ] Types (mypy) OK
- [ ] Security scans addressed or justified (Bandit/pip-audit)

---

## Migration guidance (ai-service extraction)
- [ ] OpenAPI spec for `/ai` exists and is reviewed
- [ ] `services/ai_service` scaffolded and CI enabled
- [ ] Contract tests added between `api` and `ai-service`
- [ ] Inter-service auth defined (token broker / JWT)
- [ ] Metrics & tracing added (Prometheus / OpenTelemetry)
- [ ] Rollout plan and rollback documented
