# EPIC-10 / US-13 — Conception technique

## Objectif
Synchroniser automatiquement les projets Jira où le PO est reporter, en respectant les règles d’inclusion (Epic active) et les règles de masquage.

## Approche
- Ajout d’un module `po_project_sync` pour orchestrer le refresh.
- Utilisation de `JiraClient.search_jql` pour récupérer :
  - Projets issus des tickets reporter (types Story/Etude/Projet).
  - Présence d’Epics actives par projet (status NOT IN Annulé/Done).
- Persistences via `po_project_store`.

## Règles appliquées
- Masquage **temporaire** : réinitialisé au refresh.
- Masquage **définitif** : conservé.
- Projets sans Epic active : marqués `is_active=false` et listés comme inactifs.

## Stockage
Extension du store pour stocker :
- `is_active` (bool)
- `inactive_at` (timestamp)

## Entrées / sorties
`sync_projects_for_user(jira_account_id, session)` retourne :
- `projects` (actifs)
- `inactive_projects`

## Notes
- Le filtrage par instances s’appuie sur `session.cloud_ids`.
- Le module est prêt pour branchement sur le refresh login et le refresh manuel (US suivantes).