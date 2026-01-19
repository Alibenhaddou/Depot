# EPIC-10 / US-14 — Conception technique

## Objectif
Exposer des endpoints pour lister, ajouter, masquer et rafraîchir les projets PO.

## Endpoints
- `GET /po/projects` : retourne `projects`, `inactive_projects`, `last_synced_at`.
- `POST /po/projects` : ajout manuel (y compris inactifs) via `source=manual`.
- `DELETE /po/projects/{project_key}` : masquage avec `mask_type` (temporaire/définitif).
- `POST /po/projects/refresh` : refresh Jira manuel, avec option `reset_definitif`.

## Règles clés
- Auth via session (`jira_account_id` requis).
- Masquage temporaire reset au refresh.
- Masquage définitif reset uniquement si `reset_definitif=true`.
- Les projets inactifs peuvent être ajoutés manuellement avec `is_active=false`.

## Erreurs
- 401 si session invalide.
- 400 si `source` ou `mask_type` invalide.
- 404 si projet à masquer introuvable.
- 4xx Jira propagé lors du refresh.
