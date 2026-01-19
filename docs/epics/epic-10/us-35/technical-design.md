# EPIC-10 / US-35 — Documentation du workflow projet

## Objectif
Centraliser dans une documentation unique le workflow projet (US/bugs/tests/branches/PRs) pour garantir la reprise rapide par une IA ou un nouveau développeur.

## Structure proposée

### 1. Workflow US (User Story)
1. Création issue GitHub avec label EPIC-10, priorité (P0/P1/P2), description complète (story, critères acceptation).
2. Assignation @copilot si pris en charge par l'agent.
3. Branche : `dev-usXX-<description-courte>` (depuis `dev`).
4. Développement : code + tests + doc technique.
5. Documentation :
   - `docs/epics/epic-10/us-XX/technical-design.md`
   - `docs/epics/epic-10/us-XX/tests-report.md`
6. Tests : `cd JiraVision && pytest -q`, résultat commenté sur issue.
7. Commit : message explicite (`feat: US-XX <description>`).
8. Push + PR vers `dev` (titre `US-XX: <description>`).
9. Review + merge.
10. Clôture issue avec commentaire final (résumé + référence commit/PR).

### 2. Workflow Bug
1. Création issue GitHub avec label `bug`, lien vers US d'origine si applicable.
2. Assignation @copilot si pris en charge.
3. Branche : `fix-<issue-number>-<description>` ou `dev-usXX-fix-<bug>`.
4. Correction + tests non-régression.
5. Commit : `fix: #<issue> <description>`.
6. Push + PR vers `dev`.
7. Review + merge.
8. Clôture issue avec référence commit/PR.

### 3. Organisation des tests
- **Par US** : `JiraVision/tests/epic_10/us_XX/`
- **Généraux** : `JiraVision/tests/general/` par thématique :
  - `ai/` : tests LLM, summarize, analyze
  - `auth/` : OAuth, session
  - `jira/` : clients Jira, JQL
  - `core/` : config, Redis, po_project_*
  - `routes/` : endpoints généraux
  - `observability/` : metrics, tracing
  - `coverage/` : tests de couverture

### 4. Branches & stratégie Git
- **master** : stable, production-ready.
- **dev** : intégration, base de développement.
- **dev-usXX-*** : branches de feature (US).
- **fix-*** : branches de bug.
- Merge uniquement après validation (PR review + CI).

### 5. PRs & validation
- PR vers `dev` uniquement.
- Titre explicite : `US-XX: <description>` ou `fix: #<issue> <description>`.
- Description PR : résumé changements + tests + références.
- Review : 1 approbation minimum (optionnel si solo).
- CI : pytest + lint (Vulture, mypy, flake8).

### 6. Documentation technique (obligations)
- Chaque US crée/met à jour :
  - `technical-design.md` : objectif, design, API, flux, erreurs.
  - `tests-report.md` : tests exécutés, résultats, commandes.
- Epic RBB (review big bang) :
  - `docs/epics/epic-10/rbb/tests-report.md`

### 7. App dev (démarrage rapide)
```bash
cd JiraVision
cp .env.example .env
# Éditer .env : ATLASSIAN_CLIENT_ID/SECRET, ATLASSIAN_REDIRECT_URI=http://localhost:8000/oauth/callback
docker-compose up --build
# Ouvrir http://localhost:8000
```

### 8. Assignation & suivi
- Assigner @copilot sur issue si IA prend en charge.
- Commenter issue avec progression (démarré, tests OK, PR ouverte).
- Clôture issue après merge avec message de synthèse.

## Critères d'acceptation
- La documentation est créée et accessible dans le repo.
- Tous les flux (US/bug/tests/doc/branches/PR) sont décrits pas à pas.
- La structure de tests est explicite et appliquée.
- Les règles d'assignation et de clôture sont écrites.

## Référence
- Fichier : ce document (`docs/epics/epic-10/us-35/technical-design.md`)
