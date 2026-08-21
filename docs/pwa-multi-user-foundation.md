# Fondation PWA et multi-utilisateur

## PWA

Le manifeste et le service worker installent uniquement le shell Atlas. Les appels `/api/` ne sont jamais mis en cache : un compte rendu, un ressenti ou une adaptation doit toujours provenir du serveur et ne peut pas être remplacé par une ancienne réponse hors ligne.

## Séparation des utilisateurs

La migration multi-utilisateur devra précéder toute ouverture réseau. Chaque ressource privée devra porter un `athlete_id` non vide : profil physiologique, programme, activité Garmin, décision, ressenti et journal de conversation. Le serveur devra dériver cet identifiant d'une session authentifiée et ne jamais l'accepter comme seule preuve dans le corps d'une requête.

Ordre de migration recommandé :

1. ajouter `athlete_id` aux modèles et aux fichiers privés existants ;
2. isoler le stockage dans un dépôt par utilisateur ;
3. ajouter authentification et contrôle d'accès côté serveur ;
4. migrer les données de Christophe ;
5. tester systématiquement l'absence de lecture ou d'écriture croisée ;
6. seulement ensuite exposer Atlas hors de `localhost`.

Cette étape pose l'architecture, sans prétendre que le mode multi-utilisateur est déjà activé.
