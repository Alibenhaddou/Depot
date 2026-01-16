# Service Ollama

## Objectif
Fournisseur local de modèles LLM utilisé par défaut par l’API principale et le ai-service.

## Rôle fonctionnel
- Exposer une API LLM locale compatible HTTP.
- Stocker les modèles dans un volume persistant.

## Endpoints (utilisés)

- `POST /api/chat` : génération de réponses (utilisé par `LLMClient`).

## Configuration

- `LLM_PROVIDER=ollama`
- `LLM_BASE_URL=http://ollama:11434`
- `LLM_MODEL=qwen2.5:3b`

## Stockage

- Volume Docker `ollama` monté sur `/root/.ollama` (modèles persistés).

## Observabilité

- Pas de métriques intégrées exposées par l’app.

## Évolutions attendues

- Support d’un provider externe (OpenAI) via `LLM_PROVIDER=openai`.
- Possibilité d’utiliser un LLM managé en prod.

## Journal des évolutions

| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Documentation fonctionnelle du service Ollama. | | |
