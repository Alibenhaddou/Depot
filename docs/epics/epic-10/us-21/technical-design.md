# EPIC-10 / US-21 — Clarification UI/UX panel projets PO

## Objectif
Rendre le panel Projets PO plus lisible et compréhensible, tout en restant conforme RGAA et professionnel.

## Parcours proposé
### Statuts fonctionnels (source de vérité)
- **Actif** : projet présent et mis en avant dans le dashboard.
- **Masqué** : masqué par l'utilisateur pour réduire le bruit visuel ; il réapparaît lors d'une nouvelle session/connexion (non définitif).
- **Inactif** : projet non mis en évidence et ne revient qu'après une synchronisation manuelle (ex: bouton « Synchroniser Jira »).

### Persistance / source de vérité
- **Masqué** : état **session-scopé** (stocké côté backend dans la session utilisateur, clé par `cloud_id` + `project_key`). Effet : disparaît de la vue tant que la session vit ; réapparaît à la reconnexion.
- **Inactif** : état issu de la synchronisation Jira (backend). Ne change que sur synchro manuelle (« Synchroniser Jira »).
- **Actif** : état par défaut après synchro ; peut passer à masqué via action utilisateur.

### Multi-instance Jira (cloud_id)
- Toutes les actions (masquage, sélection, filtres) sont scoppées par `cloud_id`.
- Les listes Actifs/Inactifs/Masqués ne mélangent pas plusieurs instances : l’utilisateur voit les projets de l’instance Jira courante.
- Le masquage session-scopé est donc indexé par (`cloud_id`, `project_key`).

### Règle de tri (priorisation)
- Objectif : mettre en haut les projets les plus « chauds » pour l’utilisateur.
- Critère principal : nombre de tickets **Story** ou **Étude** (non annulés, non terminés) **assignés à l’utilisateur**.
   - Filtrer sur statuses non terminés / non annulés (exclure Done/Cancelled).
   - Compter uniquement les issues affectées à l’utilisateur courant.
- Tri décroissant sur ce volume ; à égalité : tri alphabétique sur `project_key`.
- Application : tri côté frontend sur les données reçues, ou idéalement fourni déjà trié par le backend si le comptage est calculé lors de la synchro.

1) **Chargement initial**
   - Message d’attente explicite pendant le chargement (ex: « Chargement de vos projets Jira… »).
   - Si aucun projet actif, CTA principal : **« Synchroniser Jira »**.

2) **Liste principale (priorité Actifs)**
   - Colonne gauche compacte « Mes projets » centrée sur les **Actifs** (filtre par défaut).
   - Switch de filtre sous forme de pills / boutons discrets (Actifs / Inactifs / Masqués) avec `aria-pressed` et focus visible.
   - Les **Masqués** restent accessibles via ce filtre (ou un mini tiroir repliable) pour ne pas occuper d’espace en permanence.
   - Chaque projet affiche un badge de statut (Actif / Inactif / Masqué) avec les couleurs sobres définies.

3) **Détail et actions contextuelles**
   - Les actions ne s’affichent que si un projet est sélectionné.
   - Regrouper les actions de masquage sous un menu « Masquer » (temporaire / définitif).

4) **Projets inactifs (bloc discret)**
   - Bloc repliable minimal (« Projets détectés sans activité ») qui prend peu d’espace ; fermé par défaut.
   - Texte d’aide : « Inactif = pas d’epic active. Vous pouvez ré‑ajouter manuellement. »
   - Bouton : **« Ré‑ajouter »** (au clic ouvre le flux d’ajout manuel) ; visible seulement quand on déplie le bloc.

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
- Layout recommandé : colonne gauche compacte pour la liste (Actifs par défaut), panneau droit dédié au détail/étapes futures (epics à venir). La liste ne doit pas occuper plus que nécessaire ; le bloc Inactifs reste replié, les Masqués sont consultables via filtre/drawer.

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
