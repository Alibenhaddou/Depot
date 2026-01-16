# Service ai-service

## Objectif
Microservice dédié aux appels IA. Il sert de proxy, applique l’authentification partagée et centralise l’observabilité.

## Responsabilités
- Exposer une API IA dédiée.
- Appliquer l’authentification partagée.
- Gérer le proxy vers le fournisseur LLM.
- Centraliser logs/metrics liés à l’IA.

## Dépendances
- ollama (par défaut)

## Réseau et ports
- Conteneur: ct_ai_service
- Port exposé: 8001 -> 8000

## Configuration (variables d’environnement connues)
- AI_AUTH_ENABLED
- AI_SHARED_SECRET
- LLM_PROVIDER
- LLM_BASE_URL
- LLM_MODEL

## Journal des évolutions
| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Création de la documentation du service. | | |
