# Mémoire Atlas — fusion Wellness multicanal

**Décision confirmée le 5 septembre 2026**

## Hiérarchie des sources

- Garmin FIT reste prioritaire pour la structure et les détails sportifs d'une
  activité.
- Atlas Connect / Health Connect peut fournir les mesures Wellness les plus
  fraîches : sommeil, VFC RMSSD et fréquence cardiaque de repos.
- Garmin Wellness complète l'historique et les champs que Health Connect ne
  transmet pas.

La priorité s'applique champ par champ et par journée. Une mesure Health
Connect plus récente remplace l'ancien affichage du même indicateur ; elle ne
doit jamais effacer un autre indicateur absent de sa source. Une absence n'est
jamais transformée en zéro.

## Propagation obligatoire

Après chaque synchronisation Atlas Connect, les mesures reçues doivent être
cohérentes dans :

1. `health-connect-wellness.json`, qui conserve les données sources ;
2. `atlas-recovery-index.json`, recalculé par la boucle post-synchronisation ;
3. `/api/atlas/wellness-history`, qui alimente les cadres du navigateur ;
4. le module « Aujourd'hui », l'historique et la décision d'entraînement.

L'API agrège les éventuelles mesures multiples de VFC et de FC de repos d'une
même journée, conserve leur provenance `health_connect` et utilise l'indice de
récupération post-synchronisation comme indice Atlas canonique du jour.

## Incident ayant motivé la règle

Le 5 septembre 2026, Atlas Connect avait transmis 767 éléments, dont une VFC
de 70 ms et une fréquence cardiaque de repos de 39 bpm. Le moteur avait reçu
ces données, mais le cadre VFC affichait encore la mesure Garmin du 3 septembre
à 62 ms, car l'API web ne fusionnait alors que le sommeil Health Connect.

Le terme de recherche recommandé dans le dépôt est
`_health_connect_wellness_by_day`.

## Backfill VFC et provenance

Depuis le schéma Atlas Connect 6, les données volumineuses restent relues sur
30 jours lors d'une migration, tandis que sommeil, VFC RMSSD et fréquence
cardiaque de repos disposent d'un backfill ciblé de dix ans. Cela évite de
réexpédier toutes les séries cardiaques tout en récupérant une mesure Garmin
Wellness publiée tardivement dans Santé Connect.

Atlas conserve également le paquet Android d'origine de chaque VFC. L'interface
peut ainsi distinguer « Garmin via Atlas Connect » d'une autre application. Si
Garmin Connect ne publie aucune `HeartRateVariabilityRmssdRecord`, Atlas le dit
explicitement et complète uniquement à partir des archives Garmin Wellness ;
il ne fabrique jamais une valeur.

## Import quotidien de complément Garmin

L'onglet « Connexions & données » accepte une archive Garmin Wellness ZIP dont
le nom contient la journée au format `AAAA-MM-JJ`. Le serveur contrôle le ZIP,
refuse les archives sans fichier FIT, conserve la journée dans
`atlas-data/garmin/wellness-archives`, actualise le cache puis renvoie les
mesures réellement décodées. Cette voie complète Santé Connect lorsque Garmin
n'y publie pas la VFC ; elle ne remplace jamais une mesure Health Connect
présente pour le même champ et la même journée.

## Enrichissement des activités Santé Connect

Depuis le schéma Atlas Connect 7, les séries de fréquence cardiaque, vitesse,
cadence et puissance sont rattachées en priorité à une séance provenant de la
même application. Atlas transmet également le détail disponible des tours et
des segments, ainsi qu'un inventaire de couverture par activité. Cette
couverture permet au moteur de distinguer une analyse reconstruite riche d'un
simple résumé et d'expliquer les limites sans fabriquer les données que Garmin
n'a pas publiées dans Santé Connect.
