# Depot

[![Test & Coverage](https://github.com/Alibenhaddou/Depot/actions/workflows/tests.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/tests.yml)
[![Security](https://github.com/Alibenhaddou/Depot/actions/workflows/security.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/security.yml)
[![Docker Image CI](https://github.com/Alibenhaddou/Depot/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Alibenhaddou/Depot/actions/workflows/docker-image.yml)

## Description

Petit service FastAPI utilisé pour démonstration / POC autour d'intégrations Atlassian, LLMs et sessions.

## Tests et couverture

- Lancer la suite de tests :

```bash
cd ct-delivery-assistant-poc
pytest -q
```

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
