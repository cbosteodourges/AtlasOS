# Importer vos données Garmin dans Atlas

## Méthode la plus rapide

1. Ouvrez Garmin Connect dans un navigateur.
2. Ouvrez **Activités** puis **Toutes les activités**.
3. Sélectionnez **Exporter au format CSV**.
4. Dans Atlas, ouvrez le moteur **Physiologie**.
5. Déposez le CSV dans la zone d’import.

## Autres exports Garmin

Atlas 4.3 détecte également les fichiers `.FIT` et les archives `.ZIP`,
mais leur décodage sera ajouté dans une prochaine version.

## Confidentialité du prototype

Dans cette version, le CSV est lu localement par le navigateur.
Les données normalisées sont conservées dans `localStorage`.
Aucun envoi vers un serveur Atlas n’est effectué.
