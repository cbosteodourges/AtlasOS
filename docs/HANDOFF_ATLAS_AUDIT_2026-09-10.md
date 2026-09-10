# AtlasOS — reprise de l’audit, 10 septembre 2026

## Référence et limites de cette phase

Branche de travail : `health-connect-auto-sync`. Point de restauration distant vérifié : `backup/atlas-pre-audit-2026-09-10-305088f`, commit `305088f69b6c67807f052a6361fb3e5438d82ffe`, arbre `d624048772b286e15ac4f618322e7f572c567bd8`.

Aucun `AGENTS.md` trouvé dans le dépôt ou les parents de travail vérifiés. Documents consultés : handoff du 6 septembre (contenu mis à jour le 8), roadmap Cloud et `ATLAS_SANTE_FINALITE_MDR.md`. Ce dernier existe : il s’agit d’un cadrage, pas d’une validation réglementaire.

Aucun calcul, endpoint, synchronisation Android, plan, seuil ou écran de production modifié. Aucun accès au PC ou au stockage Android. Aucune fusion vers une autre branche.

Le dépôt étant public, le rapport détaillé de sécurité et sa reproduction ont été remis séparément. Aucun secret ni aucune donnée de santé réelle n’a été ajouté à ce lot.

## Livrables

- `docs/ATLAS_SAUVEGARDE_AVANT_AUDIT_2026-09-10.md` : couverture, export navigateur, procédure Windows et réversion ciblée.
- `scripts/backup_atlas_before_audit.ps1` : copie privée complète et vérification SHA-256. Préparé, non exécuté sous Windows.
- `prototype/atlas-audit-2026-09-10.html` : aperçu autonome avec données fictives et aucun accès réseau/stockage applicatif ; modes PC, tablette et mobile.
- `scripts/audit_atlas_health_baseline.cjs` : deux reproductions isolées sur fonctions exactes du code Santé.
- Rapport détaillé privé remis à Christophe : `AtlasOS_Audit_2026-09-10.md`.

## Constats prioritaires

| Priorité | Sujet | Statut |
|---|---|---|
| P0 | Contrôle d’accès du serveur et exposition potentielle de fichiers | Défaut reproduit avec fichiers factices ; détails dans le rapport privé. Correctif dédié à préparer avant ouverture réseau élargie. |
| P1 | Durée observée remplacée par la durée prescrite | Reproduit : 150 s deviennent 180 s, récupération 132 s devient 120 s, distance recalculée sur cette durée. Ne pas corriger sans validation du contrat de données et des tests. |
| P1 | Santé ne lit pas la date d’activité fournie par l’API | Reproduit : `start_time` au niveau racine n’est pas lu par `executionDate`. |
| P1 | Un signalement résolu peut redevenir actif | Reproduit : une ancienne clé v1 relue après résolution écrase l’état canonique. Migration/suppression des données à valider et sauvegarder avant correction. |
| P1 | Accueil : texte « Aucune alerte importante » fixe | Présent dans le HTML, aucun raccordement retrouvé aux déclarations Santé. |
| P1 | Santé Connect : activité modifiée et suppressions dans le même delta | La branche de reconstruction ne transmet pas la liste des suppressions, puis avance le jeton. Analyse statique ; scénario Android à tester. |
| P2 | Référence de charge sur historique incomplet | Diviseur fixe de cinq semaines ; dates futures non exclues ; API plafonnée à 100 alors que Santé demande 200. |
| P2 | Santé : scores et conseils historiques | Pondérations et seuils codés sans dossier de validation identifié ; ne pas les réactiver comme modèle clinique. |
| P2 | Performances du plan | Benchmark synthétique : médiane 0,0915 s pour 100 séances, 2,2735 s pour 500 ; durée réelle d’ouverture PC inconnue. |

## Ce qui a été réellement vérifié

- Git : état propre à la référence, intégrité des objets, bundle complet vérifié, restauration sur une copie isolée avec même commit et même arbre.
- Python **3.12.14 sur Linux** : `python3 -m unittest discover -s tests` : **458 tests, tous réussis**. Une sélection initiale de 71 tests avait également réussi ; il ne faut pas additionner les deux chiffres, les 71 sont inclus dans la suite.
- Cas automatisés existants : six fractions de 3 min, récupérations, sources Garmin/Santé Connect, dénivelé absent, historique physiologique et exclusion des reconstructions rétrospectives VO₂max/VMA.
- Le SDK Garmin FIT n’est pas installé ici : les tests de décodage utilisent des doubles ; aucune archive réelle ni aucun FIT de Christophe n’a été décodé pendant cette phase.
- Prototype : syntaxe JavaScript et intégrité statique vérifiées. Aucun asset externe, identifiants HTML initiaux uniques, réseau désactivé par CSP, aucun accès au stockage d’Atlas.
- **Non vérifié** : rendu dans Chromium ou WebKit, cibles tactiles réelles, zoom/contrastes mesurés, captures avant/après, Android, iPhone, iPad, Python 3.14, Windows/PowerShell, données privées, dernière activité réelle et export complet Garmin en attente.

Le chemin de prévisualisation géré disponible ne prend pas en charge ce fichier HTML autonome sans serveur de développement compatible. Aucun remplacement technologique n’a été introduit pour contourner cette limite. Les boutons PC/tablette/mobile ajustent la largeur de la maquette ; ce n’est pas un test matériel ou une émulation Safari.

## Direction visuelle à valider séparément

Aujourd’hui : récupération, ressenti distinct et prochaine séance ; sources/dates au second niveau. Compte rendu : réalisé, chronologie proportionnelle, conclusions et action suivante ; fractions non réalisées hachurées hors de l’axe du réalisé. Santé : Charge et contraintes / Douleurs et ressenti / Prévention. Signalements fictifs multirégions, suppression annulable, export fictif et avatar Atlas existant utilisé comme simple repère régional.

Conserver dans la version complète les accès Profil et disponibilités, Historique et Connexions & données : ils ne sont pas développés dans cette maquette limitée aux vues demandées. L’entrée Plan du prototype sert à vérifier le sens du retour depuis un compte rendu.

## Reprise : ordre des prochains lots

1. Confirmer la sauvegarde privée du PC et inventorier ce qui reste propre à Android/WebView. Aucun changement de stockage avant cette étape.
2. Traiter le contrôle d’accès serveur dans un lot indépendant avec tests négatifs et compatibilité des lectures légitimes. Ne pas limiter arbitrairement à loopback : cela casserait Android.
3. Faire valider la direction visuelle Aujourd’hui/compte rendu puis celle de Santé, indépendamment.
4. Proposer le contrat de données des fractions : `observed`, `reconstructed`, `planned`, incertitude, bornes temporelles cohérentes. Corriger les tests qui imposent actuellement le remplacement de l’observé.
5. Définir une migration idempotente des douleurs et des suppressions, avec restauration testée sur copie et conservation de l’historique.
6. Corriger/tester le delta Android mixte, les modifications anciennes hors fenêtre de lecture et les erreurs de lecture des types autorisés.
7. Faire les tests de rendu, d’accessibilité et de performance sur données synthétiques comparables puis sur le PC, avec accord approprié pour les données privées.
8. Valider les sources scientifiques et les fonctions Santé avant tout conseil personnalisé ou activation de nouvelles règles ; vérifier les droits d’usage avant diffusion de nouveaux assets.

Attentes explicitement prévues par le brief : sauvegarde privée avant opération susceptible de la modifier ; validation de la direction visuelle avant généralisation ; validation spécifique avant changements de calcul, de données ou de règles biomécaniques.

## Retour visuel de Christophe — variante mixte

La première proposition a trop atténué l’identité Atlas. La demande est de conserver la navigation simple tout en retrouvant l’avatar, les jauges colorées et le profil de l’athlète.

Nouvel aperçu autonome : `prototype/atlas-audit-mixte-2026-09-10.html`. La première maquette reste inchangée pour comparaison ; référence avant ce lot : `601ccc00c43003721d2d347ebd769039a4bdf516`.

- Aujourd’hui : avatar Atlas existant de corps entier, indice de récupération avec cadran et jauge colorée, prochaine séance, ressenti et quatre cadrans physiologiques.
- Profil : accès direct dans la navigation, avatar, pratique de l’exemple, cinq repères (VO₂max, VMA, SV1, SV2, FC maximale), quatre filières colorées et historique VO₂max.
- Cadrans cliquables : source, date, statut et explication dans une fenêtre refermable. Le contour des repères physiologiques ne représente pas une capacité normalisée inventée.
- Filières Z2, tempo, SV2 et VO₂max : les barres décrivent des durées fictives classées, et les flèches leur évolution entre deux périodes de 28 jours ; elles ne prouvent pas une progression physiologique.
- Navigation principale : Aujourd’hui / Profil / Plan / Santé. Le compte rendu s’ouvre depuis une séance et conserve le retour vers Aujourd’hui ou le plan.
- Mobile : avatar visible dans une carte compacte, navigation avec libellés et cadrans sur deux colonnes. Tablette et PC conservent davantage de largeur.

Vérifications effectuées : syntaxe JavaScript, structure HTML initiale et produite pour Aujourd’hui/Profil, identifiants uniques, avatar et quatre/cinq cadrans, quatre filières, conservation des scénarios du compte rendu (53 min pour 6 fractions, 43 min pour 4), absence d’appels réseau/stockage, premier prototype inchangé. Aucun navigateur ou appareil réel testé pendant ce lot ; les contrôles de largeur de l’aperçu ne constituent pas une validation de compatibilité.

Ce lot ne corrige pas les défauts du moteur relevés dans l’audit. Il modifie uniquement la proposition visuelle isolée, sans toucher aux écrans actifs, calculs, données, seuils, plan ou synchronisations. La validation visuelle et les confirmations de sauvegarde prévues dans le brief restent distinctes.
