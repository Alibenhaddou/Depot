# EPIC-10 / US-48 — Panel PO (Product Owner)

## Objectif
Permettre au PO de visualiser, filtrer, masquer et synchroniser ses projets Jira depuis une interface dédiée, accessible et robuste.

## Correction bug #48 - Détection des projets actifs

**Problème résolu** : La détection des projets actifs utilisait une logique basée sur les Epics, ce qui ne reflétait pas correctement l'activité réelle des POs.

**Solution mise en place** :
- Un projet est considéré comme **actif** s'il contient au moins un ticket de type **Story** ou **Etude**, dont le reporter est l'utilisateur courant, et dont le statut n'est ni "Done" ni "Annulé"
- Requête JQL utilisée : `reporter = "{account_id}" AND type in (Story, Etude) AND status NOT IN ("Done", "Annulé")`
- Les projets distincts sont extraits à partir des tickets trouvés (pas de vérification Epic)

**Impact** :
- Détection plus fiable des projets sur lesquels le PO travaille activement
- Conformité au besoin métier : focus sur les Stories/Etudes en cours, pas sur les Epics

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
