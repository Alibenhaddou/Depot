# EPIC-10 / US-16 — Conception technique

## Objectif
Garantir la fiabilité de la feature Projets PO via une couverture de tests complète (unitaires, intégration, API).

## Stratégie de tests

### Tests unitaires (logique métier)
- Module `po_project_sync` : pagination, déduplication, filtres Jira (Epic actives), règles de masquage.
- Module `po_project_store` : upsert user/project, gestion `mask_type`, timestamps.
- Fichiers : `JiraVision/tests/general/core/test_po_project_sync.py`, `test_po_project_store.py` (si créés).

### Tests API (intégration)
- Endpoints CRUD projets PO (cf. US-14).
- Fichier : `JiraVision/tests/epic_10/us_14/test_routes_po_projects.py`
- Couvre : GET list, POST add, DELETE mask, POST refresh.

### Tests UI (smoke/accessibilité)
- Navigation clavier, aria-live, focus logique (cf. US-20).
- Validation manuelle (NVDA/VoiceOver) ou outillage axe-core/pa11y.
- Rapport : `docs/epics/epic-10/us-20/tests-report.md`

## Organisation des fichiers
```
JiraVision/tests/
├── epic_10/
│   ├── us_14/
│   │   └── test_routes_po_projects.py
│   ├── us_16/ (ce répertoire, réservé pour tests spécifiques US-16)
│   └── us_20/ (tests accessibilité si automatisés)
└── general/
    ├── core/
    │   ├── test_po_project_sync.py (si créé)
    │   └── test_po_project_store.py (si créé)
    └── ...
```

## Critères de validation
- **Couverture minimale** : >80% sur modules po_project_*.
- **Non-régression** : aucun test existant ne casse.
- **CI** : pytest obligatoire avant merge, résultat commenté sur issue/PR.

## Commande
```bash
cd JiraVision
pytest tests/epic_10/ tests/general/core/ -v --cov=app.core --cov=app.routes
```

## Résultats attendus
- Tous les tests passent.
- Pas de régression sur tests généraux.
- Couverture >80% confirmée.
