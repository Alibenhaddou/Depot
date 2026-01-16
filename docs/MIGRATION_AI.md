# Migration plan: extract `ai` into `ai-service`

Short checklist and steps to perform the extraction safely for JiraVision.

1. Create `ai-service` scaffold (done) under `services/ai_service`.
2. Define OpenAPI spec for `/ai/*` endpoints (openapi.yaml included).
3. Decide inter-service auth (recommendation: token broker JWT short-lived).
4. Implement proxy in the main API (env `AI_SERVICE_URL`) and feature-flag it.
5. Add contract tests (Pact or pytest mocks) and CI pipeline for `ai-service`.
6. Add metrics (`/metrics`) and health endpoints.
7. Add OpenTelemetry tracing (OTLP endpoint configured via env).
7. Deploy to staging and run canary traffic.
8. Remove local LLM logic from main app and switch to client.

See PR template for checklist to include in pull requests.
