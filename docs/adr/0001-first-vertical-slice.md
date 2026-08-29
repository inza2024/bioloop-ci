# ADR 0001 — Première tranche verticale locale

- Statut : accepté pour le démonstrateur
- Date : 2026-08-28

## Contexte

Le rapport de référence recommande un parcours démontrable et auditable avant l'élargissement fonctionnel. Aucun coefficient scientifique validé n'est fourni dans les sources locales. La première version doit fonctionner sans API externe et distinguer les niveaux P0 à P5.

## Décision

- Utiliser Next.js/TypeScript et un monolithe modulaire FastAPI.
- Stocker les écritures locales dans SQLite et les fixtures P0 dans JSON.
- Produire uniquement un indice URI normalisé P0, sans unité physique ni économique.
- Effectuer l'appariement par règles de type/capacité et la collecte par aller-retour haversine simple.
- Garder toutes les décisions côté serveur, avec facteurs versionnés et empreinte SHA-256.
- Exiger explicitement une validation humaine ; aucune action externe n'est exécutée.

## Conséquences

Le parcours est reproductible, local et testable, mais ne permet aucune promesse de production réelle. Le passage à une estimation en `Nm³` est bloqué jusqu'à disponibilité d'un jeu de facteurs sourcé, borné, versionné et approuvé par un expert compétent.

