# BioLoop CI - dossier de préparation du MVP SIREXE Hackathon 2026

**Version :** 1.0  
**Date d'analyse :** 28 août 2026  
**Périmètre :** synthèse des matériaux locaux, vérification des URL fournies, proposition de MVP, architecture, données, sécurité IA, gouvernance, observabilité et feuille de route.

> **Règle de crédibilité scientifique** - Toute valeur de rendement, d'impact ou de crédit environnemental affichée par BioLoop doit indiquer son unité, sa formule ou son modèle, sa source, sa version, ses hypothèses et son niveau d'incertitude. En l'absence de ces éléments, elle doit être étiquetée comme simulation illustrative et ne doit pas être présentée comme une mesure ou une vérité scientifique.

## 1. Résumé exécutif

BioLoop CI est une plateforme d'orchestration de la valorisation des déchets organiques. Elle relie cinq maillons : producteurs de déchets, transporteurs, unités de transformation, détenteurs de capacités de stockage/traitement et clients des produits issus de la transformation. Sa proposition de valeur n'est pas de vendre un biodigesteur supplémentaire, mais de sécuriser le gisement, la logistique, la traçabilité et le partage de valeur autour des unités existantes ou futures.

Le classeur de préparation SIREXE classe BioLoop CI premier parmi dix concepts, avec un score de travail de 94/100. Ce score est une grille de coaching, pas une note officielle. Le concept est directement aligné sur l'un des deux défis opérationnels affichés par le concours : la valorisation des déchets en biogaz. Ses points forts sont l'alignement, l'impact, l'innovation de plateforme, la démonstration cartographique et la possibilité de montrer une chaîne complète en trois minutes. Son principal risque est de produire une interface convaincante mais fondée sur des volumes, rendements et économies non vérifiés.

Le MVP recommandé doit donc privilégier un parcours démontrable et auditable :

1. un producteur déclare un gisement organique ;
2. la plateforme qualifie la donnée et affiche son niveau de preuve ;
3. un moteur déterministe et versionné calcule des scénarios de rendement, sans inventer de coefficients ;
4. BioLoop apparie les gisements avec une unité de transformation et construit une tournée ;
5. un lot est collecté, pesé et tracé ;
6. les produits estimés ou mesurés sont proposés à des clients, avec séparation explicite entre déclaration, estimation et mesure.

Le cœur du MVP ne nécessite pas d'agent IA autonome. Une PWA hors-ligne partiel, une API FastAPI, PostgreSQL/PostGIS et OR-Tools suffisent. L'IA générative, si elle est montrée, doit rester un assistant d'explication sur des données déjà calculées et ne jamais modifier une tournée, un paiement, un coefficient de rendement ou une déclaration environnementale sans validation humaine.

## 2. Sources examinées et limites

### 2.1 Matériaux locaux

| Source | Lecture effectuée | Apport pour BioLoop CI | Limite |
|---|---|---|---|
| `SIREXE_Hackathon_2026_10_idees_recherche.xlsx` | Les 9 feuilles ont été inspectées et rendues visuellement : Accueil, Cadrage SIREXE, Portefeuille, Fiches détaillées, Benchmarks, MVP 48h, Matrice de sélection, Guide de coaching et Sources. | Positionnement, parcours, utilisateurs, données, architecture initiale, modèle économique, risques, benchmarks, plan 48 h et critères de coaching. | Les scores, budgets et jeux de données sont des hypothèses de travail. Plusieurs faits web sont datés du 04/08/2026 et peuvent avoir évolué. |
| `AI-Agent-Security-Architecture-Attack-Surface-Defense-ebook.pdf` | Lecture textuelle complète et contrôle visuel des 28 pages. | Cadre d'attaque des agents et MCP, moindre privilège, validation pré-exécution, contrôle des flux d'information, approbation humaine, observabilité et feuille de route sécurité. | Guide édité par CrowdStrike : utile comme cadre de menaces, mais orienté fournisseur. Les principes doivent être adaptés au risque réel de BioLoop, sans adopter automatiquement un produit commercial. |

### 2.2 URL fournies

| URL | Statut au 28/08/2026 | Informations accessibles et pertinentes |
|---|---|---|
| [Site officiel SIREXE Hackathon 2026](https://hackathon.sirexe.ci/) | Accessible. Page consultée directement. | Deux catégories : Prix Liberté et Prix Thématique. Le Prix Thématique couvre l'optimisation énergétique et la valorisation des déchets en biogaz. Prototype fonctionnel en 48 h. Inscriptions affichées du 09/07 au 31/08/2026 ; première sélection du 01 au 08/09 ; présélection prototype du 05 au 16/10 ; bootcamp les 19-20/11 ; finale le 22/11. Équipes de 1 à 5 personnes selon cette page. Vidéo de 3 à 5 minutes en MP4, français ou anglais, et document PDF de 10 pages maximum. Six équipes annoncées comme récompensées ; montants affichés : 10 M, 5 M et 2,5 M FCFA. La répartition exacte par catégorie reste à confirmer. |
| [Partage Gemini fourni](https://share.gemini.google/Mkoy6PMiG9z0) | Non accessible dans la session : la consultation reste en attente d'autorisation et ne fournit aucun contenu vérifiable. | Aucun fait provenant de ce lien n'est repris. Une exportation PDF/Markdown ou un partage public permettrait une analyse ultérieure sans modifier les conclusions actuelles. |

### 2.3 Divergences et points à confirmer

- Le classeur mentionne une journée d'incubation le 14/08/2026. La page officielle consultée le 28/08 affiche désormais le **vendredi 21/08/2026 de 09h à 13h**, à l'immeuble SCIAM au Plateau. Cette activité étant passée, la divergence n'affecte plus le dépôt, mais montre qu'il faut vérifier le site vivant avant toute communication.
- La page officielle consultée indique des équipes de 1 à 5 personnes. Le classeur signale qu'un article ministériel parlait de 3 à 5. Pour minimiser le risque, une équipe de 3 à 5 reste compatible avec les deux formulations.
- Le règlement du code préexistant et la répartition exacte des prix ne sont pas suffisamment explicites dans les sources accessibles. Obtenir une confirmation écrite de l'organisation.
- La date de clôture affichée est le 31/08/2026. Au 28/08, la priorité immédiate est le dossier, la vidéo et la preuve terrain, pas l'élargissement fonctionnel.

## 3. Synthèse consolidée de BioLoop CI

### 3.1 Problème

Les marchés, élevages, abattoirs, coopératives et agro-industries génèrent des déchets organiques dispersés. Les unités de méthanisation manquent souvent de visibilité sur les volumes disponibles, leur qualité, leur saisonnalité et le coût réel de collecte. Ce défaut de coordination peut conduire à une sous-alimentation des digesteurs, des tournées non rentables, des déchets contaminés et une répartition opaque de la valeur.

Cette formulation doit encore être confirmée par au moins trois entretiens locaux et, idéalement, un site pilote. Le classeur constitue une hypothèse structurée, pas une preuve terrain.

### 3.2 Proposition de valeur

**Pitch recommandé :** « BioLoop CI relie les producteurs de déchets organiques, les transporteurs, les unités de transformation et les agriculteurs pour sécuriser les approvisionnements, planifier la collecte et tracer la production de biogaz et de produits fertilisants. »

La plateforme couvre : déclaration du déchet, qualification, agrégation, simulation de rendement, appariement, planification de tournée, collecte, pesée, transformation, affectation des produits et traçabilité.

### 3.3 Parties prenantes

| Rôle | Exemples | Besoin principal | Payeur possible |
|---|---|---|---|
| Producteur de déchets | Éleveur, marché, abattoir, producteur agricole, transformateur de cacao/manioc/palmier | Enlèvement fiable, conformité, revenu ou réduction du coût de gestion | Parfois producteur/commune ; parfois aucun si la matière a une valeur positive |
| Coordinateur/collecteur | Coopérative, opérateur logistique, commune | Tournées rentables, preuves de collecte, gestion des incidents | Unité de transformation ou donneur d'ordre |
| Transformateur | Biodigesteur, compostage ou autre unité autorisée | Intrants réguliers, compatibles et traçables | Candidat principal pour abonnement et commission |
| Client produit | Agriculteur, coopérative, acheteur de gaz/énergie, distributeur | Qualité, disponibilité, prix et preuve d'origine | Client final |
| Autorité/partenaire | Commune, district, ANAGED, financeur, organisme de contrôle | Indicateurs, conformité, impact vérifiable | Licence institutionnelle ou financement de pilote |

### 3.4 Produits et vocabulaire à sécuriser

- **Biogaz :** production estimée ou mesurée, avec composition si disponible.
- **Digestat/biofertilisant/amendement :** ne pas employer ces termes comme synonymes automatiques. La dénomination commerciale et l'usage agronomique dépendent des intrants, du procédé, des analyses et des règles applicables.
- **Engrais :** l'allégation doit dépendre d'une analyse de qualité et d'une classification réglementaire. Le MVP peut afficher « potentiel fertilisant à confirmer par analyse ».
- **Crédit environnemental :** aucun crédit ne doit être calculé ou vendu à partir d'un simple facteur interne. Le MVP peut afficher un module « pré-évaluation non certifiée », désactivé par défaut, avec méthodologie et données requises.

## 4. MVP priorisé

### 4.1 Parcours de démonstration

Le scénario du classeur est solide et doit rester le fil rouge : trois marchés et deux élevages déclarent leurs déchets ; BioLoop construit une tournée, estime sous hypothèses le biogaz et les produits fertilisants potentiels, puis montre la répartition de valeur entre producteurs, transporteur et unité de transformation.

La démonstration doit rendre visible en moins de 90 secondes :

- ce qui a été déclaré ;
- ce qui a été mesuré ou vérifié ;
- les hypothèses choisies ;
- la tournée proposée et son coût ;
- le résultat attendu sous forme d'intervalle ou de scénarios ;
- l'action suivante et la personne qui doit la valider.

### 4.2 Priorités MoSCoW

#### Must have

1. **Comptes et rôles de démonstration** : producteur, coordinateur, transporteur, transformateur et client.
2. **Déclaration d'un gisement** : type, masse ou volume et unité, fréquence, humidité si connue, localisation approximative, photos facultatives, période de disponibilité et statut de preuve.
3. **Carte et liste filtrable** de 20 gisements fictifs et deux unités de transformation.
4. **Moteur d'estimation déterministe** avec coefficients configurables, source, version, plage d'incertitude et journal d'exécution.
5. **Appariement et tournée** selon compatibilité, capacité, distance, fenêtre temporelle et seuil minimal de collecte.
6. **Traçabilité d'un lot** : déclaré, planifié, collecté, pesé, accepté/refusé, transformé.
7. **Tableau de bord de démonstration** : tonnes déclarées/confirmées, distance, coût estimé, contamination, régularité, produits estimés/mesurés et valeur répartie.
8. **Mode démo résilient** : données préchargées, tournée pré-calculée, fonctionnement sans dépendance à une API externe et vidéo de secours.

#### Should have

- preuve photo horodatée et pesée saisie ;
- score de fiabilité fondé sur des règles explicites ;
- proposition d'offres de produit aux agriculteurs ;
- export d'un rapport de lot ;
- notifications simulées ;
- français simple et unités adaptées au terrain ;
- synchronisation différée d'une déclaration créée hors connexion.

#### Could have

- formulaire WhatsApp ou bot ;
- détection visuelle indicative de contamination ;
- optimisation multi-véhicules ;
- comparaison de scénarios de mélange ;
- prévision saisonnière après collecte de données locales ;
- API partenaire.

#### Won't have dans le MVP

- paiement réel ;
- certificat de crédit carbone ;
- allégation agronomique définitive sans analyse ;
- agent autonome pouvant commander, payer, supprimer ou publier ;
- modèle ML présenté comme supérieur sans baseline et jeu d'évaluation ;
- blockchain ;
- intégration obligatoire à un registre ou une donnée propriétaire.

### 4.3 Critères d'acceptation du MVP

- Un nouveau gisement peut être saisi et retrouvé sur la carte.
- Chaque champ sensible a une provenance : déclaré, estimé, mesuré ou vérifié.
- Le même jeu d'entrées et la même version de coefficients reproduisent exactement le même résultat.
- Une estimation sans coefficient sourcé est bloquée ou marquée « simulation illustrative ».
- La tournée respecte capacités et fenêtres simples, et un plan pré-calculé est disponible en secours.
- Un lot peut être suivi de la déclaration au produit issu de transformation.
- Les modifications de coefficients, statuts de lot et validations apparaissent dans le journal d'audit.
- Les tests de référence du moteur d'estimation et de la tournée passent hors ligne.

## 5. Modèle de calcul responsable

### 5.1 Principe

Le moteur doit d'abord être un service de calcul explicite, pas un modèle opaque. Les coefficients ne sont jamais codés en dur dans l'interface. Ils résident dans une table versionnée et approuvée.

Pour un intrant `i`, un schéma générique peut être :

```text
Matière fraîche_i (kg)
  × fraction de matière sèche_i
  × fraction de solides volatils_i
  × potentiel méthane_i (Nm³ CH4 / kg SV)
  × facteur d'efficacité du procédé
= méthane estimé_i (Nm³ CH4)

Biogaz estimé_i = méthane estimé_i / fraction CH4 supposée du biogaz
```

Chaque terme doit avoir : unité, valeur basse/centrale/haute, source, date de validité, intrant concerné, procédé concerné et approbateur. Les scénarios doivent éviter une fausse précision.

### 5.2 Produits fertilisants

La masse et la valeur agronomique du digestat ne doivent pas être déduites avec un coefficient universel. Utiliser progressivement :

1. bilan massique du procédé et séparation liquide/solide ;
2. analyses d'humidité et de matière sèche ;
3. analyses N-P-K, contaminants et paramètres sanitaires ;
4. règles d'éligibilité et recommandations agronomiques validées.

Avant analyses, afficher uniquement une quantité de digestat **estimée par bilan massique sous hypothèses**, et un « potentiel fertilisant à confirmer ».

### 5.3 Logistique

```text
Coût tournée = coût fixe véhicule
              + distance_km × coût_km
              + nombre_arrêts × coût_manipulation
              + masse_collectée × coût_variable_kg
              + pénalités de fenêtre/attente
```

Les paramètres de coût sont propres au pilote. La valeur métier clé est le coût par tonne réellement acceptée, pas seulement la distance minimale.

### 5.4 Impact et crédits environnementaux

Une pré-évaluation interne pourrait suivre :

```text
Réduction potentielle = émissions du scénario de référence
                        - émissions du projet
                        - fuites
                        - incertitude/conservatisme selon méthodologie
```

Elle ne devient une revendication ou un crédit qu'après sélection d'une méthodologie reconnue, définition du périmètre, additionnalité, règles de suivi, vérification indépendante et traitement du double comptage. Jusqu'alors, l'interface doit afficher « estimation exploratoire non certifiée ».

### 5.5 Niveaux de preuve

| Niveau | Libellé | Exemple |
|---|---|---|
| P0 | Simulé | Donnée fictive du hackathon |
| P1 | Déclaré | Quantité saisie par le producteur |
| P2 | Documenté | Photo, bon ou historique fourni |
| P3 | Mesuré | Pesée/capteur avec métadonnées |
| P4 | Vérifié | Contrôle par un acteur autorisé |
| P5 | Certifié | Méthode et organisme reconnus |

Les écrans, exports et API doivent conserver ce niveau ; un chiffre P1 ne doit jamais être agrégé et présenté comme P4.

## 6. Architecture scalable et sécurisée

### 6.1 Cible recommandée

```text
PWA web/mobile
   |
API HTTPS + authentification + contrôle d'accès
   |
Backend modulaire (déclarations, calcul, logistique, lots, produits, audit)
   |-------------------|-------------------|
PostgreSQL/PostGIS   Stockage objet      File de travaux
   |                                       |
Audit/outbox                         Optimisation / rapports
```

### 6.2 Frontend

- PWA TypeScript, responsive et installable ; Next.js ou équivalent.
- Formulaires courts, autosauvegarde locale et synchronisation différée.
- Carte OpenStreetMap/MapLibre ; prévoir des données/tuiles de démonstration locales.
- Affichage systématique des unités, de la provenance et de l'incertitude.
- Aucune règle de calcul métier uniquement dans le navigateur.
- Accessibilité, français clair et parcours utilisable sur téléphone d'entrée de gamme.

### 6.3 Backend

- FastAPI avec contrats OpenAPI stricts.
- **Monolithe modulaire** pour le MVP : plus rapide à tester et maintenir que des microservices prématurés.
- Modules : identité, organisations/sites, gisements, facteurs/rendements, estimation, appariement, tournées, lots, transformation, produits, commandes, preuves et audit.
- Tâches longues en arrière-plan pour optimisation ou rapport ; OR-Tools isolé derrière une interface.
- Idempotence pour synchronisation mobile et webhooks.
- Pattern outbox pour publier des événements sans perdre la cohérence de la base.
- Passage futur à des services séparés uniquement lorsqu'une charge, une équipe ou une exigence réglementaire le justifie.

### 6.4 Données

- PostgreSQL + PostGIS ; schéma multi-organisation avec `tenant_id` et politiques d'accès testées.
- Stockage objet pour photos et pièces, URL temporaires et analyse antivirus.
- Chiffrement en transit et au repos ; sauvegardes testées.
- Migrations versionnées ; aucune modification manuelle de production.
- Données GPS précises séparées des vues publiques/agrégées.
- Journal d'audit append-only avec acteur, objet, action, avant/après expurgé, heure et identifiant de corrélation.

### 6.5 IA et moteurs décisionnels

Trois couches clairement séparées :

1. **Règles et calculs déterministes** : rendements, compatibilité, coûts et score de preuve.
2. **Optimisation** : OR-Tools pour les tournées, avec contraintes et objectif enregistrés.
3. **IA facultative** : prévision de volumes, vision de contamination ou assistant de texte, seulement après baseline, données locales et évaluation.

Un LLM ne doit pas produire les nombres métier. Il peut reformuler un résultat calculé et citer les hypothèses fournies par l'API. Il n'a pas d'accès direct en écriture à la base ; les outils sont étroits, typés, autorisés par rôle et validés côté serveur.

### 6.6 Évolution de capacité

- Conteneurs reproductibles et déploiement sur un service géré simple.
- Cache uniquement pour données non sensibles et calculs reproductibles.
- CDN pour actifs statiques ; aucune donnée privée dans les clés ou logs CDN.
- Réplicas et partitionnement géographique seulement après mesure de charge.
- Feature flags pour IA, paiements, crédits et intégrations externes.
- Contrats d'API et événements versionnés pour connecter transporteurs, unités et partenaires.

## 7. Modèle de données et flux

### 7.1 Entités principales

| Domaine | Entités | Champs/relations essentiels |
|---|---|---|
| Identité | `Organization`, `User`, `Role`, `Membership` | tenant, rôle, statut, consentements |
| Terrain | `Site`, `GeoZone` | type, coordonnées privées/publiques, horaires |
| Gisement | `WasteType`, `WasteDeclaration`, `AvailabilityWindow` | quantité, unité, fréquence, humidité, saison, preuve |
| Preuve | `Measurement`, `Evidence`, `QualityTest` | méthode, appareil/labo, valeur, unité, horodatage, niveau de preuve |
| Transformation | `ProcessingUnit`, `CapacityWindow`, `AcceptedInput` | capacité, procédé, compatibilités, contraintes |
| Calcul | `YieldFactorSet`, `YieldFactor`, `EstimateRun`, `EstimateLine` | source, version, plage, formule, entrées, sortie, hash |
| Logistique | `Vehicle`, `Match`, `RoutePlan`, `RouteStop`, `CollectionEvent` | contraintes, distance, coût, statut, solveur/version |
| Traçabilité | `WasteLot`, `TransformationRun`, `ProductBatch` | parent/enfant, masse, pertes, acceptation, provenance |
| Marché | `ProductOffer`, `Order`, `Shipment`, `Settlement` | qualité, quantité, prix, validation humaine |
| Environnement | `EnvironmentalMethodology`, `EnvironmentalEstimate`, `Claim` | périmètre, baseline, version, vérification, statut |
| Gouvernance | `AuditEvent`, `Approval`, `Incident`, `DataCorrection` | acteur, raison, décision, immutabilité logique |

### 7.2 Flux nominal

1. Le producteur crée une déclaration P1 ; la localisation précise est privée.
2. Le moteur de qualité vérifie unités, bornes et champs requis ; les pièces deviennent P2.
3. Le moteur d'estimation sélectionne un jeu de facteurs approuvé et crée un `EstimateRun` immuable.
4. L'appariement filtre par compatibilité et capacité ; le solveur propose une tournée.
5. Le coordinateur valide la tournée ; aucune commande réelle n'est automatique.
6. À la collecte, la pesée crée une mesure P3 et peut recalculer le scénario.
7. L'unité accepte/refuse le lot, puis enregistre la transformation et les produits.
8. Un test de qualité et une validation déterminent les allégations autorisées.
9. Le produit est proposé au client ; toute transaction réelle exige une confirmation.
10. Les événements d'audit relient déclaration, estimation, tournée, lot et produit.

### 7.3 Invariants à imposer

- Les unités sont typées et converties par un service unique.
- Une estimation est immuable ; une correction crée une nouvelle version.
- Un coefficient approuvé ne peut être remplacé sans approbation et historique.
- La somme des lots enfants ne peut dépasser la masse disponible sans écart documenté.
- Un produit ne peut être « certifié » sans preuve P5 liée.
- Une déclaration environnementale publique ne peut être publiée sans méthodologie et approbation.

## 8. Stratégie de sécurité IA et applicative

### 8.1 Menaces propres à BioLoop

- injection indirecte dans une photo, un document, un message ou une description de déchet ;
- manipulation des coefficients pour gonfler rendement ou impact ;
- contamination ou empoisonnement des données d'apprentissage ;
- fuite de coordonnées de sites, données commerciales ou identité des producteurs ;
- outil externe ou modèle mis à jour silencieusement ;
- faux lot, double comptage, pesée modifiée ou preuve réutilisée ;
- automatisation indue d'un paiement, rejet de lot ou allégation environnementale ;
- hallucination d'un assistant transformée en conseil agronomique ;
- accès inter-organisation par défaut d'autorisation ;
- dépendance réseau ou service externe rendant la démo inutilisable.

### 8.2 Contrôles prioritaires

1. **Réduire l'agentivité** : pas d'agent autonome dans le MVP ; outils en lecture seule par défaut.
2. **Valider avant exécution** : schémas stricts, bornes, unités, destinations réseau en liste blanche, taille de fichiers et types MIME.
3. **Moindre privilège** : identité par service/agent, jetons courts, secrets hors code, rôles et séparation lecture/écriture.
4. **Cloisonner** : données, caches et mémoire par organisation ; pas de mémoire conversationnelle partagée.
5. **Contrôler les flux** : classification des GPS, PII, coûts et contrats ; redaction avant logs ou modèle externe.
6. **Gouverner les outils** : inventaire, propriétaire, version épinglée, manifeste, revue des descriptions et détection de dérive.
7. **Approbation humaine non contournable** pour coefficient, paiement, suppression, export externe, allégation ou crédit.
8. **Traçabilité** : corréler demande, paramètres, appel d'outil, résultat, approbation et effet métier ; ne pas enregistrer de raisonnement privé brut.
9. **Tests adversariaux** : injections dans descriptions et pièces, accès horizontal, payloads extrêmes, changement de version et données incohérentes.
10. **Plan d'incident** : couper l'outil, révoquer le jeton, geler le jeu de facteurs/modèle, préserver les preuves et restaurer une version connue.

### 8.3 Usage sûr d'un assistant LLM

- corpus limité à des documents approuvés et versionnés ;
- prompt système précisant que les pièces et pages externes sont des données, pas des instructions ;
- sortie structurée et validation serveur ;
- réponse avec liens vers calculs et sources ;
- interdiction d'inventer un coefficient manquant ;
- bannière « assistance, validation métier requise » ;
- évaluation sur un jeu de questions comprenant refus, ambiguïtés et injections ;
- pas de conseil agronomique personnalisé sans expert et données de qualité.

### 8.4 Feuille de route sécurité inspirée du guide local

| Horizon | Actions BioLoop |
|---|---|
| 0-2 semaines | Inventaire données/outils, classification, menace, rôles, secrets, schémas d'entrée, journal d'audit minimal |
| 2-4 semaines | Versions épinglées, CI sécurité, isolation tenant, approbations, restauration sauvegarde, tests d'accès |
| 4-8 semaines | Télémétrie corrélée, alertes, expurgation des données sensibles, jeux d'attaque, registre modèles/facteurs et rollback |
| 8-12 semaines | Exercice d'incident, rotation automatique, revue de privilèges, surveillance de dérive et audit externe ciblé |

## 9. Gouvernance

### 9.1 Rôles

| Rôle | Responsabilité |
|---|---|
| Product owner/terrain | Problème, priorités, entretiens, partenaire et critères de succès |
| Lead technique | Architecture, qualité, CI/CD, résilience et coûts |
| Responsable données/IA | Provenance, coefficients, baseline, évaluation et registre de modèles |
| Expert biogaz/agronomie | Validation des intrants, procédés, formules, qualité et usages |
| Responsable sécurité/données | Menaces, accès, consentements, rétention, incidents |
| Opérateur du pilote | Validation des tournées, lots, mesures et retours terrain |

Une même personne peut cumuler plusieurs rôles au hackathon, mais les décisions d'approbation sensibles doivent conserver une séparation logique.

### 9.2 Politiques minimales

- registre des sources et coefficients ;
- dictionnaire de données et unités ;
- politique de consentement/localisation ;
- politique de rétention et suppression ;
- gestion des corrections sans effacement de l'historique ;
- procédure d'approbation des modèles et facteurs ;
- registre de composants open source, licences et contributions ;
- critères de communication des chiffres d'impact ;
- procédure d'incident et contact responsable.

### 9.3 Gouvernance des modèles et calculs

Chaque version doit avoir une fiche : objectif, propriétaire, données, formule/modèle, source, métriques, limites, populations ou intrants couverts, date, approbation et condition de retrait. Une baseline par règles simples est obligatoire avant ML. Le modèle doit être rejeté si son gain n'est pas mesurable ou si les données locales sont insuffisantes.

## 10. Observabilité et traçabilité

### 10.1 Télémétrie technique

- traces OpenTelemetry de l'API au solveur et au stockage ;
- logs structurés sans données personnelles brutes ;
- métriques : disponibilité, latence p95, taux d'erreur, échec de synchronisation, durée/échec du solveur, file de tâches et saturation ;
- identifiant de corrélation propagé dans déclaration, estimation, tournée et lot ;
- alertes sur hausse d'erreurs, accès refusés, modifications de coefficients et appels externes inattendus.

### 10.2 Qualité des données et du calcul

- taux de déclarations avec unité valide ;
- part déclaré/mesuré/vérifié ;
- écarts déclaration-pesée ;
- coefficients sans source ou expirés ;
- reproductibilité des estimations ;
- taux de tournées recalculées et raisons ;
- dérive du volume, contamination et rendement observé par type d'intrant.

### 10.3 KPI métier

- tonnes déclarées, collectées et acceptées ;
- coût par tonne acceptée ;
- kilomètres et temps par tonne ;
- taux de contamination/rejet ;
- régularité d'alimentation de l'unité ;
- produits estimés puis mesurés ;
- commandes servies ;
- revenus/coûts répartis et écarts ;
- indicateurs environnementaux uniquement avec formule et niveau de preuve.

## 11. Développement maintenable avec GitHub et harness engineering

### 11.1 Structure de dépôt proposée

```text
apps/
  web/                  # PWA
services/
  api/                  # FastAPI, monolithe modulaire
packages/
  domain/               # Types, unités, invariants
  contracts/            # OpenAPI/JSON Schema
  estimation/           # Formules déterministes
  routing/              # Interface et contraintes OR-Tools
data/
  fixtures/             # Données fictives clairement marquées
  factor_sets/          # Jeux de coefficients versionnés
docs/
  adr/                  # Décisions d'architecture
  threat-model/
  model-cards/
  data-dictionary/
tests/
  unit/
  integration/
  e2e/
  adversarial/
evals/                  # Jeux de référence IA et calcul
infra/                  # Déploiement reproductible
```

### 11.2 Flux GitHub

- `main` protégée, changements par pull request ;
- issues liées à un résultat utilisateur et à des critères d'acceptation ;
- petites PR, revue obligatoire sur calculs, sécurité et migrations ;
- `CODEOWNERS` pour estimation, données, sécurité et infrastructure ;
- modèle de PR : risque, preuve, test, impact données, rollback et capture de démo ;
- ADR pour tout changement de base, modèle de calcul, service externe ou règle de confiance ;
- tags/release notes et artefacts signés pour chaque version de démonstration ;
- registre de propriété intellectuelle et licences.

### 11.3 CI/CD et portes de qualité

1. formatage, lint, types et tests unitaires ;
2. validation OpenAPI/JSON Schema et compatibilité des contrats ;
3. tests d'intégration avec PostgreSQL/PostGIS temporaire ;
4. migration aller et test de restauration ;
5. tests « golden » du moteur d'estimation avec unités et versions ;
6. tests du solveur sur contraintes, cas impossible et reproductibilité ;
7. E2E du parcours principal hors connexion partielle ;
8. recherche de secrets, dépendances vulnérables, SAST, IaC et SBOM ;
9. tests d'autorisation multi-organisation et injections ;
10. construction conteneur/PWA, environnement de prévisualisation et validation manuelle avant production.

### 11.4 Harness engineering

Le harness rend les calculs, modèles et futurs agents contrôlables :

- outils décrits par schémas étroits et versionnés ;
- adaptateurs de services externes remplaçables par des mocks ;
- jeux de fixtures reproductibles ;
- enregistrement/rejeu des appels non sensibles ;
- budgets de temps, taille, coût et nombre d'appels ;
- sandbox réseau/fichiers ;
- feature flags et kill switch ;
- évaluations automatiques avant changement de modèle/prompt ;
- conservation des entrées, versions et sorties nécessaires à l'audit, avec expurgation des données sensibles.

Cette approche évite que l'IA devienne le centre implicite de l'application. Elle reste un composant testable et remplaçable.

## 12. Feuille de route

### Phase 0 - dépôt immédiat (28-31 août 2026)

- confirmer l'équipe, le règlement et les éléments requis ;
- réaliser au moins trois entretiens : producteur, transporteur/unité, agriculteur/client ;
- obtenir une lettre d'intérêt ou un courriel d'un site pilote ;
- finaliser le PDF de 10 pages et la vidéo de 3-5 minutes ;
- montrer une maquette du parcours et une architecture d'une page ;
- déclarer clairement les données simulées et les hypothèses ;
- choisir deux KPI maximum pour le dossier ;
- déposer avant la dernière journée si possible.

### Phase 1 - préparation au prototype (septembre au 4 octobre)

- construire les fixtures : 20 gisements, deux unités, véhicules et coûts ;
- définir les unités, niveaux de preuve et schéma de facteurs ;
- valider un jeu de coefficients avec un expert et ses sources ;
- préparer le mode démo hors ligne et les tests de référence ;
- développer seulement ce que le règlement autorise avant l'épreuve ;
- répéter un pitch de trois et cinq minutes.

### Phase 2 - MVP 48 h

| Temps | Résultat |
|---|---|
| 0-8 h | Squelette exécutable, base, données de démo, déclaration et carte |
| 8-24 h | Estimation versionnée, appariement et première tournée |
| 24-36 h | Lots, preuves, partage de valeur et tableau de bord |
| 36-44 h | Sécurité minimale, tests, mode hors ligne, scénario en trois rôles |
| 44-48 h | Gel fonctionnel, correction, données préchargées, vidéo de secours et répétition |

### Phase 3 - présélection et finale (octobre-novembre)

- remplacer une partie des données fictives par des données autorisées ;
- connecter un site pilote sans dépendance critique pour la démo ;
- mesurer déclaration vs pesée et coût réel de tournée ;
- faire valider les hypothèses de rendement ;
- renforcer isolation, sauvegardes, observabilité et revue de sécurité ;
- préparer l'usage précis du prix : pilote, instrumentation, analyses et accompagnement terrain.

### Phase 4 - pilote 0-3 mois après hackathon

- un bassin compact : un marché ou élevage, un transporteur, une unité ;
- 4 à 8 semaines de données ;
- pesée et preuve de qualité ;
- tableau de bord des coûts et écarts ;
- contrat pilote et responsabilités ;
- décision go/no-go sur l'économie d'une tournée régulière.

### Phase 5 - 3-6 mois

- extension à un bassin agro-industriel ;
- commandes de produits et qualité documentée ;
- intégrations partenaires ;
- modèle prévisionnel seulement si les données le permettent ;
- étude méthodologique environnementale indépendante ;
- passage à une architecture plus distribuée uniquement sur preuves de charge.

## 13. Risques et hypothèses à valider

| Hypothèse/risque | Test prioritaire | Critère de passage |
|---|---|---|
| Le problème est prioritaire localement | 3 à 5 entretiens et coût actuel documenté | Douleur récurrente, décisionnaire et conséquence quantifiée |
| Les volumes déclarés sont disponibles et réguliers | Historique, observation et pesées pilotes | Écart acceptable et fréquence compatible |
| Les déchets sont compatibles | Validation expert et test qualité | Intrants acceptables, contamination maîtrisable |
| La tournée est rentable | Simulation puis une tournée réelle | Coût par tonne inférieur à la valeur créée ou au coût évité |
| Une unité a de la capacité | Lettre d'intérêt et fenêtre de traitement | Capacité, contraintes et interlocuteur confirmés |
| Un acteur paie | Entretien de prix et proposition pilote | Payeur, budget et mode de facturation identifiés |
| Les rendements sont défendables | Revue des facteurs et test sur mesure | Sources, unités, plages et limites approuvées |
| Le produit fertilisant est utilisable | Analyse et avis agronomique/réglementaire | Qualité et allégation autorisée documentées |
| Les données GPS peuvent être collectées | Consentement et minimisation | Finalité, accès et rétention acceptés |
| Le mode faible connexion fonctionne | Test en mode avion et reprise | Saisie, consultation et synchro sans perte |
| Les crédits environnementaux sont pertinents | Étude de méthodologie et MRV | Méthode applicable, données et vérification réalistes |
| L'IA apporte un gain | Baseline règles vs modèle | Amélioration mesurable sans dégradation de sécurité/équité |

### Principaux risques de démonstration

- carte ou API externe indisponible : tuiles/données locales et vidéo ;
- solveur sans solution : expliquer la contrainte bloquante et proposer une tournée pré-calculée ;
- chiffres contestés : ouvrir la fiche de coefficient et afficher l'intervalle ;
- confusion digestat/engrais : employer un vocabulaire conditionnel et montrer l'étape d'analyse ;
- trop de rôles et d'écrans : conserver un parcours central et des comptes de démonstration préconnectés ;
- équipe dispersée : un responsable par parcours, calcul, interface, preuve/pitch et intégration.

## 14. Décisions recommandées

1. Positionner BioLoop comme **système d'exploitation de la chaîne de valorisation**, non comme vendeur de digesteur.
2. Choisir un seul bassin pilote compact et un client ancre.
3. Livrer un moteur de scénarios déterministe et auditable avant tout ML.
4. Séparer visuellement déclaré, estimé, mesuré, vérifié et certifié.
5. Traiter le digestat et l'engrais comme des produits soumis à qualité et règles, non comme une sortie garantie.
6. Garder les crédits environnementaux hors du cœur du MVP.
7. Construire un monolithe modulaire et une PWA résiliente ; ne pas fragmenter l'architecture.
8. Mettre approbation humaine, isolation des organisations et audit dès la première version.
9. Utiliser GitHub comme dossier de preuve : code, décisions, tests, sources, modèles et contributions.
10. Mesurer le succès du pilote par la fiabilité du gisement et le coût par tonne acceptée, pas par le nombre d'écrans ou de fonctions IA.

## 15. Checklist de passage

- [ ] Trois entretiens qualifiés et notes conservées
- [ ] Site pilote, interlocuteur et lettre d'intérêt
- [ ] Payeur et prix pilote hypothétique testés
- [ ] Jeu de données de démonstration marqué comme simulé
- [ ] Sources des coefficients et approbateur identifiés
- [ ] Deux KPI avec formule, unité, baseline et incertitude
- [ ] Parcours exécutable hors connexion partielle
- [ ] Tests golden estimation et tournée
- [ ] Matrice rôles/accès et audit minimal
- [ ] Démo de trois minutes et version cinq minutes répétées
- [ ] Vidéo de secours et données préchargées
- [ ] PDF, vidéo, code, licences et propriété intellectuelle vérifiés
- [ ] Confirmation écrite du règlement sur le code préexistant et la répartition des prix

---

### Références directes

- Classeur local : `SIREXE_Hackathon_2026_10_idees_recherche.xlsx`
- Guide local de sécurité : `AI-Agent-Security-Architecture-Attack-Surface-Defense-ebook.pdf`
- Site officiel : https://hackathon.sirexe.ci/
- Partage Gemini fourni mais non accessible : https://share.gemini.google/Mkoy6PMiG9z0
- Benchmarks BioLoop recensés dans le classeur : Sistema.bio, Bio2Watt/BMW ; étude Applied Energy sur la prévision de méthane pour BioPilot. Ces références sont des points de départ à vérifier et ne constituent pas des facteurs de rendement prêts à l'emploi.
