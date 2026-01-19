# EPIC-10 / US-15 — Conception technique

## Objectif
Ajouter un panel UI permettant au PO de visualiser et gérer ses projets.

## UI
- Cartes/onglets projets en haut (filtrées par instances actives).
- Zone de détail pour le projet sélectionné.
- Actions: rafraîchir, ajouter, masquer temporaire/définitif.
- Liste des projets inactifs avec ré‑ajout manuel.
- Compteur de projets masqués calculé à l’affichage.

## Intégration API
Les endpoints suivants sont implémentés dans `/app/routes/po.py` :

### GET /po/projects
Retourne les projets de l'utilisateur connecté.

**Réponse** :
```json
{
  "projects": [...],
  "inactive_projects": [...],
  "last_synced_at": 1705680000
}
```

### POST /po/projects/refresh
Rafraîchit les projets depuis Jira. Peut réinitialiser les masquages définitifs si `reset_definitif=true`.

**Corps de requête** :
```json
{
  "reset_definitif": false
}
```

### POST /po/projects
Ajoute un projet manuellement (source=manual).

**Corps de requête** :
```json
{
  "project_key": "PROJ1",
  "project_name": "Project Name",
  "cloud_id": "cloud_id"
}
```

### DELETE /po/projects/{project_key}
Masque un projet (temporaire ou définitif).

**Corps de requête** :
```json
{
  "mask_type": "temporaire"
}
```

## Notes
- Les projets masqués ne sont pas affichés, le compteur est calculé côté UI.
- Le ré‑ajout d’un inactif force un ajout manuel (source=manual) pour garantir la persistance.
- L'authentification est vérifiée via la session utilisateur.
- Les tests sont disponibles dans `/tests/epic_10/us_15/test_routes_po.py`.
