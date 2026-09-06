# Atlas Cloud — feuille de route 24/7

## Objectif
Supprimer la dépendance au PC personnel pour la synchronisation Santé Connect. Atlas Connect doit pouvoir transmettre les deltas Garmin, Foodvisor et autres sources Health Connect à Atlas OS à toute heure, en Wi-Fi ou réseau mobile.

## Architecture cible
Garmin / Foodvisor / autres apps -> Santé Connect -> Atlas Connect -> HTTPS Internet -> Atlas Cloud -> stockage / moteur physiologique -> interfaces Atlas.

Le PC personnel devient uniquement un client d'Atlas et peut rester éteint.

## Prérequis avant migration
1. Valider la synchronisation différentielle Health Connect sur données réelles : sommeil/Wellness, nutrition et activités.
2. Finaliser le delta riche des ExerciseSessionRecord sans réimport global.
3. Remplacer progressivement les gros JSON mutables par un stockage transactionnel adapté au multi-utilisateur.
4. Séparer strictement utilisateurs, appareils, tokens et données.
5. Ajouter HTTPS, rotation/révocation des tokens, limites de requêtes, journalisation et sauvegardes.
6. Préparer les exigences RGPD et l'hébergement approprié aux données traitées avant ouverture à des utilisateurs externes.

## Phase Cloud de développement
- VPS Linux isolé de l'environnement local.
- Déploiement reproductible Atlas OS (service + configuration + sauvegarde).
- Domaine/API HTTPS dédié, par exemple api.atlas-performance.fr.
- Environnement de test distinct de la production.
- Atlas Connect configurable entre serveur local et serveur Cloud pendant la migration.
- Test clé : PC personnel éteint, création d'une donnée Santé Connect, transmission automatique au Cloud, puis consultation ultérieure depuis Atlas.

## Phase production
- Base de données transactionnelle et migrations versionnées.
- Authentification utilisateurs et association sécurisée des appareils.
- Chiffrement en transit et protections des données au repos.
- Sauvegardes automatiques et procédure de restauration testée.
- Monitoring, alertes, métriques de synchronisation et reprise idempotente.
- Politique de conservation/suppression/export des données.
- Dimensionnement et montée en charge selon utilisateurs réels.

## Principe de coût
Commencer petit pour le prototype Cloud et dimensionner après mesure réelle. Le moteur delta Health Connect doit rester la voie normale afin de réduire bande passante, stockage, CPU et coût serveur.

## État au 6 septembre 2026
- Ouverture Atlas Connect -> vérification automatique Health Connect : validée.
- Contrôle manuel différentiel : validé.
- 28 catégories Health Connect autorisées sur le téléphone de test.
- Aucun changement -> aucune retransmission : validé.
- Delta direct pour de nombreux records Wellness/Nutrition et flux autonomes : implémenté, validation terrain en cours.
- Worker Android en arrière-plan : installé ; exécution exacte laissée à Android.
- Reprise sûre : le ChangesToken n'est avancé qu'après confirmation Atlas.
- Protection contre synchronisations concurrentes : ajoutée.
- Stockage Wellness compacté de 173249 records / 68.1 Mio à 52457 records / 24.6 Mio avec sauvegarde préalable.
- Serveur local de développement : port 8011 via scripts/start_atlas_os.ps1.

## Prochain jalon
Stabiliser le delta Health Connect, puis réaliser un audit de déploiement Cloud avant tout achat ou migration. La branche stable performance-sync-1.0 reste intacte tant que cette expérimentation n'est pas validée.
