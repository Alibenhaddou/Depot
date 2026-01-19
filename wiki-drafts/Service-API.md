# Service API (FastAPI)

## Objectif
Service principal de JiraVision exposant l’API métier, la UI POC, l’OAuth Atlassian et l’orchestration Jira/IA.

## Responsabilités
- Authentifier via OAuth Atlassian.
- Gérer les sessions utilisateur (cookie + Redis).
- Exposer les endpoints Jira (issue, search, instances).
- Exposer les endpoints IA (summarize, analyze, stream).
- Servir la UI POC et la page de login.
- Centraliser métriques et traces.

## Dépendances
- Redis (sessions).
- Jira Cloud (API REST).
- ai-service (optionnel via proxy).
- Ollama/OpenAI (LLM) si fallback local.

## Endpoints (fonctionnels)

### Santé & observabilité

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/metrics` | Metrics Prometheus | N/A |
| GET | `/` | Redirect vers `/ui` | N/A |

### Auth (Atlassian OAuth)

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/login` | Redirection OAuth Atlassian | N/A |
| GET | `/oauth/callback` | Callback OAuth (échange token) | N/A |
| GET | `/logout` | Déconnexion (purge session) | N/A |

### UI Auth

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/auth` | Page HTML de login | N/A |
| GET | `/auth/state` | État de connexion (booléen) | Cookie session |

### UI POC

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/ui` | UI POC (redirige si non connecté) | Cookie session |
| GET | `/ui/state` | État UI (logged_in, debug links) | Cookie session |

### Projets PO

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/po/projects` | Liste projets actifs/inactifs + `last_synced_at` (chargement initial UI) | Cookie session |
| POST | `/po/projects` | Ajout manuel d’un projet actif | Cookie session |
| DELETE | `/po/projects/{project_key}` | Masquage d’un projet (temporaire/définitif) | Cookie session |
| POST | `/po/projects/refresh` | Synchronisation Jira et mise à jour actifs/inactifs | Cookie session |

### Jira

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/jira/issue?issue_key=KEY-1` | Détails d’un ticket Jira | Cookie session |
| GET | `/jira/search?jql=...` | Recherche JQL | Cookie session |
| POST | `/jira/select?cloud_id=...` | Sélection d’une instance Jira | Cookie session |
| GET | `/jira/instances` | Liste des instances accessibles | Cookie session |

### IA

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/ai/token` | Token inter-service pour ai-service | Cookie session |
| POST | `/ai/summarize-jql` | Résumé de tickets Jira | Cookie session |
| POST | `/ai/analyze-issue` | Analyse détaillée d’un ticket | Cookie session |
| POST | `/ai/analyze-issue/stream` | Analyse en streaming (SSE) | Cookie session |

### Debug (dev only)

| Méthode | Endpoint | Description | Condition |
|---|---|---|---|
| GET | `/debug/cookie` | Diagnostic cookie/session | ENABLE_DEBUG_ROUTES=true |
| GET | `/debug/session` | Dump session (sanitisé) | ENABLE_DEBUG_ROUTES=true |
| GET | `/debug/routes` | Liste de routes debug | ENABLE_DEBUG_ROUTES=true |

## Contrats principaux

### `/po/projects`

**Réponse (extrait)**
```json
{
  "projects": [{"project_key":"ABC","project_name":"Alpha","cloud_id":null,"mask_type":"none"}],
  "inactive_projects": [{"project_key":"DEF","project_name":"Delta","cloud_id":"<id>"}],
  "last_synced_at": 1700000000
}
```

### `/ai/summarize-jql`

**Request**
```json
{
  "jql": "project = ABC order by updated DESC",
  "max_results": 20,
  "cloud_id": "<optional>"
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
  "result": "texte structuré en français"
}
```

### `/ai/analyze-issue/stream`

Réponse **SSE** avec events :
- `log` (progression)
- `error` (code + message)
- `result` (résultat final)

Exemple (format SSE) :
```
event: log
data: "Début de l'analyse"

event: result
data: {"text":"..."}
```

## Authentification & session

- Cookie `sid` signé.
- Session persistée dans Redis (`session:{sid}`).
- OAuth Atlassian obligatoire pour Jira/IA.

## Erreurs & codes

- **401** : session absente, token expiré, instance non connectée.
- **404** : ticket Jira introuvable.
- **502** : Jira/LLM/ai-service indisponible.

## Observabilité

- Metrics Prometheus : `/metrics`.
- Tracing OpenTelemetry si `OTEL_EXPORTER_OTLP_ENDPOINT` défini.

## Évolutions attendues

- Externalisation complète du traitement IA vers `ai-service`.
- Ajout d’une base de données dédiée si besoin de persistance métier.
- Sécurisation renforcée des routes debug (désactivées en prod).

## Journal des évolutions

| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-19 | doc | Ajout des endpoints Projets PO + chargement initial UI (GET /po/projects). | | |
| 2026-01-16 | initial | Documentation fonctionnelle complète du service API. | | |
