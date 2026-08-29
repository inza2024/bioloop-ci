# Dictionnaire de données — tranches verticales 01 et 02

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
| `evidence.original_filename` | texte d'affichage | documenté | P2 | jamais utilisé comme chemin de stockage |
| `evidence.media_type` | MIME | documenté | P2 | JPEG, PNG ou PDF, concordant avec extension et signature |
| `evidence.size_bytes` | octets | documenté | P2 | > 0 et ≤ 5 Mio |
| `evidence.sha256` | hexadécimal SHA-256 | calculé sur pièce P2 | P2 | empreinte du binaire, pas une validation du contenu |
| `evidence.captured_at` | ISO 8601 avec fuseau | déclaré | P2 | facultatif ; EXIF non fiable et non promu P4 |
| `measurement.quantity_kg` | kg de matière fraîche mesurée | mesuré | P3 | > 0 et ≤ 50 000 ; mesure immuable |
| `measurement.method` | catégorie contrôlée | mesuré | P3 | méthode déclarée, appareil facultatif |
| `measurement.supersedes_measurement_id` | identifiant | mesuré | P3 | correction par nouvelle ligne, ancienne conservée |
| `lot.measured_quantity_kg` | kg | dérivé de mesure | P3 | copie immuable de la mesure source, jamais de la déclaration P1 |
| `lot.status` | statut | événement de démo | P1/P3 | `lot_created`, puis une seule décision `accepted` ou `refused` |
| décision de lot | texte/horodatage | déclaré par acteur non authentifié | P1 | motif obligatoire pour refus ; jamais P4 |
| `estimate_lineage` | identifiants | audit | P0/P3 | parent P1, enfant recalculé, mesure P3 source |
| scénario recalculé | URI | simulé | P0 | masse P3 × multiplicateur P0 ; sortie toujours P0 |

## Invariant de preuve

Une donnée ne monte jamais automatiquement de niveau : une pièce reste P2, une pesée saisie reste P3 et une décision non authentifiée reste P1. Le calcul dérivé conserve le niveau le plus faible de ses entrées ; les scénarios restent P0 à cause des facteurs illustratifs. Aucun élément ne peut être publié comme vérifié P4 ou certifié P5.
