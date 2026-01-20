# EPIC-10 / US-48 — Panel PO (Product Owner)

## Objectif
Permettre au PO de visualiser, filtrer, masquer et synchroniser ses projets Jira depuis une interface dédiée, accessible et robuste.

## Fonctionnalités principales
- Listing des projets Jira par instance (multi-cloud)
- Filtres (actifs, inactifs, masqués)
- Masquage temporaire/définitif, réintégration
- Synchronisation manuelle avec Jira
- Gestion des droits d’accès (authentification, session)
- Accessibilité RGAA

## Endpoints backend
- `GET /po/projects` : liste projets (actifs/inactifs)
- `POST /po/projects` : ajout manuel
- `DELETE /po/projects/{project_key}` : masquage
- `POST /po/projects/refresh` : synchronisation

## Scénarios utilisateurs
- En tant que PO, je peux masquer un projet définitivement ou temporairement
- En tant que PO, je peux réintégrer un projet masqué
- En tant que PO, je peux synchroniser mes projets Jira à la demande
- En tant que PO, je peux filtrer mes projets par statut

## Tests & Couverture
- 100% de couverture sur les endpoints critiques (auth, ajout, masquage, refresh)
- Tests unitaires et E2E (voir dossier `tests/epic_10/us_48/`)

## Accessibilité & RGAA
- Navigation clavier complète
- Feedback visuel et ARIA live
- Contrastes et focus visibles

## Points de vigilance
- Robustesse des sessions (fallback Redis)
- Gestion fine des erreurs (401, 400, 404)
- Documentation à jour (technique + utilisateur)

## À compléter
- Captures d’écran UI
- Exemples de payloads
- Liens vers la documentation utilisateur et PO
