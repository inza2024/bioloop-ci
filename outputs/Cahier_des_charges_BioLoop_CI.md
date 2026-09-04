# Cahier des charges fonctionnel et technique — BioLoop CI

**Plateforme numérique de coordination et de traçabilité de la valorisation des déchets organiques**

| Élément | Valeur |
|---|---|
| Projet | BioLoop CI |
| Version du document | 1.0 |
| Date | 3 septembre 2026 |
| Statut | Référence de travail pour l'équipe projet |
| Dépôt de référence | `https://github.com/inza2024/bioloop-ci` — dépôt privé |
| Version applicative couverte | Tranches verticales 01 à 05, commit `66fb8fcdb7f515587329b1ef6728e7304840c104` |
| Propriétaire du document | Porteur de projet BioLoop CI — à nommer formellement |
| Prochaine revue | À chaque jalon majeur ou modification du périmètre |

### Historique des versions

| Version | Date | Auteur/validation | Évolution |
|---|---|---|---|
| 1.0 | 3 septembre 2026 | Équipe BioLoop CI — validation à compléter | Création du référentiel fonctionnel et technique couvrant les tranches 01 à 05 |

> **Règle de crédibilité** — BioLoop CI ne doit jamais présenter une donnée simulée, déclarée ou calculée comme une mesure scientifique validée. Toute valeur doit conserver sa provenance, son unité, sa méthode, sa version et son niveau de preuve. Les estimations de biogaz, fertilisant, engrais ou impact environnemental ne peuvent devenir des allégations réelles qu'après validation des données, facteurs, méthodes et acteurs compétents.

---

## 1. Objet du document

Le présent cahier des charges définit les objectifs, le périmètre, les utilisateurs, les règles métier, les exigences fonctionnelles et techniques, les exigences de sécurité, les principes de gouvernance, les livrables et les critères de recette du projet BioLoop CI.

Il constitue la référence commune pour :

- le porteur de projet et le responsable produit ;
- les développeurs frontend, backend et mobile/PWA ;
- les responsables données et intelligence artificielle ;
- les experts métier en déchets, biogaz, agronomie et qualité ;
- les opérateurs logistiques et unités de transformation pilotes ;
- les responsables sécurité, tests, documentation et déploiement ;
- les partenaires institutionnels, financeurs et futurs utilisateurs.

Ce document ne remplace pas les spécifications détaillées d'une fonctionnalité, les maquettes, les ADR, le dictionnaire des données, les contrats API ou les plans de test. Ces éléments doivent rester liés aux exigences identifiées ici.

## 2. Résumé exécutif

BioLoop CI est une plateforme d'orchestration de la valorisation des déchets organiques en Côte d'Ivoire. Elle relie les producteurs de déchets, les opérateurs logistiques, les unités de transformation, les contrôleurs, les agriculteurs et les autres clients des produits issus de la transformation.

La plateforme doit permettre de :

1. déclarer et documenter un gisement de déchets organiques ;
2. distinguer ce qui est simulé, déclaré, documenté, mesuré, vérifié ou certifié ;
3. apparier les gisements avec des unités compatibles et disponibles ;
4. planifier, affecter et tracer les collectes ;
5. mesurer les quantités collectées et créer des lots traçables ;
6. accepter ou refuser les lots dans les unités de transformation ;
7. enregistrer les transformations, sorties physiques, contrôles qualité et stocks ;
8. publier aux clients uniquement les produits disponibles et suffisamment qualifiés ;
9. conserver une chaîne de provenance et un journal d'audit de bout en bout ;
10. fournir progressivement des recommandations logistiques et prévisions explicables, soumises à validation humaine.

BioLoop CI n'est pas, à ce stade, un système de certification, un laboratoire, un outil de vente de crédits carbone, un moteur de paiement ou un agent autonome. Le produit actuel est un pilote local démontrable, non homologué pour une exploitation de production.

## 3. Contexte et justification

Les producteurs de déchets organiques et les unités de valorisation rencontrent plusieurs difficultés :

- visibilité insuffisante sur les gisements disponibles ;
- quantités et fréquences souvent déclaratives et hétérogènes ;
- coûts logistiques élevés et tournées peu coordonnées ;
- manque de preuves sur les collectes, pesées et transformations ;
- approvisionnement irrégulier des unités de traitement ;
- difficulté à qualifier, tracer et commercialiser les produits issus de la transformation ;
- risque de présenter des estimations comme des rendements réels ;
- absence d'une chaîne numérique commune entre les différents acteurs.

BioLoop CI répond à ces problèmes en proposant un système d'exploitation de la chaîne de valorisation : données partagées selon les droits, décisions attribuées, niveaux de preuve, historique immuable, coordination logistique et outils d'aide à la décision.

## 4. Vision et objectifs

### 4.1 Vision

Devenir la plateforme de référence pour sécuriser, coordonner et tracer les flux de déchets organiques valorisables, depuis leur déclaration jusqu'aux produits issus de la transformation.

### 4.2 Objectifs métier

| ID | Objectif | Indicateur attendu |
|---|---|---|
| OBJ-01 | Fiabiliser la connaissance des gisements | Part des déclarations documentées, mesurées ou vérifiées |
| OBJ-02 | Régulariser l'approvisionnement des unités | Quantité mesurée livrée par période et écart à la planification |
| OBJ-03 | Réduire l'inefficacité logistique | Coût, distance et temps par tonne acceptée |
| OBJ-04 | Garantir la traçabilité | Part des lots disposant d'une provenance complète |
| OBJ-05 | Sécuriser les décisions | Part des actions sensibles attribuées, autorisées et auditées |
| OBJ-06 | Donner de la visibilité aux clients | Stock libéré, réservé et livré avec statut qualité visible |
| OBJ-07 | Préparer l'usage responsable de l'IA | Modèles comparés à une baseline, versionnés et évalués |
| OBJ-08 | Soutenir un pilote terrain | Utilisation effective par au moins un bassin pilote compact |

### 4.3 Critères de succès du pilote

- un producteur peut déclarer un gisement depuis un téléphone ;
- un logisticien peut recevoir une affectation et confirmer une collecte ;
- une unité peut accepter un lot, enregistrer sa transformation et ses sorties ;
- un contrôleur peut créer un événement de vérification distinct ;
- un client peut consulter un produit libéré et réserver une quantité disponible ;
- le coordinateur peut retracer toute la chaîne et identifier chaque acteur ;
- aucune valeur P0/P1/P2/P3 n'est présentée comme P4/P5 sans événement autorisé ;
- le parcours principal reste démontrable sans dépendance critique à un service externe.

## 5. Périmètre

### 5.1 Inclus dans le périmètre

- gestion des comptes, organisations, appartenances, rôles et sessions ;
- portails dédiés par partie prenante ;
- déclaration, documentation, mesure et vérification des gisements ;
- catalogue de déchets, producteurs, unités, compatibilités et capacités ;
- appariement gisement-unité ;
- propositions et affectations de collecte ;
- preuves, pesées, lots, décisions et historique ;
- transformations, sorties physiques et pertes mesurées ;
- contrôles qualité et libération interne des produits ;
- registre de stock, réservations et annulations ;
- notifications internes ;
- PWA responsive et installation mobile ;
- saisie hors connexion limitée et synchronisation idempotente ;
- audit, provenance, niveaux de preuve et observabilité ;
- données synthétiques de démonstration clairement identifiées ;
- préparation des services d'optimisation et d'IA explicable ;
- documentation, tests automatisés, migrations et gouvernance GitHub.

### 5.2 Hors périmètre actuel

- paiement, facturation, portefeuille électronique ou partage financier réel ;
- délivrance de certification P5 ;
- validation réglementaire automatique d'un engrais ou biofertilisant ;
- vente, émission ou certification de crédits environnementaux ;
- conseil agronomique personnalisé sans expert et données validées ;
- pilotage automatique d'équipements industriels ;
- agent IA autonome pouvant accepter, rejeter, payer, publier ou supprimer ;
- déploiement de production homologué ;
- remplacement d'un laboratoire, d'un organisme de contrôle ou d'un expert métier ;
- promesse de rendement physique ou économique fondée sur les URI illustratives.

### 5.3 Périmètre géographique initial

Le pilote doit cibler un bassin compact en Côte d'Ivoire, idéalement composé de :

- un ou plusieurs marchés, élevages ou producteurs agricoles ;
- un opérateur logistique ;
- une unité de transformation identifiée ;
- un ou plusieurs agriculteurs ou clients potentiels ;
- un acteur de contrôle ou expert partenaire.

Les coordonnées du démonstrateur sont fictives P0. Toute donnée de localisation réelle devra être autorisée, minimisée et protégée.

## 6. Parties prenantes et utilisateurs

| Acteur | Exemples | Besoin principal | Portail attendu |
|---|---|---|---|
| Producteur de déchets | marché, élevage, coopérative, agro-industrie, exploitation | déclarer, documenter et suivre l'enlèvement | Portail producteur |
| Logisticien/collecteur | transporteur, coopérative, commune | organiser les tournées, collecter et prouver | Portail logistique |
| Unité de transformation | biodigesteur, compostage, autre unité autorisée | sécuriser les intrants, traiter et tracer les sorties | Portail unité |
| Contrôleur terrain/qualité | agent autorisé, laboratoire, expert | vérifier les mesures, produits et conformités | Portail contrôle |
| Coordinateur BioLoop | équipe opérationnelle/administrateur | superviser, autoriser, auditer et résoudre les incidents | Portail coordinateur |
| Client/agriculteur | agriculteur, coopérative, distributeur, acheteur de gaz | consulter la disponibilité, qualité et provenance | Portail client |
| Partenaire institutionnel | commune, district, agence, financeur | suivre des indicateurs agrégés et vérifiables | Tableau institutionnel futur |
| Équipe produit/technique | PO, développeurs, données, sécurité, experts | faire évoluer et maintenir le service | Outils internes et GitHub |

## 7. État du produit au 3 septembre 2026

### 7.1 Fonctionnalités déjà réalisées

| Tranche | Contenu livré | Statut |
|---|---|---|
| 01 | déclaration P1, appariement, scénarios URI P0, proposition géodésique | Réalisé et testé |
| 02 | preuves P2, mesures P3, lots, décision, recalcul et provenance | Réalisé et testé |
| 03 | six portails, rôles de démonstration, notifications, collecte et P4 explicite | Réalisé et testé |
| 04 | comptes pilotes, sessions, PWA, hors-ligne limité, Alembic et données enrichies | Réalisé et testé |
| 05 | administration, transformations, produits, qualité, stock et réservations | Réalisé et testé |

### 7.2 Socle technique existant

- frontend Next.js 16/TypeScript, responsive et PWA ;
- API FastAPI modulaire ;
- SQLite pour le pilote local ;
- SQLAlchemy 2 et Alembic introduits progressivement ;
- authentification pilote avec Argon2id, session opaque et cookie HttpOnly ;
- CSRF, contrôle d'origine et limitation des tentatives de connexion ;
- tests Pytest, Playwright, build TypeScript et migrations ;
- dépôt GitHub privé avec branche `main` synchronisée ;
- données synthétiques P0 avec graine et version fixes.

### 7.3 Limites connues

- repository métier encore majoritairement SQLite ;
- absence de PostgreSQL/PostGIS métier complet ;
- preuves stockées localement, sans stockage objet ni antivirus ;
- absence de MFA et récupération de compte ;
- absence de sauvegarde/restauration automatisée et supervision de production ;
- distances géodésiques, sans réseau routier ni trafic ;
- absence de laboratoire connecté et de certification P5 ;
- aucun paiement ni intégration de messagerie externe ;
- aucune IA entraînée ou validée sur des données terrain.

## 8. Principes de priorité

Les exigences utilisent la convention MoSCoW :

- **Must** : indispensable au pilote ou à la sécurité ;
- **Should** : forte valeur, à réaliser dès que le socle Must est stable ;
- **Could** : amélioration facultative ;
- **Won't now** : explicitement exclu de la version concernée.

Une exigence Must ne peut être considérée terminée que si ses critères d'acceptation sont automatisés lorsque cela est pertinent et vérifiés manuellement sur le parcours utilisateur.

## 9. Exigences fonctionnelles

### 9.1 Identité, comptes et organisations

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-ID-01 | Permettre l'inscription avec nom, email, mot de passe et organisation | Must | Un producteur/client obtient une appartenance active et le bon portail |
| FON-ID-02 | Permettre connexion, déconnexion et expiration de session | Must | Une session expirée ou révoquée ne donne plus accès aux API privées |
| FON-ID-03 | Gérer plusieurs appartenances par utilisateur | Should | Le changement d'organisation ne donne accès qu'à la portée sélectionnée |
| FON-ID-04 | Soumettre logistique et unité à approbation | Must | Une appartenance `pending` ne peut exécuter aucune action métier |
| FON-ID-05 | Réserver contrôle/coordination à l'invitation | Must | Aucun formulaire public ne permet l'auto-attribution d'un rôle sensible |
| FON-ID-06 | Permettre révocation de session et appartenance | Must | L'effet est immédiat, attribué et audité |
| FON-ID-07 | Prévoir récupération de compte et MFA | Should | Flux testés, secrets protégés et politique documentée |

### 9.2 Déclaration et qualification des gisements

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-GIS-01 | Déclarer type, quantité, unité, fréquence, disponibilité et site | Must | La déclaration est persistée P1 avec propriétaire et horodatage |
| FON-GIS-02 | Joindre une photo ou un document | Must | Fichier validé, haché, stocké sous nom serveur et classé P2 |
| FON-GIS-03 | Enregistrer une mesure et sa méthode | Must | La mesure P3 est immuable ; une correction crée une nouvelle ligne |
| FON-GIS-04 | Gérer disponibilité, humidité, contamination et saison si connues | Should | Chaque champ indique source, unité et niveau de preuve |
| FON-GIS-05 | Retrouver et filtrer les gisements | Must | Recherche par type, zone, période, organisation et preuve |
| FON-GIS-06 | Synchroniser une déclaration créée hors connexion | Must | Une clé d'idempotence empêche tout doublon au retour du réseau |

### 9.3 Appariement et capacité

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-MAT-01 | Filtrer les unités incompatibles | Must | Une unité rejetée par type/capacité ne peut recevoir le lot |
| FON-MAT-02 | Classer les unités compatibles | Must | Le classement expose critères, version et limites |
| FON-MAT-03 | Tenir compte de la capacité disponible | Must | Aucun appariement approuvé ne dépasse la capacité disponible connue |
| FON-MAT-04 | Exiger validation humaine | Must | Une proposition ne déclenche jamais seule une collecte réelle |
| FON-MAT-05 | Expliquer l'absence de solution | Should | L'utilisateur voit les contraintes bloquantes et les actions possibles |

### 9.4 Logistique et tournées

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-LOG-01 | Créer et affecter une collecte | Must | Le logisticien affecté voit les arrêts, fenêtres et quantités |
| FON-LOG-02 | Confirmer collecte, preuve et pesée | Must | La transition est unique, attribuée et génère le lot attendu |
| FON-LOG-03 | Planifier plusieurs producteurs et véhicules | Should | Capacités, compatibilités et fenêtres sont respectées |
| FON-LOG-04 | Versionner et approuver les tournées | Must cible | Toute modification conserve l'historique et exige une approbation |
| FON-LOG-05 | Calculer un coût de tournée paramétrable | Should | Formule, paramètres, unité et version sont visibles |
| FON-LOG-06 | Distinguer distance illustrative et distance routière | Must | Aucune distance haversine n'est présentée comme temps/trajet réel |
| FON-LOG-07 | Gérer incidents et échecs de collecte | Should | Motif, acteur, date, nouvelle action et audit sont conservés |

### 9.5 Lots, décisions et provenance

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-LOT-01 | Créer un lot depuis une mesure précise | Must | Le lot référence mesure, preuves, unité et déclaration sources |
| FON-LOT-02 | Accepter/refuser un lot avec rôle autorisé | Must | Seule l'unité destinataire décide ; un refus exige un motif |
| FON-LOT-03 | Conserver les statuts et décisions | Must | Aucun événement historique n'est écrasé |
| FON-LOT-04 | Afficher la provenance de bout en bout | Must | Déclaration, collecte, lot, transformation, produit et réservation sont reliés |
| FON-LOT-05 | Gérer corrections sans suppression | Must | Toute correction référence l'élément remplacé et son auteur |

### 9.6 Transformation et produits

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-TRA-01 | Transformer uniquement un lot accepté | Must | Toute autre source est refusée côté serveur |
| FON-TRA-02 | Enregistrer entrée, perte, procédé, opérateur et période | Must | Les mesures P3 possèdent unité, méthode et horodatage |
| FON-TRA-03 | Saisir explicitement chaque sortie physique | Must | Aucune quantité produit n'est générée depuis les URI |
| FON-TRA-04 | Gérer plusieurs lots d'entrée et de sortie | Should | Le bilan conserve toutes les relations parent/enfant |
| FON-TRA-05 | Distinguer catégories et allégations autorisées | Must | « digestat », « biofertilisant » et « engrais » ne sont pas synonymes automatiques |

### 9.7 Qualité et libération

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-QUA-01 | Enregistrer un contrôle qualité | Must | Paramètre, valeur, unité, méthode, auteur, date et preuve sont conservés |
| FON-QUA-02 | Gérer quarantaine, analyse, libération et rejet | Must | Les transitions sont autorisées et auditées |
| FON-QUA-03 | Réserver P4 à un acteur autorisé | Must | L'événement P4 est séparé et ne devient jamais P5 automatiquement |
| FON-QUA-04 | Gérer des spécifications versionnées | Should | Toute conclusion indique référentiel, version et approbateur |
| FON-QUA-05 | Connecter un laboratoire ou importer un rapport | Could | L'import conserve original, empreinte et provenance |

### 9.8 Inventaire et clients

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-STO-01 | Calculer le stock depuis un registre immuable | Must | Production, ajustement, réservation et livraison déterminent le solde |
| FON-STO-02 | Interdire stock négatif et double réservation | Must | Les transactions concurrentes sont refusées ou sérialisées correctement |
| FON-STO-03 | Publier uniquement les produits libérés | Must | Un produit en quarantaine est invisible aux clients |
| FON-CLI-01 | Filtrer les disponibilités | Must | Catégorie, zone, preuve, qualité et quantité sont filtrables |
| FON-CLI-02 | Consulter la provenance | Must | Le client voit les étapes et limites autorisées sans données privées indues |
| FON-CLI-03 | Réserver et annuler | Must | La réservation est idempotente et isolée par organisation |
| FON-CLI-04 | Gérer livraison et réception | Should | Chaque mouvement est attribué, horodaté et relié au stock |
| FON-CLI-05 | Intégrer paiement/facturation | Won't now | À traiter dans un chantier réglementaire et financier séparé |

### 9.9 Administration et notifications

| ID | Exigence | Priorité | Critère d'acceptation principal |
|---|---|---|---|
| FON-ADM-01 | Approuver/refuser une organisation | Must | Décision motivée, non auto-approuvable et auditée |
| FON-ADM-02 | Créer des invitations sensibles | Must | Jeton aléatoire, haché, expirant et affiché une seule fois |
| FON-ADM-03 | Filtrer le journal d'audit | Must | Recherche par acteur, organisation, objet, événement et corrélation |
| FON-ADM-04 | Gérer paramètres et référentiels | Should | Modification versionnée, justifiée et soumise à approbation |
| FON-NOT-01 | Produire des notifications internes idempotentes | Must | Un même événement ne génère pas de doublons |
| FON-NOT-02 | Préparer email/SMS/WhatsApp | Could | Adaptateur externe désactivable, consentement et journalisation |

## 10. Règles métier fondamentales

### 10.1 Niveaux de preuve

| Niveau | Libellé | Définition | Exemple |
|---|---|---|---|
| P0 | Simulé | donnée fictive, règle illustrative ou résultat exploratoire | fixture, distance haversine, URI |
| P1 | Déclaré | information saisie par un acteur sans mesure indépendante | quantité déclarée, réservation |
| P2 | Documenté | pièce ou historique associé | photo, bon, PDF horodaté |
| P3 | Mesuré | mesure avec méthode et métadonnées | pesée, volume de sortie |
| P4 | Vérifié | contrôle explicite par un acteur autorisé | libération interne, contrôle terrain |
| P5 | Certifié | méthode et organisme reconnus | absent du MVP |

Règles obligatoires :

- aucune promotion automatique de niveau ;
- une pièce P2 ne transforme pas automatiquement une déclaration en mesure P3 ;
- une session authentifiée attribue l'acteur, mais ne change pas le niveau métier ;
- une sortie calculée conserve au mieux le niveau de son intrant le moins probant ;
- une donnée P0 ne peut soutenir une communication scientifique ou commerciale réelle ;
- une libération interne P4 n'est pas une certification P5.

### 10.2 Estimations et facteurs

- chaque jeu de facteurs possède un identifiant, une version, une source, une période de validité et un approbateur ;
- les URI actuelles restent une convention de démonstration sans équivalence en `Nm³`, `kWh`, FCFA ou produit fertilisant ;
- tout calcul physique futur doit utiliser des unités typées et une formule vérifiable ;
- une modification de facteur crée une nouvelle version ;
- le résultat doit afficher hypothèses, intervalle, niveau de preuve et limites ;
- aucun résultat ne doit être présenté comme validé sans source et modèle explicites.

### 10.3 Vocabulaire produit

- **digestat brut** : sortie du procédé, sans allégation agronomique automatique ;
- **amendement/biofertilisant** : usage à confirmer selon analyses et règles applicables ;
- **engrais** : appellation conditionnée à la qualité, la composition et la conformité ;
- **biogaz** : volume mesuré ou estimation avec composition, conditions et méthode explicites ;
- **crédit environnemental** : hors périmètre sans méthodologie reconnue et vérification indépendante.

## 11. Parcours métier nominal

```text
Inscription/organisation
        ↓
Déclaration P1 du gisement
        ↓
Preuve P2 et/ou mesure P3
        ↓
Appariement et proposition P0
        ↓
Validation humaine et affectation logistique
        ↓
Collecte + pesée P3 + création du lot
        ↓
Acceptation/refus par l'unité
        ↓
Transformation et sorties physiques P3
        ↓
Contrôle qualité et libération interne P4
        ↓
Stock disponible dérivé
        ↓
Réservation client P1 et livraison future
        ↓
Audit et provenance de bout en bout
```

### 11.1 Parcours alternatifs à couvrir

- déclaration incomplète ou incohérente ;
- aucune unité compatible ;
- unité sans capacité ;
- collecte impossible ou annulée ;
- écart important entre déclaré et mesuré ;
- lot refusé ;
- transformation annulée ;
- sortie en quarantaine ou rejetée ;
- stock insuffisant ;
- réservation concurrente ;
- session expirée ou rôle révoqué ;
- synchronisation hors ligne rejouée ;
- incident ou preuve suspecte.

## 12. Exigences PWA, mobile et expérience utilisateur

| ID | Exigence | Priorité | Critère |
|---|---|---|---|
| UX-01 | Interface responsive 390/768/1024/1440 px | Must | Aucun débordement et actions principales accessibles |
| UX-02 | PWA installable | Must | Manifeste et service worker valides |
| UX-03 | Français clair et vocabulaire métier contrôlé | Must | Libellés compréhensibles et avertissements visibles |
| UX-04 | Indicateur de réseau et synchronisation | Must | L'utilisateur connaît l'état en ligne/hors ligne |
| UX-05 | Accessibilité clavier, labels et contrastes | Should | Tests automatiques et revue manuelle |
| UX-06 | Formulaires courts et adaptés au terrain | Must | Saisie possible sur téléphone d'entrée de gamme |
| UX-07 | Erreurs actionnables | Must | Message clair, sans fuite technique ni perte de saisie |
| UX-08 | Affichage systématique preuve/unité/source | Must | Toute valeur sensible expose son statut |

Le cache hors ligne ne doit contenir ni session, ni portail privé, ni preuve, ni mesure, ni lot. La seule opération hors ligne actuelle est une nouvelle déclaration P1 avec clé d'idempotence.

## 13. Exigences relatives aux données

### 13.1 Modèle conceptuel

| Domaine | Entités principales |
|---|---|
| Identité | utilisateur, organisation, appartenance, rôle, session, invitation |
| Sites | site producteur, unité, zone, coordonnées, horaires |
| Gisements | type de déchet, déclaration, disponibilité, preuve, mesure |
| Logistique | véhicule, capacité, collecte, tournée, arrêt, incident |
| Lots | lot de déchets, décision, statut, provenance |
| Transformation | exécution, intrants, pertes, sorties, produit |
| Qualité | analyse, spécification, contrôle, libération/rejet |
| Stock | mouvement, réservation, annulation, livraison |
| Calcul | facteurs, estimation, scénario, version, empreinte |
| Gouvernance | audit, approbation, notification, correction, incident |

### 13.2 Exigences DATA

| ID | Exigence | Priorité |
|---|---|---|
| DATA-01 | Chaque donnée sensible porte provenance et niveau de preuve | Must |
| DATA-02 | Les unités sont explicites et validées | Must |
| DATA-03 | Les événements importants sont append-only | Must |
| DATA-04 | Les migrations sont versionnées et non destructives par défaut | Must |
| DATA-05 | Les données P0 sont séparées des données terrain | Must |
| DATA-06 | Les coordonnées précises sont privées et minimisées | Must |
| DATA-07 | Les politiques de rétention/suppression sont documentées | Must avant pilote réel |
| DATA-08 | Les sauvegardes et restaurations sont testées | Must avant production |
| DATA-09 | PostgreSQL/PostGIS devient la cible métier | Should |
| DATA-10 | Photos et pièces migrent vers un stockage objet sécurisé | Should |

### 13.3 Données synthétiques

Les profils `small` et `enriched` servent exclusivement à la démonstration, aux tests et à l'évaluation technique. Ils doivent conserver :

- une graine fixe ;
- un identifiant de version ;
- une classification P0 ;
- des coordonnées fictives ;
- une procédure reproductible ;
- une séparation stricte des futures observations terrain.

Ils ne constituent ni un jeu d'entraînement autorisé, ni une preuve de volumes, comportements, rendements ou performances locales.

## 14. Intelligence artificielle et moteurs décisionnels

### 14.1 Principes

BioLoop doit séparer :

1. les règles et calculs déterministes ;
2. l'optimisation mathématique des tournées ;
3. les modèles prédictifs facultatifs ;
4. les assistants génératifs éventuels.

L'IA est un composant d'aide à la décision, jamais l'autorité finale.

### 14.2 Cas d'usage autorisés progressivement

| ID | Cas d'usage | Conditions minimales |
|---|---|---|
| IA-01 | Prévision des volumes d'apport à 7/30 jours | historique local, split temporel, baseline et métriques |
| IA-02 | Détection d'écarts/anomalies | explication des facteurs, seuil/version, revue humaine |
| IA-03 | Recommandation d'appariement | contraintes explicites et possibilité de refus humain |
| IA-04 | Optimisation des tournées | objectif, contraintes, solveur/version et fallback |
| IA-05 | Aide à la lecture des documents | corpus approuvé, sortie structurée et validation serveur |
| IA-06 | Assistant d'explication | accès en lecture, citation des données et absence de nombre inventé |

### 14.3 Cas interdits sans validation supplémentaire

- prédire ou annoncer un rendement scientifique depuis les données P0 ;
- inventer un coefficient manquant ;
- qualifier automatiquement un produit comme engrais ;
- prendre seul une décision de collecte, rejet, libération, paiement ou publication ;
- produire un conseil agronomique personnalisé non validé ;
- publier un impact ou crédit environnemental ;
- entraîner un modèle avec des données sans autorisation ou provenance.

### 14.4 Exigences IA

| ID | Exigence | Priorité |
|---|---|---|
| IA-GOV-01 | Comparer tout modèle à une baseline simple | Must |
| IA-GOV-02 | Versionner données, variables, code et modèle | Must |
| IA-GOV-03 | Documenter métriques, limites et domaine d'usage | Must |
| IA-GOV-04 | Afficher le niveau de preuve des entrées/sorties | Must |
| IA-GOV-05 | Conserver une validation humaine | Must |
| IA-GOV-06 | Évaluer dérive, erreurs et sous-groupes pertinents | Should |
| IA-GOV-07 | Prévoir désactivation et retour à la baseline | Must |
| IA-GOV-08 | Interdire l'écriture directe d'un LLM dans la base | Must |

Tout prototype entraîné uniquement sur des données synthétiques doit afficher : **« Prototype IA entraîné sur données synthétiques — non validé terrain »**.

## 15. Architecture cible

### 15.1 Vue logique

```text
PWA Next.js / mobile web
          |
          | HTTPS, cookie HttpOnly, CSRF
          v
API FastAPI modulaire
  | identité / organisations / RBAC
  | gisements / preuves / mesures
  | appariement / logistique / lots
  | transformation / qualité / inventaire
  | calcul / optimisation / IA
  | notifications / audit / observabilité
          |
          +-------------------+--------------------+
          |                   |                    |
 PostgreSQL/PostGIS     Stockage objet       File de travaux
          |                   |                    |
   données métier       photos/documents     optimisation/rapports
```

### 15.2 Principes d'architecture

- conserver un monolithe modulaire tant que la charge ne justifie pas des services séparés ;
- appliquer toutes les règles et autorisations côté backend ;
- utiliser des contrats API stricts et versionnés ;
- isoler les services externes derrière des adaptateurs ;
- rendre les calculs, optimisations et modèles remplaçables ;
- appliquer l'idempotence aux synchronisations et événements externes ;
- utiliser une outbox pour les notifications et intégrations futures ;
- ne migrer vers des microservices que sur preuve de charge, d'équipe ou de conformité.

### 15.3 Évolution depuis l'existant

1. stabiliser les tranches 01 à 05 ;
2. compléter les tournées multi-producteurs et multi-véhicules ;
3. migrer progressivement les repositories vers SQLAlchemy ;
4. introduire PostgreSQL/PostGIS et tester les migrations ;
5. migrer les preuves vers un stockage objet avec antivirus ;
6. ajouter sauvegardes, supervision et environnement de préproduction ;
7. connecter un pilote terrain ;
8. introduire les modèles prédictifs uniquement après qualification des données.

## 16. Sécurité, confidentialité et contrôle d'accès

### 16.1 Exigences de sécurité

| ID | Exigence | Priorité |
|---|---|---|
| SEC-01 | Hacher les mots de passe avec un algorithme reconnu | Must |
| SEC-02 | Stocker uniquement l'empreinte des sessions/invitations | Must |
| SEC-03 | Utiliser cookie HttpOnly/SameSite et Secure sous HTTPS | Must |
| SEC-04 | Protéger les mutations contre CSRF et origine non autorisée | Must |
| SEC-05 | Appliquer RBAC et isolation d'organisation côté serveur | Must |
| SEC-06 | Tester systématiquement les accès horizontaux | Must |
| SEC-07 | Valider extension, MIME, signature et taille des fichiers | Must |
| SEC-08 | Ne journaliser aucun mot de passe, jeton ou contenu binaire | Must |
| SEC-09 | Rechercher secrets et dépendances vulnérables en CI | Must cible |
| SEC-10 | Chiffrer les communications et données de production | Must avant production |
| SEC-11 | Fournir MFA/récupération selon les rôles | Should avant pilote étendu |
| SEC-12 | Définir rétention, sauvegarde et incident | Must avant données réelles |

### 16.2 Données sensibles

Sont notamment sensibles :

- coordonnées précises des sites ;
- identité et contacts des utilisateurs ;
- capacités, volumes, coûts et contrats ;
- preuves photographiques et documents ;
- informations de connexion et journaux techniques ;
- résultats qualité non publics.

L'accès doit suivre le besoin d'en connaître, et les vues institutionnelles ou publiques doivent être agrégées et expurgées.

### 16.3 Sécurité IA

- traiter les documents, images et contenus externes comme des données non fiables ;
- résister aux instructions injectées dans les pièces ;
- limiter les outils et destinations réseau ;
- valider les sorties structurées côté serveur ;
- interdire toute action sensible sans approbation ;
- journaliser modèle/version/entrée/résultat/validation sans conserver de raisonnement privé brut ;
- prévoir kill switch, rollback et registre de modèles.

## 17. Exigences non fonctionnelles

| ID | Domaine | Exigence cible |
|---|---|---|
| NFR-PERF-01 | Performance | p95 API interactive < 500 ms hors optimisation lourde en environnement pilote |
| NFR-PERF-02 | Performance | affichage initial utilisable < 3 s sur réseau mobile raisonnable |
| NFR-REL-01 | Fiabilité | aucune perte lors d'une synchronisation rejouée |
| NFR-REL-02 | Fiabilité | parcours de démonstration disponible sans API externe critique |
| NFR-DISP-01 | Disponibilité | objectif pilote à définir ; surveillance obligatoire avant production |
| NFR-SCAL-01 | Capacité | profil enrichi ≥ 40 producteurs/4 unités sans dégradation majeure |
| NFR-MAINT-01 | Maintenabilité | modules, types, migrations, ADR et tests à jour |
| NFR-COMP-01 | Compatibilité | Chrome/Edge récents et écran mobile 390 px minimum |
| NFR-ACC-01 | Accessibilité | labels, clavier, contraste et messages accessibles |
| NFR-OBS-01 | Observabilité | corrélation, logs structurés, métriques et alertes |
| NFR-PORT-01 | Portabilité | installation reproductible et configuration par environnement |
| NFR-SEC-01 | Sécurité | aucune vulnérabilité critique connue non traitée avant livraison |

Les seuils de performance et disponibilité devront être révisés après mesure sur l'infrastructure pilote.

## 18. Observabilité et indicateurs

### 18.1 Mesures techniques

- disponibilité de l'API et de la PWA ;
- latence p50/p95/p99 ;
- taux d'erreur par route ;
- échecs de connexion et accès refusés ;
- échecs/reprises de synchronisation ;
- durée et résultat des migrations ;
- durée/échec des optimisations ;
- saturation stockage, base et file de travaux ;
- appels externes inattendus.

### 18.2 Qualité des données

- part P1/P2/P3/P4/P5 ;
- déclarations avec unité valide ;
- écart déclaré/mesuré ;
- preuves rejetées ;
- lots acceptés/refusés et motifs ;
- produits en quarantaine/libérés/rejetés ;
- incohérences de stock ;
- facteurs sans source ou expirés.

### 18.3 KPI métier

- tonnes déclarées, collectées, acceptées et transformées ;
- coût par tonne acceptée ;
- distance/temps par tonne ;
- taux de collecte réussie ;
- taux de contamination ou refus ;
- régularité d'approvisionnement ;
- produits mesurés, libérés, réservés et livrés ;
- délai déclaration → collecte → transformation → disponibilité ;
- satisfaction et usage par rôle.

Tout KPI environnemental devra afficher sa formule, son périmètre, sa méthodologie et son niveau de preuve.

## 19. Tests et assurance qualité

### 19.1 Stratégie de test

| Niveau | Contenu |
|---|---|
| Unitaires | règles, conversions, transitions, autorisations, soldes |
| Intégration | API, repository, migrations, stockage, idempotence |
| Contractuels | OpenAPI, schémas, compatibilité des réponses |
| E2E | parcours complets par rôle desktop/mobile |
| Sécurité | accès horizontal, CSRF, fichiers, sessions, invitations |
| Golden | calculs déterministes et reproductibilité |
| Adversariaux | entrées extrêmes, pièces malveillantes, injection, concurrence |
| Terrain | faible connexion, téléphone réel, pesée, incident et reprise |

### 19.2 Portes de qualité

Une fonctionnalité n'est livrable que si :

- les critères d'acceptation sont satisfaits ;
- les tests existants ne régressent pas ;
- TypeScript et le build passent ;
- les migrations s'appliquent sur une base existante ;
- `git diff --check` ne remonte pas d'erreur ;
- la documentation et le dictionnaire sont mis à jour ;
- les risques sécurité/données sont documentés ;
- la revue visuelle mobile et desktop est effectuée ;
- un plan de retour ou désactivation existe pour les changements à risque.

## 20. Méthode de développement et GitHub

### 20.1 Organisation du travail

- `main` doit rester stable et démontrable ;
- chaque évolution part d'une branche `feature/`, `fix/`, `docs/` ou `chore/` ;
- une issue décrit le besoin, le périmètre et les critères d'acceptation ;
- chaque pull request reste ciblée et révisable ;
- calculs, migrations, sécurité et IA exigent une revue renforcée ;
- toute décision structurante crée ou met à jour un ADR ;
- les versions de démonstration utilisent des tags et notes de version.

### 20.2 Définition de Ready

Une tâche est prête lorsque :

- le problème utilisateur est compris ;
- le rôle et la portée organisationnelle sont identifiés ;
- les données, unités et niveaux de preuve sont définis ;
- les critères d'acceptation sont testables ;
- les dépendances et risques sont connus ;
- les maquettes ou contrats nécessaires sont disponibles.

### 20.3 Définition de Done

Une tâche est terminée lorsque :

- code, tests et documentation sont livrés ;
- les autorisations serveur sont testées ;
- aucune donnée sensible n'est exposée ;
- le parcours est vérifié visuellement ;
- migration et compatibilité sont validées ;
- le commit est poussé et lié à l'issue/PR ;
- les limites sont explicites ;
- le responsable produit accepte le résultat.

### 20.4 Gestion des versions

- utiliser le versionnement sémantique lorsque les releases commencent ;
- versionner séparément API, schéma, facteurs, modèles et données synthétiques ;
- ne jamais modifier silencieusement un facteur ou un modèle publié ;
- joindre notes de version, migrations, risques et procédure de rollback.

## 21. Gouvernance et responsabilités

### 21.1 Rôles de l'équipe

| Rôle projet | Responsabilités |
|---|---|
| Sponsor/porteur | vision, partenariats, arbitrage et financement |
| Product Owner | besoins, backlog, priorités et recette métier |
| Lead technique | architecture, qualité, intégration et dette technique |
| Développeur frontend/PWA | interfaces, accessibilité, hors-ligne et tests E2E |
| Développeur backend | API, règles métier, autorisations et migrations |
| Responsable données/IA | dictionnaire, qualité, modèles, évaluations et fiches modèle |
| Expert déchets/biogaz | compatibilités, procédés et facteurs physiques |
| Expert agronomie/qualité | analyses, usages et vocabulaire produit |
| Responsable sécurité | menaces, accès, secrets, incidents et conformité |
| QA/Test | stratégie de test, non-régression et recette |
| Opérateur pilote | procédures terrain, collecte, pesée et retours |
| Documentation/communication | guides, vidéo, support et présentation |

### 21.2 RACI simplifié

Légende : **R** responsable de réalisation, **A** valide, **C** consulté, **I** informé.

| Activité | PO | Lead | Dev | Data/IA | Expert métier | Sécurité | QA |
|---|---|---|---|---|---|---|---|
| Priorisation | A/R | C | I | C | C | I | I |
| Architecture | C | A/R | R | C | I | C | C |
| Règles métier | A | C | R | C | A/C | I | C |
| Facteurs/rendements | C | I | I | R | A | C | C |
| Modèle IA | C | C | C | A/R | C | C | R |
| Sécurité | I | R | R | C | I | A/R | C |
| Tests/recette | A | C | R | C | C | C | A/R |
| Déploiement | I | A/R | R | I | I | C | C |

Les personnes doivent être nommées explicitement dans le registre projet. Une même personne peut cumuler plusieurs rôles, mais une décision sensible doit garder une séparation logique entre création et approbation.

## 22. Livrables attendus

| ID | Livrable | Responsable pressenti | Critère de réception |
|---|---|---|---|
| LIV-01 | Code source versionné | Lead/Dev | dépôt propre, tests et historique |
| LIV-02 | PWA installable | Frontend | manifeste, mobile, hors-ligne limité |
| LIV-03 | API documentée | Backend | OpenAPI à jour et tests contractuels |
| LIV-04 | Schéma et migrations | Backend/Data | migration testée et rollback documenté |
| LIV-05 | Dictionnaire des données | Data | champs, unités, preuves et propriétaires |
| LIV-06 | ADR | Lead | décisions structurantes tracées |
| LIV-07 | Fiches facteurs/modèles | Data/Experts | sources, métriques, limites, approbation |
| LIV-08 | Plan et résultats de test | QA | couverture des critères d'acceptation |
| LIV-09 | Guide utilisateur par rôle | Produit/Documentation | parcours compréhensible par chaque acteur |
| LIV-10 | Guide d'exploitation | Lead/Sécurité | configuration, sauvegarde, incident, restauration |
| LIV-11 | Démo et vidéo de secours | Produit | parcours stable et message crédible |
| LIV-12 | Rapport pilote | PO/Data/Experts | KPI, écarts, incidents et décision go/no-go |

## 23. Roadmap recommandée

### Phase A — Consolidation immédiate

- stabiliser `main` et traiter les défauts bloquants ;
- compléter ce cahier des charges avec les noms et décisions de l'équipe ;
- créer le backlog GitHub à partir des exigences ;
- documenter installation et parcours par rôle ;
- préparer une release de démonstration reproductible.

### Phase B — Intelligence opérationnelle et logistique

- tournées multi-producteurs et multi-véhicules ;
- contraintes de capacité et fenêtres ;
- coûts paramétrables ;
- baseline déterministe et optimisation ;
- prévision des apports et anomalies explicables uniquement en P0 si données synthétiques.

### Phase C — Durcissement du pilote

- PostgreSQL/PostGIS ;
- stockage objet et antivirus ;
- sauvegarde/restauration ;
- MFA/récupération ;
- observabilité et alertes ;
- CI sécurité et environnements distincts.

### Phase D — Validation terrain

- accords et consentements ;
- bassin pilote compact ;
- procédures de pesée et qualité ;
- 4 à 8 semaines de données ;
- comparaison déclaré/mesuré ;
- coût réel par tonne acceptée ;
- validation des facteurs par experts.

### Phase E — Extension contrôlée

- commandes et livraisons ;
- intégrations partenaires ;
- modèles prédictifs évalués ;
- analyses agronomiques et énergétiques ;
- étude environnementale indépendante ;
- montée en charge guidée par les mesures.

## 24. Critères de recette globale

La version pilote est acceptable lorsque :

1. les six rôles accèdent uniquement à leur périmètre ;
2. une déclaration peut être créée sur mobile et synchronisée sans doublon ;
3. une collecte est affectée, prouvée et mesurée ;
4. un lot est accepté/refusé sans écrasement de l'historique ;
5. une transformation produit des sorties uniquement par saisie mesurée ;
6. un produit reste invisible avant libération ;
7. le stock ne peut devenir négatif ;
8. le client peut réserver et annuler sa propre quantité ;
9. la provenance complète est consultable ;
10. toute action sensible est autorisée et auditée ;
11. les données P0 à P5 sont correctement distinguées ;
12. les tests backend, build, migrations et E2E passent ;
13. le parcours fonctionne à 390 px sans débordement ;
14. aucune dépendance externe critique n'empêche la démonstration ;
15. les limites scientifiques et opérationnelles sont visibles.

## 25. Risques et mesures de maîtrise

| Risque | Impact | Mesure de maîtrise |
|---|---|---|
| Volumes déclarés inexacts | mauvaise planification | pesée P3, score de fiabilité, historique des écarts |
| Intrants incompatibles/contaminés | rejet ou dommage procédé | compatibilité, contrôle et décision unité |
| Données synthétiques prises pour réelles | perte de crédibilité | marquage P0 permanent et avertissements |
| Rendements contestés | risque scientifique/commercial | facteurs sourcés, experts, intervalle et blocage |
| Fuite de localisation/données | risque sécurité et commercial | minimisation, RBAC, chiffrement et vues agrégées |
| Accès inter-organisation | violation de confidentialité | contrôles serveur et tests horizontaux |
| Perte de preuves | rupture de traçabilité | stockage objet, hash, sauvegardes et rétention |
| Stock concurrent incohérent | réservation impossible à servir | transactions, contraintes et tests de concurrence |
| IA non fiable | décision erronée | baseline, métriques, explicabilité, validation humaine |
| Dépendance réseau | blocage terrain | PWA, reprise et mode démo local |
| Équipe dispersée | retards et incohérence | PO, RACI, issues petites et revues fréquentes |
| Dette SQLite | limites de concurrence | migration progressive vers PostgreSQL/PostGIS |
| Confusion P4/P5 | risque réglementaire | vocabulaire, rôles et contrôles d'interface/API |

## 26. Hypothèses à valider sur le terrain

- les producteurs acceptent de déclarer régulièrement leurs gisements ;
- les quantités et fréquences sont suffisamment stables ;
- les unités ont une capacité et un besoin identifiables ;
- un transporteur peut opérer une tournée économiquement viable ;
- les déchets sont compatibles avec les procédés visés ;
- un acteur accepte de financer ou payer le service ;
- les produits disposent d'un usage et d'un client potentiel ;
- les données de localisation peuvent être collectées avec consentement ;
- les facteurs scientifiques peuvent être validés ;
- l'IA apporte un gain mesurable au-delà des règles simples.

Chaque hypothèse doit être reliée à un entretien, une observation, une mesure ou une expérimentation, avec un critère explicite de passage ou d'abandon.

## 27. Dépendances et prérequis

### 27.1 Techniques

- Python 3.12 et environnement virtuel ;
- Node.js 22 via NVM ;
- navigateur Chromium pour Playwright ;
- Git et accès au dépôt GitHub privé ;
- à terme PostgreSQL/PostGIS, stockage objet et infrastructure HTTPS.

### 27.2 Métier

- expert biogaz/procédés ;
- expert agronomie/qualité ;
- partenaire producteur ;
- opérateur logistique ;
- unité de transformation ;
- client/agriculteur ;
- règles applicables aux déchets et produits à confirmer.

### 27.3 Données

- catalogue des intrants ;
- capacités et compatibilités réelles ;
- mesures déclarées et pesées ;
- temps, distances et coûts réels ;
- analyses qualité ;
- production réellement mesurée ;
- consentements et droits d'utilisation.

## 28. Gestion des changements

Toute demande modifiant le périmètre, une règle de preuve, un facteur, un rôle, une migration, un fournisseur externe ou une action automatisée doit :

1. être décrite dans une issue ;
2. indiquer le besoin utilisateur et le bénéfice ;
3. analyser impacts données, sécurité, coût et compatibilité ;
4. définir critères d'acceptation et tests ;
5. créer un ADR si la décision est structurante ;
6. être approuvée par le Product Owner et le responsable concerné ;
7. mettre à jour le présent cahier des charges si le périmètre change.

## 29. Glossaire

| Terme | Définition |
|---|---|
| Gisement | quantité de déchets disponible à un site et une période |
| Intrant | matière introduite dans un procédé de transformation |
| Lot | unité traçable de matière rattachée à une mesure et des preuves |
| Digestat | matière résiduelle issue d'une digestion, sans allégation automatique |
| Biofertilisant | produit à vocation fertilisante soumis à qualité et règles applicables |
| URI | unité de rendement illustrative, sans équivalence physique/économique |
| Provenance | liens entre origine, transformations, décisions et acteurs |
| PWA | application web progressive installable et partiellement résiliente hors ligne |
| RBAC | contrôle d'accès fondé sur les rôles |
| Idempotence | répétition d'une requête sans création d'effet supplémentaire |
| Baseline | méthode simple servant de référence à un modèle plus complexe |
| P0–P5 | échelle BioLoop de simulé à certifié |
| ADR | document de décision d'architecture |
| RACI | matrice responsable, approbateur, consulté, informé |

## 30. Documents de référence

- `README.md` — état, lancement, architecture et limites ;
- `outputs/BioLoop_CI_MVP_Hackathon_SIREXE_2026.md` — rapport de cadrage ;
- `docs/data-dictionary.md` — dictionnaire des données ;
- `docs/adr/0001` à `0005` — décisions d'architecture ;
- `docs/model-cards/deterministic-decision-services-v1.md` — services décisionnels ;
- `docs/analytics/transformation-dataset-v1.md` — jeu analytique interne ;
- `SIREXE_Hackathon_2026_10_idees_recherche.xlsx` — matériau de recherche local, non suivi par Git ;
- `AI-Agent-Security-Architecture-Attack-Surface-Defense-ebook.pdf` — cadre de sécurité local, non suivi par Git.

## 31. Approbation du cahier des charges

| Fonction | Nom | Décision | Date | Commentaire |
|---|---|---|---|---|
| Porteur de projet | À compléter | ☐ Approuvé ☐ À corriger | | |
| Product Owner | À compléter | ☐ Approuvé ☐ À corriger | | |
| Lead technique | À compléter | ☐ Approuvé ☐ À corriger | | |
| Responsable données/IA | À compléter | ☐ Approuvé ☐ À corriger | | |
| Expert métier | À compléter | ☐ Approuvé ☐ À corriger | | |
| Responsable sécurité/QA | À compléter | ☐ Approuvé ☐ À corriger | | |

---

### Règle d'utilisation par l'équipe

Chaque nouvelle fonctionnalité doit citer au moins une exigence de ce cahier des charges dans son issue ou sa pull request. Si aucune exigence ne couvre le besoin, l'équipe doit d'abord décider s'il s'agit d'une clarification ou d'un changement de périmètre, puis mettre à jour ce document avant la livraison.
