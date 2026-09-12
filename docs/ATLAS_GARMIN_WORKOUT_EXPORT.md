# Export des séances Atlas vers Garmin

Atlas dispose désormais d'un format universel de séance (`atlas.workout.v1`)
et d'un premier connecteur Garmin. Le serveur local peut convertir une séance
du programme actif en fichier Garmin FIT valide.

Ce mode local utilise le protocole FIT public et le SDK officiel. Il ne se
connecte pas à Garmin Connect, n'utilise aucun identifiant Garmin et ne dépend
donc pas de l'acceptation de la demande Atlas au Garmin Connect Developer
Program. Il ne doit pas être présenté comme une synchronisation Garmin Connect.

## Utilisation pilote

1. Ouvrir le plan d'entraînement dans Atlas.
2. Ouvrir la séance souhaitée.
3. Si Atlas propose une adaptation, la valider avant l'export.
4. Appuyer sur **Télécharger la séance FIT**.
5. Effectuer ce téléchargement sur le PC, puis relier la montre Garmin au PC
   par USB. Le téléchargement sur smartphone ne transmet pas encore la séance
   à la montre.
6. Copier le fichier `.fit` dans le dossier `GARMIN/NEWFILES` de la montre,
   puis éjecter proprement la montre.
7. Sur la montre, ouvrir Course > Entraînements et sélectionner la séance Atlas.

La séance contient les étapes, répétitions, récupérations et cibles d'allure,
de vitesse ou de fréquence cardiaque disponibles dans le programme Atlas.

## API locale

- `GET /api/atlas-coach/workout-export?workout_id=...&format=json`
  renvoie la séance universelle et précise si la version originale ou adaptée
  a été sélectionnée.
- `GET /api/atlas-coach/workout-export?workout_id=...&format=fit`
  télécharge le fichier Garmin FIT.

## Synchronisation directe à venir

Le connecteur officiel Garmin Training API utilisera la même représentation
universelle. Il supprimera l'étape USB dès que Garmin aura fourni et validé les
identifiants partenaires Atlas. Aucun identifiant Garmin personnel ne doit être
stocké dans le dépôt.
