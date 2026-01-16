# EPIC-10 / US-11 — Rapport de tests

## Objectif
Valider le modèle de données (utilisateurs, projets, masquage) avec une couverture 100% des nouvelles fonctions.

## Scénarios testés
1) Upsert utilisateur (création)
- Parcours : création d’un user avec display_name + email
- Résultat attendu : created_at/updated_at définis, champs persistés
- Résultat obtenu : OK

2) Upsert utilisateur (mise à jour)
- Parcours : mise à jour display_name sans écraser email
- Résultat attendu : created_at inchangé, updated_at mis à jour
- Résultat obtenu : OK

3) last_synced_at
- Parcours : set_last_synced_at sur user inexistant
- Résultat attendu : user créé + last_synced_at défini
- Résultat obtenu : OK

4) Upsert projet + déduplication
- Parcours : création puis update d’un projet identique
- Résultat attendu : created_at conservé, updated_at mis à jour, champs modifiés
- Résultat obtenu : OK

5) Validation des entrées
- Parcours : source invalide / mask_type invalide
- Résultat attendu : ValueError levée
- Résultat obtenu : OK

6) Masquage projet
- Parcours : mask_type definitif puis reset none
- Résultat attendu : masked_at défini puis remis à None
- Résultat obtenu : OK

7) Masquage projet absent
- Parcours : set_project_mask sur projet inexistant
- Résultat attendu : KeyError levée
- Résultat obtenu : OK

8) Tri liste projets
- Parcours : insertion ALPHA/BETA
- Résultat attendu : tri stable par project_key
- Résultat obtenu : OK

## Couverture
- Objectif : 100% sur le module po_project_store
- Résultat : OK (tests dédiés US-11)