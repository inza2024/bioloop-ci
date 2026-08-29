# BioLoop CI — tranches verticales 01 et 02 du MVP

BioLoop CI est un démonstrateur local pour le SIREXE Hackathon 2026. Il couvre désormais deux parcours liés : déclarer un gisement et produire une proposition illustrative, puis documenter le gisement, enregistrer une mesure, créer un lot, saisir une décision de l'unité et recalculer sans effacer l'historique.

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

La démo n'inclut volontairement ni paiement, ni crédit carbone, ni blockchain, ni agent IA autonome, ni authentification de production. Aucun LLM n'intervient dans les calculs.

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

## Parcours de démonstration

1. Vérifier les huit producteurs et deux unités, marqués P0.
2. Choisir un producteur fictif et saisir une masse en kilogrammes.
3. Enregistrer la déclaration : quantité et type deviennent P1, la localisation reste P0.
4. Sélectionner une unité compatible parmi les résultats P0.
5. Générer la proposition et vérifier les scénarios, la version, l'empreinte, les hypothèses et la tournée.
6. Montrer le verrou « validation humaine requise » : aucune collecte n'est déclenchée.
7. Ajouter une petite image JPEG/PNG ou un PDF : la pièce reste P2.
8. Saisir une masse mesurée en kilogrammes : la nouvelle donnée est P3, pas P4.
9. Créer le lot et vérifier qu'il reprend la masse mesurée, pas la masse déclarée.
10. Accepter ou refuser le lot ; un refus exige un motif et la décision ne peut plus être écrasée.
11. Recalculer les trois scénarios à partir de la mesure et comparer les deux exécutions.
12. Lire le journal : les identifiants sont corrélés, le contenu binaire n'est jamais journalisé.

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
services/api/app/             monolithe FastAPI modulaire
  catalog.py                  lecture des fixtures P0
  matching.py                 compatibilité et capacité déterministes
  estimation.py               scénarios versionnés et empreinte SHA-256
  evidence.py                 contrôle et stockage local des pièces P2
  routing.py                  proposition géodésique simple
  repository.py               migrations SQLite additives et audit append-only
data/fixtures/                producteurs, unités et types fictifs
data/factor_sets/             jeu illustratif versionné
services/api/tests/           tests golden, règles et API
apps/web/tests/               test Playwright du parcours
docs/                         décisions et dictionnaire des données
```

Le backend est un monolithe modulaire. SQLite accélère la démo locale ; PostgreSQL/PostGIS reste la cible d'un pilote. Le frontend consomme exclusivement les contrats HTTP de FastAPI.

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

Les entrées ont des types, longueurs et bornes explicites. Une unité incompatible est rejetée côté serveur. Les exécutions sont déterministes pour une même masse, un même déchet, une même unité, une même provenance et une même version de facteurs.

### Sécurité des preuves locales

- le nom fourni par le navigateur sert uniquement de métadonnée d'affichage ;
- tout séparateur de chemin ou traversée `..` est refusé ;
- extension, type MIME et signature binaire doivent correspondre ;
- le serveur génère un nom aléatoire et n'expose aucune route de chemin ou de téléchargement arbitraire ;
- le flux est interrompu au-delà de 5 Mio et aucun fichier partiel n'est conservé ;
- l'empreinte SHA-256 est stockée, mais ni le binaire ni les métadonnées EXIF ne sont journalisés ;
- aucune géolocalisation EXIF n'est publiée ou promue comme preuve vérifiée.

Les tables sont créées par migrations additives `CREATE TABLE IF NOT EXISTS` et `ALTER TABLE` ciblé. Une base de la tranche 01 est conservée et enrichie sans suppression.

## Données et niveaux de preuve

| Niveau | Statut utilisé | Exemple dans cette tranche |
|---|---|---|
| P0 | simulé | sites, coordonnées, capacité, compatibilité, scénarios, distance |
| P1 | déclaré | masse et type saisis par l'utilisateur |
| P2 | documenté | pièce JPEG/PNG/PDF fournie, empreinte et métadonnées |
| P3 | mesuré | pesée saisie avec méthode, heure et appareil facultatif |
| P4 | vérifié | défini dans la légende, pas encore collecté |
| P5 | certifié | défini dans la légende, pas encore collecté |

Le niveau d'un résultat dérivé ne dépasse pas son intrant le moins probant. Les scénarios restent donc P0 même lorsque leur masse d'entrée est mesurée P3. Une décision d'unité est P1 dans cette démo car l'acteur n'est pas authentifié ; elle ne constitue jamais un contrôle P4.

## Limites scientifiques et opérationnelles

- Les multiplicateurs `0,80 / 1,00 / 1,20` sont une convention logicielle normalisée, pas des coefficients scientifiques.
- Les URI n'ont aucune équivalence physique ou économique.
- Aucun facteur de matière sèche, solides volatils, potentiel méthane ou efficacité procédé n'est renseigné.
- Compatibilités et capacités doivent être validées par une unité réelle avant pilote.
- La distance haversine n'est ni une distance routière, ni une optimisation de tournée, ni une estimation de coût.
- Une preuve P2 et une mesure P3 sont des saisies de démonstration : aucune analyse qualité ou validation terrain indépendante n'est encore liée.
- Le stockage de pièces local n'inclut ni antivirus, ni stockage objet, ni URL temporaire ; ces contrôles sont requis avant pilote.
- L'acteur de décision n'est pas authentifié et son acceptation/refus ne vaut pas vérification P4.
- L'audit local est minimal et ne remplace pas les contrôles d'accès, signatures et sauvegardes d'un environnement de production.

La règle de crédibilité et le périmètre fonctionnel proviennent de `outputs/BioLoop_CI_MVP_Hackathon_SIREXE_2026.md`. Les fichiers de recherche restent inchangés.

## Prochaine tranche recommandée

Ajouter une **validation P4 réellement contrôlée** : identité et rôles de démonstration, séparation producteur/unité, approbation explicite, contrôle d'accès horizontal, rapport de lot et politique de rétention des pièces. Cette étape doit précéder toute allégation scientifique, transaction ou intégration externe.
