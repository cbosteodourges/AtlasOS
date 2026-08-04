# ATLAS OS — Vision du moteur Performance

## Objectif central

ATLAS doit devenir un moteur de performance adaptatif capable de comprendre comment chaque utilisateur réagit à l’entraînement, d’identifier les préparations et les séances qui lui réussissent le mieux, puis de proposer et d’ajuster un plan jusqu’à une compétition cible.

Le moteur ne doit pas appliquer un programme générique ni reproduire automatiquement le profil initial de développement.

## Premier profil de validation

Le premier prototype utilise le profil réel de Christophe afin de :

- valider l’import des données ;
- tester les analyses longitudinales ;
- comparer des compétitions réussies et ratées ;
- identifier les séances et enchaînements efficaces ;
- construire le premier plan adaptatif ;
- valider l’interface web.

Ce profil constitue un cas de validation, pas une norme imposée aux futurs utilisateurs.

## Adaptation au niveau de l’utilisateur

ATLAS doit fonctionner pour :

- un débutant ;
- un amateur loisir ;
- un amateur régulier ;
- un compétiteur ;
- un sportif confirmé ;
- un sportif de haut niveau.

Le moteur doit combiner :

- le niveau déclaré ;
- le niveau observé dans l’historique ;
- l’expérience sportive ;
- le volume et la fréquence habituels ;
- les performances ;
- les références physiologiques ;
- la récupération ;
- les contraintes personnelles ;
- la tolérance individuelle à la charge.

ATLAS doit comparer prioritairement l’utilisateur à lui-même.

## Période de préparation dynamique

La durée de préparation ne doit pas être fixée à douze semaines.

ATLAS doit détecter le début réel de la préparation à partir de :

- la reprise après une coupure ;
- l’évolution du volume ;
- la régularité ;
- l’apparition de séances spécifiques ;
- les sorties longues ;
- les blocs de charge ;
- la récupération ;
- l’affûtage final.

Selon l’utilisateur et la compétition, la période pertinente pourra être plus courte ou plus longue.

## Identification des séances efficaces

Chaque séance doit recevoir une empreinte comprenant notamment :

- son type ;
- sa durée, sa distance et son dénivelé ;
- son allure, sa fréquence cardiaque et sa puissance ;
- sa cadence et ses dynamiques de course ;
- son Training Effect ;
- son effort perçu ;
- son ressenti ;
- les conditions environnementales ;
- sa place dans la préparation ;
- la charge accumulée avant la séance ;
- la récupération observée après la séance.

Une séance est efficace si elle produit l’adaptation recherchée avec un coût de fatigue acceptable et sans compromettre les séances suivantes.

## Analyse de la réponse individuelle

ATLAS doit étudier :

### Réponse immédiate

- respect de l’objectif de la séance ;
- difficulté perçue ;
- ressenti ;
- dérive cardiaque ;
- maintien de l’allure et de la puissance.

### Réponse à 24–72 heures

- HRV ;
- fréquence cardiaque au repos ;
- sommeil ;
- Body Battery ;
- fatigue ;
- douleur ;
- capacité à réaliser la séance suivante.

### Effet longitudinal

- amélioration de l’efficacité aérobie ;
- progression sur les séances comparables ;
- tolérance au volume et à l’intensité ;
- réussite ou échec en compétition ;
- apparition de fatigue ou de blessure.

## Comparaison des compétitions

ATLAS doit comparer les préparations réussies et ratées en tenant compte :

- du type et de la distance de compétition ;
- du volume et de la fréquence ;
- des séances spécifiques ;
- des sorties longues ;
- de la récupération ;
- de l’affûtage ;
- du ressenti ;
- de la météo et du terrain ;
- des événements personnels ou médicaux.

Les conclusions doivent présenter un niveau de confiance et distinguer corrélation, hypothèse et causalité probable.

## Plan d’entraînement personnalisé

L’utilisateur doit pouvoir définir :

- une date de compétition ;
- une distance ;
- un type de course ;
- un objectif ;
- ses jours disponibles ;
- ses contraintes ;
- ses douleurs éventuelles.

ATLAS doit calculer une durée de préparation adaptée et générer un plan personnalisé à partir de l’historique et du profil.

## Ajustement continu

Le plan ne doit pas être figé.

Après chaque synchronisation, ATLAS doit pouvoir :

- maintenir la séance suivante ;
- réduire le volume ou l’intensité ;
- remplacer une séance par de la récupération ;
- déplacer une sortie longue ;
- ajouter du repos ;
- prolonger ou raccourcir un bloc ;
- adapter l’affûtage.

Une seule mauvaise donnée ne doit pas provoquer une modification excessive. Les décisions doivent s’appuyer sur plusieurs signaux et sur leur tendance.

## Interface web prioritaire

La première version web doit proposer un parcours simple :

1. importer les données ;
2. analyser l’historique ;
3. visualiser ce qui fonctionne le mieux ;
4. visualiser ce qui fonctionne moins bien ;
5. définir une future compétition ;
6. générer un plan personnalisé ;
7. suivre son adaptation jusqu’à l’objectif.

## Transposabilité

L’architecture doit rester indépendante de Garmin.

Les données provenant de Garmin, Apple Santé, Polar, Coros, Suunto, Strava ou d’autres capteurs doivent être converties vers un modèle commun.

Les données absentes doivent rester facultatives afin de permettre l’évolution vers de nouveaux appareils et de nouveaux capteurs.

## Principe directeur

Toute évolution du moteur Performance ou de son interface doit contribuer à cette boucle :

**profil → historique → réponse individuelle → séances efficaces → plan personnalisé → nouvelles données → adaptation du plan**