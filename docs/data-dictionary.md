# Dictionnaire de données — tranches verticales 01 à 05

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
| `organization.id` | identifiant `ORG-*` | fictif | P0 | organisation isolant la portée des données privées |
| `demo_user.id` | identifiant `USER-*` | fictif | P0 | identité sélectionnable ; aucune authentification de production |
| `membership.role` | rôle contrôlé | fictif | P0 | une appartenance active par utilisateur de démonstration |
| `waste_declaration.owner_organization_id` | identifiant | attribution | P1 | déduit du site producteur ; filtre horizontal côté API |
| `collection.status` | `assigned` / `collected` | simulé puis déclaré par acteur | P0 puis P1 | affectation illustrative ; transition unique confirmée par la logistique assignée |
| `collection.stops` | séquence ordonnée | simulé | P0 | trois arrêts déterministes ; pas un itinéraire routier |
| `collection.total_straight_line_km` | km géodésiques illustratifs | simulé | P0 | aller-retour haversine soumis à validation humaine |
| `notification.dedup_key` | empreinte interne | événement | sans niveau métier | unicité SQLite ; empêche le doublon d'un même événement métier |
| `audit.actor_user_id` | identifiant | attribution | P0/P1/P2/P3/P4 selon événement | acteur fictif ayant déclenché l'opération |
| `audit.actor_organization_id` | identifiant | attribution | idem événement | organisation portée dans l'audit append-only |
| `verification.outcome` | `verified` / `non_conform` | vérifié | P4 | ligne séparée, horodatée, réservée au contrôleur terrain |
| `verification.idempotency_key` | texte contrôlé | événement | P4 | une relance renvoie le même contrôle sans dupliquer l'événement |
| projection `declared.value_kg` | kg attendus | base déclarée P1, résultat simulé | P0 | cadence P1 prolongée mécaniquement sur 7 ou 30 jours |
| projection `measured_basis.value_kg` | kg attendus | base mesurée P3, résultat simulé | P0 | dernière mesure P3 multipliée par la même cadence déclarée |
| `forecast.version` | identifiant | configuration | P0 | `deterministic-declaration-cadence-v1`, sans apprentissage ni LLM |
| `waste_declaration.client_idempotency_key` | texte opaque client | navigateur | sans promotion | unique par organisation ; rejouer la même clé renvoie la déclaration existante |
| `pilot_user.password_hash` | PHC Argon2id | secret dérivé | sécurité | jamais journalisé ni renvoyé par l'API |
| `pilot_session.token_hash` | hexadécimal SHA-256 | secret dérivé | sécurité | seul le cookie contient le jeton opaque ; expiration et révocation serveur |
| `pilot_membership.status` | `active` / `pending` | workflow d'accès | attribution | producteur/client actifs ; logistique/unité en attente ; rôles sensibles sur invitation |
| `pilot_membership.role` | rôle contrôlé | attribution serveur | attribution | plusieurs appartenances possibles, une seule active par session |
| `synthetic_data.seed` | entier | configuration | P0 | `20260830`, reproductibilité du profil enrichi |
| `synthetic_data.version` | identifiant | configuration | P0 | `pilot-p0-fixed-seed-v1` |
| `decision_metadata.uncertainty` | texte | contrat de service | P0 | limites explicites ; aucune distribution scientifique inventée |
| `decision_metadata.human_validation_required` | booléen | contrat de service | P0 | vrai pour prévision, appariement, tournée et anomalie de référence |
| `pilot_role_invitation.token_hash` | hexadécimal SHA-256 | secret dérivé | sécurité | jeton aléatoire affiché une fois ; expiration 1 à 168 h ; jamais stocké en clair |
| `pilot_admin_action` | événement | attribution serveur | selon décision | acteur, organisation, rôle, motif, corrélation et horodatage ; historique séparé |
| `transformation_run.status` | statut | déclaré par l'unité | P1 | `planned`, `in_progress`, `completed` ou `cancelled` ; transitions contrôlées |
| `transformation_input.measured_quantity` | kg | mesuré à l'entrée unité | P3 | lot accepté uniquement ; > 0 et ≤ masse P3 du lot source |
| `transformation_run.loss_quantity` | `kg`, `L` ou `m3` | mesuré | P3 | facultatif ; méthode et date obligatoires lorsqu'une perte est saisie |
| `product_batch.category` | catégorie contrôlée | déclaré et mesuré | P3 | aucune catégorie ne crée automatiquement une allégation d'engrais |
| `product_batch.quantity` | `kg`, `L` ou `m3` | mesuré par l'opérateur | P3 | saisie explicite ; jamais calculée depuis les URI illustratives |
| `product_batch.measurement_method` | texte | mesuré | P3 | méthode de mesure obligatoire et auditée |
| `product_batch.quality_status` | statut | workflow qualité | P3/P4 | `quarantine`, `pending_analysis`, `released` ou `rejected` |
| `product_quality_test` | valeur + unité | mesuré ou vérifié | P3/P4 | P4 uniquement lorsqu'enregistré par le contrôleur ; document facultatif |
| `product_release_event` | décision | vérifié interne | P4 | contrôleur/coordinateur seulement ; ne vaut jamais certification P5 |
| `inventory_movement.on_hand_delta` | même unité que le produit | événement | P3 ou P1 | production/ajustement/livraison ; somme dérivée, aucune quantité courante éditable |
| `inventory_movement.reserved_delta` | même unité que le produit | événement | P1/P3 | réservation/annulation/livraison ; registre immuable par déclencheurs SQLite |
| `customer_reservation.quantity` | même unité que le produit | déclaré client | P1 | produit libéré, disponible et clé idempotente unique par organisation cliente |
| `analytics.schema_version` | identifiant | configuration | sans promotion | `transformation-analytics-v1`, interne, sans entraînement ni LLM externe |

## Invariant de preuve

Une donnée ne monte jamais automatiquement de niveau : une pièce reste P2, une pesée saisie reste P3 et une décision d'une identité non authentifiée reste P1. Le calcul dérivé conserve le niveau le plus faible de ses entrées ; scénarios et projections restent P0 à cause des règles illustratives. Seule une ligne `verification` séparée, créée par le rôle contrôleur et auditée, porte P4. Aucun élément n'est certifié P5.

Une session authentifiée attribue un acteur et une organisation, mais ne change jamais le niveau de preuve d'une donnée métier. Une déclaration synchronisée depuis IndexedDB reste P1. Le client ne met jamais en file une pièce P2, une mesure P3, un lot, une décision ou une vérification.

Une entrée ou sortie de transformation réellement saisie est P3. Le contrôle qualité peut être P3 ou P4 selon le rôle ; l'événement séparé de libération est P4. Le stock dérivé ne rehausse aucun niveau. Réserver ou annuler est une déclaration P1 du client. Aucun de ces événements ne devient P5 sans processus de certification absent du MVP.

## Tables additives de la tranche 03

`organizations`, `demo_users`, `memberships`, `collections`, `notifications` et `verifications` sont ajoutées sans supprimer les lignes antérieures. Les colonnes `owner_organization_id` et les trois champs d'acteur d'audit sont ajoutés par `ALTER TABLE` ciblé. Les anciennes déclarations reconnues par leur `producer_id` sont rattachées à l'organisation fictive correspondante ; les anciens événements sans acteur restent lisibles avec des champs nuls.

## Tables additives de la tranche 04

`pilot_users`, `pilot_organizations`, `pilot_memberships`, `pilot_sessions`, `pilot_login_attempts` et `pilot_role_invitations` sont créées par Alembic. `client_idempotency_key` est ajouté à `waste_declarations` avec un index unique par organisation. La migration ne supprime ni table, ni colonne, ni historique existant.

## Tables additives de la tranche 05

`pilot_admin_actions`, `transformation_runs`, `transformation_inputs`, `transformation_evidence`, `product_batches`, `product_quality_tests`, `product_release_events`, `customer_reservations` et `inventory_movements` sont ajoutées par `0005_transformation_inventory`. `site_id` complète les organisations pilotes et les invitations reçoivent acteur, création, utilisation et révocation. Les soldes sont calculés depuis les mouvements ; deux déclencheurs SQLite interdisent leur mise à jour et leur suppression. Le `downgrade` ne détruit aucune donnée.
