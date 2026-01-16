# Service ollama

## Objectif
Fournisseur local de modèles LLM, utilisé par le service ai-service.

## Responsabilités
- Héberger et servir des modèles LLM.
- Répondre aux requêtes du service ai-service.

## Réseau et ports
- Conteneur: ct_ollama
- Port exposé: 11434 -> 11434
- Volume: ollama (persistant pour les modèles)

## Configuration
- Aucune variable spécifique dans le Compose actuel.

## Journal des évolutions
| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Création de la documentation du service. | | |
