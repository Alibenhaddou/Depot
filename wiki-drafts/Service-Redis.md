# Service Redis

## Objectif
Stockage clé‑valeur en mémoire utilisé pour la **gestion des sessions** et du cache applicatif.

## Rôle fonctionnel
- Stocker les sessions utilisateur (OAuth Atlassian).
- Permettre une persistance temporaire entre requêtes.
- Offrir un fallback en mémoire si Redis indisponible (dev only).

## Données stockées

### Clé principale
- `session:{sid}` → JSON sérialisé.

### Exemple (session)
```json
{
  "created_at": 1737000000,
  "cloud_ids": ["<cloud_id>"]
}
```

## TTL & expiration

- TTL glissant : renouvelé à chaque accès.
- Valeur contrôlée par `SESSION_MAX_AGE_SECONDS`.

## Accès

- Lecture / écriture via `app/core/redis.py`.
- En cas d’indisponibilité, fallback vers `_local_store` (mémoire locale).

## Sécurité

- Aucune donnée sensible ne doit être stockée en clair en dehors des tokens nécessaires.
- Les tokens OAuth sont stockés dans la session Redis (accès contrôlé via cookie signé).

## Observabilité

- Pas de métriques dédiées à Redis dans l’app actuelle.

## Évolutions attendues

- Externaliser Redis (managed) en prod.
- Ajouter métriques ou monitoring Redis.
- Isoler les données (si multi‑tenant).

## Journal des évolutions

| Date | Version | Description | Auteur | Référence |
|------|---------|-------------|--------|-----------|
| 2026-01-16 | initial | Documentation fonctionnelle du service Redis. | | |
