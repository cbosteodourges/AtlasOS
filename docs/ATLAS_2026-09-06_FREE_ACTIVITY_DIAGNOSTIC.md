# AtlasOS — diagnostic activités libres du 6 septembre 2026

## Contexte

Branche : `health-connect-auto-sync`.

Ce document conserve le diagnostic réalisé sur les trois activités du dimanche 6 septembre 2026 (vélo de récupération, course familiale, randonnée) et la trajectoire de correction.

## Cas de référence : course familiale

Activité Health Connect : `health_connect:8fe6e3b4-d4be-3f4d-a08e-8b8c66afbf90`.

Données de référence confirmées par Garmin :

- course très facile / récupération, globalement Z1 ;
- durée environ 36 min ;
- distance 4,89 km ;
- FC moyenne Garmin : 105 bpm ;
- FC maximale Garmin : 144 bpm ;
- deux petites accélérations mécaniques volontaires avec la famille, détectées par Atlas sur environ 9 s et 6 s ;
- une variation ponctuelle d'environ 34 s a aussi été détectée, mais elle ne doit pas requalifier la nature globale très facile de la sortie.

## Diagnostic moteur

Le moteur détectait initialement :

- accélération 9 s ;
- longue portion facile transformée à tort en `recovery` ;
- accélération 6 s ;
- nouvelle portion facile transformée à tort en `recovery` ;
- Z2 34 s ;
- fin facile / cool down.

La cause identifiée se trouve dans `DetailedSessionAnalyzer._mark_recoveries()` : toute `acceleration` ouvrait automatiquement un contexte de récupération. Une micro-variation de vitesse suffisait donc à transformer les Z1 suivants en `recovery`.

Un correctif local a été testé : `acceleration` ne déclenche plus à elle seule `recovery_context`; `sv2`, `vma` et `sprint` le déclenchent toujours. Après recalcul du vrai cas :

- `recovery_duration_seconds` passe de 1442 s à 0 ;
- les longues portions faciles redeviennent Z1 ;
- les accélérations de 9 s et 6 s restent détectées ;
- `matched = false` reste correct.

Ce comportement est souhaité : conserver les événements mécaniques réels sans leur donner artificiellement le poids physiologique d'un bloc intense.

## Principe physiologique à conserver

Atlas doit distinguer :

1. **événement instantané observé** (accélération, variation ponctuelle de vitesse ou de FC) ;
2. **zone instantanée** ;
3. **nature physiologique globale de la séance** ;
4. **travail spécifique structurant** d'une séance prescrite.

Une brève incursion dans une autre zone ne doit pas requalifier une sortie globalement Z1. Une accélération courte peut être réelle sans constituer un travail spécifique. La réponse cardiaque peut être retardée : l'absence de hausse instantanée de FC ne doit donc pas supprimer automatiquement une accélération réelle.

Pour qu'une accélération courte devienne un signal physiologique structurant, Atlas pourra ultérieurement combiner durée, vitesse relative à la VMA, répétition du motif et réponse cardiaque pendant/après l'événement.

## Appariement au plan déjà corrigé

Le cas a révélé qu'une activité libre pouvait consommer une séance planifiée du même jour ou du lendemain. Les corrections déjà poussées sur la branche imposent désormais une preuve structurelle plus forte et empêchent une activité libre de valider une séance déplacée sur la seule base date + sport + durée.

Pour la course familiale :

- `sport = running` ;
- `matched = false` ;
- la séance planifiée reste disponible ;
- l'apprentissage automatique ne doit pas utiliser cette fausse association.

## UX calendrier / historique déjà corrigée

Les activités Health Connect sont désormais distinguées : course, randonnée, vélo.

Les activités libres ne doivent plus afficher le score d'exécution d'une prescription non appariée. Le calendrier classe la course familiale et la randonnée comme activités libres Z1 / très légères. La convention visuelle retenue est Z1 récupération = vert.

## Problèmes encore à terminer

### 1. Compte-rendu d'activité libre

Le compte-rendu doit respecter `matched = false` jusqu'au bout :

- titre basé sur le sport réel ;
- aucun score d'exécution de prescription ;
- aucune conformité cible ;
- aucune récupération notée ;
- aucune phrase « écarts par rapport au plan » ;
- aucune notion de « travail spécifique » pour une sortie libre globalement facile ;
- analyse descriptive des données réellement observées.

### 2. FC globale vs micro-bloc

Le compte-rendu affichait environ 135 bpm parce qu'il reprenait la FC du fragment Z2 d'environ 34 s. La référence globale correcte est 105 bpm moyenne / 144 bpm max d'après Garmin.

Le résumé d'une activité libre doit utiliser les métriques globales de l'activité, jamais la moyenne d'un micro-bloc présenté comme « travail spécifique ».

### 3. Activité globale absente dans l'exécution recalculée

Dans le JSON recalculé observé, `activity` était `null` alors que `detailed_analysis` était présent. Il faut comprendre/pérenniser le transport des métriques globales dans le compte-rendu afin que l'UI dispose de durée, distance, vitesse/allure, FC moyenne/max, dénivelé, température, etc.

### 4. Température absente

Une température Health Connect absente/null était convertie en `0 °C` par `Number(null)`. L'UI doit conserver l'absence (`NaN`/null) et afficher « non disponible », jamais 0 °C par défaut.

### 5. Chronologie activité libre

Pour une activité libre, la chronologie ne doit pas reprendre les pseudo-fractions du matcher comme structure prescrite. Elle doit montrer l'effort global et, si utile, les événements ponctuels réels (par exemple les deux accélérations) sans les surpondérer.

### 6. Randonnée

Une randonnée libre doit être analysée comme `hiking`, sans concepts de prescription running : durée, distance, FC, dénivelé, charge et intensité observée sont pertinents ; score d'exécution, cible spécifique et récupération prescrite ne le sont pas.

## Correctif concurrence optional-workouts

Une course concurrente a été identifiée autour de `atlas-coach-optional-workouts.json.tmp` : plusieurs requêtes pouvaient utiliser le même temporaire et provoquer `WinError 2` / `WinError 32`. Une sérialisation par verrou et un temporaire unique par thread ont été ajoutés et validés localement avant commit.

## Règle de sécurité pour la reprise

Ne pas supprimer les accélérations de 9 s et 6 s : elles correspondent à deux accélérations réellement effectuées. Corriger leur **interprétation**, pas leur existence.

Ne pas transformer arbitrairement le fragment de 34 s en séance Z2 structurante. Le conserver comme variation ponctuelle si les données le justifient, tout en maintenant la classification globale récupération/Z1.

Ne pas fusionner vers `performance-sync-1.0` avant validation du cas réel course + randonnée + vélo et des comptes-rendus associés.
