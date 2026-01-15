# Depot

[![Test & Coverage](https://github.com/Alibenhaddou/Depot/actions/workflows/tests.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/tests.yml)
[![Security](https://github.com/Alibenhaddou/Depot/actions/workflows/security.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/security.yml)
[![Docker Image CI](https://github.com/Alibenhaddou/Depot/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/docker-image.yml)
[![Sonar](https://sonarcloud.io/api/project_badges/measure?project=Alibenhaddou_Depot&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Alibenhaddou_Depot)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Alibenhaddou_Depot&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Alibenhaddou_Depot)

## Description

Petit service FastAPI utilisé pour démonstration / POC autour d'intégrations Atlassian, LLMs et sessions.

## Tests et couverture

- Lancer la suite de tests :

```bash
cd ct-delivery-assistant-poc
pytest -q
```

- Pour utiliser le `ai-service` externe (migration progressive), exportez la variable d'environnement :

```bash
export AI_SERVICE_URL="http://ai-service:8000"
```

Avec `AI_SERVICE_URL` configurée, l'application principale fera un proxy des appels `/ai/*` vers le service externe (utile pour tests et migration canary).

### Observabilité (optionnel)

Pour activer le tracing OpenTelemetry (API principale + ai-service), configurez :

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318/v1/traces"
```

Les métriques Prometheus sont exposées sur `/metrics` pour les deux services.
- Générer le rapport de coverage HTML et XML :

```bash
cd ct-delivery-assistant-poc
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q
```

- Consulter le rapport HTML localement (option simple) :

```bash
# partir du repo racine
python -m http.server --directory ct-delivery-assistant-poc/htmlcov 8000
# ouvrir http://localhost:8000 dans votre navigateur
```

> Astuce pour les tests : si vous rencontrez l'avertissement Starlette "Setting per-request cookies is being deprecated", définissez les cookies sur l'instance `TestClient` :

```py
client.cookies.set("sid", "value")
client.cookies.set("oauth_state", "xyz")
res = client.get("/some/path")
```

## Contribution

- Suivez la convention de style (Black), vérifiez `flake8` et `mypy` avant d'ouvrir une PR.
- Les workflows GitHub Actions exécutent les tests et génèrent la couverture automatiquement.
