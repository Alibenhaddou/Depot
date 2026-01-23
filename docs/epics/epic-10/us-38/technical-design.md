# EPIC-10 / US-38 — Versioning des microservices

## Objectif
Exposer un numéro de version par microservice (API, ai-service) pour tracer les déploiements et faciliter le support.

## Approche proposée

### 1. Schéma de versioning
- **Semver** : `MAJOR.MINOR.PATCH` (ex: `1.0.0`, `1.1.0`, `1.1.1`)
- MAJOR : breaking changes
- MINOR : nouvelles fonctionnalités rétro-compatibles
- PATCH : corrections de bugs

### 2. Stockage version
- Variable d'environnement : `APP_VERSION` (optionnel, défaut `dev`)
- Fichier : `VERSION` à la racine de chaque service (ex: `JiraVision/VERSION`, `services/ai_service/VERSION`)

### 3. Exposition via API
- Endpoint : `GET /version` (ou `/health` enrichi)
- Réponse :
```json
{
  "service": "api",
  "version": "1.0.0",
  "build_date": "2026-01-19T12:00:00Z"
}
```

### 4. Intégration CI/CD
- Injection `APP_VERSION` via variable d'env au build Docker.
- Tag Git automatique à chaque release (ex: `v1.0.0`).

## Endpoints implémentés

### GET /version (API principale)
```json
{
  "service": "api",
  "version": "1.0.0",
  "python_version": "3.12.3",
  "build_date": "2026-01-19T12:00:00Z"
}
```

### GET /version (ai-service)
```json
{
  "service": "ai-service",
  "version": "1.0.0",
  "python_version": "3.12.3",
  "build_date": "2026-01-19T12:00:00Z"
}
```

## Modification /health (optionnel)
Enrichir `/health` avec version :
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Critères d'acceptation
1. Chaque service expose sa version via `/version` ou `/health`.
2. La version respecte semver.
3. La version est documentée dans le README et le wiki.
4. Aucune régression sur routes existantes.

## Tests
- Ajout tests unitaires pour endpoint `/version`.
- Vérification format semver.

## Prochaines étapes
- Créer fichiers `VERSION` à la racine de chaque service.
- Implémenter endpoint `/version` dans `app/main.py` et `ai_app/main.py`.
- Documenter dans README + wiki.
