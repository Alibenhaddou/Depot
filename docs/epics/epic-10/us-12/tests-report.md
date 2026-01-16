# EPIC-10 / US-12 — Rapport de tests

## Objectif
Valider le mapping utilisateur Jira vers la base locale.

## Scénarios testés
1) Création utilisateur avec email
- Parcours : appel `upsert_user_from_jira` avec accountId + displayName + email
- Résultat attendu : user persiste avec tous les champs
- Résultat obtenu : OK

2) Création utilisateur sans email
- Parcours : appel `upsert_user_from_jira` sans email
- Résultat attendu : user créé, email absent
- Résultat obtenu : OK

3) accountId manquant
- Parcours : appel `upsert_user_from_jira` sans accountId
- Résultat attendu : ValueError
- Résultat obtenu : OK

4) JiraClient /myself
- Parcours : `get_myself` appelle `_request` avec GET /myself
- Résultat attendu : appel correct
- Résultat obtenu : OK

## Couverture
- Objectif : 100% sur `po_user.py` + nouvelle méthode JiraClient
- Résultat : OK (tests dédiés US-12)