# ADR 0005 — Administration, transformation mesurée et inventaire dérivé

- Statut : accepté pour le pilote local, non certifié production
- Date : 2026-09-02

## Contexte

La tranche 04 apporte comptes, sessions, organisations et PWA, mais ne couvre ni validation administrative complète, ni conversion physique traçable après acceptation d'un lot. Le rapport de référence interdit de confondre les URI illustratives P0 avec un rendement scientifique ou une quantité réelle de biogaz, digestat ou fertilisant.

## Décision

- Conserver le monolithe modulaire FastAPI/Next.js et étendre Alembic de façon additive.
- Réserver l'administration au coordinateur actif ; empêcher l'auto-approbation et l'auto-attribution des rôles sensibles.
- Générer les invitations avec un jeton aléatoire, stocker uniquement SHA-256, imposer une expiration et limiter la livraison à l'affichage local de démonstration.
- Créer une exécution de transformation uniquement depuis des lots acceptés de l'unité et conserver chaque mesure d'entrée, preuve, opérateur, statut et perte.
- Ne jamais créer de sortie physique à partir d'une URI : toute sortie produit exige catégorie, quantité, unité, méthode, date et localisation explicites.
- Distinguer la mesure produit P3, le contrôle qualité P3/P4 et l'événement de libération interne P4. Aucune certification P5 ni allégation automatique d'engrais.
- Enregistrer production, ajustement, réservation, annulation et livraison dans un registre append-only. Calculer `on_hand`, `reserved` et `available` par somme des mouvements.
- Publier au client uniquement les produits `released` avec disponibilité positive et isoler réservations/annulations par organisation.
- Documenter un jeu analytique interne versionné ; interdire entraînement et appel à un LLM externe dans cette tranche.

## Conséquences

Le parcours local relie désormais déclaration, preuve, mesure, collecte, lot, transformation, produit, qualité, stock et réservation avec acteurs, organisations, horodatages, corrélations et niveaux de preuve. La démo ne couvre pas laboratoire certifié, signature forte, stockage objet, journal inviolable, paiement, facturation, transport de livraison, conversion énergétique validée, conformité réglementaire fertilisante, sauvegarde ou exploitation de production.

Le `downgrade` de la migration reste volontairement non destructif. Cette prudence protège les données pilotes au prix d'une suppression manuelle des nouvelles tables si un retour de schéma complet devenait nécessaire.
