# EPIC-10 / US-14 — Conception technique

## Objectif
Exposer les endpoints API REST pour gérer les projets PO (CRUD complet + refresh).

## Endpoints implémentés

### GET /po/projects
Liste les projets de l'utilisateur authentifié (actifs + inactifs) + métadonnées.

**Réponse (200 OK)** :
```json
{
  "projects": [
    {
      "project_key": "ABC",
      "project_name": "Alpha",
      "cloud_id": "site-abc",
      "source": "jira",
      "mask_type": "none",
      "is_active": true,
      "created_at": 1700000000,
      "updated_at": 1700000000
    }
  ],
  "inactive_projects": [
    {
      "project_key": "DEF",
      "project_name": "Delta",
      "cloud_id": "site-def",
      "source": "jira",
      "mask_type": "none",
      "is_active": false,
      "inactive_at": 1700000000
    }
  ],
  "last_synced_at": 1700000000
}
```

### POST /po/projects
Ajout manuel d'un projet (y compris ré-ajout d'un inactif).

**Body** :
```json
{
  "project_key": "XYZ",
  "project_name": "Project XYZ",
  "cloud_id": "site-xyz",
  "source": "manual",
  "is_active": true
}
```

**Réponse (201 Created)** :
```json
{
  "message": "Projet ajouté",
  "project": { ... }
}
```

### DELETE /po/projects/{project_key}?cloud_id=<id>
Masquage d'un projet (temporaire ou définitif).

**Body** :
```json
{
  "mask_type": "temporaire",
  "cloud_id": "site-abc"
}
```

**Réponse (200 OK)** :
```json
{
  "message": "Projet masqué",
  "mask_type": "temporaire"
}
```

**Note** : query param `cloud_id` optionnel pour désambiguïser en multi-instance.

### POST /po/projects/refresh
Synchronisation manuelle depuis Jira (réinitialise les masques temporaires).

**Body** :
```json
{
  "reset_definitif": false
}
```

**Réponse (200 OK)** :
```json
{
  "message": "Synchronisation terminée",
  "projects": [...],
  "inactive_projects": [...],
  "last_synced_at": 1700000000
}
```

## Authentification & autorisation
- Cookie session requis (401 si absent/invalide).
- Isolation par `jira_account_id` : un PO ne voit que ses projets.

## Gestion d'erreurs
- **400** : payload invalide (champs manquants, types incorrects).
- **401** : session absente/expirée.
- **404** : projet introuvable (DELETE).
- **409** : projet déjà existant (POST).
- **502** : Jira indisponible (refresh).

## Tests associés
- Fichier : `JiraVision/tests/epic_10/us_14/test_routes_po_projects.py`
- Couvre : list, add, refresh, mask (temporaire/définitif), erreurs (400/401/404).

## Notes
- Refresh login déclenche automatiquement `sync_projects_for_user` (US-13).
- Refresh manuel conserve les masques définitifs, réinitialise les temporaires.
- Multi-instance : filtrage par `cloud_id` appliqué côté sync (US-13) et endpoint.
