# ai-service (scaffold)

Service FastAPI autonome contenant la logique IA extraite du POC principal.

But: fournir les endpoints existants `/ai/*` pour permettre la migration progressive.

Fichiers principaux:
- `ai_app/main.py` : point d'entrée FastAPI
- `ai_app/routes/ai.py` : routes `summarize-jql`, `analyze-issue`, `analyze-issue/stream`
- `ai_app/clients/llm.py` : client LLM (Ollama/OpenAI)
- `ai_app/core/auth.py` : vérification du token inter-service
- `openapi.yaml` : spec OpenAPI minimale

Ce scaffold fournit des stubs et des tests de contrat de base ; à compléter par l'équipe pour l'intégration LLM et l'auth inter-service.

## Variables d'environnement (exemples)

- `AI_AUTH_ENABLED` (true/false)
- `AI_SHARED_SECRET` (secret partagé avec l'API principale)
- `AI_TOKEN_TTL_SECONDS` (durée de validité du token)
- `OTEL_EXPORTER_OTLP_ENDPOINT` (si tracing activé)
