# EPIC-10 / US-11 — Conception technique

## Objectif
Mettre en place le modèle de données pour la gestion des projets PO (persistance, masquage, source).

## Modèle retenu
- Stockage Redis (avec fallback in‑memory pour dev/test).
- Entités logiques :
  - Utilisateur PO (identifié par jira_account_id)
  - Projets par utilisateur (clé unique par user + project_key + cloud_id)

## Schéma (conceptuel)
### User
- jira_account_id (string, unique)
- display_name (string, optional)
- email (string, optional)
- created_at (timestamp)
- updated_at (timestamp)
- last_synced_at (timestamp, optional)

### UserProject
- project_key (string)
- project_name (string)
- cloud_id (string, optional)
- source (jira | manual)
- mask_type (none | temporaire | definitif)
- masked_at (timestamp, optional)
- created_at (timestamp)
- updated_at (timestamp)

## Stockage
Clés Redis :
- po_user:{jira_account_id} -> JSON User
- po_projects:{jira_account_id} -> JSON dict {project_id -> UserProject}

Project_id = "{cloud_id}:{project_key}" (cloud_id = "default" si absent).

## Comportements clés
- Upsert utilisateur : conserve created_at, met à jour updated_at.
- Upsert projet : dé‑duplication par project_id, update des champs, mask_type géré.
- Masquage : mask_type + masked_at, reset si mask_type = none.

## Notes
- Les timestamps sont en epoch seconds.
- Le compteur de projets masqués est calculé côté UI (pas stocké).