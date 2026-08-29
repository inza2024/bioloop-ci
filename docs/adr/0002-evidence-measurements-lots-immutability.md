# ADR 0002 — Preuves, mesures, lots et immutabilité

- Statut : accepté pour le démonstrateur
- Date : 2026-08-29

## Contexte

La deuxième tranche doit relier une déclaration P1 à une preuve P2, une mesure P3, un lot et une décision de l'unité, sans promouvoir automatiquement ces données en P4/P5. Elle doit fonctionner sur une base SQLite créée par la tranche précédente et conserver chaque estimation historique.

## Décision

- Ajouter les tables `evidence`, `measurements`, `lots`, `lot_evidence`, `lot_decisions`, `lot_status_events` et `estimate_lineage` par migrations additives.
- Stocker les pièces dans `data/local/evidence/`, hors Git, sous un nom aléatoire généré côté serveur.
- Accepter uniquement JPEG, PNG et PDF jusqu'à 5 Mio après validation concordante de l'extension, du MIME et de la signature binaire.
- Ne fournir aucune route de téléchargement par chemin et ne jamais journaliser le contenu binaire.
- Rendre preuves, mesures et décisions append-only au niveau de l'API : une correction de mesure crée une nouvelle ligne et une décision existante renvoie un conflit.
- Construire chaque lot depuis une mesure P3 précise et revalider la compatibilité/capacité de l'unité avec la masse mesurée.
- Créer un nouveau `EstimateRun` P0 pour un recalcul P3 et relier explicitement parent, enfant et mesure source.
- Classer la décision de l'acteur non authentifié en P1, jamais en P4.

## Conséquences

La provenance et les écarts déclaré/mesuré sont démontrables sans effacer l'historique. Le stockage local reste adapté à une démo, mais un pilote exigera authentification, autorisations, stockage objet, analyse antivirus, rétention, sauvegarde et validation terrain indépendante.
