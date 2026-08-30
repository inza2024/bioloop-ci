# Fiche des services décisionnels déterministes — v1

## Statut commun

- Classification : simulation illustrative P0.
- Exécution : locale, déterministe, sans LLM, modèle entraîné ou service externe.
- Sortie : proposition ou signal à revoir ; jamais une commande, une preuve, un rejet automatique ou une allégation scientifique.
- Validation humaine : obligatoire.

## ForecastService

- Version : `deterministic-declaration-cadence-v1`.
- Variables : masse déclarée P1, dernière masse P3 disponible, fréquence, date de disponibilité.
- Période : 7 et 30 jours.
- Incertitude : non quantifiée faute de distribution et de validation terrain.
- Limites : pas de saisonnalité, contamination, indisponibilité, acceptation probable ou production réelle.

## MatchingService

- Version : `compatibility-capacity-distance-v1`.
- Variables : type, masse, compatibilités/capacités P0 et coordonnées P0.
- Période : instantanée.
- Incertitude : qualité matière, route et trafic absents.
- Limites : catalogue fictif, aucune analyse matière.

## RoutingService

- Version : `direct-haversine-roundtrip-v1`.
- Variables : coordonnées P0, date, masse.
- Période : date déclarée.
- Incertitude : aucune distance routière ou durée.
- Limites : un seul gisement, aucun solveur multi-véhicules.

## AnomalyDetectionService

- Version : `declared-measured-gap-rule-v1`.
- Variables : masse P1 et masse P3.
- Période : comparaison ponctuelle.
- Règle : signal de revue lorsque l'écart relatif atteint 25 %.
- Incertitude : seuil logiciel non validé scientifiquement.
- Limites : ne détecte ni fraude, ni contamination, ni erreur de capteur ; ne change aucun niveau de preuve.
