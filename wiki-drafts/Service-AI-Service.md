# Service ai-service (FastAPI)

## Objectif
Microservice dédié au traitement IA de JiraVision : proxy LLM, auth inter-service, métriques et traces. Conçu pour isoler la logique IA de l’API principale.

## Responsabilités
- Exposer les endpoints IA `/ai/*`.
- Appliquer l’auth inter-service (token signé) si activée.
- Router vers le LLM (Ollama/OpenAI).
- Exposer health/ready/metrics.

## Dépendances
- LLM provider (Ollama par défaut, OpenAI possible).
- API principale (émet le token inter-service).

## Endpoints

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/health` | Liveness | N/A |
| GET | `/ready` | Readiness | N/A |
| GET | `/metrics` | Metrics Prometheus | N/A |
| POST | `/ai/summarize-jql` | Résumé de tickets | Token inter-service (si activé) |
| POST | `/ai/analyze-issue` | Analyse ticket | Token inter-service (si activé) |
| POST | `/ai/analyze-issue/stream` | Analyse en streaming (SSE) | Token inter-service (si activé) |

## Auth inter-service

- **Header** : `Authorization: Bearer <token>`
- **Signature** : `itsdangerous` avec `AI_SHARED_SECRET`
- **TTL** : `AI_TOKEN_TTL_SECONDS`
- Si `AI_AUTH_ENABLED=false`, l’auth est désactivée.

## Contrats principaux

### `/ai/summarize-jql`

**Request**
```json
{
  "jql": "project = ABC order by updated DESC",
  "max_results": 20,
  "cloud_id": "<optional>",
  "issues": [ {"key":"ABC-1", "summary":"..."} ]
}
```

**Réponse (extrait)**
```json
{
  "cloud_id": "<id>",
  "count": 20,
  "result": {
    "summary": "...",
    "highlights": ["..."],
    "risks": ["..."],
    "next_actions": ["..."]
  }
}
```

### `/ai/analyze-issue`

**Request**
```json
{
  "issue_key": "ABC-123",
  "cloud_id": "<optional>",
  "max_links": 2,
  "max_comments": 2
}
```

**Réponse (extrait)**
```json
{
  "cloud_id": "<id>",
  "result": "Analyse exemple"
}
```

### `/ai/analyze-issue/stream`

Réponse **SSE** avec events :
- `log` (progression)
- `error` (JSON avec `code` et `message`)
- `result` (JSON avec `text`)

Exemple :
```
event: log
data: "Début de l'analyse"

event: error
data: {"code":502,"message":"LLM indisponible"}

event: result
data: {"text":"Analyse progressive - résultat exemple"}
```

## Observabilité

- Metrics Prometheus : `/metrics`.
- Tracing OpenTelemetry si `OTEL_EXPORTER_OTLP_ENDPOINT` défini.

## Erreurs & codes

- **401** : token manquant / expiré / invalide.
- **400** : payload invalide.
- **502** : LLM indisponible.

## Évolutions attendues

- Remplacer les stubs par le traitement IA complet.
- Enrichir la spec OpenAPI (schemas, codes d’erreur, exemples).
- Ajouter des tests de contrat pour garantir la compatibilité API.

## Journal des évolutions

| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Documentation fonctionnelle complète du service ai-service. | | |
