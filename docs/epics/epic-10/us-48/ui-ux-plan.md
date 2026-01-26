# Plan d’amélioration UI/UX – Panel Projets PO

## 1. Recueil des US et exigences UI/UX  
- US-15 : Panel PO  
  - Cartes/onglets projets en haut (filtrées par instances actives)  
  - Zone détail projet sélectionné  
  - Actions : synchroniser, ajouter, masquer temporaire/définitif  
  - Liste projets inactifs + bouton “Ré-ajouter”  
- US-20 : Conformité RGAA  
  - Navigation clavier (Tab/Enter/Espace, flèches gauche/droite)  
  - Rôles ARIA (`tablist`, `tab`, `region`, `aria-live`, `aria-pressed`)  
  - Focus visible, contraste WCAG AA  
- US-21 : Styles et micro-copies  
  - Badges colorés sobres : Actif (vert), Inactif (ambre), Masqué (gris-bleu)  
  - Libellés : “Projets détectés sans activité”, “Forcer l’ajout”, “Synchroniser Jira”  
  - Micro-copies claires et accessibles  
- US-48 : Scénarios utilisateurs & retours bugs  
  - Message “Non autorisé” vs redirection brutale  
  - Comptage masqués/inactifs clairement affiché  
  - Gestion des erreurs réseau et état vide  

## 2. Problèmes identifiés  
- Filtre “Masqués” séparé du reste, peu visible  
- Liste “Inactifs” trop compacte, sans indication de contexte  
- Absence de skeleton loader ou indicateur de chargement global  
- Boutons d’action (ajout, synchro, masquage) peu uniformes  
- Détails projet minimalistes (pas de statut, pas de date de dernière synchro)  
- Message d’erreur générique, manque CTA “Réessayer”  

## 3. Proposition de design soigné  
1. Barre latérale gauche fixe  
   - Logo, instances, filtres (Actifs/Inactifs/Masqués) sous forme de **pills**  
   - Indicateur visuel du filtre actif (`aria-current`)  
2. Section principale  
   - **Skeleton cards** lors du chargement (animation légère)  
   - **Cartes détaillées** :  
     - Titre (project_key), description courte (project_name)  
     - Badges de statut (couleurs RGAA)  
     - Icônes d’action : rafraîchir, masquer, détails  
   - Tri visuel : icône “hot” sur projets à plus forte activité  
3. Zone détail à droite  
   - En-tête projet (clé + nom), date dernière synchro, instance  
   - Statistiques clés (nombre de stories/études ouvertes)  
   - Actions contextuelles (Masquer temp./def., Ré-ajouter) en bouton primaire/secondaire  
4. Bloc “Inactifs”  
   - Entête repliable (accordion ARIA)  
   - Liste de projets inactifs avec bouton “Forcer l’ajout”  
   - Indication nombre inactifs dans le pill “Inactifs (N)”  
5. Feedback et erreurs  
   - Zone toast ARIA-live en haut à droite pour retours (succès/erreur)  
   - Message d’erreur détaillé + bouton “Réessayer”  
6. Accessibilité  
   - Roving tabindex pour projets (navigation flèches)  
   - Labels explicites sur tous les boutons  
   - Contrastes conformes (test WCAG AA)  

## 4. Étapes de mise en œuvre  
1. Créer fichiers CSS et classes (`pills`, `card`, `skeleton`)  
2. Mettre à jour `poc.html` : restructurer layout en grilles/flex  
3. Adapter `poc.js` :  
   - Afficher skeleton pendant chargement  
   - Rendre “Inactifs” en accordion ARIA  
   - Ajouter stats et date synchro dans détails  
   - Uniformiser boutons et badges  
4. Tests manuels et automatisés (accessibilité + snapshot UI)  
5. Recette finale et documentation utilisateur

## 5. Référence tickets GitHub UI/UX Panel PO
- #53 Harmonisation & amélioration des boutons d’action (Panel PO)
- #48 US: Gestion complète des projets (liste, détails, actions, synchro, masquage)
- #47 US-21: bugs UX/ARIA/accessibilité panneau statuts
- #20 / #19 Mise en conformité RGAA du panel PO
- #15 US: UI panel projets PO (structure, filtres, liste/inactifs)
- #16 US: Tests feature projets PO (accessibilité + non régression)

Ces tickets servent de backlog prioritaire pour les prochains incréments UI/UX du panel PO.