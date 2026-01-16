# Documentation – JiraVision

Bienvenue dans la documentation **exhaustive** de JiraVision. Ce wiki est la **source unique de vérité** pour :
- l’infrastructure applicative,
- l’architecture technique,
- la documentation fonctionnelle **par service**.

> ✅ **Politique d’évolution** : toute modification applicative (code, config, infra, endpoints) doit **mettre à jour** la page correspondante et son **journal des évolutions**.

## Navigation

- [Infrastructure applicative](Infrastructure-applicative)
- [Architecture technique](Architecture-technique)
- [Documentation fonctionnelle par service](Services)

## Organisation & extensibilité

Ce wiki est conçu pour accompagner les évolutions futures :
- chaque page contient un **journal des évolutions** ;
- chaque service dispose d’une page **fonctionnelle dédiée** ;
- les flux majeurs sont décrits avec **diagrammes** (Mermaid) ;
- la documentation est **scindée** par domaines pour éviter les “dumps” monolithiques.

## Règles de mise à jour (obligatoires)

1. **Toute PR** qui change un comportement utilisateur, un endpoint, une configuration, un flux, un service ou une dépendance **doit** :
   - mettre à jour la page concernée,
   - ajouter une ligne dans le **journal des évolutions**.
2. Toute décision structurante (ajout de service, changement d’auth, changement d’infra) **doit** être reflétée dans :
   - [Infrastructure applicative](Infrastructure-applicative) **ou**
   - [Architecture technique](Architecture-technique).
3. Les pages par service restent le **contrat fonctionnel** de référence.

## Conventions de rédaction

- Utiliser le **présent** et un ton factuel.
- Décrire ce qui est **en production** ou **en usage dans le POC**.
- Les sections obligatoires doivent rester présentes.

## Contact / ownership

- Owner principal : à renseigner
- Relecteur technique : à renseigner

## Journal des évolutions

| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Création du wiki et structure documentaire. | | |
