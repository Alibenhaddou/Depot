# Service api

## Objectif
Backend principal de JiraVision. Il expose l’API métier, orchestre les requêtes, et délègue les appels IA au service dédié.

## Responsabilités
- Exposer les routes HTTP de l’application.
- Gérer la logique métier.
- Interagir avec Redis pour le cache et/ou les sessions.
- Appeler le service ai-service pour les fonctionnalités IA.

## Dépendances
- redis
- ai-service

## Réseau et ports
- Conteneur: ct_api
- Port exposé: 8000 -> 8000

## Configuration (variables d’environnement connues)
- REDIS_HOST
- REDIS_PORT
- AI_SERVICE_URL
- AI_AUTH_ENABLED
- AI_SHARED_SECRET

## Journal des évolutions
| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Création de la documentation du service. | | |
