# EPIC-10 / US-48 — Panel PO (Product Owner)

## Guide utilisateur (draft)

### Accès au panel
- Authentification obligatoire (OAuth Atlassian)
- Accès via l'URL `/ui` après connexion

### Fonctions principales
- **Lister les projets Jira** par instance (multi-cloud)
- **Filtrer** : Actifs, Inactifs, Masqués
- **Masquer** un projet (temporaire/définitif)
- **Réintégrer** un projet masqué
- **Synchroniser** les projets Jira (bouton « Synchroniser Jira »)
- **Ajouter** un projet manuellement

### Accessibilité (RGAA)
- Navigation clavier : tous les boutons, filtres, tabs et actions sont accessibles via Tab/Entrée/Espace
- Focus visible sur tous les éléments interactifs
- Feedback ARIA live sur les actions (masquage, synchronisation, erreurs)
- Contrastes respectés (vérifiés via outils RGAA)
- Libellés explicites et aria-labels sur les filtres, listes, statuts

### Bonnes pratiques d'utilisation
- Utiliser les filtres pour retrouver rapidement un projet
- Synchroniser régulièrement pour garder la liste à jour
- Utiliser le masquage définitif pour les projets obsolètes
- Réintégrer un projet masqué via le bouton dédié

### Limitations connues
- Les projets actifs sont détectés automatiquement : un projet est actif s'il contient au moins un ticket Story ou Etude, dont vous êtes le reporter, et dont le statut n'est ni "Done" ni "Annulé"
- La synchronisation dépend de la disponibilité de l'API Jira
- Les erreurs d'authentification ou de session sont signalées en temps réel

### Support
- En cas de problème, consulter la documentation technique ou contacter l'équipe support via le canal projet
