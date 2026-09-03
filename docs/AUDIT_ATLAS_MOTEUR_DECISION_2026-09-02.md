# AtlasOS — audit et feuille de route vers un moteur de décision physiologique low cost

Date : 2 septembre 2026  
Dépôt : `cbosteodourges/AtlasOS`  
Branche auditée : `performance-sync-1.0`  
Révision auditée : `c447d9f`

## 1. Décision stratégique

Atlas ne doit pas être présenté comme une application de plans moins chère. Sa catégorie cible est :

> Un moteur de décision physiologique pour les coureurs amateurs, capable de comprendre leur réponse individuelle, d'adapter un plan à leur vraie vie et d'expliquer chaque décision, avec ou sans montre et à prix très accessible.

La promesse doit réunir deux dimensions indissociables :

1. **Le corps réel** : entraînement réalisé, profil physiologique, sommeil, récupération, douleur, charge et réponse à 24–72 heures.
2. **La vie réelle** : travail, famille, fatigue, indisponibilité, séance manquée ou déplacée et réorganisation prudente du programme.

Proposition de valeur :

> Atlas transforme chaque séance et chaque imprévu en une décision expliquée pour la suite.

## 2. État technique vérifié

### 2.1 Socle réellement présent

- Prototype web/PWA local et mono-utilisateur.
- Serveur Python et API Atlas.
- Programme actif Norwegian Singles 3+1 pour le semi-marathon de Lille du 25 octobre 2026.
- Générateur de programmes et modèles structurés de séances.
- Analyse des activités FIT et Health Connect normalisées.
- Rapprochement entre séance prévue et activité réalisée.
- Reconstruction et analyse détaillée des fractions, récupérations, vitesses et fréquences cardiaques.
- Profil physiologique continu : VO2max, VMA, SV1, SV2 et FC maximale.
- Ajustements physiologiques bornés, traçables et non appliqués deux fois.
- Historique physiologique par séance, y compris plusieurs changements le même jour.
- Indice Atlas de récupération utilisant les données réellement disponibles.
- Analyse longitudinale des conditions associées aux bonnes et mauvaises séances.
- Saisie et suivi des douleurs, drapeaux rouges et historique corporel.
- Interface Aujourd'hui, Entraînement, Santé et historique des indicateurs.
- Connecteurs et modèle commun multimarques en cours de structuration.

### 2.2 Plan vivant et adaptation à la vraie vie

Cette brique existe déjà et constitue un avantage produit majeur :

- déplacement d'une séance vers une autre date ;
- détection des séances déjà présentes à la date cible ;
- remplacement facultatif d'une séance facile ;
- protection d'au moins un jour entre charges difficiles ;
- rééquilibrage automatique des autres séances difficiles ;
- contrôle aux frontières de deux semaines ;
- prévisualisation des conséquences avant application ;
- confirmation explicite de l'utilisateur ;
- sauvegarde du programme avant modification ;
- annulation et restauration du programme précédent ;
- analyse d'une séance déclarée non effectuée ;
- distinction entre séance clé à préserver et séance complémentaire à ne pas reporter systématiquement.

Le moteur de décision connaît cinq actions : `MAINTAIN`, `REDUCE`, `REPLACE`, `POSTPONE`, `CANCEL`. Il compare l'Indice Atlas, la demande physiologique et biomécanique de la séance et la compatibilité du jour.

### 2.3 Limites actuelles de cette brique

- Le report est mieux implanté côté moteur/API que dans l'expérience calendrier actuelle.
- Les motifs humains ne sont pas encore modélisés avec assez de finesse : manque de temps, travail, garde des enfants, déplacement, mauvaise nuit, fatigue ressentie, maladie, douleur, météo ou contrainte matérielle.
- Les conséquences sont surtout calculées par règles d'espacement ; elles ne replanifient pas encore toute la microstructure selon le stimulus perdu et l'objectif prioritaire.
- La décision quotidienne et le déplacement manuel utilisent des briques proches mais encore distinctes.
- La réorganisation n'évalue pas encore complètement la charge cumulée, la récupération probable, la proximité de la compétition et la valeur physiologique du stimulus.
- L'interface doit montrer clairement : ce qui bouge, ce qui ne bouge pas, le risque évité et l'effet attendu.

### 2.4 Qualité et tests

La suite contient 372 tests : 363 réussissent et 9 échouent lors de l'audit.

Échecs observés :

- 3 autour du module nutrition/navigation ;
- 3 autour de la PWA/navigation ;
- 1 sur l'exposition du report dans le calendrier ;
- 2 sur la normalisation Garmin/historique Garmin.

Plusieurs semblent être des tests non actualisés après des choix d'interface récents. Les deux échecs Garmin et celui du calendrier doivent néanmoins être diagnostiqués avant de poursuivre. La règle de développement doit redevenir : aucune nouvelle phase tant que la suite de référence n'est pas entièrement verte.

## 3. Évaluation de maturité

| Domaine | Maturité | Diagnostic |
|---|---:|---|
| Vision et différenciation | 4/5 | Positionnement distinctif désormais clair. |
| Profil physiologique continu | 3.5/5 | Brique avancée, à valider sur davantage de séances et profils. |
| Analyse séance prévue/réalisée | 4/5 | Une des forces actuelles d'Atlas. |
| Plan vivant / imprévus | 3/5 | Moteur réel présent, UX et raisonnement multi-jours à approfondir. |
| Récupération et sommeil | 3/5 | Fonctionnel mais calibration personnelle encore à fiabiliser. |
| Douleur et santé | 2.5/5 | Saisie et prudence présentes ; boucle automatique avec le plan incomplète. |
| Génération multi-profils route | 2.5/5 | Fondations présentes ; validation systématique à faire. |
| Trail | 1.5/5 | Champs et intentions présents, moteur spécifique non terminé. |
| Sans montre | 2/5 | Déclarations possibles ; enregistrement et calibration simplifiés incomplets. |
| Connecteurs grand public | 2/5 | Health Connect avancé ; industrialisation multimarques incomplète. |
| UX grand public | 2.5/5 | Riche, mais encore complexe et hétérogène. |
| Multi-utilisateur / sécurité | 1/5 | Prototype local ; bloquant absolu avant bêta externe. |
| Paiement / modèle low cost | 1/5 | Prix imaginé, coûts réels et infrastructure non validés. |
| Validation scientifique et clinique | 1.5/5 | Règles prudentes, mais protocole formel de validation à construire. |

## 4. Produit cible minimal

Le premier Atlas commercial ne doit pas tout faire. Il doit parfaitement réussir une boucle centrale :

1. Construire un profil initial avec ou sans montre.
2. Générer un plan adapté à l'objectif et aux disponibilités.
3. Présenter la séance du jour et son objectif physiologique.
4. Importer ou recueillir la séance réellement effectuée.
5. Comparer précisément prescription et réalisation.
6. Recueillir le ressenti et les événements de vie utiles.
7. Observer la réponse immédiate puis à 24–72 heures.
8. Mettre à jour uniquement les connaissances réellement soutenues.
9. Maintenir, réduire, remplacer, reporter ou annuler.
10. Montrer les conséquences avant validation.
11. Expliquer la décision en langage simple.
12. Vérifier ensuite si la décision a produit l'effet recherché.

Tout élément ne renforçant pas cette boucle est secondaire pour la première commercialisation.

## 5. Feuille de route organisée

### Phase 0 — Stabiliser la branche

Objectif : obtenir une base fiable avant toute extension.

- Diagnostiquer et corriger les 9 tests en échec.
- Distinguer régressions produit et attentes de tests obsolètes.
- Vérifier manuellement le report, sa confirmation et son annulation sur PC et Android.
- Tester une séance déplacée sur une journée vide, occupée par une endurance, occupée par une séance clé et à cheval sur deux semaines.
- Geler un jeu de données de référence anonyme pour les tests.
- Documenter les versions des schémas de profil, programme, séance et décision.

Critère de sortie : 372/372 tests réussis et parcours critique reproductible.

### Phase 1 — Unifier le moteur du plan vivant

Objectif : faire des imprévus de la vie une entrée native du moteur.

- Créer un objet `LifeConstraintEvent` avec catégorie, date, durée, sévérité, certitude et commentaire.
- Catégories initiales : temps indisponible, mauvaise nuit, fatigue, travail, famille, déplacement, maladie, douleur, météo et séance manquée.
- Fusionner déplacement manuel, séance manquée et décision physiologique dans un même service de replanification.
- Calculer l'importance de la séance : stimulus, phase, objectif, proximité compétition, répétition possible et coût de récupération.
- Évaluer un horizon de 7 jours, puis vérifier les 14 jours suivants.
- Préserver les séances clés utiles sans vouloir rattraper toute charge perdue.
- Interdire automatiquement les empilements dangereux.
- Générer au moins deux options : report prudent et abandon compensé, lorsque les deux sont valides.
- Expliquer les conséquences de chaque option.

Critère de sortie : Atlas gère correctement une semaine perturbée sans casser la logique du cycle.

### Phase 2 — Fermer la boucle physiologique

Objectif : passer d'indicateurs calculés à un véritable apprentissage individuel.

- Sauvegarder systématiquement le contexte avant séance.
- Mesurer la réponse immédiate, à 24 h, 48 h et 72 h.
- Relier chaque réponse à l'empreinte de la séance source.
- Apprendre séparément tolérance physiologique, musculaire, tendineuse et neuromusculaire.
- Distinguer effet aigu, tendance et changement durable.
- Ajouter un niveau de confiance pour chaque connaissance.
- Ne jamais déduire une causalité d'une observation isolée.
- Évaluer après coup si une réduction, un report ou un remplacement a été bénéfique.
- Produire un journal de décision auditable.

Critère de sortie : Atlas peut expliquer non seulement pourquoi il adapte, mais aussi si ses adaptations précédentes semblent avoir fonctionné.

### Phase 3 — Fiabiliser données et fonctionnement sans montre

Objectif : rendre la valeur Atlas indépendante du matériel.

- Finaliser la synchronisation Health Connect quotidienne manuelle avec progression robuste.
- Fiabiliser sommeil, VFC, FC nocturne/repos et fraîcheur des données.
- Traiter explicitement les données absentes sans les inventer.
- Ajouter la saisie simplifiée d'une activité : durée, distance, RPE, terrain, dénivelé, douleur et ressenti.
- Proposer des tests terrain guidés : demi-Cooper, endurance stable, seuil progressif adapté au niveau.
- Construire une confiance de profil visible et évolutive.
- Garder Garmin, Coros, Suunto, Polar et FIT derrière le même modèle commun.

Critère de sortie : un utilisateur sans montre reçoit un plan cohérent et voit son profil gagner en précision.

### Phase 4 — Valider le générateur sur six profils

Objectif : prouver qu'Atlas n'est pas une projection du profil de Christophe.

- Profil A : débutant, premier 5 km.
- Profil B : débutant régulier, premier 10 km.
- Profil C : intermédiaire, semi-marathon.
- Profil D : confirmé, 10 km performance.
- Profil E : confirmé, marathon.
- Profil F : coureur nature, trail court avec dénivelé.
- Générer pour chacun un plan complet, ses semaines de charge/allègement et ses adaptations.
- Injecter les scénarios : réussite, fatigue, douleur, mauvaise nuit, manque de temps et séance manquée.
- Contrôler progressivité, spécificité, récupération, cohérence biomécanique et affûtage.
- Faire relire les résultats avec l'expertise STAPS, kinésithérapie et physiologie de Christophe.

Critère de sortie : validation documentée des six profils et correction des biais communs.

### Phase 5 — Construire le vrai moteur trail

Objectif : ne pas transposer naïvement un plan route.

- Programmer en durée, effort et terrain plutôt qu'en allure seule.
- Modéliser distance, D+, D-, technicité et alternance course-marche.
- Estimer effort équivalent et charge spécifique des montées.
- Modéliser charge excentrique et dommages musculaires des descentes.
- Apprendre la tolérance musculaire et tendineuse personnelle.
- Allonger la récupération après certaines sorties techniques ou très descendantes.
- Reproduire progressivement le profil de la compétition cible.

Critère de sortie : le profil F obtient des décisions différentes d'un 10 km route à charge cardiovasculaire comparable.

### Phase 6 — Simplifier l'expérience et prouver la valeur

Objectif : cacher la complexité sans cacher les raisons.

- Page Aujourd'hui centrée sur trois questions : comment je suis, que dois-je faire, pourquoi ?
- Écran après séance : prévu, réalisé, appris, décidé.
- Écran d'imprévu : « Ma journée a changé » avec choix rapides.
- Prévisualisation visuelle avant/après de la semaine réorganisée.
- Historique des décisions et possibilité d'annulation.
- Démonstration commerciale interactive avec un scénario réaliste.
- Uniformiser terminologie, navigation et tailles de composants.
- Garder les détails experts accessibles sans les imposer au débutant.

Critère de sortie : un nouveau testeur comprend l'intérêt spécifique d'Atlas en moins de trois minutes.

### Phase 7 — Industrialiser et sécuriser

Objectif : rendre possible une bêta externe réelle.

- Ajouter `athlete_id` à chaque ressource privée.
- Stockage séparé par utilisateur et authentification serveur.
- Tests systématiques d'isolation entre comptes.
- HTTPS, gestion des secrets, chiffrement des sauvegardes et restauration testée.
- Consentement par type de donnée, export et suppression.
- Analyse RGPD des données de santé.
- Relecture médicale des messages Santé et cadrage non diagnostique.
- Surveillance des erreurs, journal d'accès et procédure d'incident.
- Bêta fermée progressive avant ouverture publique.

Critère de sortie : aucune donnée ne peut être lue ou modifiée depuis un autre compte et le cycle de vie des données est maîtrisé.

### Phase 8 — Valider l'économie low cost

Objectif : casser le prix sans rendre le produit déficitaire.

- Mesurer le coût par utilisateur actif : calcul, stockage, synchronisation, IA, support, paiement, sauvegarde et communication.
- Garder les calculs déterministes dans le moteur local/serveur.
- Utiliser l'IA conversationnelle uniquement sur un résumé structuré et pour l'explication, pas pour recalculer les données brutes.
- Définir une limite de coût mensuel par utilisateur.
- Tester trois hypothèses annuelles : 19,99 €, 24,99 € et 29,99 €.
- Prévoir une offre Fondateurs limitée si le coût réel le permet.
- Ne pas appauvrir la boucle centrale dans l'offre payante principale.
- Évaluer les commissions des boutiques et l'intérêt d'une souscription web.

Critère de sortie : marge positive démontrée dans des scénarios de 1 000, 10 000 et 50 000 utilisateurs actifs.

### Phase 9 — Bêta et lancement

Objectif : prouver rétention et confiance avant l'acquisition massive.

- Cohorte 1 : 20 à 30 testeurs fortement suivis.
- Cohorte 2 : 100 à 300 utilisateurs couvrant les six profils.
- Cohorte 3 : 1 000 utilisateurs avec support industrialisé.
- Mesurer activation, première synchronisation réussie, plan accepté, séances analysées, adaptations acceptées/refusées, rétention à 4 et 12 semaines.
- Mesurer les erreurs de décision et les corrections manuelles.
- Recueillir les raisons de départ et le consentement à payer.
- Lancer l'acquisition large uniquement lorsque la boucle centrale est fiable.

## 6. Ordre immédiat des travaux

Les cinq prochains lots doivent être exécutés dans cet ordre :

1. **Rétablir les tests** et vérifier le parcours de report dans le calendrier.
2. **Unifier le plan vivant** autour des contraintes physiologiques et des événements de vie.
3. **Fermer la boucle post-séance à 24–72 h** avec apprentissage de la réponse individuelle.
4. **Créer le banc d'essai des six profils** et corriger le générateur.
5. **Mesurer le coût réel par utilisateur** avant de figer le prix de rupture.

Le trail, la refonte commerciale et le multi-utilisateur suivent, mais la sécurité multi-utilisateur reste un préalable absolu à toute bêta externe.

## 7. Ce qu'Atlas doit éviter

- Devenir un clone moins cher de Campus.
- Refaire le réseau social de Strava.
- Modifier silencieusement le programme.
- Rattraper mécaniquement toutes les séances manquées.
- Faire croire qu'une donnée absente a été mesurée.
- Transformer un score isolé en vérité physiologique.
- Poser un diagnostic médical.
- Promettre le trail avant d'avoir un moteur réellement spécifique.
- Fixer un prix spectaculaire sans connaître le coût d'un utilisateur actif.
- Ouvrir le prototype mono-utilisateur sur Internet.

## 8. Indicateurs de réussite du produit

- Pourcentage de séances correctement rapprochées du programme.
- Pourcentage de séances donnant une analyse exploitable.
- Taux d'acceptation des adaptations proposées.
- Taux d'annulation ou de correction des décisions Atlas.
- Réduction des conflits de calendrier après un report.
- Continuité du plan malgré les imprévus.
- Progression des indicateurs avec confiance suffisante.
- Absence d'augmentation des douleurs actives.
- Rétention à 4, 12 et 24 semaines.
- Coût technique par utilisateur actif.
- Conversion gratuit vers payant et résiliation.

## Conclusion

Atlas possède déjà plusieurs briques rares réunies dans un même prototype : analyse détaillée de la séance réalisée, profil physiologique évolutif, récupération, douleur, décisions explicables et réorganisation prudente du calendrier. Le projet n'est donc plus au stade d'une simple idée de plan adaptatif.

Le chemin critique consiste maintenant à réunir ces briques dans une seule boucle fiable et visible. Le véritable produit n'est ni le plan, ni le score, ni le graphique pris isolément : c'est la décision personnalisée qui permet au coureur amateur de continuer à progresser malgré les variations de son corps et de sa vie.
