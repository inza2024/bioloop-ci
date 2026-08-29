# ADR 0003 — Identités, autorisations et notifications de démonstration

- Statut : accepté pour le démonstrateur
- Date : 2026-08-29

## Contexte

La troisième tranche doit démontrer une responsabilité distribuée entre organisations sans prétendre fournir une authentification de production. Le parcours doit préserver les données existantes, empêcher les lectures horizontales entre producteurs, réserver la décision à l'unité destinataire et n'autoriser P4 qu'à travers un événement de contrôle séparé. Les projections opérationnelles ne peuvent pas devenir des prédictions scientifiques faute d'historique qualifié.

## Décision

- Conserver le monolithe modulaire FastAPI, Next.js et SQLite.
- Charger les organisations, utilisateurs et appartenances fictifs depuis `data/fixtures/demo_identities.json`, puis les persister dans des tables additives.
- Transmettre l'identité choisie par `X-Demo-User-ID` et afficher partout « mode démonstration — aucune authentification de production ».
- Résoudre rôle, organisation et site côté API ; ne jamais considérer un masquage frontend comme une autorisation.
- Porter `actor_user_id`, `actor_organization_id` et `actor_role` dans chaque nouvel événement d'audit et dans les décisions attribuées.
- Rattacher chaque déclaration à une organisation productrice et appliquer les contrôles horizontaux dans `CollaborationService`.
- Représenter la collecte comme une affectation persistée et une transition unique `assigned → collected`, liée à une pièce P2 et à une mesure P3.
- Réserver `accepted/refused` à l'opérateur de l'unité destinataire ; conserver la décision comme P1 puisque l'identité n'est pas authentifiée pour la production.
- Créer P4 uniquement par une ligne `verification` explicite, horodatée, attribuée au rôle contrôleur terrain et protégée par une clé d'idempotence.
- Persister les notifications internes avec une clé de déduplication unique ; n'appeler aucun email, SMS ou fournisseur externe.
- Définir `ForecastService` comme interface remplaçable et utiliser `deterministic-declaration-cadence-v1`, qui agrège mécaniquement déclarations P1 et dernières mesures P3 sur 7 et 30 jours. Toute sortie reste P0.
- Conserver un mode de compatibilité sans en-tête pour les routes historiques des tranches 01–02, exécuté sous le coordinateur fictif. Les nouveaux espaces `/api/v1/demo/*` exigent toujours un en-tête explicite.

## Matrice d'autorisation

| Rôle | Portée | Mutations |
|---|---|---|
| Producteur | organisation propre | déclaration, proposition et preuve propres |
| Logistique | collecte assignée | preuve, mesure, confirmation, lot |
| Opérateur unité | unité liée | décision de lot uniquement |
| Contrôleur terrain | contrôles en attente | événement P4 |
| Coordinateur | transversal | audit et opérations historiques de démonstration |
| Client/agriculteur | produits représentés | aucune mutation |

## Conséquences

Le démonstrateur rend visibles les frontières de responsabilité et teste les refus serveur, mais un utilisateur peut encore choisir n'importe quelle identité fictive. Un pilote devra remplacer l'en-tête par une identité vérifiée, une session signée, MFA selon le risque, un RBAC administrable et un audit protégé contre l'altération.

Les projections sont reproductibles et auditables mais ne capturent aucune saisonnalité, contamination, indisponibilité, acceptation probable, temps routier ou production réelle. Avant d'envisager un modèle entraîné, il faut accumuler des historiques qualifiés de masses déclarées et mesurées, fréquence, saison, déchets, contamination, acceptation/refus, temps de collecte, capacité et production réellement mesurée.
