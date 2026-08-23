# Feuille de route Atlas — état au 23 août 2026

## Résultat actuel

Atlas dispose d'un programme Norwegian Singles 3+1 validé, d'une analyse FIT et Wellness, d'un historique consultable, d'une expérience PC/smartphone sur le réseau local et d'un accès fondateur intégral. Le prototype reste local et mono-utilisateur : il ne doit pas encore être présenté comme un service grand public hébergé.

## 1. Synchronisation des données

| Source | État réel | Prochaine étape |
| --- | --- | --- |
| Garmin | Opérationnel en import FIT incrémental et Wellness | Stabiliser le traitement en arrière-plan et les messages de progression |
| Sans montre | Opérationnel pour ressenti, douleur et récupération | Ajouter une saisie d'activité simplifiée |
| Strava | Connecteur serveur prêt | Créer l'application Strava, configurer OAuth et tester la révocation |
| Health Connect | Architecture définie | Développer l'application/pont Android et le consentement par type de donnée |
| Polar Flow | Autorisation requise | Demander AccessLink ou prendre en charge l'export utilisateur |
| Suunto | Autorisation partenaire requise | Obtenir l'accès API ou formaliser l'import FIT |
| COROS | Autorisation requise | Obtenir l'accès API ou formaliser FIT/TCX |

Règle produit : une carte fournisseur ne doit jamais afficher « connecté » sans jeton valide, consentement enregistré et première synchronisation vérifiée.

## 2. Contrôle du plan et de l'historique

Le module `plan_history_audit.py` contrôle désormais :

- les séances obligatoires passées sans exécution associée ;
- les doublons d'exécution sur une même séance ;
- les exécutions liées à un ancien programme ;
- la cohérence globale après révision du plan.

À intégrer ensuite à l'API et à une alerte administrateur avant chaque publication de programme. Une révision ne doit jamais effacer l'historique : elle crée une nouvelle version et conserve les identifiants des séances déjà effectuées.

## 3. Santé et douleur du coureur

Le module anatomique 3D existant est conservé. Une sélection directe, plus simple sur smartphone, couvre maintenant le pied, la cheville, la jambe, le genou, le bassin et la région fessière. Les déclarations enregistrent côté, intensité au repos et à l'effort, ancienneté, difficulté à l'appui et commentaire.

Cette fonction est un outil d'orientation et de suivi, pas un diagnostic. Les signaux d'alerte déclenchent une recommandation d'arrêt des impacts et d'avis professionnel. Avant commercialisation, les formulations doivent être relues par un médecin du sport et la protection des données de santé validée juridiquement.

## 4. Parcours utilisateur cible

1. Logo Atlas.
2. Première utilisation uniquement : avatar et consentements.
3. Choix de la source de données ou « sans montre ».
4. Profil initial, disponibilités et éventuel test demi-Cooper.
5. Objectifs A, B et C.
6. Génération du plan avec validation explicite.
7. Page Aujourd'hui à chaque connexion suivante.
8. Import incrémental, compte-rendu, ressenti, récupération puis proposition d'adaptation.
9. Toute adaptation montre les raisons et attend une validation.

À tester avec trois profils : nouvel utilisateur sans montre, nouvel utilisateur avec Garmin, utilisateur existant dont le programme est déjà actif.

## 5. Préparation commerciale

Offre retenue : **Atlas Performance — 6,99 €/mois ou 49,99 €/an**.

- Mensuel : une semaine glissante visible, recalculée selon les données physiologiques, biomécaniques et de récupération.
- Annuel : programme complet visible.
- Fondateur : accès intégral de contrôle.

### Bloquants avant bêta externe

- authentification et séparation stricte par `athlete_id` ;
- hébergement HTTPS, sauvegardes chiffrées et restauration testée ;
- consentement, export et suppression des données ;
- politique de confidentialité, conditions d'utilisation et cadre des données de santé ;
- paiement serveur et webhooks vérifiés ;
- surveillance des erreurs et support ;
- validation clinique des messages Santé ;
- tests d'isolation entre comptes et tests mobiles réels.

### Décisions à prendre avec Christophe

- priorité du premier fournisseur après Garmin ;
- périmètre exact de la bêta et nombre de testeurs ;
- durée de conservation des données FIT, Wellness et douleur ;
- professionnels chargés de la validation médicale et juridique ;
- hébergeur, domaine, solution d'authentification et prestataire de paiement.
