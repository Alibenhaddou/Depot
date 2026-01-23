# EPIC-10 / US-48 — Panel PO (Product Owner)

## [Mise à jour 2026-01-20]

### Fonctionnement de la détection des projets actifs
- Un projet est considéré comme "actif" s'il contient au moins un ticket de type Story ou Etude, dont le reporter est l'utilisateur courant, et dont le statut n'est ni "Done" ni "Annulé".
- La synchronisation automatique ou manuelle interroge Jira avec la JQL suivante :

    type in (Story, Etude) AND reporter = currentUser() AND status NOT IN ("Done", "Annulé")

- Les projets distincts sont extraits à partir des tickets trouvés.
- Les autres projets sont considérés comme "inactifs" ou "masqués" selon leur statut local.

### Points importants
- La logique précédente basée sur les epics a été remplacée pour une détection plus fiable et conforme au besoin métier.
- Le code orphelin (fonctions Epic non utilisées) a été supprimé pour plus de clarté.
- La documentation technique et utilisateur a été mise à jour pour refléter ce changement.
- Les tests unitaires ont été adaptés pour valider la nouvelle logique.

---

## Historique des modifications
- 2026-01-20 : Correction de la détection des projets actifs (voir bug #48)
- 2026-01-19 : Ajout de la synchronisation automatique au chargement du panel
- ...
