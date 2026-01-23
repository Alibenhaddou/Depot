# EPIC-10 / US-12 — Conception technique

## Objectif
Mapper l’utilisateur Jira vers la base locale au moment du login OAuth.

## Design
- Ajout d’un helper `upsert_user_from_jira`.
- Appel `/myself` via JiraClient après login.
- Sauvegarde en base via `po_project_store`.
- Stockage dans la session : `jira_account_id`, `jira_display_name`, `jira_email`.

## Flux
1) OAuth callback obtient `access_token`
2) Sélection `active_cloud_id`
3) Appel Jira `/myself`
4) Persist user + enrichissement session

## Gestion d’erreurs
- Si `/myself` échoue -> HTTP 502.
- Si `accountId` manquant -> HTTP 502.

## Notes
- L’email peut être absent (scopes).