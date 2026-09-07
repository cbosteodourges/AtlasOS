# Atlas Santé — Finalité prévue et frontière réglementaire MDR

**Date de cadrage initial : 7 septembre 2026**
**Statut : document directeur produit — à réévaluer avant toute diffusion publique**

## 1. Pourquoi ce document existe
Ce document fixe la direction du module **Atlas Santé** afin que son développement reste cohérent avec la vocation première d’Atlas : entraînement, performance, prévention sportive et gestion prudente des contraintes ressenties par l’utilisateur.

Il doit servir de garde-fou pendant le développement : une nouvelle fonction Santé ne doit pas être ajoutée uniquement parce qu’elle est techniquement possible. Il faut d’abord vérifier qu’elle ne transforme pas involontairement Atlas en logiciel revendiquant une finalité médicale.

## 2. MDR : définition
**MDR** signifie **Medical Device Regulation**, c’est-à-dire le **Règlement (UE) 2017/745 relatif aux dispositifs médicaux**.

Un logiciel peut entrer dans le champ des dispositifs médicaux si sa finalité prévue est notamment le diagnostic, la prévention, la surveillance, la prédiction, le pronostic, le traitement ou l’atténuation d’une maladie ou d’une blessure. Pour les logiciels, le cadrage européen pertinent comprend notamment le guide **MDCG 2019-11 Rev.1 (juin 2025)** relatif à la qualification et à la classification des logiciels.

La présence d’un avertissement du type « ceci ne remplace pas un avis médical » ne suffit pas à elle seule à exclure le MDR : il faut regarder la finalité revendiquée et ce que le logiciel fait réellement.

## 3. Finalité prévue proposée pour Atlas Santé
> **Atlas Santé est un module d’accompagnement de l’entraînement sportif permettant à l’utilisateur de signaler des gênes, douleurs et contraintes ressenties, d’en suivre l’évolution et de permettre au moteur Atlas d’en tenir compte de manière prudente dans l’organisation et l’adaptation de l’entraînement. Il fournit des informations générales d’anatomie, de mobilité, de renforcement, de récupération et de prévention sportive. Atlas Santé n’a pas pour finalité de diagnostiquer une pathologie, d’identifier la cause médicale d’un symptôme, de prescrire un traitement ou de remplacer l’évaluation d’un professionnel de santé.**

Cette formulation est une base de travail et devra faire l’objet d’une validation réglementaire/juridique avant commercialisation.

## 4. Fonctions prévues — première architecture

### 4.1 Carte anatomique interactive
Créer des illustrations **originales Atlas** : silhouette face/dos et vues régionales utiles à la course à pied (bassin/hanche, cuisse, genou, jambe, cheville/pied, rachis, etc.).

L’utilisateur peut toucher une région et signaler une gêne ou douleur. La carte enregistre une **localisation**, pas un diagnostic.

Exemple : `genou_droit_lateral`, et non `syndrome_bandelette_ilio_tibiale`.

### 4.2 Caractérisation de la gêne
Informations envisageables :
- intensité 0–10 ;
- côté et localisation ;
- apparition pendant, après ou indépendamment de l’entraînement ;
- ancienneté ;
- évolution ;
- gêne pendant certaines activités simples ;
- suivi à J+1/J+2 et dans le temps.

Ces informations alimentent l’état sportif courant et la gestion de charge.

### 4.3 Interaction avec le moteur central Atlas
Le moteur peut croiser la gêne déclarée avec les données d’entraînement déjà connues : charge récente, volume, intensité, séances rapides, dénivelé, historique d’entraînement, etc.

Finalité : **adapter les contraintes de l’entraînement**, pas déterminer la pathologie responsable.

Actions envisageables : diminution prudente d’une contrainte, substitution ou déplacement d’une séance, récupération supplémentaire, surveillance de l’évolution, retour progressif à la charge habituelle.

### 4.4 Suivi longitudinal
Conserver l’historique de la gêne et permettre une représentation de son évolution en parallèle de la charge d’entraînement. À terme, Atlas peut mettre en évidence des associations temporelles avec des changements de charge ou de pratique, sans les présenter comme une causalité ou un diagnostic médical.

### 4.5 Conseils généraux et exercices
Bibliothèque Atlas de contenus originaux : mobilité générale, renforcement musculaire, contrôle moteur, récupération, préparation à l’effort.

Les exercices doivent être présentés comme des contenus généraux liés à l’activité sportive et à la région concernée, et non comme le « traitement personnalisé » d’une pathologie diagnostiquée par Atlas.

Prévoir des illustrations/animations/vidéos Atlas originales.

### 4.6 Signaux d’alerte et orientation
Atlas doit pouvoir interrompre son conseil sportif lorsqu’une situation déclarée dépasse son cadre et recommander une évaluation par un professionnel de santé.

Objectif : **orienter sans diagnostiquer**.

Les critères exacts et leur formulation devront être validés avant mise en production.

## 5. Frontière fonctionnelle à préserver

### Fonctions compatibles avec l’orientation actuelle à étudier/développer
- localisation d’une gêne sur une carte anatomique ;
- intensité et évolution rapportées par l’utilisateur ;
- historique des symptômes ressentis ;
- mise en relation descriptive avec l’entraînement ;
- adaptation prudente de la charge et du planning sportif ;
- informations anatomiques générales ;
- exercices généraux de mobilité/renforcement/récupération ;
- recommandation de suspendre/adapter l’entraînement et de consulter lorsque la situation sort du cadre d’Atlas.

### Fonctions à ne pas introduire sans nouvelle analyse réglementaire
- annoncer ou probabiliser un diagnostic (« tendinopathie », « syndrome fémoro-patellaire », « fracture de fatigue », etc.) à partir des données utilisateur ;
- identifier automatiquement la cause médicale d’une douleur ;
- proposer un diagnostic différentiel clinique personnalisé ;
- prescrire ou choisir un traitement pour une pathologie identifiée ;
- présenter un programme comme un protocole thérapeutique personnalisé destiné à traiter une lésion/pathologie ;
- revendiquer qu’Atlas prévient, diagnostique, surveille ou traite une maladie/blessure au sens médical sans avoir engagé le cadre réglementaire correspondant.

## 6. CD-ROM d’encyclopédie anatomique récupéré en septembre 2026
Une ancienne encyclopédie d’anatomie humaine sur CD-ROM a été récupérée comme **source de référence et d’étude**. Le CD contient notamment de nombreux fichiers `.PMG` et des ressources anatomiques/multimédias anciennes.

Décision :
- conserver une copie intégrale du CD ;
- analyser techniquement ses ressources et identifier les vues utiles ;
- rechercher les mentions de licence, éditeur, auteurs et copyright ;
- **ne pas considérer qu’une image devient propriété d’Atlas simplement parce qu’elle est modifiée** ;
- ne pas intégrer directement dans le produit distribué des illustrations protégées sans droits suffisants ;
- privilégier la création de représentations anatomiques **originales Atlas**, à partir de connaissances anatomiques et de références multiples.

Vues prioritaires envisagées : corps face/dos, bassin-hanche, cuisse, genou, jambe, cheville-pied, rachis, puis vues musculaires/articulaires pertinentes pour le coureur.

## 7. Architecture produit cible
Flux conceptuel :

`Utilisateur -> carte anatomique -> localisation + intensité + contexte -> moteur central Atlas -> adaptation prudente de l’entraînement -> suivi J+1/J+2 -> retour progressif / conseil général / orientation professionnelle si nécessaire`

La donnée « douleur/gêne » devient ainsi une contrainte supplémentaire du moteur d’entraînement Atlas, au même titre que les informations de récupération et de charge, sans être transformée automatiquement en diagnostic.

## 8. Règle de développement à appliquer à chaque nouvelle fonction Santé
Avant implémentation, répondre à ces questions :
1. Quelle est la finalité exacte de la fonction ?
2. Sert-elle à gérer l’entraînement ou à diagnostiquer/traiter une affection ?
3. Quel résultat est présenté à l’utilisateur ?
4. Le vocabulaire implique-t-il une affirmation médicale ?
5. Une décision thérapeutique individualisée est-elle produite ?
6. Quel serait le risque d’une recommandation erronée ?
7. Faut-il une nouvelle analyse MDR/AI Act/RGPD avant de poursuivre ?

Si une fonction franchit ou approche la frontière médicale, **ne pas l’intégrer automatiquement au produit public** : la mettre en attente pour revue réglementaire.

## 9. Évolution possible à long terme
Atlas pourrait un jour choisir volontairement une finalité de logiciel dispositif médical. Cela constituerait une trajectoire distincte, avec analyse de qualification/classification, gestion des risques, évaluation clinique/performance, documentation technique, conformité MDR et autres obligations applicables.

Ce n’est pas l’objectif de la première version d’Atlas Santé.

## 10. Références réglementaires à conserver dans le dossier projet
- Règlement (UE) 2017/745 relatif aux dispositifs médicaux (MDR).
- Commission européenne / MDCG : **MDCG 2019-11 Rev.1, juin 2025 — Guidance on Qualification and Classification of Software in Regulation (EU) 2017/745 – MDR and Regulation (EU) 2017/746 – IVDR**.
- MDCG 2025-6 : questions/réponses relatives à l’articulation entre MDR/IVDR et AI Act.

**Important :** ce document constitue un cadrage produit et technique, pas un avis juridique. Avant commercialisation du module Santé, faire valider la finalité prévue, les allégations, l’interface et les fonctions effectivement implémentées par une compétence réglementaire adaptée.