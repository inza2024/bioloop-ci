# ADR 0004 — Fondation pilote : comptes, PWA et données enrichies

- Statut : accepté pour le pilote local, non certifié production
- Date : 2026-08-30

## Contexte

Les tranches 01 à 03 démontrent le calcul, la traçabilité et les responsabilités avec des identités fictives sélectionnables. Un pilote mobile exige une identité locale réelle, une reprise réseau limitée et un volume de données P0 plus représentatif, sans transformer le démonstrateur en architecture distribuée ni prétendre fournir une sécurité de production.

## Décision

- Conserver le monolithe modulaire FastAPI et Next.js.
- Ajouter SQLAlchemy 2 et Alembic progressivement : nouvelles tables d'identité/session et colonne d'idempotence, sans supprimer le repository SQLite historique.
- Hacher les mots de passe avec Argon2id et ne stocker que SHA-256 du jeton de session opaque.
- Transporter la session par cookie HttpOnly/SameSite, Secure sous HTTPS ; exiger CSRF et origine sur les mutations authentifiées.
- Autoriser l'auto-inscription active pour producteurs/clients, `pending` pour logistique/unités, et refuser l'auto-attribution de contrôle/coordination.
- Modéliser plusieurs appartenances par utilisateur et contrôler le portail/rôle actif côté serveur.
- Garder le sélecteur d'identités fictives derrière `BIOLOOP_DEMO_IDENTITIES_ENABLED`.
- Installer une PWA dont le service worker ne cache que le shell public et exclut API/portails privés.
- Autoriser hors ligne uniquement la création d'une déclaration P1 dans IndexedDB, avec clé d'idempotence et synchronisation explicite.
- Fournir deux profils P0 : `small` pour la stabilité et `enriched` à graine/version fixes pour le pilote.
- Définir des contrats décisionnels étroits et déterministes ; aucun LLM ou modèle externe.

## Conséquences

Le pilote local dispose d'une attribution serveur, d'une reprise réseau contrôlée et d'un chemin de migration de données. Il ne dispose pas encore de MFA, récupération de compte, administration complète des invitations, stockage objet, antivirus, journal inviolable, PostgreSQL/PostGIS métier complet, sauvegardes pilotées ou supervision de production. Les données synthétiques et toutes les règles décisionnelles de référence restent P0 avec validation humaine.
