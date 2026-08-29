# BioLoop CI — première tranche verticale du MVP

BioLoop CI est un démonstrateur local pour le SIREXE Hackathon 2026. Cette tranche couvre un seul parcours de bout en bout : consulter un bassin fictif, déclarer un gisement organique, choisir une unité compatible, calculer trois scénarios illustratifs et obtenir une proposition simple de collecte.

> **Avertissement scientifique** — Aucun résultat affiché n'est un rendement biogaz validé. Le moteur produit des **URI (unités de rendement illustratives)** avec un jeu de multiplicateurs P0 intitulé « simulation illustrative ». Il n'effectue aucune conversion vers `Nm³`, `kWh`, FCFA, digestat, engrais ou crédit environnemental.

## Ce que la démo permet

- consulter huit producteurs et deux unités de transformation fictifs, tous P0 ;
- saisir une déclaration P1 (type, masse, fréquence et disponibilité) ;
- filtrer les unités par compatibilité et capacité fictives ;
- reproduire trois scénarios bas, central et haut avec une version et une empreinte SHA-256 ;
- afficher formule, unités, hypothèses, source de configuration et niveau de preuve ;
- proposer un aller-retour direct fondé sur une distance géodésique illustrative ;
- conserver déclarations, exécutions et événements d'audit dans SQLite.

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

Pour réinitialiser les déclarations locales, arrêter l'API puis supprimer `data/local/bioloop.db`. Ce fichier est ignoré par Git.

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
  routing.py                  proposition géodésique simple
  repository.py               SQLite et audit append-only minimal
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

Les entrées ont des types, longueurs et bornes explicites. Une unité incompatible est rejetée côté serveur. Les exécutions sont déterministes pour une même masse, un même déchet, une même unité et une même version de facteurs.

## Données et niveaux de preuve

| Niveau | Statut utilisé | Exemple dans cette tranche |
|---|---|---|
| P0 | simulé | sites, coordonnées, capacité, compatibilité, scénarios, distance |
| P1 | déclaré | masse et type saisis par l'utilisateur |
| P2 | documenté | défini dans la légende, pas encore collecté |
| P3 | mesuré | défini dans la légende, pas encore collecté |
| P4 | vérifié | défini dans la légende, pas encore collecté |
| P5 | certifié | défini dans la légende, pas encore collecté |

Le niveau d'un résultat dérivé ne dépasse pas son intrant le moins probant. Les scénarios restent donc P0 même si la masse est déclarée P1.

## Limites scientifiques et opérationnelles

- Les multiplicateurs `0,80 / 1,00 / 1,20` sont une convention logicielle normalisée, pas des coefficients scientifiques.
- Les URI n'ont aucune équivalence physique ou économique.
- Aucun facteur de matière sèche, solides volatils, potentiel méthane ou efficacité procédé n'est renseigné.
- Compatibilités et capacités doivent être validées par une unité réelle avant pilote.
- La distance haversine n'est ni une distance routière, ni une optimisation de tournée, ni une estimation de coût.
- La déclaration n'est pas une pesée ; aucune photo, analyse qualité ou validation terrain n'est encore liée.
- L'audit local est minimal et ne remplace pas les contrôles d'accès, signatures et sauvegardes d'un environnement de production.

La règle de crédibilité et le périmètre fonctionnel proviennent de `outputs/BioLoop_CI_MVP_Hackathon_SIREXE_2026.md`. Les fichiers de recherche restent inchangés.

## Prochaine tranche recommandée

Ajouter le passage **déclaré P1 → documenté P2 → mesuré P3** : pièce/photo horodatée, saisie d'une pesée, création d'un lot, acceptation ou refus par l'unité et recalcul immuable à partir de la masse mesurée. Cette tranche apporte davantage de crédibilité terrain avant toute optimisation avancée ou facteur scientifique.
