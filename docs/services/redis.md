# Service redis

## Objectif
Stockage clé-valeur en mémoire pour cache, sessions ou données temporaires.

## Responsabilités
- Stockage rapide et volatile.
- Partage d’état entre instances de l’API.

## Réseau et ports
- Conteneur: ct_redis
- Port exposé: 6379 -> 6379

## Configuration
- Aucune variable spécifique dans le Compose actuel.

## Journal des évolutions
| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Création de la documentation du service. | | |
