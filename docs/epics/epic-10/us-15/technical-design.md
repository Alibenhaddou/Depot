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
- GET /po/projects
- POST /po/projects
- DELETE /po/projects/{project_key}
- POST /po/projects/refresh

## Notes
- Les projets masqués ne sont pas affichés, le compteur est calculé côté UI.
- Le ré‑ajout d’un inactif force un ajout manuel (source=manual) pour garantir la persistance.
