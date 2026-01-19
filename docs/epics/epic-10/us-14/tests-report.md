# EPIC-10 / US-14 — Rapport de tests

## Tests exécutés
- pytest JiraVision/tests/epic_10/us_13/test_po_project_sync.py -q
- pytest JiraVision/tests/epic_10/us_14/test_routes_po_projects.py -q
- pytest JiraVision/tests --cov=app --cov-report=term-missing

## Résultats
- OK (9 passed) pour `us_13` (inclut reset_definitif)
- OK (8 passed) pour `us_14`
- OK (213 passed), couverture 100%
