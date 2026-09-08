# Importer vos données Garmin dans Atlas

## Méthode la plus rapide

1. Ouvrez Garmin Connect dans un navigateur.
2. Ouvrez **Activités** puis **Toutes les activités**.
3. Sélectionnez **Exporter au format CSV**.
4. Dans Atlas, ouvrez le moteur **Physiologie**.
5. Déposez le CSV dans la zone d’import.

## Archives Garmin FIT

Le pipeline local Atlas décode désormais récursivement les fichiers `.FIT`.
Avant un premier import massif, auditez le dossier sans modifier les sources :

```powershell
python .\scripts\audit_fit_archive.py --input ".\atlas-data\garmin"
```

Le rapport privé `atlas-data/private/fit-archive-audit.json` indique la période
couverte, les sports, les erreurs éventuelles, les champs physiologiques
réellement présents et le débit de décodage.

L'import incrémental dans Atlas Coach se lance ensuite avec :

```powershell
python .\scripts\sync_atlas_coach_pilot.py --input ".\atlas-data\garmin"
```

Cette commande affiche séparément le temps de décodage et le temps total
d'import, d'analyse et de fusion. Atlas Connect transmet Santé Connect ; les
archives FIT restent une source privée locale importée par ce pipeline.

## Confidentialité du prototype

Dans cette version, le CSV est lu localement par le navigateur.
Les données normalisées sont conservées dans `localStorage`.
Aucun envoi vers un serveur Atlas n’est effectué.
