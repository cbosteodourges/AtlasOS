# ATLAS OS — Rapport de passation
## Santé Connect, application Atlas unifiée, identité visuelle et trajectoire Cloud
**Mise à jour : 7 septembre 2026**

## 1. Point de reprise
- Dépôt : `cbosteodourges/AtlasOS`
- Branche de travail : `health-connect-auto-sync`
- Branche stable préservée : `performance-sync-1.0`
- Handoff de référence : ce fichier.
- Roadmap Cloud : `docs/ATLAS_CLOUD_ROADMAP.md`.
- Serveur local : port **8011** via `scripts/start_atlas_os.ps1`.
- Commande Windows : `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_atlas_os.ps1"`.

## 2. Direction produit
Atlas Connect devient le moteur technique invisible d'une application unique **Atlas**. L'utilisateur touche Atlas et arrive directement dans Atlas OS. Les fonctions Connect doivent rester accessibles dans `Connexions & données` : association téléphone, état Health Connect, permissions, synchronisation et diagnostic.

Architecture locale : `Garmin / Foodvisor -> Santé Connect -> Atlas Android -> Wi-Fi -> Atlas OS PC:8011`.
Architecture cible : `Garmin / Foodvisor -> Santé Connect -> Atlas Android -> HTTPS -> Atlas Cloud 24/7`.

## 3. Health Connect / delta — acquis
- 28 catégories Health Connect autorisées, dénivelé inclus (`READ_ELEVATION_GAINED`).
- Une permission optionnelle absente ne bloque plus toute la synchro.
- Ouverture Atlas -> vérification automatique ; bouton Synchroniser -> même chemin différentiel.
- Aucun changement -> `Atlas à jour · aucune nouvelle donnée` validé.
- `ChangesToken` limité aux types autorisés, recréé si permissions changent, avancé uniquement après confirmation Atlas.
- WorkManager en arrière-plan + verrou contre synchronisations concurrentes.
- `HealthDeltaSync` pour nutrition, sommeil, VFC, FC repos/détaillée, poids/composition, VO2max, SpO2, respiration, température, pression, hydratation, calories, pas, étages, distance, dénivelé, vitesse, cadence et puissance.
- Test réel : chemin `Delta transmis à Atlas` atteint ; bug UI bloqué à 95 % corrigé.
- Dernier chantier : remplacer le fallback complet de `ExerciseSessionRecord` par une relecture ciblée de la séance modifiée et de ses flux.

## 4. Tests terrain suivants
1. Vrai delta Foodvisor/Nutrition.
2. Wellness Garmin du matin : sommeil, VFC, FC repos, etc.
3. Activité Garmin : préserver FC, vitesse, distance, tours/segments, cadence, puissance, dénivelé.
4. Mesurer le nombre réel d'éléments transmis et vérifier leur intégration Atlas.

## 4 bis. Activités libres — stabilisation du 7 septembre 2026
- Commits moteur/interface : `58637fb`, `0b73078`.
- Une activité `matched:false` conserve désormais ses métriques globales dans `activity`, mais ne transporte plus les scores, le nom ni la conformité du candidat rejeté. `automatic_learning_allowed` reste faux.
- Le compte-rendu libre utilise durée, distance, vitesse/allure et FC moyenne/max globales. Les micro-blocs servent uniquement à la chronologie ; une température absente reste « non disponible ».
- Cas de référence `health_connect:8fe6e3b4-d4be-3f4d-a08e-8b8c66afbf90` : dominante attendue récupération/Z1, accélérations réelles de 9 s et 6 s conservées, variation Z2 de 34 s visible mais non structurante, récupération artificielle nulle.
- Randonnée/marche : analyse continue propre au sport, sans zones VMA running ni seuils running. Vélo libre : même compte-rendu descriptif sans score ; le rendu vélo apparié ne référence plus de variables inexistantes.
- Validation automatisée : 53 tests ciblés passent ; 411/412 tests de la suite complète passent. L'unique échec préexistant concerne l'attente UTC du test Garmin CSV simplifié (`08:15Z` attendu, `06:15Z` obtenu), sans lien avec ce chantier. Syntaxe JS, compilation Python et `git diff --check` validés.
- Validation terrain course familiale sur PC : compte-rendu libre correct, dominante Z1 verte, 36:24 / 4,89 km, FC globale 106/144 bpm, deux accélérations et variation Z2 conservées, température absente correctement signalée. Finitions suivantes poussées : suppression de l'onglet « Séance initiale » et formulation « Effort observé » pour les activités libres. Randonnée, vélo et rendu smartphone restent à contrôler.

## 4 ter. Vélo Health Connect — chronologie cardiaque du 7 septembre 2026
- Les tours automatiques restent neutralisés, mais le vélo n'est plus aplati en un unique bloc vert : Atlas reconstruit des segments Z1 à Z5 depuis la série de fréquence cardiaque Health Connect.
- Calcul : réserve cardiaque individuelle lorsque FC repos + FC max sont connues, sinon pourcentage de FC max ; médiane temporelle sur ±15 s et absorption des changements de moins de 30 s. Vitesse, cadence et puissance enrichissent les métriques des blocs sans utiliser la VMA running.
- Le dénivelé Android distingue désormais une vraie valeur nulle d'une donnée absente : aucun `ElevationGainedRecord` associé produit `null`/« Non disponible », plus `0 m`. Les enregistrements de la même source que la séance sont prioritaires pour éviter les doublons inter-applications.
- Schéma de synchronisation Android porté à 8 afin de forcer un backfill d'activité après installation de la nouvelle APK. Santé Connect ne fournit pas ici d'altitude point par point ; Atlas ne peut afficher le dénivelé vélo que si une application publie un `ElevationGainedRecord` dans Santé Connect.
- Validation terrain après recalcul : la sortie vélo de 81 min / 33,8 km est reconstruite depuis les seules données Health Connect, avec 192 m de dénivelé retrouvé et des passages Z1 à Z4 visibles. Une hystérésis de 3 points d'intensité stabilise désormais les oscillations autour des frontières de zones sans effacer les bosses soutenues. Aucun FIT ni import Garmin direct n'a été utilisé pour ce test.

## 5. Stockage / performance
- Avant compactage : **173249 records / 68,1 Mio**.
- Après : **52457 records / 24,6 Mio**.
- Sauvegarde : `health-connect-wellness.backup-before-compact-20260906-155637.json`.
- Cause : séries FC dupliquées par fenêtres de synchro chevauchantes.
- Ingest serveur sérialisé + retries OneDrive.
- Avant Cloud multi-utilisateur : migrer les gros JSON mutables vers un stockage transactionnel.

## 6. Application Atlas unifiée
- `AtlasWebActivity` est le launcher Android ; libellé application : **Atlas**.
- Atlas OS s'ouvre directement dans WebView interne ; plus d'IP à ouvrir manuellement dans Chrome.
- `MainActivity` reste l'écran technique Connect / Health Connect.
- Prochaine UX : carte Atlas Connect dans `Connexions & données` avec état Connecté, dernière synchro, Synchroniser maintenant, Autorisations, Paramètres/diagnostic.

## 7. Identité visuelle Atlas
### Icône
Visuel retenu : cercle/liseré blanc, A Atlas, avatar biomécanique central, homme à gauche, femme à droite, mot ATLAS.

**Règle : ne pas recréer artistiquement une autre icône pour un problème de cadrage.** Android utilise une icône adaptative (`ic_launcher`, `ic_launcher_round`). Le foreground pré-paddé `atlas_logo_foreground_safe.png` sert à préserver le visuel complet dans la safe zone. Ajuster seulement le cadrage/padding si nécessaire. Même identité souhaitée sur Windows via `.ico`.

### Fonds / branding
Assets officiels à réutiliser pour application, plateforme, site et supports :
- `assets/branding/atlas-wallpaper-mobile.png` : version sombre mobile, poussée sur GitHub et validée visuellement sur smartphone ;
- `assets/branding/atlas-wallpaper-mobile-white.png` : variante blanche si présente sur la branche après push local utilisateur.

Le fond sombre a été dimensionné verticalement pour conserver cercle, avatar, coureurs et ATLAS visibles sur l'écran d'accueil.

## 8. Atlas Cloud 24/7
Voir `docs/ATLAS_CLOUD_ROADMAP.md`.
Objectif : PC personnel éteint -> Atlas Android envoie quand même les deltas par Internet -> Cloud traite -> Atlas est déjà à jour à l'ouverture.

Avant Cloud : stabiliser delta, activité delta riche, stockage transactionnel, séparation utilisateurs/appareils/tokens, HTTPS, rotation/révocation tokens, rate limiting, logs, sauvegardes, exigences RGPD/hébergement adaptées.

## 9. Ordre de reprise recommandé
1. Terminer uniquement le cadrage Android de l'icône existante puis l'utiliser sous Windows, sans recréer l'image.
2. Intégrer Atlas Connect dans `Connexions & données`.
3. Valider les vrais deltas Foodvisor, Wellness Garmin et activité Garmin.
4. Supprimer le dernier fallback complet des activités et ne relire que la séance modifiée et ses flux.
5. Stabiliser/tester avant fusion vers `performance-sync-1.0`.
6. Préparer Atlas Cloud 24/7.

## 10. Artefacts locaux à ne pas commiter sans décision explicite
- `src/performance/__pycache__/models.cpython-314.pyc`
- `app/atlas-hub.html.backup-20260825-223028`
- `app/css/atlas-health.css.backup-20260825-223028`
- `health-connect-seance-2026-08-31.json`
- `health-connect-seance-2026-09-01.json`

## 11. Méthode de collaboration / continuité entre chats
- Si GitHub permet une modification directe et que les informations suffisent : modifier avant de répondre.
- Ne pas demander `continue` à chaque étape.
- Ne pas générer une nouvelle image lorsqu'il s'agit seulement d'intégrer/cadrer un visuel existant.
- Préserver la branche stable ; pas de `push --force`.
- Plusieurs chats ChatGPT peuvent concerner Atlas. **GitHub est la source de vérité inter-chat.**
- Pour reprendre depuis n'importe quel nouveau chat : `Reprends AtlasOS depuis la branche health-connect-auto-sync. Lis docs/HANDOFF_ATLAS_2026-09-06_HEALTH_CONNECT_APP.md puis docs/ATLAS_CLOUD_ROADMAP.md et vérifie l'état GitHub actuel avant toute modification.`
