# EPIC-10 / US-21 — Clarification UI/UX panel projets PO

## Objectif
Rendre le panel Projets PO plus lisible et compréhensible, tout en restant conforme RGAA et professionnel.

## Parcours proposé
1) **Chargement initial**
   - Message d’attente explicite pendant le chargement (ex: « Chargement de vos projets Jira… »).
   - Si aucun projet actif, CTA principal : **« Synchroniser Jira »**.

2) **Liste principale unique**
   - Remplacer l’affichage séparé par une liste « Mes projets » avec filtres :
     - **Actifs** (par défaut)
     - **Inactifs**
     - **Masqués**
   - Chaque projet affiche un badge de statut (Actif / Inactif / Masqué).

3) **Détail et actions contextuelles**
   - Les actions ne s’affichent que si un projet est sélectionné.
   - Regrouper les actions de masquage sous un menu « Masquer » (temporaire / définitif).

4) **Projets inactifs**
   - Remplacer la section fixe par un bloc repliable :
     - Titre : « Projets détectés sans activité »
     - Aide : « Inactif = pas d’epic active. Vous pouvez ré‑ajouter manuellement. »
   - Bouton : **« Ré‑ajouter »** (et non « Ajouter ») pour réduire l’ambiguïté.

## Micro‑copies / libellés
- « Projets inactifs » → « Projets détectés sans activité »
- « Ré‑ajout manuel » → « Forcer l’ajout »
- « Rafraîchir » → « Synchroniser Jira »
- Message succès « Projets chargés. » → toast discret (zone status), non affiché dans la carte.

## UI/Styles (RGAA + pro)
- Ajout d’accents colorés légers :
  - Badge **Actif** : vert doux (#E8F5E9, texte #1B5E20)
  - Badge **Inactif** : ambre doux (#FFF8E1, texte #8D6E00)
  - Badge **Masqué** : bleu/gris doux (#EEF2F7, texte #314155)
- CTA principal (Synchroniser Jira) : bouton primaire bleu (#2D6CDF, texte blanc), contraste vérifié.
- Conserver focus visible et navigation clavier.

## Contraintes RGAA
- Contrastes conformes (WCAG AA minimum).
- Rôles ARIA et libellés explicites conservés.
- Les filtres et le bloc repliable doivent être accessibles au clavier.

## Critères d’acceptation
- Le chargement initial affiche un message clair.
- Une seule liste « Mes projets » avec filtres Actifs/Inactifs/Masqués.
- Les actions sont uniquement visibles si un projet est sélectionné.
- La section « Projets détectés sans activité » est repliable et expliquée.
- Les libellés proposés sont appliqués.
- Les accents colorés restent sobres et conformes RGAA.
