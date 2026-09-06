# ATLAS OS — Rapport de passation
## Santé Connect, application Atlas unifiée et trajectoire Cloud
**Date : 6 septembre 2026**

## 1. Branche et sécurité du travail
- Dépôt : `cbosteodourges/AtlasOS`
- Branche de travail : `health-connect-auto-sync`
- Branche de référence préservée : `performance-sync-1.0`
- Serveur local de développement : **8011** via `scripts/start_atlas_os.ps1`.
- Ne pas lancer directement `tools/atlas_web_server.py` pour le workflow habituel : son port par défaut est 8010.
- Démarrage Windows connu : `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_atlas_os.ps1"`.

## 2. Objectif produit désormais retenu
Atlas Connect ne doit plus être perçu comme une application séparée. L'utilisateur touche une seule icône **Atlas** :
1. le moteur Android Health Connect reste actif en arrière-plan ;
2. Atlas OS s'ouvre directement dans l'application ;
3. les fonctions techniques Connect restent accessibles depuis les réglages / `Connexions & données` : association téléphone, serveur, autorisations Health Connect, synchronisation et diagnostic.

Architecture locale actuelle :
`Garmin / Foodvisor -> Santé Connect -> application Atlas (moteur Connect) -> Wi-Fi -> Atlas OS PC:8011`.

Architecture cible :
`Garmin / Foodvisor -> Santé Connect -> application Atlas -> HTTPS -> Atlas Cloud 24/7`.

## 3. Santé Connect — acquis validés sur téléphone réel
- Association téléphone / serveur Atlas fonctionnelle.
- 28 catégories Health Connect autorisées, dont le dénivelé après correction du manifeste (`READ_ELEVATION_GAINED`).
- Une permission optionnelle manquante ne bloque plus toute la synchronisation.
- Le nom de la permission manquante est affichable.
- Ouverture de l'application -> contrôle automatique Health Connect.
- Bouton `Synchroniser Atlas` -> même chemin différentiel que l'ouverture, et non plus réimport forcé.
- Aucun changement -> `Atlas à jour · aucune nouvelle donnée` validé.
- `ChangesToken` construit uniquement avec les record types réellement autorisés.
- Si les permissions changent, le token est recréé proprement.
- Le token n'est avancé qu'après confirmation de réception par Atlas : principe de reprise après indisponibilité serveur.
- Worker Android / WorkManager installé pour contrôles en arrière-plan ; l'instant exact d'exécution reste géré par Android.
- Verrou de synchronisation ajouté pour éviter les exécutions concurrentes foreground / Worker.

## 4. Delta Health Connect
Un vrai chemin delta a été ajouté (`HealthDeltaSync`).

Records autonomes sérialisables directement : nutrition, sommeil, VFC RMSSD, FC repos, FC détaillée, poids, composition corporelle, VO2max, SpO2, respiration, température, pression artérielle, hydratation, calories, pas, étages, distance, dénivelé, vitesse, cadence et puissance.

Le premier test Foodvisor a initialement provoqué ~446 éléments car un changement de flux d'activité déclenchait le fallback complet. La logique a ensuite été resserrée : les flux composants peuvent passer en delta ; seul un `ExerciseSessionRecord` lui-même conserve actuellement le chemin d'enrichissement complet de sécurité.

Un test a ensuite atteint `Delta transmis à Atlas · 95 %`, confirmant l'utilisation effective du nouveau chemin delta. Le blocage visuel à 95 % provenait de callbacks UI asynchrones et a été corrigé. Après réouverture : `Atlas à jour · aucune nouvelle donnée`.

### À valider encore sur données réelles
- prochain repas Foodvisor : vérifier le nombre exact d'éléments transmis ;
- prochain Wellness nocturne Garmin : sommeil, VFC, FC repos et autres deltas ;
- prochaine activité Garmin : vérifier que l'activité complète reste riche (FC, vitesse, distance, tours/segments, puissance/cadence/dénivelé) sans réimport global inutile ;
- migrer ensuite `ExerciseSessionRecord` vers un delta riche ciblé de séance.

## 5. Stockage Wellness et performance
Ancien `health-connect-wellness.json` : **173 249 records / 68,1 Mio**.
Après outil de compactage : **52 457 records / 24,6 Mio**.
Sauvegarde créée avant compactage : `health-connect-wellness.backup-before-compact-20260906-155637.json`.

Cause identifiée : accumulation de séries FC dont les IDs dépendaient de fenêtres de synchronisation se chevauchant.

Le serveur dispose également d'une sérialisation d'ingest protégée et de retries contre certains `PermissionError` temporaires OneDrive.

### Trajectoire stockage
Ne pas conserver à long terme de gros JSON mutables comme architecture multi-utilisateur. Préparer un stockage transactionnel / base de données avant Atlas Cloud public.

## 6. Application Atlas unifiée Android
`AtlasWebActivity` a été ajoutée et est devenue le launcher Android.
- Libellé application : **Atlas**.
- Lancement -> Atlas OS directement dans une WebView interne.
- L'utilisateur n'a plus à ouvrir Atlas Connect puis saisir/ouvrir l'IP dans Chrome.
- L'écran technique `MainActivity` reste présent pour Connect / Santé Connect.
- Objectif UX suivant : intégrer explicitement les commandes Connect dans la page Atlas OS `Connexions & données` : état connecté, dernière synchro, synchroniser, autorisations, paramètres/diagnostic.

Si le serveur local est indisponible, l'application doit informer que les données Health Connect restent en attente ; le futur Cloud supprimera la dépendance au PC local.

## 7. Icône Atlas
Décision visuelle : utiliser l'image fournie par l'utilisateur avec :
- cercle/liseré blanc ;
- A Atlas ;
- avatar biomécanique central ;
- personnage masculin à gauche ;
- personnage féminin à droite ;
- mot ATLAS.

Important : **ne plus générer artistiquement une autre icône sans demande explicite**. Le problème restant est uniquement l'intégration/cadrage Android.

Une icône adaptative Android a été introduite (`ic_launcher`, `ic_launcher_round`, foreground/background). Les premières tentatives ont trop zoomé/coupé les personnages. Un foreground pré-paddé `atlas_logo_foreground_safe.png` a ensuite été préparé avec marge transparente et référencé par `atlas_icon_foreground.xml`. Le dernier état a été poussé sur la branche ; rendu final à vérifier après build/install. Si le cadrage reste incorrect, ajuster uniquement la proportion/marge du foreground existant, sans modifier le visuel source.

Pour Windows, un `.ico` correspondant au même visuel a été préparé côté conversation ; objectif : même identité téléphone + PC.

## 8. Atlas Cloud 24/7
Roadmap détaillée déjà enregistrée dans `docs/ATLAS_CLOUD_ROADMAP.md`.

Objectif : le PC personnel ne doit plus être nécessaire pour recevoir les données. Le téléphone transmettra les deltas en Wi-Fi/4G/5G vers un serveur Atlas disponible en permanence.

Avant achat/migration :
1. stabiliser le delta réel ;
2. delta riche des activités ;
3. stockage transactionnel ;
4. séparation utilisateurs/appareils/tokens ;
5. HTTPS, révocation/rotation tokens, rate limiting, logs, sauvegardes ;
6. exigences RGPD/hébergement adaptées avant utilisateurs externes ;
7. environnement Cloud de test distinct de la production.

Test Cloud de référence futur : **PC personnel éteint -> nouvelle donnée Health Connect -> transmission automatique au Cloud -> Atlas déjà à jour à la prochaine ouverture.**

## 9. Priorités du prochain chat
### Priorité A — finir l'icône
Compiler/installer le dernier foreground safe et contrôler visuellement : cercle/liseré complet + homme + femme + A + avatar. Ajuster seulement le padding si nécessaire. Puis appliquer le même visuel au raccourci Windows.

### Priorité B — centre Connect dans `Connexions & données`
Transformer la carte Atlas Connect existante en centre de connexion : `Connecté`, statut Health Connect, dernière synchro, `Synchroniser maintenant`, `Autorisations Santé Connect`, `Paramètres de connexion / diagnostic`.

### Priorité C — validation terrain du delta
Utiliser les prochains événements naturels Foodvisor, Wellness Garmin et activité Garmin. Mesurer le nombre de changements réellement transmis et vérifier les données finales dans Atlas.

### Priorité D — activité delta riche
Éliminer le dernier fallback `ExerciseSessionRecord -> HealthSync complet` en relisant uniquement la séance modifiée et ses flux temporels associés.

### Priorité E — stabilisation et fusion
Une fois les tests concluants : tests automatisés, audit des changements de branche, nettoyage des artefacts locaux non suivis, puis stratégie de fusion vers `performance-sync-1.0` sans toucher au site ostéopathie.

### Priorité F — Cloud
Après stabilisation locale, audit de déploiement et choix du premier environnement Atlas Cloud de développement.

## 10. Fichiers locaux à ne pas commiter par inadvertance
Des artefacts locaux ont été observés :
- `src/performance/__pycache__/models.cpython-314.pyc`
- `app/atlas-hub.html.backup-20260825-223028`
- `app/css/atlas-health.css.backup-20260825-223028`
- `health-connect-seance-2026-08-31.json`
- `health-connect-seance-2026-09-01.json`

Ils ne doivent pas être ajoutés automatiquement aux commits sans décision explicite.

## 11. Règles de collaboration retenues
- Quand une modification GitHub peut être faite directement et que les informations sont suffisantes : **la faire d'abord**, puis donner les commandes utilisateur nécessaires ; ne pas annoncer simplement qu'elle sera faite.
- Ne pas demander à l'utilisateur de répéter `continue` entre chaque étape exploitable.
- Ne pas générer de nouvelles créations d'images quand la demande concerne uniquement le cadrage/intégration d'un visuel existant.
- Préserver la branche stable et éviter les `push --force`.
