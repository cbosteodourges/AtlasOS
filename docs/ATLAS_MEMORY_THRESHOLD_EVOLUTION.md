# Mémoire Atlas — évolution conjointe de SV1 et SV2

**Décision prise le 4 septembre 2026**  
**Schéma logiciel : `threshold_state_v2`**

## Pourquoi cette évolution existe

Christophe a identifié une limite fondamentale de l'ancien profil par filière :
un coureur qui respecte les allures prescrites par Atlas ne doit pas être classé
en régression simplement parce que son allure d'entraînement reste sous son
seuil. L'adaptation doit être recherchée dans la relation entre charge externe
(principalement la vitesse) et charge interne (principalement la fréquence
cardiaque), puis dans le déplacement réel des points de seuil.

SV1 et SV2 ne sont donc plus considérés comme une vitesse fixe. Chaque seuil est
un état physiologique daté :

```text
seuil = vitesse + fréquence cardiaque + %FCmax + %réserve cardiaque
        + confiance + preuves + date de validation
```

## Références produit étudiées

- Garmin estime le seuil lactique comme un couple allure–fréquence cardiaque et
  peut le détecter automatiquement pendant des efforts soutenus.
- COROS produit simultanément Threshold Pace, Threshold Heart Rate et FCmax,
  puis répercute ces résultats dans les zones et EvoLab.
- Suunto associe un test allure–FC à ZoneSense, qui utilise les intervalles RR
  pour caractériser l'état métabolique du jour.
- Polar utilise la relation vitesse–FC pour le Running Index et privilégie des
  tests structurés pour VMA, VO2max, FCmax et les zones individualisées.

Atlas retient le meilleur de ces approches, avec une exigence supplémentaire :
chaque changement doit être explicable et accompagné de ses preuves.

## Invariants scientifiques

1. Une baisse de FC à vitesse identique indique une amélioration probable de
   l'efficacité cardiovasculaire, pas à elle seule une baisse de la FC de seuil.
2. Une hausse de FC au seuil est favorable seulement si le point de rupture se
   déplace aussi vers une vitesse supérieure, ou si d'autres preuves convergent.
3. Une FC plus haute à vitesse identique peut refléter chaleur, fatigue, dérive
   cardiaque, déshydratation ou récupération insuffisante.
4. Aucun SV1 ou SV2 ne doit être modifié après une seule séance.
5. Les blocs d'échauffement génériques ne servent jamais à estimer directement
   la FC de SV1.
6. L'absence de mesure n'est jamais convertie en zéro.
7. Une projection reste distincte de la référence validée.

## Fonctionnement retenu

Le moteur `heart_rate_speed_profile.py` réalise deux calculs complémentaires :

1. comparaison de la FC récente et historique dans des classes de vitesse de
   0,2 km/h, sur plusieurs séances ;
2. construction de `weekly_threshold_state_profile`, qui produit pour SV1 et
   SV2 une référence actuelle, une projection vitesse–FC, la fraction de FCmax,
   la fraction de réserve cardiaque, une direction et une confiance.

La vitesse projetée vient de l'évolution FC–allure. La FC projetée vient
uniquement de blocs explicitement identifiés près du seuil concerné. Deux
semaines ISO distinctes, utilisables et concordantes sont exigées avant
validation automatique. Une même semaine recalculée plusieurs fois ne compte
jamais comme deux confirmations.

Les variations appliquées lors d'une validation restent bornées à :

- ±0,15 km/h par validation pour SV1 ou SV2 ;
- ±2 bpm par validation pour la fréquence cardiaque correspondante.

## Propagation dans Atlas

Après validation, la nouvelle référence est écrite dans :

- `physiology-longitudinal.json`, avec l'historique hebdomadaire ;
- l'instantané physiologique du programme actif ;
- les bulles de références physiologiques d'« Aujourd'hui » ;
- le bandeau physiologique du menu « Entraînement » ;
- les futurs calculs de zones et les prochaines analyses de séances ;
- les cibles de vitesse et de FC des séances futures concernées, dans une
  limite de ±2 % par révision et sans modifier les séances déjà réalisées.

Le programme conserve son identité et ses séances : aucun doublon n'est créé.
Une projection non confirmée est affichée comme telle mais ne devient pas une
prescription validée.

## Données mémorisées

Le fichier longitudinal conserve :

- `latest_threshold_evolution` ;
- `threshold_evolution_history`, limité à 104 semaines ;
- la référence courante validée ;
- la méthode, la confiance, la direction et les métriques appliquées.

Cette mémoire doit être consultée avant toute future modification de
l'algorithme des seuils. Le terme de recherche recommandé dans le dépôt est
`threshold_state_v2`.

## Calibration d'un nouveau profil

Depuis le 4 septembre 2026, l'accompagnement d'un utilisateur sans historique
est organisé en cinq étapes visibles dans l'onglet « Calibration du profil » :

1. profil provisoire à partir des informations initiales ;
2. programme immédiatement disponible avec une intensité prudente ;
3. calibration progressive pendant 2 à 4 semaines ;
4. actualisation hebdomadaire à partir des tendances exploitables ;
5. profil établi, relié aux zones et aux séances futures.

L'interface compte uniquement les séances FIT qui comportent au moins un bloc
daté avec durée, vitesse et fréquence cardiaque cohérentes. Le profil initial
devient bien étayé à partir de 8 séances exploitables réparties sur 4 semaines,
puis établi à partir de 12 séances et d'au moins 3 filières observées. Ces
repères décrivent la maturité des données ; ils ne remplacent pas les règles de
validation physiologique de `threshold_state_v2`.

La communication publique reste volontairement sobre. Elle peut indiquer :

- « Analyse longitudinale : Atlas observe l'évolution de votre profil au fil
  des entraînements. »
- « Programme connecté au profil : les évolutions confirmées influencent
  automatiquement les prochaines séances. »

Les coefficients, fenêtres d'analyse et règles de validation du moteur ne sont
pas exposés dans l'interface publique.

## Améliorations futures prévues

- intégrer pente, température, vent et surface avec un poids explicite ;
- utiliser les intervalles RR/DFA-alpha1 lorsque les FIT les fournissent de
  manière suffisamment fiable ;
- détecter des points de rupture par régression segmentée sur les séances
  progressives ;
- confronter périodiquement Atlas à un test terrain standardisé ou à une mesure
  laboratoire lactate/ventilatoire ;
- réviser les bornes de validation après un banc d'essai multi-athlètes ;
- expliquer séparément efficacité cardiovasculaire, déplacement du seuil et
  état physiologique du jour.
