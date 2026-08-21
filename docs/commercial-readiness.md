# Préparation commerciale d’Atlas OS

## État actuel

Atlas reste un prototype mono-utilisateur exécuté localement. Il ne possède encore ni comptes clients, ni paiement, ni hébergement de données de santé, ni sauvegarde distante. Une présentation commerciale ne doit pas laisser penser que ces fonctions sont déjà actives.

## Offres de travail à valider

| Fonction | Atlas Coach | Atlas Pro |
|---|---:|---:|
| Prix mensuel envisagé | 3,99 € | 6,99 € |
| Prix annuel envisagé | 29,99 € | 49,99 € |
| Programme et analyse des séances | Oui | Oui |
| Ressenti et adaptation expliquée | Oui | Oui |
| Rapport longitudinal avancé | Synthèse | Complet |
| Export et suivi approfondi | Limité | Étendu |

Ces prix sont des hypothèses produit, pas encore des tarifs publiés. Le contenu exact des deux niveaux doit être stabilisé avant toute communication.

## Passage obligatoire avant une bêta

1. stabiliser le circuit Garmin → analyse → ressenti → adaptation ;
2. créer une identité utilisateur authentifiée et isoler chaque donnée par `athlete_id` ;
3. définir quelles données restent locales et lesquelles sont synchronisées ;
4. chiffrer les échanges, les sauvegardes et les secrets ;
5. réaliser une analyse RGPD spécifique aux données de santé et documenter consentement, durée de conservation, export et suppression ;
6. définir hébergement, stockage, surveillance, support et procédure d’incident ;
7. intégrer Stripe côté serveur avec webhooks vérifiés, sans placer de secret dans l’application ;
8. rédiger CGU, politique de confidentialité, mentions légales et limites médicales avec validation professionnelle ;
9. ouvrir une bêta à un groupe limité avec consentement explicite et canal de retour.

## Modèle de coûts à renseigner

Le seuil de rentabilité devra intégrer, pour chaque formule : TVA applicable, commission de paiement, hébergement, stockage, sauvegardes, e-mails, surveillance, support, comptabilité, assurance et fiscalité. Aucun calcul sérieux n’est possible tant que le volume d’utilisateurs, le pays de vente et l’architecture d’hébergement ne sont pas arrêtés.

## Période d’essai

Une période d’essai peut être envisagée après stabilisation de l’onboarding et des paiements. Elle ne doit pas donner accès à une fausse synchronisation : l’état local, synchronisé ou indisponible doit toujours être visible.
