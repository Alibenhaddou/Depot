# EPIC-10 / US-20 — Conception technique

## Objectif
Rendre le panel projets PO conforme RGAA (navigation clavier, ARIA, contrastes).

## Ajustements UI
- Rôles ARIA (tablist, tab, region) et labels explicites.
- Région d’annonce `role=status` pour les messages d’état.
- Focus visible et logique lors de la sélection d’un projet.
- Navigation clavier sur les onglets (flèches gauche/droite).

## Notes
- Les boutons et champs restent accessibles au clavier par défaut.
- Les messages d’erreur/succès sont annoncés via `aria-live`.
