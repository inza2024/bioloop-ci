# Jeu analytique interne — `transformation-analytics-v1`

## Finalité et classification

Ce jeu prépare une future analyse des transformations BioLoop. Il relie des intrants déclarés/mesurés, un type de déchet, un procédé, une durée, des pertes, des sorties mesurées et leur statut qualité. Il est strictement interne et ne constitue ni validation scientifique, ni jeu d'entraînement autorisé.

- `training_authorized`: `false`
- `external_llm_used`: `false`
- accès : coordinateur BioLoop actif
- génération : requête SQL déterministe, sans modèle statistique
- données synthétiques : P0, identifiées par la source de démonstration
- actions locales : conservent leur propre niveau P1 à P4

## Grain et champs

Une ligne représente la combinaison d'une exécution, d'un lot d'entrée et, lorsqu'elle existe, d'un lot produit. Les champs couvrent : identifiants de transformation/lot/produit, procédé, dates, statut, quantité et preuve d'entrée, type de déchet, acceptation, pertes, quantité/unité/preuve de sortie et statut qualité.

## Limites

Le schéma ne permet pas de déduire un rendement scientifique, une performance économique, une valeur énergétique, une conformité fertilisante ou une causalité. Les durées incomplètes, unités physiques hétérogènes, méthodes de mesure déclarées et données P0 doivent être filtrées et validées avant toute étude future. Aucun calcul métier ni décision automatisée ne consomme ce jeu dans le MVP.
