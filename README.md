# BioLoop CI — tranches verticales 01 à 04 du MVP

BioLoop CI est un démonstrateur local pour le SIREXE Hackathon 2026. Il relie la déclaration et l'estimation illustrative, la traçabilité P2/P3 du lot, une collaboration multi-acteurs, puis une fondation pilote mobile avec comptes locaux, sessions serveur, PWA et données synthétiques enrichies optionnelles.

> **Avertissement scientifique** — Aucun résultat affiché n'est un rendement biogaz validé. Le moteur produit des **URI (unités de rendement illustratives)** avec un jeu de multiplicateurs P0 intitulé « simulation illustrative ». Il n'effectue aucune conversion vers `Nm³`, `kWh`, FCFA, digestat, engrais ou crédit environnemental.

## Ce que la démo permet

- consulter huit producteurs et deux unités de transformation fictifs, tous P0 ;
- saisir une déclaration P1 (type, masse, fréquence et disponibilité) ;
- filtrer les unités par compatibilité et capacité fictives ;
- reproduire trois scénarios bas, central et haut avec une version et une empreinte SHA-256 ;
- afficher formule, unités, hypothèses, source de configuration et niveau de preuve ;
- proposer un aller-retour direct fondé sur une distance géodésique illustrative ;
- joindre une pièce JPEG, PNG ou PDF de 5 Mo maximum comme preuve P2 ;
- enregistrer une mesure P3 et une correction sous forme de nouvel enregistrement ;
- créer un lot à partir d'une mesure précise et de preuves associées ;
- accepter ou refuser le lot avec un acteur de démonstration non authentifié ;
- conserver le calcul P1 et créer un nouveau calcul lié à la mesure P3 ;
- consulter la provenance, l'historique de statut et les événements corrélés dans SQLite.
- sélectionner une identité et une organisation fictives, clairement signalées comme non authentifiées pour la production ;
- séparer les vues et autorisations des six rôles de démonstration ;
- persister des notifications internes idempotentes sans service externe ;
- confirmer une collecte par la logistique avant de créer le lot ;
- attribuer acceptation/refus à l'opérateur de l'unité destinataire ;
- créer un événement P4 uniquement avec le rôle contrôleur terrain ;
- afficher des projections déterministes P0 sur 7 et 30 jours, avec bases P1 et P3 séparées ;
- présenter au client un état vide honnête tant qu'aucun produit qualifié n'existe.

La tranche 04 ajoute une **authentification pilote locale**, pas une sécurité de production certifiée. La démo n'inclut volontairement ni paiement, ni crédit carbone, ni blockchain, ni agent IA autonome. Aucun LLM ni modèle externe n'intervient dans les calculs, prévisions, appariements ou tournées.

## Fondation pilote ajoutée en tranche 04

- inscription et connexion locales avec mot de passe Argon2id ;
- jeton de session opaque, dont seule l'empreinte SHA-256 est stockée côté serveur ;
- cookie `HttpOnly`, `SameSite=Lax`, `Secure` lorsque `BIOLOOP_COOKIE_SECURE=true` ;
- protection CSRF par double soumission, contrôle d'origine, limitation des échecs de connexion et erreurs génériques ;
- modèle utilisateur → appartenances → organisations, avec organisation/rôle actifs ;
- portails attribués par le backend, redirection par rôle et isolation des déclarations par organisation ;
- manifeste PWA, icônes, navigation mobile, statut réseau et proposition d'installation ;
- file IndexedDB réservée aux **nouvelles déclarations**, avec identifiant d'idempotence et synchronisation au retour du réseau ;
- SQLAlchemy 2 et Alembic pour la nouvelle fondation, sans réécriture brutale du repository SQLite historique ;
- profil enrichi P0 reproductible : 40 producteurs, 4 unités, véhicules/capacités fictifs, disponibilités, historiques et clients ;
- contrats `ForecastService`, `MatchingService`, `RoutingService` et `AnomalyDetectionService`, avec versions, variables, preuve, incertitude, limites et validation humaine.

Le service worker ne cache jamais `/api/*` ni `/portal/*`. Aucune session, preuve, mesure, pièce binaire ou donnée privée n'est mise en cache hors ligne. Une synchronisation de déclaration ne crée pas de preuve et ne promeut aucun niveau P1 vers P2/P3/P4.

## Prérequis

- Python 3.12 avec le module `venv` ;
- NVM avec Node.js 22 et npm ;
- pour le test E2E : Chromium installé par Playwright.

Sur Ubuntu/Debian, si `python3 -m venv` indique que `ensurepip` manque, installer d'abord le paquet système correspondant, par exemple `python3.12-venv`.

## Installation

Depuis la racine du dépôt :

```bash
nvm install 22
nvm use 22
node --version
```

La dernière commande doit afficher une version `v22.x.x`. Le fichier `.nvmrc`
permet ensuite de resélectionner la version attendue avec `nvm use` dans tout
nouveau terminal.

Installer ensuite les dépendances de manière reproductible :

```bash
python3 -m venv .venv
.venv/bin/pip install -r services/api/requirements-dev.txt
npm --prefix apps/web ci
npm --prefix apps/web exec -- playwright install chromium
```

Sur Ubuntu, `python3.12-venv` doit être installé pour obtenir `pip` dans `.venv`. Cette dépendance système n'est jamais installée automatiquement par le projet.

Les valeurs par défaut fonctionnent sans fichier d'environnement. Pour les personnaliser dans le terminal courant :

```bash
cp .env.example .env
set -a
. ./.env
set +a
```

## Lancement local

Ouvrir deux terminaux VS Code à la racine.

Terminal 1 — API :

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir services/api --reload --port 8000
```

Terminal 2 — interface :

```bash
nvm use
NEXT_PUBLIC_API_URL=http://localhost:8000 npm --prefix apps/web run dev
```

Puis ouvrir [http://localhost:3000](http://localhost:3000). La documentation OpenAPI est disponible sur [http://localhost:8000/docs](http://localhost:8000/docs).

Les tâches VS Code « BioLoop: API » et « BioLoop: Web » proposent les mêmes commandes. `make dev-api` et `make dev-web` sont aussi disponibles.

### Comptes et validation pilote

Depuis la section « Compte local et portail attribué » :

- un producteur ou client peut créer une organisation et une appartenance `active` ;
- une organisation logistique ou unité de transformation obtient une appartenance `pending` et ne peut exécuter aucune action métier avant validation ;
- les rôles contrôleur terrain et coordinateur BioLoop ne sont jamais disponibles en auto-inscription : une invitation/approbation administrateur sera nécessaire ;
- une même personne peut posséder plusieurs appartenances et changer d'organisation active, sans élargir sa portée serveur.

Le sélecteur historique d'identités fictives reste disponible seulement lorsque `BIOLOOP_DEMO_IDENTITIES_ENABLED=true`. Il est clairement distinct d'une session pilote et peut être désactivé pour tester le parcours authentifié.

### Profils de données

`BIOLOOP_SYNTHETIC_PROFILE=small` conserve les 8 producteurs et 2 unités historiques afin de préserver les tests et la démo courte. `BIOLOOP_SYNTHETIC_PROFILE=enriched` expose 40 producteurs et 4 unités en conservant les identifiants existants. Les extensions utilisent la graine fixe `20260830`, la version `pilot-p0-fixed-seed-v1` et restent intégralement P0.

```bash
BIOLOOP_SYNTHETIC_PROFILE=enriched make dev-api
```

Ces historiques synthétiques ne sont ni des observations terrain, ni des données d'entraînement validées.

## Parcours de démonstration

1. Dans la section 05, sélectionner le producteur Abobo en « mode démonstration ».
2. Vérifier les huit producteurs et deux unités, marqués P0.
3. Saisir une masse et enregistrer la déclaration P1 pour son propre site.
4. Sélectionner une unité compatible puis générer les scénarios et la collecte P0.
5. Revenir en section 05 et choisir le rôle logistique : la collecte assignée et ses trois arrêts illustratifs apparaissent.
6. Joindre une pièce, saisir une pesée et confirmer : la pièce reste P2, la masse devient P3, puis le lot est créé.
7. Choisir l'opérateur d'unité : vérifier compatibilité, capacité P0 et projections 7/30 jours, puis accepter ou refuser le lot.
8. Choisir le contrôleur : créer l'événement de vérification explicite P4.
9. Choisir le coordinateur : filtrer le journal par acteur, organisation, objet ou corrélation.
10. Choisir le client/agriculteur : constater qu'aucun stock ou produit n'est inventé.

Le parcours historique de la section 04 reste disponible pour démontrer séparément preuve P2, mesure P3, lot, décision et recalcul. Sans en-tête de démonstration, ces routes historiques utilisent le coordinateur fictif afin de préserver les tranches 01 et 02.

Pour réinitialiser toutes les données locales, arrêter l'API puis supprimer `data/local/bioloop.db` et le contenu de `data/local/evidence/`. La base et les pièces sont ignorées par Git.

## Tests

Backend, règles et parcours API :

```bash
.venv/bin/python -m pytest
```

Build TypeScript/Next.js :

```bash
npm --prefix apps/web run build
```

Parcours navigateur complet (démarre automatiquement l'API et Next.js) :

```bash
npm --prefix apps/web run test:e2e
```

## Architecture

```text
apps/web/                     Next.js + TypeScript, aucune règle métier
  app/manifest.ts             manifeste PWA versionné
  public/sw.js                cache du shell public uniquement
  lib/offline-declarations.ts file IndexedDB limitée aux déclarations
services/api/app/             monolithe FastAPI modulaire
  auth.py                     Argon2, sessions opaques, appartenances et limitation
  database.py                 SQLAlchemy 2, migration Alembic et abstraction géographique
  repository_interfaces.py   ports pour migration progressive des repositories
  synthetic_data.py           profil P0 enrichi à graine fixe
  decision_services.py        contrats et références déterministes
  catalog.py                  lecture des fixtures P0
  matching.py                 compatibilité et capacité déterministes
  estimation.py               scénarios versionnés et empreinte SHA-256
  evidence.py                 contrôle et stockage local des pièces P2
  routing.py                  proposition géodésique simple
  repository.py               migrations SQLite additives et audit append-only
  identity.py                 identités, organisations et permissions fictives
  collaboration.py            autorisations et vues de travail par rôle
  forecasting.py              interface et projection déterministe versionnée
data/fixtures/                producteurs, unités et types fictifs
data/factor_sets/             jeu illustratif versionné
services/api/tests/           tests golden, règles et API
apps/web/tests/               test Playwright du parcours
docs/                         décisions et dictionnaire des données
services/api/alembic/         migrations additives versionnées
```

Le backend reste un monolithe modulaire. SQLite accélère la démo locale. `DATABASE_URL` prépare SQLAlchemy/Alembic à PostgreSQL ; le repository métier historique reste volontairement sur SQLite pendant cette migration progressive. PostGIS n'est pas installé : `GeoPoint` marque la frontière d'adaptation future, sans prétendre fournir aujourd'hui des requêtes géospatiales PostgreSQL.

Appliquer explicitement les migrations :

```bash
PYTHONPATH=services/api .venv/bin/alembic -c services/api/alembic.ini upgrade head
```

La migration `0004_pilot_auth` est additive et son `downgrade` ne supprime aucune donnée locale.

### API principale

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/health` | santé locale |
| `GET` | `/api/v1/catalog` | producteurs, unités, déchets et légende de preuve |
| `POST` | `/api/v1/declarations` | créer une déclaration P1 |
| `GET` | `/api/v1/declarations/{id}/matches` | unités compatibles P0 |
| `POST` | `/api/v1/declarations/{id}/proposal` | scénarios et collecte P0 |
| `POST/GET` | `/api/v1/declarations/{id}/evidence` | ajout binaire sécurisé et liste des preuves P2 |
| `POST/GET` | `/api/v1/declarations/{id}/measurements` | ajout immuable et liste des mesures P3 |
| `POST` | `/api/v1/declarations/{id}/lots` | création d'un lot depuis une mesure précise |
| `GET` | `/api/v1/lots/{id}` | lot, décision et historique de statut |
| `POST` | `/api/v1/lots/{id}/decision` | acceptation ou refus non écrasable |
| `POST` | `/api/v1/declarations/{id}/recalculations` | nouvelle estimation liée à une mesure P3 |
| `GET` | `/api/v1/declarations/{id}/timeline` | provenance et journal corrélé |
| `GET` | `/api/v1/demo/actors` | catalogue public des identités fictives |
| `GET` | `/api/v1/demo/workspace` | espace autorisé du rôle sélectionné |
| `GET` | `/api/v1/demo/notifications` | notifications internes de l'organisation active |
| `POST` | `/api/v1/demo/collections/{id}/confirm` | collecte liée à une preuve P2 et une mesure P3 |
| `POST` | `/api/v1/demo/verifications` | événement P4 réservé au contrôleur terrain |
| `GET` | `/api/v1/demo/audit` | audit filtrable réservé au coordinateur |
| `GET` | `/api/v1/auth/csrf` | amorcer la protection CSRF |
| `POST` | `/api/v1/auth/register` | créer un compte et une appartenance autorisée |
| `POST` | `/api/v1/auth/login` | ouvrir une session pilote locale |
| `GET` | `/api/v1/auth/me` | lire l'utilisateur et l'organisation actifs |
| `POST` | `/api/v1/auth/logout` | révoquer la session serveur |
| `POST` | `/api/v1/auth/memberships/{id}/activate` | changer d'appartenance accessible |
| `GET` | `/api/v1/auth/portal/{role}` | vue attribuée et contrôlée côté backend |
| `GET` | `/api/v1/pilot/synthetic-data` | données P0 enrichies avec version et graine |

Les entrées ont des types, longueurs et bornes explicites. Une unité incompatible est rejetée côté serveur. Les exécutions sont déterministes pour une même masse, un même déchet, une même unité, une même provenance et une même version de facteurs.

Chaque réponse API porte `X-Correlation-ID` et des en-têtes de durcissement. Les audits d'authentification ne contiennent ni mot de passe, ni email brut, ni cookie, ni jeton de session. Cette fondation locale n'inclut toutefois ni MFA, ni récupération de compte, ni fournisseur d'identité, ni rotation de clés, ni journal inviolable, ni administration complète des invitations.

### Sécurité des preuves locales

- le nom fourni par le navigateur sert uniquement de métadonnée d'affichage ;
- tout séparateur de chemin ou traversée `..` est refusé ;
- extension, type MIME et signature binaire doivent correspondre ;
- le serveur génère un nom aléatoire et n'expose aucune route de chemin ou de téléchargement arbitraire ;
- le flux est interrompu au-delà de 5 Mio et aucun fichier partiel n'est conservé ;
- l'empreinte SHA-256 est stockée, mais ni le binaire ni les métadonnées EXIF ne sont journalisés ;
- aucune géolocalisation EXIF n'est publiée ou promue comme preuve vérifiée.

Les tables sont créées par migrations additives `CREATE TABLE IF NOT EXISTS` et `ALTER TABLE` ciblé. Une base de la tranche 01 est conservée et enrichie sans suppression.

## Identités et autorisations de démonstration

Le frontend transmet `X-Demo-User-ID`, choisi dans un catalogue JSON fictif. FastAPI résout l'appartenance, applique les autorisations et inscrit utilisateur, organisation et rôle dans chaque nouvel événement d'audit. Ce sélecteur n'est pas une connexion : il n'offre ni mot de passe, ni session signée, ni MFA, ni protection contre l'usurpation.

| Rôle | Lecture | Écriture autorisée |
|---|---|---|
| Producteur | ses déclarations uniquement | déclaration de son site, proposition et preuve P2 propre |
| Logistique | collectes assignées | preuve P2, pesée P3, confirmation puis lot assigné |
| Opérateur unité | lots de son unité | acceptation ou refus non écrasable |
| Contrôleur terrain | lots en attente de contrôle | événement de vérification P4 explicite et idempotent |
| Coordinateur | vue transversale et audit filtrable | opérations de démonstration sur le parcours historique |
| Client/agriculteur | produits réellement représentés | aucune dans cette tranche |

Les notifications `proposal.available`, `collection.assigned`, `lot.incoming`, `control.required` et `lot.decision_recorded` sont persistées avec une clé de déduplication. Aucun email, SMS ou message externe n'est envoyé.

## Données et niveaux de preuve

| Niveau | Statut utilisé | Exemple dans cette tranche |
|---|---|---|
| P0 | simulé | sites, coordonnées, capacité, compatibilité, scénarios, distance |
| P1 | déclaré | masse et type saisis par l'utilisateur |
| P2 | documenté | pièce JPEG/PNG/PDF fournie, empreinte et métadonnées |
| P3 | mesuré | pesée saisie avec méthode, heure et appareil facultatif |
| P4 | vérifié | événement séparé créé par le contrôleur terrain fictif autorisé |
| P5 | certifié | défini dans la légende, pas encore collecté |

Le niveau d'un résultat dérivé ne dépasse pas son intrant le moins probant. Les scénarios restent donc P0 même lorsque leur masse d'entrée est mesurée P3. Une décision d'unité reste P1 car l'identité de démonstration n'est pas une authentification de production ; seul l'événement de contrôle séparé est P4.

Les projections 7/30 jours sont des agrégations mécaniques P0. Elles prolongent la cadence déclarée et affichent séparément la base P1 et la dernière masse P3 disponible. La version actuelle est `deterministic-declaration-cadence-v1` : aucun LLM et aucun modèle prédictif n'intervient.

## Limites scientifiques et opérationnelles

- Les multiplicateurs `0,80 / 1,00 / 1,20` sont une convention logicielle normalisée, pas des coefficients scientifiques.
- Les URI n'ont aucune équivalence physique ou économique.
- Aucun facteur de matière sèche, solides volatils, potentiel méthane ou efficacité procédé n'est renseigné.
- Compatibilités et capacités doivent être validées par une unité réelle avant pilote.
- La distance haversine n'est ni une distance routière, ni une optimisation de tournée, ni une estimation de coût.
- Une preuve P2 et une mesure P3 sont des saisies de démonstration : aucune analyse qualité ou validation terrain indépendante n'est encore liée.
- Le stockage de pièces local n'inclut ni antivirus, ni stockage objet, ni URL temporaire ; ces contrôles sont requis avant pilote.
- Les identités sont sélectionnables par en-tête et ne sont pas authentifiées ; elles servent à démontrer l'autorisation, l'attribution et l'audit, pas la sécurité de production.
- Le rôle contrôleur permet un événement P4 dans ce modèle, mais aucune qualification, signature professionnelle ou certification P5 n'est fournie.
- Les projections ne modélisent ni saisonnalité, contamination, disponibilité, probabilité d'acceptation, temps routier ni production réelle.
- Avant tout apprentissage, il faudra un historique de masses déclarées/mesurées, fréquences, saisons, déchets, contaminations, acceptations/refus, temps de collecte, capacités et productions réellement mesurées.
- L'audit local ne remplace pas session signée, RBAC administrable, journal inviolable, sauvegardes et supervision d'un environnement de production.
- L'authentification pilote ne constitue pas une homologation ou certification de sécurité de production.
- Le cache hors ligne ne couvre ni portails privés, ni preuves, ni mesures, ni lots ; seule une nouvelle déclaration peut attendre la reprise réseau.
- Le profil enrichi est P0, créé par une règle déterministe à graine fixe ; il ne prouve aucun volume ou comportement réel.
- Le seuil d'anomalie de référence est une règle logicielle illustrative et ne conclut ni à une fraude, ni à une contamination.
- PostgreSQL/PostGIS reste une cible : cette tranche prépare la migration mais ne remplace pas encore le repository métier SQLite.

La règle de crédibilité et le périmètre fonctionnel proviennent de `outputs/BioLoop_CI_MVP_Hackathon_SIREXE_2026.md`. Les fichiers de recherche restent inchangés.

## Prochaine tranche recommandée

Ajouter une tranche **administration des invitations et validation d'organisations → transformation mesurée → produit qualifié → disponibilité client**. Elle devra d'abord fournir l'approbation explicite des unités/logisticiens et des rôles sensibles, puis enregistrer entrées, pertes et sorties mesurées, critères qualité, statut de libération, stock disponible et provenance, sans déduire un rendement scientifique des URI illustratives. MFA, récupération de compte, stockage objet sécurisé, rétention et PostgreSQL/PostGIS complet restent des prérequis distincts avant production.
