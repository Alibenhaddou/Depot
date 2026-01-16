# Workflow Projet - Epic #10

Ce document décrit le workflow complet du projet Depot/JiraVision pour les User Stories, bugs, tests, branches et Pull Requests. Il permet à toute nouvelle IA ou développeur de reprendre le projet immédiatement.

---

## Table des matières

1. [Flux User Story (US)](#flux-user-story-us)
2. [Flux Bug](#flux-bug)
3. [Règles d'assignation](#règles-dassignation)
4. [Tests obligatoires](#tests-obligatoires)
5. [Structure de documentation](#structure-de-documentation)
6. [Organisation des tests](#organisation-des-tests)
7. [Stratégie de branches](#stratégie-de-branches)
8. [Règles des Pull Requests](#règles-des-pull-requests)
9. [Intégration GitHub Project](#intégration-github-project)
10. [Démarrage de l'application en développement](#démarrage-de-lapplication-en-développement)

---

## Flux User Story (US)

### Étape par étape

1. **Création de l'US** : Créer une issue GitHub avec le label `user-story` et l'associer à l'Epic correspondant (ex: Epic #10)

2. **Création de la branche** : Créer une branche dédiée depuis `dev`
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b DEV-US#<numéro>
   ```
   Exemple : `DEV-US#25` pour l'US #25

3. **Développement** : Implémenter les fonctionnalités requises
   - Suivre les conventions de code (Black, flake8, mypy)
   - Ajouter des tests unitaires avec 100% de couverture
   - Documenter les changements

4. **Tests** : Exécuter la suite de tests complète
   ```bash
   cd JiraVision
   pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q
   ```
   - Tous les tests doivent passer
   - Couverture de 100% requise pour le code nouveau/modifié
   - Commenter l'issue avec les résultats des tests

5. **Documentation** : Créer la documentation technique
   - Créer `docs/epics/epic-10/us-XX/technical-design.md` avec l'architecture et les décisions techniques
   - Créer `docs/epics/epic-10/us-XX/tests-report.md` avec les résultats détaillés des tests

6. **Commit** : Committer les changements avec un message descriptif
   ```bash
   git add .
   git commit -m "feat: implémentation US#XX - <description courte>"
   ```

7. **Push** : Pousser la branche vers le dépôt distant
   ```bash
   git push origin DEV-US#<numéro>
   ```

8. **Pull Request** : Créer une PR vers la branche `dev`
   - Utiliser le template de PR (`.github/PULL_REQUEST_TEMPLATE.md`)
   - Remplir tous les champs de la checklist
   - Référencer l'issue US dans la description (ex: `Closes #25`)
   - Assigner les reviewers appropriés

9. **Validation** : La PR doit passer tous les checks CI/CD
   - Tests (100% coverage)
   - Linting (Black, flake8)
   - Type checking (mypy)
   - Security scans (Bandit, pip-audit)

10. **Merge** : Une fois approuvée, merger la PR dans `dev`
    ```bash
    # Via l'interface GitHub (merge standard ou squash)
    ```

11. **Clôture de l'issue** : Fermer l'issue US manuellement ou automatiquement via le mot-clé `Closes #XX` dans la PR

---

## Flux Bug

### Étape par étape

1. **Création/Association** : 
   - Créer une issue GitHub avec le label `bug`
   - Associer le bug à l'US d'origine si applicable (référencer l'US dans la description)
   - Décrire le bug, les étapes de reproduction et le comportement attendu

2. **Création de la branche dédiée** : Créer une branche depuis `dev`
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b bugfix/bug-<numéro>-<description-courte>
   ```
   Exemple : `bugfix/bug-42-fix-auth-redirect`

3. **Correction** : Implémenter le fix
   - Corriger le problème identifié
   - Ajouter des tests de régression pour empêcher le bug de revenir
   - S'assurer que tous les tests existants passent toujours

4. **Tests** : Exécuter la suite de tests
   ```bash
   cd JiraVision
   pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q
   ```
   - Vérifier que le bug est corrigé
   - Vérifier que les tests de régression passent
   - Commenter l'issue avec les résultats des tests

5. **Pull Request** : Créer une PR vers `dev`
   - Référencer l'issue bug (ex: `Fixes #42`)
   - Décrire la cause du bug et la solution implémentée
   - Lier à l'US d'origine si applicable

6. **Validation** : La PR doit passer tous les checks CI/CD

7. **Merge** : Merger après approbation

8. **Clôture de l'issue** : Fermer l'issue bug

---

## Règles d'assignation

- **Assigner @copilot** sur toutes les issues US et bugs dès qu'ils sont pris en charge
- Utiliser l'assignation GitHub pour suivre qui travaille sur quoi
- Ne jamais laisser une issue sans assigné si le travail est en cours

Commande pour s'assigner via l'interface GitHub :
```
# Via l'interface web ou via gh CLI
gh issue edit <numéro> --add-assignee @copilot
```

---

## Tests obligatoires

### Exigences

- **Obligation de lancer pytest** avant toute PR
- **Commenter l'issue** avec les résultats des tests (succès/échec, couverture)
- **100% de couverture** pour le code nouveau ou modifié

### Commandes

```bash
# Tests complets avec couverture
cd JiraVision
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q

# Tests rapides (sans rapport de couverture)
cd JiraVision
pytest -q

# Tests d'un module spécifique
cd JiraVision
pytest tests/test_routes.py -v

# Voir le rapport HTML de couverture
python -m http.server --directory JiraVision/htmlcov 8000
# Ouvrir http://localhost:8000 dans le navigateur
```

### Format du commentaire sur l'issue

```markdown
## Résultats des tests

**Date** : YYYY-MM-DD
**Branche** : DEV-US#XX
**Commit** : <hash>

### Tests
- ✅ Tous les tests passent (X tests, Y assertions)
- ✅ Couverture : 100% des lignes ajoutées/modifiées

### Commande
```bash
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:htmlcov -q
```

### Output
```
[Coller l'output complet de pytest ici]
```
```

---

## Structure de documentation

### Pour chaque User Story

Créer deux fichiers dans `docs/epics/epic-10/us-XX/` :

1. **`technical-design.md`** : Documentation technique
   ```markdown
   # Technical Design - US#XX : [Titre]
   
   ## Contexte
   [Description du problème et de la solution]
   
   ## Architecture
   [Diagrammes, composants affectés]
   
   ## Décisions techniques
   [Choix technologiques et justifications]
   
   ## Impacts
   [Impacts sur le code existant, migrations nécessaires]
   
   ## Références
   [Liens vers l'issue, PR, documentation externe]
   ```

2. **`tests-report.md`** : Rapport de tests
   ```markdown
   # Tests Report - US#XX : [Titre]
   
   ## Résumé
   - Tests ajoutés : X
   - Tests modifiés : Y
   - Couverture : Z%
   
   ## Tests unitaires
   [Liste des tests ajoutés]
   
   ## Tests d'intégration
   [Tests d'intégration si applicable]
   
   ## Cas limites testés
   [Edge cases couverts]
   
   ## Résultats pytest
   ```
   [Output complet de pytest]
   ```
   ```

### Pour l'Epic RBB (Recette Build & Battle)

Créer `docs/epics/epic-10/rbb/tests-report.md` pour documenter les tests de validation complète de l'Epic.

---

## Organisation des tests

### Structure des répertoires

```
JiraVision/tests/
├── epic_10/                    # Tests spécifiques à l'Epic #10
│   ├── us_25/                  # Tests pour US#25
│   │   ├── test_us25_feature.py
│   │   └── test_us25_integration.py
│   ├── us_26/                  # Tests pour US#26
│   │   └── test_us26_feature.py
│   └── ...
├── general/                    # Tests généraux par thématique
│   ├── ai/                     # Tests liés à l'AI
│   │   ├── test_ai_proxy.py
│   │   └── test_ai_service_client.py
│   ├── auth/                   # Tests d'authentification
│   │   ├── test_auth_session_store.py
│   │   └── test_routes_auth_*.py
│   ├── jira/                   # Tests clients Jira
│   │   └── test_clients_jira*.py
│   ├── llm/                    # Tests LLM
│   │   └── test_clients_llm*.py
│   ├── core/                   # Tests core (Redis, etc.)
│   │   └── test_core_redis.py
│   ├── observability/          # Tests télémétrie/métriques
│   │   ├── test_metrics.py
│   │   └── test_telemetry.py
│   ├── routes/                 # Tests routes API
│   │   └── test_routes*.py
│   └── coverage/               # Tests de couverture complémentaires
│       └── test_coverage_remaining.py
└── conftest.py                 # Configuration pytest partagée
```

### Convention de nommage

- Tests US : `test_us<numéro>_<feature>.py`
- Tests généraux : `test_<thématique>_<composant>.py`
- Tests d'intégration : `test_<composant>_integration.py`

### Migration progressive

Les tests existants actuellement dans `JiraVision/tests/` (sans structure de sous-répertoires) seront progressivement réorganisés selon cette structure lors des prochaines US.

---

## Stratégie de branches

### Branches principales

- **`master`** : Branche stable de production
  - Code validé et déployable en production
  - Merge uniquement depuis `dev` après validation complète
  - Tag avec les versions (v1.0.0, v1.1.0, etc.)

- **`dev`** : Branche d'intégration
  - Intégration continue des US et bugfixes
  - Tous les développements convergent ici avant d'aller en `master`
  - Tests CI/CD doivent passer en permanence

- **`stable-base`** : Branche de base stable
  - Point de référence stable pour les développements
  - Utilisé comme base pour les branches de feature en cas de besoin

### Branches de travail

- **User Story** : `DEV-US#<numéro>`
  - Exemple : `DEV-US#25`
  - Créée depuis `dev`
  - Mergée dans `dev` via PR

- **Bugfix** : `bugfix/bug-<numéro>-<description-courte>`
  - Exemple : `bugfix/bug-42-fix-auth-redirect`
  - Créée depuis `dev`
  - Mergée dans `dev` via PR

- **Hotfix** : `hotfix/<description>` (si nécessaire)
  - Pour corrections urgentes en production
  - Créée depuis `master`
  - Mergée dans `master` ET `dev`

### Workflow Git

```bash
# Commencer une nouvelle US
git checkout dev
git pull origin dev
git checkout -b DEV-US#25

# Travailler et committer
git add .
git commit -m "feat: ajout de la fonctionnalité X"

# Pousser la branche
git push origin DEV-US#25

# Après merge de la PR, nettoyer la branche locale
git checkout dev
git pull origin dev
git branch -d DEV-US#25
```

---

## Règles des Pull Requests

### Destination

- **Toutes les PRs doivent cibler la branche `dev` uniquement**
- Ne jamais créer de PR directement vers `master`
- Le merge de `dev` vers `master` se fait après validation complète de l'Epic

### Processus de validation

1. **Création de la PR**
   - Utiliser le template `.github/PULL_REQUEST_TEMPLATE.md`
   - Remplir toutes les sections (Description, Checklist, Migration guidance si applicable)
   - Référencer l'issue associée avec `Closes #XX` ou `Fixes #XX`

2. **Checks automatiques** (CI/CD)
   - ✅ Tests : 100% de couverture requise
   - ✅ Linting : Black, flake8 sans erreur
   - ✅ Type checking : mypy sans erreur
   - ✅ Security : Bandit, pip-audit (justifier les exceptions si nécessaire)

3. **Review**
   - Au moins 1 approbation requise
   - Répondre aux commentaires de review
   - Effectuer les corrections demandées

4. **Merge**
   - Après approbation et succès de tous les checks
   - Utiliser "Squash and merge" ou "Merge commit" selon la préférence de l'équipe
   - Supprimer la branche après merge (option automatique GitHub)

### Checklist PR

Avant de créer une PR, vérifier :

- [ ] Tests ajoutés/mis à jour avec 100% de couverture
- [ ] `black .` exécuté sans erreur
- [ ] `flake8 .` exécuté sans erreur
- [ ] `mypy .` exécuté sans erreur
- [ ] Tests passent : `pytest -q`
- [ ] Documentation technique créée (si US)
- [ ] Tests report créé (si US)
- [ ] Issue commentée avec résultats des tests
- [ ] Branche à jour avec `dev`

---

## Intégration GitHub Project

### Configuration

- **GitHub Projects v2** est utilisé pour le suivi du projet
- **Token classic requis** : Pour l'ajout automatique des issues/PRs aux projets, un token GitHub classic avec les permissions `repo` et `project` est nécessaire

### Configuration du token

1. Aller sur GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Générer un nouveau token avec les scopes :
   - `repo` (accès complet aux repositories)
   - `project` (accès aux projects)
3. Copier le token et le stocker en sécurité
4. Ajouter le token comme secret dans le repository :
   - Repository Settings > Secrets and variables > Actions
   - Créer un secret `GH_PROJECT_TOKEN` avec la valeur du token

### Ajout automatique

Si configuré correctement, les issues et PRs seront automatiquement ajoutées au projet GitHub associé à l'Epic.

Sinon, ajouter manuellement :
- Via l'interface GitHub : Sidebar de l'issue/PR > Projects > Ajouter au projet
- Via gh CLI :
  ```bash
  gh issue edit <numéro> --add-project "<nom-du-projet>"
  ```

---

## Démarrage de l'application en développement

### Prérequis

- Docker et Docker Compose installés
- Python 3.11+
- Variables d'environnement configurées

### Variables d'environnement importantes

Créer un fichier `JiraVision/.env` avec au minimum :

```bash
# Atlassian OAuth
ATLASSIAN_CLIENT_ID=your_client_id
ATLASSIAN_CLIENT_SECRET=your_client_secret
ATLASSIAN_REDIRECT_URI=http://localhost:8000/auth/callback
ATLASSIAN_SCOPES=read:jira-user,read:jira-work,write:jira-work

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Service (optionnel)
AI_SERVICE_URL=http://ai-service:8000

# Observabilité (optionnel)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

**Note importante** : `ATLASSIAN_REDIRECT_URI` doit correspondre exactement à l'URL de callback configurée dans l'application Atlassian OAuth.

### Démarrage avec Docker Compose

```bash
# Copier le fichier d'exemple
cp JiraVision/.env.example JiraVision/.env

# Éditer les variables d'environnement
nano JiraVision/.env

# Démarrer l'application et Redis
cd JiraVision
docker-compose up --build

# En arrière-plan (mode détaché)
docker-compose up -d --build

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

L'application sera accessible sur : http://localhost:8000

### Démarrage avec Uvicorn (sans Docker)

```bash
# Installer les dépendances
cd JiraVision
pip install -r requirements.txt

# Démarrer Redis (dans un terminal séparé)
redis-server

# Démarrer l'application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'application sera accessible sur : http://localhost:8000

### Endpoints disponibles

- `/` : Page d'accueil
- `/auth/login` : Authentification Atlassian OAuth
- `/auth/callback` : Callback OAuth
- `/jira/*` : Endpoints Jira
- `/ai/*` : Endpoints AI (proxy vers ai-service si configuré)
- `/metrics` : Métriques Prometheus
- `/docs` : Documentation OpenAPI (Swagger UI)
- `/redoc` : Documentation ReDoc

### Développement avec rechargement automatique

Uvicorn en mode `--reload` détecte automatiquement les changements de code et recharge l'application.

Pour un développement plus avancé avec diagnostics continus :
```bash
# Utiliser mode watch avec tests
cd JiraVision
pytest --watch
```

### Debugging

Pour débugger l'application :

1. **Logs applicatifs** : Configurer le niveau de log dans `.env`
   ```bash
   LOG_LEVEL=DEBUG
   ```

2. **Debugger Python** : Utiliser VSCode ou PyCharm avec les configurations de debug appropriées

3. **Tests avec output détaillé**
   ```bash
   pytest -v --tb=long
   ```

---

## Résumé des commandes essentielles

```bash
# Créer une branche US
git checkout dev && git pull origin dev && git checkout -b DEV-US#XX

# Tests complets
cd JiraVision && pytest --cov=app --cov-report=html:htmlcov -q

# Linting et formatage
black . && flake8 . && mypy .

# Pousser et créer une PR
git push origin DEV-US#XX
gh pr create --base dev --title "feat: US#XX - titre" --body "Closes #XX"

# Démarrer l'app en dev
cd JiraVision && docker-compose up --build

# Voir les logs Docker
docker-compose logs -f app
```

---

## Contacts et ressources

- **Repository** : https://github.com/Alibenhaddou/Depot
- **Epic #10** : https://github.com/Alibenhaddou/Depot/issues/10
- **Documentation services** : `/docs/services/`
- **Template PR** : `.github/PULL_REQUEST_TEMPLATE.md`
- **Contributing** : `CONTRIBUTING.md`

---

**Version** : 1.0  
**Dernière mise à jour** : 2026-01-16  
**Auteur** : @copilot pour Epic #10
