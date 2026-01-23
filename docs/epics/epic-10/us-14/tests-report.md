# EPIC-10 / US-14 — Rapport de tests

## Tests exécutés
- **Unitaires/intégration** : `JiraVision/tests/epic_10/us_14/test_routes_po_projects.py`
- Endpoints couverts :
  - GET /po/projects (list, avec projets actifs/inactifs)
  - POST /po/projects (ajout manuel)
  - DELETE /po/projects/{project_key} (masquage temporaire/définitif)
  - POST /po/projects/refresh (refresh manuel)

## Couverture
- Scénarios nominaux (200/201).
- Erreurs (400, 401, 404, 409).
- Règles métier : masquage temporaire vs définitif, ré-ajout inactifs.

## Résultats
- ✅ Tous tests passent (pytest).
- ✅ Isolation utilisateur vérifiée.
- ✅ Multi-instance supporté (cloud_id).

## Commande
```bash
cd JiraVision
pytest tests/epic_10/us_14/ -v
```
