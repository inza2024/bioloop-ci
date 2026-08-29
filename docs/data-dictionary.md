# Dictionnaire de données — tranche verticale 01

| Champ | Unité | Provenance | Preuve | Règle |
|---|---|---|---|---|
| `quantity_kg` | kg de matière fraîche déclarée | déclaré | P1 | > 0 et ≤ 50 000 ; aucune pesée |
| `waste_type_id` | identifiant | déclaré | P1 | doit exister dans le catalogue |
| coordonnées producteur/unité | degrés décimaux | simulé | P0 | coordonnées fictives non publiques |
| `daily_capacity_kg` | kg/j | simulé | P0 | capacité de démonstration |
| compatibilité | liste d'identifiants | simulé | P0 | configuration fictive de l'unité |
| multiplicateur | URI/kg | simulé | P0 | convention logicielle 0,80 / 1,00 / 1,20 |
| scénario | URI | simulé | P0 | masse P1 × multiplicateur P0 ; résultat P0 |
| distance | km géodésiques illustratifs | simulé | P0 | haversine, deux décimales, sans route ni trafic |

## Invariant de preuve

Un calcul dérivé conserve le niveau de preuve le plus faible de ses entrées. Aucun champ de cette tranche ne peut être publié comme mesuré, vérifié ou certifié.
